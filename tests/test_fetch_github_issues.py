"""Tests for scripts/web_api/fetch_github_issues.py."""
from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.web_api.fetch_github_issues import (
    ISSUES_FIELDS,
    _handle_rate_limit,
    _headers,
    issues_to_rows,
    main,
    parse_args,
)


# ---------------------------------------------------------------------------
# _headers
# ---------------------------------------------------------------------------

class TestHeaders:
    def test_includes_accept_header(self) -> None:
        h = _headers(None)
        assert h.get("Accept") == "application/vnd.github+json"

    def test_no_authorization_without_token(self) -> None:
        h = _headers(None)
        assert "Authorization" not in h

    def test_includes_authorization_with_token(self) -> None:
        h = _headers("mytoken")
        assert h.get("Authorization") == "Bearer mytoken"

    def test_empty_string_token_includes_authorization(self) -> None:
        # An empty string is falsy but we still get the header key
        h = _headers("")
        # _headers only adds Authorization if token is truthy; empty string is falsy
        assert "Authorization" not in h


# ---------------------------------------------------------------------------
# _handle_rate_limit
# ---------------------------------------------------------------------------

class TestHandleRateLimit:
    def test_does_not_sleep_when_remaining_positive(self) -> None:
        resp = MagicMock()
        resp.headers = {"X-RateLimit-Remaining": "10"}
        with patch("scripts.web_api.fetch_github_issues.time.sleep") as mock_sleep:
            _handle_rate_limit(resp)
        mock_sleep.assert_not_called()

    def test_sleeps_when_remaining_zero(self) -> None:
        import time
        resp = MagicMock()
        reset_time = int(time.time()) + 60
        resp.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time),
        }
        with patch("scripts.web_api.fetch_github_issues.time.sleep") as mock_sleep:
            _handle_rate_limit(resp)
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] >= 1

    def test_handles_missing_rate_limit_headers(self) -> None:
        resp = MagicMock()
        resp.headers = {}
        # Should not raise; defaults to remaining=1
        with patch("scripts.web_api.fetch_github_issues.time.sleep") as mock_sleep:
            _handle_rate_limit(resp)
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# issues_to_rows
# ---------------------------------------------------------------------------

class TestIssuesToRows:
    def _make_issue(self, **kwargs) -> dict:
        defaults = {
            "number": 1,
            "title": "Test issue",
            "state": "open",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/1",
            "user": {"login": "octocat"},
        }
        defaults.update(kwargs)
        return defaults

    def test_returns_list_of_dicts(self) -> None:
        rows = issues_to_rows([self._make_issue()])
        assert isinstance(rows, list)
        assert isinstance(rows[0], dict)

    def test_extracts_all_fields(self) -> None:
        issue = self._make_issue()
        row = issues_to_rows([issue])[0]
        assert row["number"] == "1"
        assert row["title"] == "Test issue"
        assert row["state"] == "open"
        assert row["created_at"] == "2024-01-01T00:00:00Z"
        assert row["updated_at"] == "2024-01-02T00:00:00Z"
        assert row["html_url"] == "https://github.com/owner/repo/issues/1"
        assert row["user"] == "octocat"

    def test_handles_missing_user(self) -> None:
        issue = self._make_issue(user=None)
        row = issues_to_rows([issue])[0]
        assert row["user"] == ""

    def test_handles_missing_optional_fields(self) -> None:
        row = issues_to_rows([{}])[0]
        assert row["number"] == ""
        assert row["title"] == ""
        assert row["user"] == ""

    def test_empty_input(self) -> None:
        assert issues_to_rows([]) == []

    def test_multiple_issues(self) -> None:
        issues = [self._make_issue(number=i, title=f"Issue {i}") for i in range(5)]
        rows = issues_to_rows(issues)
        assert len(rows) == 5
        assert rows[3]["title"] == "Issue 3"

    def test_number_is_stringified(self) -> None:
        row = issues_to_rows([self._make_issue(number=42)])[0]
        assert row["number"] == "42"


# ---------------------------------------------------------------------------
# main / parse_args
# ---------------------------------------------------------------------------

class TestFetchGithubIssuesMain:
    def _make_issue_response(self) -> list[dict]:
        return [
            {
                "number": 1,
                "title": "First issue",
                "state": "open",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "html_url": "https://github.com/owner/repo/issues/1",
                "user": {"login": "dev"},
            }
        ]

    def test_dry_run_exits_zero_without_writing(self, tmp_path: Path) -> None:
        out = tmp_path / "issues.csv"
        args = parse_args(["owner", "repo", "--output", str(out), "--dry-run"])

        mock_resp = MagicMock()
        mock_resp.headers = {"X-RateLimit-Remaining": "60"}
        mock_resp.json.side_effect = [self._make_issue_response(), []]
        mock_resp.raise_for_status = MagicMock()

        with patch("scripts.web_api.fetch_github_issues.requests.get", return_value=mock_resp):
            rc = main(args)

        assert rc == 0
        assert not out.exists()

    def test_writes_csv_when_not_dry_run(self, tmp_path: Path) -> None:
        out = tmp_path / "issues.csv"
        args = parse_args(["owner", "repo", "--output", str(out)])

        mock_resp = MagicMock()
        mock_resp.headers = {"X-RateLimit-Remaining": "60"}
        mock_resp.json.side_effect = [self._make_issue_response(), []]
        mock_resp.raise_for_status = MagicMock()

        with patch("scripts.web_api.fetch_github_issues.requests.get", return_value=mock_resp):
            rc = main(args)

        assert rc == 0
        assert out.exists()
        with out.open(encoding="utf-8") as fh:
            reader = list(csv.DictReader(fh))
        assert len(reader) == 1
        assert reader[0]["title"] == "First issue"

    def test_csv_has_expected_headers(self, tmp_path: Path) -> None:
        out = tmp_path / "issues.csv"
        args = parse_args(["owner", "repo", "--output", str(out)])

        mock_resp = MagicMock()
        mock_resp.headers = {"X-RateLimit-Remaining": "60"}
        mock_resp.json.side_effect = [[], ]
        mock_resp.raise_for_status = MagicMock()

        with patch("scripts.web_api.fetch_github_issues.requests.get", return_value=mock_resp):
            main(args)

        with out.open(encoding="utf-8") as fh:
            headers = fh.readline().strip().split(",")
        for field in ISSUES_FIELDS:
            assert field in headers

    def test_pagination_fetches_multiple_pages(self, tmp_path: Path) -> None:
        out = tmp_path / "issues.csv"
        args = parse_args(["owner", "repo", "--output", str(out)])

        page1 = self._make_issue_response()
        page2 = [dict(self._make_issue_response()[0], number=2, title="Second")]
        page3: list = []

        mock_resp = MagicMock()
        mock_resp.headers = {"X-RateLimit-Remaining": "60"}
        mock_resp.json.side_effect = [page1, page2, page3]
        mock_resp.raise_for_status = MagicMock()

        with patch("scripts.web_api.fetch_github_issues.requests.get", return_value=mock_resp):
            rc = main(args)

        assert rc == 0
        with out.open(encoding="utf-8") as fh:
            reader = list(csv.DictReader(fh))
        assert len(reader) == 2


class TestFetchGithubIssuesParseArgs:
    def test_required_positional_args(self) -> None:
        args = parse_args(["myowner", "myrepo"])
        assert args.owner == "myowner"
        assert args.repo == "myrepo"

    def test_defaults(self) -> None:
        args = parse_args(["owner", "repo"])
        assert args.output == "issues.csv"
        assert args.state == "all"
        assert args.token is None
        assert args.dry_run is False

    def test_dry_run_flag(self) -> None:
        args = parse_args(["owner", "repo", "--dry-run"])
        assert args.dry_run is True

    def test_state_choices(self) -> None:
        for state in ("open", "closed", "all"):
            args = parse_args(["owner", "repo", "--state", state])
            assert args.state == state

    def test_custom_output(self) -> None:
        args = parse_args(["owner", "repo", "--output", "custom.csv"])
        assert args.output == "custom.csv"

    def test_token_arg(self) -> None:
        args = parse_args(["owner", "repo", "--token", "abc123"])
        assert args.token == "abc123"

"""Tests for agent/coding_agent.py — tool helpers, internal utilities, and CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.coding_agent import (
    REPO_ROOT,
    SCRIPTS_ROOT,
    CATEGORIES,
    CodingAgent,
    _assert_in_scripts,
    _parse_plan,
    _resolve_path,
    build_parser,
    main,
    tool_list_files,
    tool_read_file,
    tool_run_command,
    tool_write_file,
)


# ---------------------------------------------------------------------------
# tool_list_files
# ---------------------------------------------------------------------------

class TestToolListFiles:
    def test_returns_sorted_list(self) -> None:
        # Use the real scripts root — it already contains files
        files = tool_list_files(SCRIPTS_ROOT)
        assert files == sorted(files)

    def test_returns_relative_paths(self) -> None:
        files = tool_list_files(SCRIPTS_ROOT)
        for f in files:
            assert not Path(f).is_absolute()

    def test_returns_empty_list_for_nonexistent_dir(self, tmp_path: Path) -> None:
        result = tool_list_files(tmp_path / "does_not_exist")
        assert result == []

    def test_does_not_include_directories(self) -> None:
        files = tool_list_files(SCRIPTS_ROOT)
        # All returned entries should resolve to files, not directories
        assert all((REPO_ROOT / f).is_file() for f in files)


# ---------------------------------------------------------------------------
# tool_read_file
# ---------------------------------------------------------------------------

class TestToolReadFile:
    def test_reads_existing_file(self, tmp_path: Path) -> None:
        # tool_read_file resolves relative paths against REPO_ROOT; use absolute
        f = tmp_path / "readme.txt"
        f.write_text("hello", encoding="utf-8")
        assert tool_read_file(f) == "hello"

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            tool_read_file(tmp_path / "ghost.txt")


# ---------------------------------------------------------------------------
# tool_write_file
# ---------------------------------------------------------------------------

class TestToolWriteFile:
    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        dest = SCRIPTS_ROOT / "utilities" / "_test_dry.py"
        try:
            msg = tool_write_file(dest, "content", dry_run=True)
            assert "dry-run" in msg
            assert not dest.exists()
        finally:
            dest.unlink(missing_ok=True)

    def test_raises_for_path_outside_scripts(self, tmp_path: Path) -> None:
        outside = tmp_path / "evil.txt"
        with pytest.raises(ValueError, match="Safety violation"):
            tool_write_file(outside, "evil", dry_run=True)

    def test_writes_inside_scripts_when_not_dry_run(self) -> None:
        dest = SCRIPTS_ROOT / "utilities" / "_test_write_real.py"
        try:
            tool_write_file(dest, "# real", dry_run=False)
            assert dest.exists()
            assert dest.read_text(encoding="utf-8") == "# real"
        finally:
            dest.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# tool_run_command
# ---------------------------------------------------------------------------

class TestToolRunCommand:
    def test_returns_stdout(self) -> None:
        out = tool_run_command(["echo", "hello"])
        assert "hello" in out

    def test_captures_stderr(self) -> None:
        out = tool_run_command(["python3", "-c", "import sys; sys.stderr.write('err')"])
        assert "err" in out

    def test_non_zero_exit_does_not_raise(self) -> None:
        # Should log a warning but not raise
        out = tool_run_command(["python3", "-c", "import sys; sys.exit(1)"])
        assert isinstance(out, str)


# ---------------------------------------------------------------------------
# _resolve_path
# ---------------------------------------------------------------------------

class TestResolvePath:
    def test_absolute_path_unchanged(self, tmp_path: Path) -> None:
        result = _resolve_path(tmp_path)
        assert result == tmp_path.resolve()

    def test_relative_path_resolved_against_repo_root(self) -> None:
        result = _resolve_path("scripts/common/file_ops.py")
        assert result == (REPO_ROOT / "scripts/common/file_ops.py").resolve()


# ---------------------------------------------------------------------------
# _assert_in_scripts
# ---------------------------------------------------------------------------

class TestAssertInScripts:
    def test_passes_for_path_inside_scripts(self) -> None:
        _assert_in_scripts(SCRIPTS_ROOT / "utilities" / "some_script.py")

    def test_raises_for_path_outside_scripts(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Safety violation"):
            _assert_in_scripts(tmp_path / "malicious.py")

    def test_raises_for_repo_root_itself(self) -> None:
        with pytest.raises(ValueError):
            _assert_in_scripts(REPO_ROOT / "main.py")


# ---------------------------------------------------------------------------
# _parse_plan
# ---------------------------------------------------------------------------

class TestParsePlan:
    def test_parses_json_array(self) -> None:
        raw = '[{"category": "utilities", "filename": "foo.py", "description": "bar", "docstring": "", "body": ""}]'
        plan = _parse_plan(raw)
        assert isinstance(plan, list)
        assert plan[0]["category"] == "utilities"

    def test_strips_markdown_fences(self) -> None:
        raw = '```json\n[{"category": "utilities", "filename": "x.py", "description": "", "docstring": "", "body": ""}]\n```'
        plan = _parse_plan(raw)
        assert isinstance(plan, list)
        assert len(plan) == 1

    def test_strips_plain_backtick_fence(self) -> None:
        raw = '```\n[{"category": "data_processing", "filename": "y.py", "description": "", "docstring": "", "body": ""}]\n```'
        plan = _parse_plan(raw)
        assert plan[0]["category"] == "data_processing"

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_plan("not json at all")

    def test_handles_whitespace(self) -> None:
        raw = '  \n[{"category": "web_api", "filename": "z.py", "description": "", "docstring": "", "body": ""}]\n  '
        plan = _parse_plan(raw)
        assert plan[0]["filename"] == "z.py"


# ---------------------------------------------------------------------------
# CodingAgent
# ---------------------------------------------------------------------------

class TestCodingAgent:
    def test_dry_run_true_when_auto_apply_false(self) -> None:
        agent = CodingAgent(dry_run=True, auto_apply=False)
        assert agent.dry_run is True

    def test_auto_apply_overrides_dry_run(self) -> None:
        agent = CodingAgent(dry_run=True, auto_apply=True)
        assert agent.dry_run is False

    def test_model_stored(self) -> None:
        agent = CodingAgent(model="gpt-4")
        assert agent.model == "gpt-4"

    def test_suggest_returns_formatted_plan(self) -> None:
        agent = CodingAgent()
        plan = [
            {"category": "utilities", "filename": "foo.py", "description": "Does foo"},
        ]
        with patch.object(agent, "_plan", return_value=plan):
            result = agent.suggest("make foo")
        assert "Suggested plan:" in result
        assert "[utilities]" in result
        assert "foo.py" in result
        assert "Does foo" in result

    def test_suggest_handles_empty_plan(self) -> None:
        agent = CodingAgent()
        with patch.object(agent, "_plan", return_value=[]):
            result = agent.suggest("nothing")
        assert "Suggested plan:" in result

    def test_run_returns_empty_list_in_dry_run(self) -> None:
        agent = CodingAgent(dry_run=True)
        plan = [{"category": "utilities", "filename": "test.py", "body": "# code"}]
        with patch.object(agent, "_plan", return_value=plan):
            written = agent.run("some task")
        assert written == []

    def test_run_returns_paths_when_auto_apply(self) -> None:
        agent = CodingAgent(auto_apply=True)
        plan = [{"category": "utilities", "filename": "_test_agent_run.py", "body": "# code"}]
        dest = CATEGORIES["utilities"] / "_test_agent_run.py"
        try:
            with patch.object(agent, "_plan", return_value=plan):
                written = agent.run("write a script")
            assert len(written) == 1
            assert written[0] == dest
        finally:
            dest.unlink(missing_ok=True)

    def test_apply_entry_unknown_category_defaults_to_utilities(self) -> None:
        agent = CodingAgent(dry_run=True)
        entry = {"category": "nonexistent", "filename": "_unk.py", "body": "# x"}
        # Should not raise
        result = agent._apply_entry(entry)
        assert result is None  # dry_run → None

    def test_recommend_git_snapshot_does_not_raise(self) -> None:
        agent = CodingAgent()
        agent._recommend_git_snapshot()  # just logs


# ---------------------------------------------------------------------------
# CLI — build_parser / main
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_list_files_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--list-files"])
        assert args.list_files is True

    def test_auto_apply_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--auto-apply", "task"])
        assert args.auto_apply is True

    def test_suggest_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--suggest", "task"])
        assert args.suggest is True

    def test_model_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["task"])
        assert args.model == "gpt-4o-mini"

    def test_custom_model(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--model", "gpt-4", "task"])
        assert args.model == "gpt-4"


class TestMain:
    def test_list_files_exits_zero(self, capsys: pytest.CaptureFixture) -> None:
        rc = main(["--list-files"])
        assert rc == 0

    def test_no_task_exits_one(self) -> None:
        rc = main([])
        assert rc == 1

    def test_suggest_calls_agent_suggest(self, capsys: pytest.CaptureFixture) -> None:
        plan = [{"category": "utilities", "filename": "x.py", "description": "desc", "docstring": "", "body": ""}]
        with patch("agent.coding_agent._call_llm", return_value=json.dumps(plan)):
            rc = main(["--suggest", "do something"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Suggested plan:" in out

    def test_run_dry_run_exits_zero(self, capsys: pytest.CaptureFixture) -> None:
        plan = [{"category": "utilities", "filename": "_main_test.py", "body": "# x"}]
        with patch("agent.coding_agent._call_llm", return_value=json.dumps(plan)):
            rc = main(["do something"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "dry-run" in out.lower() or "no files" in out.lower()

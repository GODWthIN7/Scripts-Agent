"""Tests for scripts/data_processing/merge_csvs.py."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pytest

from scripts.data_processing.merge_csvs import (
    build_summary,
    main,
    merge_csvs,
    normalize_header,
    parse_args,
)


# ---------------------------------------------------------------------------
# normalize_header
# ---------------------------------------------------------------------------

class TestNormalizeHeader:
    def test_lowercases_headers(self) -> None:
        assert normalize_header(["NAME", "AGE"]) == ["name", "age"]

    def test_replaces_spaces_with_underscores(self) -> None:
        assert normalize_header(["First Name", "Last Name"]) == ["first_name", "last_name"]

    def test_replaces_hyphens_with_underscores(self) -> None:
        assert normalize_header(["first-name"]) == ["first_name"]

    def test_strips_whitespace(self) -> None:
        assert normalize_header(["  col  "]) == ["col"]

    def test_mixed_transformations(self) -> None:
        assert normalize_header(["  My-Col Name  "]) == ["my_col_name"]

    def test_empty_list(self) -> None:
        assert normalize_header([]) == []

    def test_single_header(self) -> None:
        assert normalize_header(["ID"]) == ["id"]


# ---------------------------------------------------------------------------
# merge_csvs
# ---------------------------------------------------------------------------

class TestMergeCsvs:
    def _write_csv(self, path: Path, headers: list[str], rows: list[list[str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(rows)

    def test_merges_two_identical_schema_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.csv"
        f2 = tmp_path / "b.csv"
        self._write_csv(f1, ["Name", "Age"], [["Alice", "30"], ["Bob", "25"]])
        self._write_csv(f2, ["Name", "Age"], [["Charlie", "35"]])

        headers, rows = merge_csvs([f1, f2])
        assert headers == ["name", "age"]
        assert len(rows) == 3
        assert rows[0]["name"] == "Alice"

    def test_merges_files_with_different_columns(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.csv"
        f2 = tmp_path / "b.csv"
        self._write_csv(f1, ["Name"], [["Alice"]])
        self._write_csv(f2, ["Name", "Email"], [["Bob", "bob@example.com"]])

        headers, rows = merge_csvs([f1, f2])
        # Both 'name' and 'email' should be in headers
        assert "name" in headers
        assert "email" in headers

    def test_normalizes_headers(self, tmp_path: Path) -> None:
        f = tmp_path / "c.csv"
        self._write_csv(f, ["First Name", "Last-Name"], [["X", "Y"]])
        headers, _ = merge_csvs([f])
        assert "first_name" in headers
        assert "last_name" in headers

    def test_skips_file_with_no_headers(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.csv"
        f.write_text("", encoding="utf-8")
        headers, rows = merge_csvs([f])
        assert rows == []

    def test_empty_input_list(self) -> None:
        headers, rows = merge_csvs([])
        assert headers == []
        assert rows == []

    def test_single_file_single_row(self, tmp_path: Path) -> None:
        f = tmp_path / "single.csv"
        self._write_csv(f, ["id"], [["1"]])
        headers, rows = merge_csvs([f])
        assert headers == ["id"]
        assert len(rows) == 1
        assert rows[0]["id"] == "1"

    def test_no_duplicate_headers(self, tmp_path: Path) -> None:
        f1 = tmp_path / "x.csv"
        f2 = tmp_path / "y.csv"
        self._write_csv(f1, ["col"], [["a"]])
        self._write_csv(f2, ["col"], [["b"]])
        headers, _ = merge_csvs([f1, f2])
        assert headers.count("col") == 1


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

class TestBuildSummary:
    def test_includes_row_count(self) -> None:
        rows = [{"a": "1"}, {"a": "2"}]
        summary = build_summary(["a"], rows)
        assert "2" in summary

    def test_includes_column_names(self) -> None:
        summary = build_summary(["name", "age"], [])
        assert "name" in summary
        assert "age" in summary

    def test_includes_column_count(self) -> None:
        summary = build_summary(["x", "y", "z"], [])
        assert "3" in summary

    def test_empty_data(self) -> None:
        summary = build_summary([], [])
        assert "0" in summary


# ---------------------------------------------------------------------------
# main / parse_args
# ---------------------------------------------------------------------------

class TestMergeCsvsMain:
    def _write_csv(self, path: Path, headers: list[str], rows: list[list[str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(rows)

    def test_returns_1_for_missing_input_file(self, tmp_path: Path) -> None:
        args = parse_args([str(tmp_path / "nonexistent.csv")])
        assert main(args) == 1

    def test_dry_run_does_not_write_output(self, tmp_path: Path) -> None:
        f = tmp_path / "input.csv"
        self._write_csv(f, ["a"], [["1"]])
        out = tmp_path / "merged.csv"
        args = parse_args([str(f), "--output", str(out), "--dry-run"])
        rc = main(args)
        assert rc == 0
        assert not out.exists()

    def test_writes_merged_csv_when_not_dry_run(self, tmp_path: Path) -> None:
        f = tmp_path / "input.csv"
        self._write_csv(f, ["id", "value"], [["1", "alpha"], ["2", "beta"]])
        out = tmp_path / "merged.csv"
        args = parse_args([str(f), "--output", str(out)])
        rc = main(args)
        assert rc == 0
        assert out.exists()

    def test_merged_csv_contains_all_rows(self, tmp_path: Path) -> None:
        f1 = tmp_path / "f1.csv"
        f2 = tmp_path / "f2.csv"
        self._write_csv(f1, ["col"], [["row1"]])
        self._write_csv(f2, ["col"], [["row2"]])
        out = tmp_path / "out.csv"
        args = parse_args([str(f1), str(f2), "--output", str(out)])
        main(args)
        with out.open(encoding="utf-8") as fh:
            reader = list(csv.DictReader(fh))
        assert len(reader) == 2


class TestMergeCsvsParseArgs:
    def test_defaults(self) -> None:
        args = parse_args(["file.csv"])
        assert args.output == "merged.csv"
        assert args.dry_run is False

    def test_dry_run_flag(self) -> None:
        args = parse_args(["file.csv", "--dry-run"])
        assert args.dry_run is True

    def test_custom_output(self) -> None:
        args = parse_args(["file.csv", "--output", "custom.csv"])
        assert args.output == "custom.csv"

    def test_multiple_inputs(self) -> None:
        args = parse_args(["a.csv", "b.csv", "c.csv"])
        assert args.inputs == ["a.csv", "b.csv", "c.csv"]

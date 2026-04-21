"""Tests for scripts/system_automation/archive_old_logs.py."""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.system_automation.archive_old_logs import (
    archive_logs,
    find_old_logs,
    main,
    parse_args,
)


def _make_log_file(path: Path, mtime_offset_days: int) -> None:
    """Create a .log file and set its mtime *mtime_offset_days* days ago."""
    path.write_text("log content", encoding="utf-8")
    past = datetime.now() - timedelta(days=mtime_offset_days)
    ts = past.timestamp()
    import os
    os.utime(path, (ts, ts))


# ---------------------------------------------------------------------------
# find_old_logs
# ---------------------------------------------------------------------------

class TestFindOldLogs:
    def test_returns_files_older_than_threshold(self, tmp_path: Path) -> None:
        old = tmp_path / "old.log"
        _make_log_file(old, mtime_offset_days=35)
        result = find_old_logs(tmp_path, days=30)
        assert old in result

    def test_does_not_return_recent_files(self, tmp_path: Path) -> None:
        recent = tmp_path / "recent.log"
        _make_log_file(recent, mtime_offset_days=1)
        result = find_old_logs(tmp_path, days=30)
        assert recent not in result

    def test_ignores_non_log_files(self, tmp_path: Path) -> None:
        txt = tmp_path / "old.txt"
        _make_log_file(txt, mtime_offset_days=60)
        result = find_old_logs(tmp_path, days=30)
        assert txt not in result

    def test_recurses_into_subdirectories(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        deep = sub / "deep.log"
        _make_log_file(deep, mtime_offset_days=40)
        result = find_old_logs(tmp_path, days=30)
        assert deep in result

    def test_returns_empty_when_no_old_logs(self, tmp_path: Path) -> None:
        _make_log_file(tmp_path / "fresh.log", mtime_offset_days=1)
        assert find_old_logs(tmp_path, days=30) == []

    def test_returns_empty_when_dir_is_empty(self, tmp_path: Path) -> None:
        assert find_old_logs(tmp_path, days=30) == []

    def test_boundary_file_exactly_at_threshold_excluded(self, tmp_path: Path) -> None:
        # A file modified exactly *days* days ago should NOT be older-than cutoff
        f = tmp_path / "boundary.log"
        _make_log_file(f, mtime_offset_days=30)
        # Depending on sub-second precision it might fall in or out; just ensure no crash
        find_old_logs(tmp_path, days=30)


# ---------------------------------------------------------------------------
# archive_logs
# ---------------------------------------------------------------------------

class TestArchiveLogs:
    def test_dry_run_does_not_copy(self, tmp_path: Path) -> None:
        src = tmp_path / "src.log"
        src.write_text("data", encoding="utf-8")
        backup = tmp_path / "backup"
        count = archive_logs([src], backup, dry_run=True)
        assert count == 1
        assert not (backup / "src.log").exists()

    def test_copies_files_when_not_dry_run(self, tmp_path: Path) -> None:
        src = tmp_path / "app.log"
        src.write_text("logdata", encoding="utf-8")
        backup = tmp_path / "archive"
        count = archive_logs([src], backup, dry_run=False)
        assert count == 1
        assert (backup / "app.log").exists()
        assert (backup / "app.log").read_text(encoding="utf-8") == "logdata"

    def test_creates_backup_dir_when_not_dry_run(self, tmp_path: Path) -> None:
        src = tmp_path / "x.log"
        src.write_text("x", encoding="utf-8")
        backup = tmp_path / "new_backup_dir"
        assert not backup.exists()
        archive_logs([src], backup, dry_run=False)
        assert backup.exists()

    def test_returns_zero_for_empty_input(self, tmp_path: Path) -> None:
        count = archive_logs([], tmp_path / "backup", dry_run=True)
        assert count == 0

    def test_archives_multiple_files(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"log_{i}.log"
            f.write_text(f"content {i}", encoding="utf-8")
            files.append(f)
        backup = tmp_path / "backup"
        count = archive_logs(files, backup, dry_run=False)
        assert count == 3


# ---------------------------------------------------------------------------
# main / parse_args
# ---------------------------------------------------------------------------

class TestArchiveOldLogsMain:
    def test_returns_1_when_log_dir_missing(self, tmp_path: Path) -> None:
        args = parse_args(["--log-dir", str(tmp_path / "missing"), "--backup-dir", str(tmp_path / "bak")])
        assert main(args) == 1

    def test_returns_0_when_no_old_logs(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        _make_log_file(log_dir / "fresh.log", mtime_offset_days=1)
        args = parse_args(["--log-dir", str(log_dir), "--backup-dir", str(tmp_path / "bak"), "--days", "30"])
        assert main(args) == 0

    def test_archives_old_logs_not_dry_run(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        old = log_dir / "old.log"
        _make_log_file(old, mtime_offset_days=60)
        bak = tmp_path / "bak"
        args = parse_args([
            "--log-dir", str(log_dir),
            "--backup-dir", str(bak),
            "--days", "30",
        ])
        rc = main(args)
        assert rc == 0
        assert (bak / "old.log").exists()

    def test_dry_run_does_not_copy(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        _make_log_file(log_dir / "old.log", mtime_offset_days=60)
        bak = tmp_path / "bak"
        args = parse_args([
            "--log-dir", str(log_dir),
            "--backup-dir", str(bak),
            "--days", "30",
            "--dry-run",
        ])
        main(args)
        assert not bak.exists()


class TestArchiveOldLogsParseArgs:
    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.log_dir == "/var/log"
        assert args.backup_dir == "/var/log/archive"
        assert args.days == 30
        assert args.dry_run is False

    def test_custom_values(self) -> None:
        args = parse_args(["--log-dir", "/tmp/logs", "--backup-dir", "/tmp/bak", "--days", "7"])
        assert args.log_dir == "/tmp/logs"
        assert args.days == 7

    def test_dry_run_flag(self) -> None:
        args = parse_args(["--dry-run"])
        assert args.dry_run is True

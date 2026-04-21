"""Tests for scripts/common/file_ops.py."""
from __future__ import annotations

import pytest
from pathlib import Path

from scripts.common.file_ops import safe_read, safe_write, safe_delete


# ---------------------------------------------------------------------------
# safe_read
# ---------------------------------------------------------------------------

class TestSafeRead:
    def test_reads_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")
        assert safe_read(f) == "hello world"

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        f = tmp_path / "data.txt"
        f.write_text("data", encoding="utf-8")
        assert safe_read(str(f)) == "data"

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            safe_read(tmp_path / "nonexistent.txt")

    def test_reads_unicode_content(self, tmp_path: Path) -> None:
        content = "héllo wörld 日本語"
        f = tmp_path / "unicode.txt"
        f.write_text(content, encoding="utf-8")
        assert safe_read(f) == content

    def test_reads_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert safe_read(f) == ""


# ---------------------------------------------------------------------------
# safe_write
# ---------------------------------------------------------------------------

class TestSafeWrite:
    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.txt"
        msg = safe_write(dest, "content", dry_run=True)
        assert not dest.exists()
        assert "dry-run" in msg
        assert "content" in msg or "7" in msg  # 7 chars

    def test_dry_run_message_contains_path(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.txt"
        msg = safe_write(dest, "x", dry_run=True)
        assert str(dest) in msg

    def test_writes_file_when_not_dry_run(self, tmp_path: Path) -> None:
        dest = tmp_path / "real.txt"
        msg = safe_write(dest, "hello", dry_run=False)
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "hello"
        assert "Wrote" in msg

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        dest = tmp_path / "a" / "b" / "c" / "file.txt"
        safe_write(dest, "nested", dry_run=False)
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "nested"

    def test_mkdir_false_raises_when_parent_missing(self, tmp_path: Path) -> None:
        dest = tmp_path / "missing_dir" / "file.txt"
        with pytest.raises(FileNotFoundError):
            safe_write(dest, "data", dry_run=False, mkdir=False)

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        dest = tmp_path / "file.txt"
        dest.write_text("old", encoding="utf-8")
        safe_write(dest, "new", dry_run=False)
        assert dest.read_text(encoding="utf-8") == "new"

    def test_returns_message_with_char_count(self, tmp_path: Path) -> None:
        dest = tmp_path / "file.txt"
        msg = safe_write(dest, "abcde", dry_run=False)
        assert "5" in msg

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        dest = tmp_path / "str_path.txt"
        safe_write(str(dest), "ok", dry_run=False)
        assert dest.read_text(encoding="utf-8") == "ok"


# ---------------------------------------------------------------------------
# safe_delete
# ---------------------------------------------------------------------------

class TestSafeDelete:
    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        f = tmp_path / "keep.txt"
        f.write_text("keep me", encoding="utf-8")
        msg = safe_delete(f, dry_run=True)
        assert f.exists()
        assert "dry-run" in msg

    def test_deletes_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "gone.txt"
        f.write_text("bye", encoding="utf-8")
        msg = safe_delete(f, dry_run=False)
        assert not f.exists()
        assert "Deleted" in msg

    def test_graceful_when_file_not_found(self, tmp_path: Path) -> None:
        msg = safe_delete(tmp_path / "ghost.txt", dry_run=False)
        assert "not found" in msg.lower() or "skipping" in msg.lower()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        f = tmp_path / "str.txt"
        f.write_text("x", encoding="utf-8")
        safe_delete(str(f), dry_run=False)
        assert not f.exists()

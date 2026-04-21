"""Tests for scripts/utilities/md_to_text.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.utilities.md_to_text import (
    convert_files,
    main,
    md_to_text,
    parse_args,
)


# ---------------------------------------------------------------------------
# md_to_text
# ---------------------------------------------------------------------------

class TestMdToText:
    def test_removes_headings(self) -> None:
        result = md_to_text("# Heading One\n## Heading Two\n")
        assert "#" not in result
        assert "Heading One" in result
        assert "Heading Two" in result

    def test_removes_bold(self) -> None:
        result = md_to_text("**bold text**")
        assert "**" not in result
        assert "bold text" in result

    def test_removes_italic_asterisk(self) -> None:
        result = md_to_text("*italic*")
        assert "*" not in result
        assert "italic" in result

    def test_removes_bold_underscore(self) -> None:
        result = md_to_text("__bold__")
        assert "__" not in result
        assert "bold" in result

    def test_removes_italic_underscore(self) -> None:
        result = md_to_text("_italic_")
        assert "_" not in result
        assert "italic" in result

    def test_removes_link_keeps_text(self) -> None:
        result = md_to_text("[link text](https://example.com)")
        assert "link text" in result
        assert "https://example.com" not in result
        assert "[" not in result

    def test_removes_images(self) -> None:
        result = md_to_text("![alt text](image.png)")
        assert "![" not in result
        assert "image.png" not in result

    def test_removes_fenced_code_blocks(self) -> None:
        md = "Some text\n```python\nprint('hello')\n```\nMore text"
        result = md_to_text(md)
        assert "print" not in result
        assert "Some text" in result
        assert "More text" in result

    def test_strips_inline_code_backticks(self) -> None:
        result = md_to_text("Use `code` here")
        assert "`" not in result
        assert "code" in result

    def test_removes_horizontal_rules(self) -> None:
        result = md_to_text("---\n")
        assert "---" not in result

    def test_collapses_blank_lines(self) -> None:
        result = md_to_text("a\n\n\n\nb")
        # No more than two consecutive newlines
        assert "\n\n\n" not in result

    def test_empty_input(self) -> None:
        assert md_to_text("") == ""

    def test_plain_text_unchanged(self) -> None:
        text = "Just plain text with no markdown."
        result = md_to_text(text)
        assert result == text

    def test_removes_horizontal_rule_stars(self) -> None:
        result = md_to_text("***\n")
        assert "***" not in result

    def test_removes_horizontal_rule_underscores(self) -> None:
        result = md_to_text("___\n")
        assert "___" not in result


# ---------------------------------------------------------------------------
# convert_files
# ---------------------------------------------------------------------------

class TestConvertFiles:
    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        src = tmp_path / "doc.md"
        src.write_text("# Title\nHello", encoding="utf-8")
        out_dir = tmp_path / "output"
        count = convert_files([src], out_dir, dry_run=True)
        assert count == 1
        assert not (out_dir / "doc.txt").exists()

    def test_writes_txt_file_when_not_dry_run(self, tmp_path: Path) -> None:
        src = tmp_path / "doc.md"
        src.write_text("# Title\nHello", encoding="utf-8")
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        count = convert_files([src], out_dir, dry_run=False)
        assert count == 1
        txt = out_dir / "doc.txt"
        assert txt.exists()
        content = txt.read_text(encoding="utf-8")
        assert "Hello" in content
        assert "#" not in content

    def test_converts_multiple_files(self, tmp_path: Path) -> None:
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.md"
            f.write_text(f"# Doc {i}", encoding="utf-8")
            files.append(f)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        count = convert_files(files, out_dir, dry_run=False)
        assert count == 3

    def test_returns_zero_for_empty_list(self, tmp_path: Path) -> None:
        count = convert_files([], tmp_path, dry_run=True)
        assert count == 0

    def test_output_filename_has_txt_extension(self, tmp_path: Path) -> None:
        src = tmp_path / "readme.md"
        src.write_text("text", encoding="utf-8")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        convert_files([src], out_dir, dry_run=False)
        assert (out_dir / "readme.txt").exists()


# ---------------------------------------------------------------------------
# main / parse_args
# ---------------------------------------------------------------------------

class TestMdToTextMain:
    def test_returns_0_when_no_markdown_files(self, tmp_path: Path) -> None:
        args = parse_args(["--input-dir", str(tmp_path), "--output-dir", str(tmp_path / "out")])
        rc = main(args)
        assert rc == 0

    def test_converts_markdown_in_dry_run(self, tmp_path: Path) -> None:
        md_file = tmp_path / "a.md"
        md_file.write_text("# Hello", encoding="utf-8")
        out = tmp_path / "out"
        args = parse_args([
            "--input-dir", str(tmp_path),
            "--output-dir", str(out),
            "--dry-run",
        ])
        rc = main(args)
        assert rc == 0
        assert not out.exists()

    def test_converts_markdown_to_txt_files(self, tmp_path: Path) -> None:
        md_file = tmp_path / "b.md"
        md_file.write_text("**bold** text", encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()
        args = parse_args(["--input-dir", str(tmp_path), "--output-dir", str(out)])
        rc = main(args)
        assert rc == 0
        assert (out / "b.txt").exists()


class TestMdToTextParseArgs:
    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.input_dir == "."
        assert args.output_dir == "./output"
        assert args.dry_run is False

    def test_dry_run_flag(self) -> None:
        args = parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_custom_dirs(self) -> None:
        args = parse_args(["--input-dir", "/in", "--output-dir", "/out"])
        assert args.input_dir == "/in"
        assert args.output_dir == "/out"

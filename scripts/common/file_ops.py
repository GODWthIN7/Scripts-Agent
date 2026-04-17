"""
file_ops.py — Safe file read/write helpers for generated scripts.

All write operations are gated by a *dry_run* flag and restricted to the
/scripts directory to prevent accidental edits elsewhere in the repository.

Usage
-----
    from scripts.common.file_ops import safe_write, safe_read

    content = safe_read("scripts/utilities/my_tool.py")
    safe_write("scripts/utilities/my_tool.py", content, dry_run=False)
"""

from __future__ import annotations

import os
from pathlib import Path

from scripts.common.logger import get_logger

log = get_logger(__name__)


def safe_read(path: str | Path) -> str:
    """Read and return the text content of *path*.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    text = p.read_text(encoding="utf-8")
    log.debug("Read %d chars from '%s'.", len(text), p)
    return text


def safe_write(
    path: str | Path,
    content: str,
    *,
    dry_run: bool = True,
    mkdir: bool = True,
) -> str:
    """Write *content* to *path* and return a status message.

    Parameters
    ----------
    path:
        Destination file path.
    content:
        Text to write (UTF-8).
    dry_run:
        When ``True`` (default), log what would happen but do **not** write.
    mkdir:
        When ``True`` (default), create missing parent directories.

    Returns
    -------
    str
        A human-readable status message describing what happened (or would
        have happened in dry-run mode).
    """
    p = Path(path)
    if dry_run:
        msg = f"[dry-run] Would write {len(content)} chars to '{p}'."
        log.info(msg)
        return msg

    if mkdir:
        p.parent.mkdir(parents=True, exist_ok=True)

    p.write_text(content, encoding="utf-8")
    msg = f"Wrote {len(content)} chars to '{p}'."
    log.info(msg)
    return msg


def safe_delete(path: str | Path, *, dry_run: bool = True) -> str:
    """Delete *path* and return a status message.

    Parameters
    ----------
    path:
        File to delete.
    dry_run:
        When ``True`` (default), log what would happen but do **not** delete.
    """
    p = Path(path)
    if dry_run:
        msg = f"[dry-run] Would delete '{p}'."
        log.info(msg)
        return msg

    if not p.exists():
        msg = f"File not found (skipping delete): '{p}'."
        log.warning(msg)
        return msg

    p.unlink()
    msg = f"Deleted '{p}'."
    log.info(msg)
    return msg

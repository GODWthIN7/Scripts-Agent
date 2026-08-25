"""
csv_ops.py — CSV read/write helpers with dry-run support.

Usage
-----
    from scripts.common.csv_ops import write_csv, read_csv

    write_csv("out.csv", ["a", "b"], rows, dry_run=True)
"""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.common.logger import get_logger

log = get_logger(__name__)


def read_csv(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Return ``(fieldnames, rows)`` read from the CSV at *path*.

    An empty field list is returned when the file has no header row.
    """
    p = Path(path)
    with p.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            log.warning("No headers found in '%s'.", p)
            return [], []
        return list(reader.fieldnames), list(reader)


def write_csv(
    path: str | Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    *,
    dry_run: bool = True,
    mkdir: bool = True,
) -> str:
    """Write *rows* to the CSV at *path* and return a status message.

    Parameters
    ----------
    fieldnames:
        Column order for the header row; keys absent from it are ignored.
    dry_run:
        When ``True`` (default), log what would happen but do **not** write.
    mkdir:
        When ``True`` (default), create missing parent directories.
    """
    p = Path(path)
    if dry_run:
        msg = f"[dry-run] Would write {len(rows)} row(s) to '{p}'."
        log.info(msg)
        return msg

    if mkdir:
        p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    msg = f"Wrote {len(rows)} row(s) to '{p}'."
    log.info(msg)
    return msg


def normalize_header(header: list[str]) -> list[str]:
    """Return *header* lowercased, stripped and with separators as underscores."""
    return [col.strip().lower().replace(" ", "_").replace("-", "_") for col in header]

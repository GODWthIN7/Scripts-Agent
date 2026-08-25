"""
cli.py — Shared CLI scaffolding for generated scripts.

Every generated script exposes ``main(args)`` plus ``parse_args()`` and adds the
same ``--dry-run`` flag, start-up log line and ``sys.exit`` wiring.  Those pieces
live here so scripts only declare the arguments unique to them.

Usage
-----
    from scripts.common.cli import build_parser, log_start, run

    def parse_args(argv=None):
        parser = build_parser("Convert Markdown files to plain text.")
        parser.add_argument("--input-dir", default=".")
        return parser.parse_args(argv)

    def main(args):
        log_start("md_to_text", dry_run=args.dry_run)
        ...

    if __name__ == "__main__":
        run(main, parse_args)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence

from scripts.common.logger import get_logger

DRY_RUN_HELP = "Show what would be done without making changes."


def build_parser(description: str, **kwargs) -> argparse.ArgumentParser:
    """Return an ``ArgumentParser`` that already declares ``--dry-run``."""
    parser = argparse.ArgumentParser(description=description, **kwargs)
    add_dry_run(parser)
    return parser


def add_dry_run(parser: argparse.ArgumentParser, help: str = DRY_RUN_HELP) -> None:
    """Add the standard ``--dry-run`` flag to *parser*."""
    parser.add_argument("--dry-run", action="store_true", default=False, help=help)


def log_start(script_name: str, **params) -> None:
    """Log the standard ``<script> starting (k=v, ...)`` banner."""
    details = ", ".join(f"{key}={value}" for key, value in params.items())
    get_logger(script_name).info("%s starting (%s)", script_name, details)


def run(
    main: Callable[[argparse.Namespace], int],
    parse_args: Callable[[Sequence[str] | None], argparse.Namespace],
    argv: Sequence[str] | None = None,
) -> None:
    """Parse *argv*, call *main* and exit with its return code."""
    sys.exit(main(parse_args(argv)))

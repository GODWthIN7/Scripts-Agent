"""
paths.py — Repository path constants and helpers.

Usage
-----
    from scripts.common.paths import REPO_ROOT, SCRIPTS_ROOT, resolve_path

    resolve_path("scripts/utilities/my_tool.py")
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"

CATEGORIES = {
    name: SCRIPTS_ROOT / name
    for name in ("system_automation", "data_processing", "web_api", "utilities")
}


def ensure_repo_root_on_path() -> Path:
    """Add :data:`REPO_ROOT` to ``sys.path`` if it is missing and return it."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return REPO_ROOT


def resolve_path(path: str | Path) -> Path:
    """Resolve *path*, treating relative paths as relative to :data:`REPO_ROOT`."""
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p.resolve()


def assert_in_scripts(path: str | Path) -> Path:
    """Return *path* resolved, raising ``ValueError`` if it escapes ``/scripts``."""
    resolved = resolve_path(path)
    try:
        resolved.relative_to(SCRIPTS_ROOT.resolve())
    except ValueError:
        raise ValueError(
            f"Safety violation: attempted write to '{resolved}' which is outside "
            f"the allowed /scripts directory."
        )
    return resolved

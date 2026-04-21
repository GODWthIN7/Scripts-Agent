"""
conftest.py — Shared pytest fixtures used across the test suite.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure the repo root is importable regardless of how pytest is invoked.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

---
applyTo: "**/*.py"
---

Prioritize Python 3.11-compatible code and preserve the repository's existing style:
- Keep module docstrings and type hints where already used.
- Prefer small, explicit functions and clear logging over dense logic.
- Reuse `scripts.common` helpers (`logger`, `file_ops`, `config`) instead of duplicating behavior.
- Avoid broad refactors unless explicitly requested.

When changing executable flows, validate with:
- `python main.py --list-files`
- `python -m unittest discover`

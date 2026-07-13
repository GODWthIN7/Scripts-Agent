# Repository custom instructions for Copilot

This repository is a Python-first Copilot Script Agent that generates automation scripts under `scripts/`.

## Project overview
- Entry point: `main.py`.
- Core orchestration: `agent/coding_agent.py`.
- Shared runtime helpers: `scripts/common/{logger.py,file_ops.py,config.py}`.
- Generated/maintained script categories: `scripts/system_automation`, `scripts/data_processing`, `scripts/web_api`, and `scripts/utilities`.

## Repository conventions
- Keep changes focused and minimal.
- Prefer extending existing modules over introducing new dependencies.
- Preserve dry-run and safety behavior for any file-writing logic.
- Keep writes scoped to the `scripts/` tree unless explicitly required otherwise.
- Do not commit secrets; read sensitive values from environment variables.

## Build, test, and validation
- Python environment: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Quick functional check: `python main.py --list-files`.
- Baseline test discovery: `python -m unittest discover`.
- If touching script-generation paths, also run a safe dry-run invocation, for example:
  - `python main.py --suggest "<task>"`
  - `python main.py "<task>"`

## Change guidance
- For `agent/` or `main.py` changes, verify CLI behavior and avoid breaking existing flags (`--list-files`, `--suggest`, `--auto-apply`, `--model`).
- For `scripts/common/file_ops.py`, maintain path-safety guarantees and dry-run semantics.
- For generated script templates, keep `argparse`, `main()`, logging, and clear module docstrings.

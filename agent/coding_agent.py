"""
coding_agent.py — Core agent loop and tool wrappers for the Copilot Script Agent.

The agent accepts a natural-language task, plans which script(s) to create or
update, and then writes polished, production-ready Python automation scripts into
the /scripts directory tree.

Supported script categories
----------------------------
- system_automation   — file management, log archiving, OS-level tasks
- data_processing     — CSV/JSON manipulation, ETL, reporting
- web_api             — HTTP clients, API pagination, web scraping
- utilities           — CLI helpers, format converters, general tools

Safe defaults
-------------
- Dry-run mode is on by default; pass ``--auto-apply`` to write files.
- All writes are confined to the /scripts directory.
- Recommends a git snapshot before any write operation.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.common.logger import get_logger
from scripts.common.file_ops import safe_write, safe_read

log = get_logger(__name__)

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
    _OPENAI_IMPORT_ERROR: ImportError | None = None
except ImportError as exc:  # pragma: no cover
    _OPENAI_AVAILABLE = False
    _OPENAI_IMPORT_ERROR = exc
    log.debug("openai package unavailable: %s", exc)


class AgentError(RuntimeError):
    """Raised when the agent cannot complete a task."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"

CATEGORIES = {
    "system_automation": SCRIPTS_ROOT / "system_automation",
    "data_processing": SCRIPTS_ROOT / "data_processing",
    "web_api": SCRIPTS_ROOT / "web_api",
    "utilities": SCRIPTS_ROOT / "utilities",
}

SCRIPT_TEMPLATE = '''\
"""
{docstring}
"""

from __future__ import annotations

import argparse
import logging
import sys

from scripts.common.logger import get_logger

log = get_logger(__name__)


def main(args: argparse.Namespace) -> int:
    """Entry point for {name}."""
    log.info("Starting %s (dry_run=%s)", __file__, args.dry_run)

    # TODO: implement task logic here

    log.info("Done.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="{description}")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without making changes.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main(parse_args()))
'''

SYSTEM_PROMPT = """\
You are Copilot Script Agent — an expert Python automation engineer.

Your job:
1. Analyze the user task.
2. Decide which category (system_automation, data_processing, web_api, utilities) each
   script belongs to.  A task may require more than one script.
3. For each script produce a JSON plan entry:
   {
     "category": "<category>",
     "filename": "<snake_case_name>.py",
     "description": "<one-line description>",
     "docstring": "<module docstring paragraph>",
     "body": "<complete Python source code as a string>"
   }
4. Return ONLY a JSON array of plan entries and nothing else.

Script rules:
- Always include main(), argparse with --dry-run, logging, and a top-of-file docstring.
- Use tqdm for any loop/batch operation with a sensible desc= and unit=.
- Import shared helpers from scripts.common (logger, file_ops, config) when relevant.
- Never import or use secrets directly — read from env vars.
- All file writes go through scripts.common.file_ops.safe_write unless there is a
  compelling reason (document it).
"""


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------

def tool_list_files(directory: str | Path = SCRIPTS_ROOT) -> list[str]:
    """Return a sorted list of files under *directory* relative to REPO_ROOT."""
    base = Path(directory)
    if not base.exists():
        return []
    return sorted(str(p.relative_to(REPO_ROOT)) for p in base.rglob("*") if p.is_file())


def tool_read_file(path: str | Path) -> str:
    """Return the text content of *path* (resolved relative to REPO_ROOT if needed)."""
    resolved = _resolve_path(path)
    return safe_read(resolved)


def tool_write_file(path: str | Path, content: str, *, dry_run: bool = True) -> str:
    """Write *content* to *path* and return a status message."""
    resolved = _resolve_path(path)
    _assert_in_scripts(resolved)
    return safe_write(resolved, content, dry_run=dry_run)


def tool_run_command(
    cmd: list[str],
    *,
    cwd: str | Path = REPO_ROOT,
    check: bool = True,
    timeout: int = 120,
) -> str:
    """Run *cmd* in a subprocess and return combined stdout+stderr.

    Raises
    ------
    AgentError
        If the command cannot be executed, times out, or (when *check* is
        ``True``) exits with a non-zero status.
    """
    log.debug("Running command: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AgentError(
            f"Command {cmd!r} timed out after {timeout}s."
        ) from exc
    except OSError as exc:
        raise AgentError(f"Command {cmd!r} could not be executed: {exc}") from exc

    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        if check:
            raise AgentError(
                f"Command {cmd!r} exited with code {result.returncode}: {output}"
            )
        log.warning("Command exited with code %d", result.returncode)
    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p.resolve()


def _assert_in_scripts(path: Path) -> None:
    """Raise ValueError if *path* is outside the /scripts directory."""
    try:
        path.relative_to(SCRIPTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(
            f"Safety violation: attempted write to '{path}' which is outside "
            f"the allowed /scripts directory."
        ) from exc


def _call_llm(messages: list[dict[str, str]], model: str = "gpt-4o-mini") -> str:
    """Call the OpenAI chat API and return the assistant message content."""
    if not _OPENAI_AVAILABLE:
        raise AgentError(
            "openai package is not installed. Run: pip install openai"
        ) from _OPENAI_IMPORT_ERROR
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AgentError(
            "OPENAI_API_KEY environment variable is not set."
        )
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
    except Exception as exc:  # openai raises a wide range of API errors
        raise AgentError(f"OpenAI request failed (model={model}): {exc}") from exc

    if not response.choices:
        raise AgentError(f"OpenAI returned no choices (model={model}).")
    content = response.choices[0].message.content
    if not content:
        raise AgentError(f"OpenAI returned an empty message (model={model}).")
    return content


def _parse_plan(raw: str) -> list[dict[str, Any]]:
    """Extract and parse the JSON plan from *raw* LLM output."""
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        )
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AgentError(
            f"Model output is not valid JSON ({exc}). Output was: {raw[:500]!r}"
        ) from exc

    if not isinstance(plan, list) or not all(isinstance(e, dict) for e in plan):
        raise AgentError(
            "Model output must be a JSON array of plan objects; got "
            f"{type(plan).__name__}: {raw[:500]!r}"
        )
    return plan


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

class CodingAgent:
    """Orchestrates the LLM-driven script generation loop."""

    def __init__(
        self,
        *,
        dry_run: bool = True,
        auto_apply: bool = False,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.dry_run = dry_run and not auto_apply
        self.model = model
        log.info(
            "CodingAgent initialized (dry_run=%s, model=%s)",
            self.dry_run,
            self.model,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, task: str) -> list[Path]:
        """Run the agent for *task* and return the list of files written."""
        log.info("Task: %s", task)

        if not self.dry_run:
            self._recommend_git_snapshot()

        plan = self._plan(task)
        log.info("Plan contains %d script(s).", len(plan))

        written: list[Path] = []
        failures: list[str] = []
        for entry in plan:
            filename = entry.get("filename", "<unnamed>")
            try:
                path = self._apply_entry(entry)
            except (OSError, ValueError) as exc:
                log.error("Failed to apply '%s': %s", filename, exc)
                failures.append(filename)
                continue
            if path:
                written.append(path)

        if failures:
            raise AgentError(
                f"{len(failures)} of {len(plan)} script(s) could not be written: "
                + ", ".join(failures)
            )
        return written

    def suggest(self, task: str) -> str:
        """Return a human-readable plan without writing any files."""
        plan = self._plan(task)
        lines = ["Suggested plan:"]
        for i, entry in enumerate(plan, 1):
            cat = entry.get("category", "?")
            fn = entry.get("filename", "?")
            desc = entry.get("description", "")
            lines.append(f"  {i}. [{cat}] {fn} — {desc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _plan(self, task: str) -> list[dict[str, Any]]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        raw = _call_llm(messages, model=self.model)
        return _parse_plan(raw)

    def _apply_entry(self, entry: dict[str, Any]) -> Path | None:
        category = entry.get("category", "utilities")
        filename = entry.get("filename", "script.py")
        body = entry.get("body", "")

        if category not in CATEGORIES:
            log.warning("Unknown category '%s'; defaulting to utilities.", category)
            category = "utilities"

        dest = CATEGORIES[category] / filename
        result = tool_write_file(dest, body, dry_run=self.dry_run)
        log.info(result)
        return None if self.dry_run else dest

    def _recommend_git_snapshot(self) -> None:
        log.info(
            "Recommendation: create a git snapshot before the agent writes files.\n"
            "  git add -A && git commit -m 'snapshot before agent run'"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copilot Script Agent — generates Python automation scripts.",
    )
    parser.add_argument("task", nargs="?", help="Natural-language task description.")
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        default=False,
        help="Write generated scripts to disk (default: dry-run only).",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        default=False,
        help="Print a plan without writing any files.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        default=False,
        help="List existing scripts and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_files:
        files = tool_list_files()
        if files:
            print("\n".join(files))
        else:
            print("No scripts found.")
        return 0

    if not args.task:
        parser.print_help()
        return 1

    agent = CodingAgent(
        dry_run=not args.auto_apply,
        auto_apply=args.auto_apply,
        model=args.model,
    )

    try:
        if args.suggest:
            print(agent.suggest(args.task))
            return 0
        written = agent.run(args.task)
    except AgentError as exc:
        log.error("%s", exc)
        return 1
    except (OSError, ValueError) as exc:
        log.error("Agent run failed: %s", exc)
        return 1

    if written:
        print("Files written:")
        for p in written:
            print(f"  {p.relative_to(REPO_ROOT)}")
    else:
        print("Dry-run complete — no files written. Pass --auto-apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

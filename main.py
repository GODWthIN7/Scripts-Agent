"""
main.py — Entrypoint for Copilot Script Agent.

Examples
--------
List existing scripts::

    python main.py --list-files

Get a plan without writing files::

    python main.py --suggest "Create a script that fetches GitHub issues and exports them to CSV"

Generate scripts (dry-run)::

    python main.py "Archive logs older than 30 days"

Generate and write scripts to disk::

    python main.py --auto-apply "Archive logs older than 30 days"
"""

import sys

from agent.coding_agent import main

if __name__ == "__main__":
    sys.exit(main())

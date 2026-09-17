#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Backward-compatible execution forwarder for fleet-refresh.
Delegates to canonical implementation in 08-Base-Scripts.

DATA FLOW:
Forwards CLI execution to `python3 08-Base-Scripts/main.py fleet-refresh "$@"`.
"""

import sys
import subprocess
from pathlib import Path

def main() -> None:
    current = Path(__file__).resolve().parent
    workspace_root = current.parents[2]
    main_py = workspace_root / "obsidian-brain" / "08-Base-Scripts" / "main.py"
    if not main_py.exists():
        main_py = current.parent.parent / "08-Base-Scripts" / "main.py"

    cmd = [sys.executable, str(main_py), "fleet-refresh"] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)

if __name__ == "__main__":
    main()

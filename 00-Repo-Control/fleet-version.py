#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Fleet-level execution forwarder for fleet-version.
Delegates to canonical fleet-version implementation in 08-Squad-Agent.

DATA FLOW:
Forwards CLI execution to `python3 08-Squad-Agent/main.py fleet-version "$@"`.
"""

import sys
import subprocess
from pathlib import Path

def main() -> None:
    current = Path(__file__).resolve().parent
    workspace_root = current.parents[2]
    main_py = workspace_root / "obsidian-brain" / "08-Squad-Agent" / "main.py"

    cmd = [sys.executable, str(main_py), "fleet-version"] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)

if __name__ == "__main__":
    main()

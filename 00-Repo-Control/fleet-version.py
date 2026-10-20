#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Fleet-level execution forwarder for fleet-version.
Delegates to canonical fleet-version implementation in 08-Squad-Agent.

DATA FLOW:
1. Forwards CLI execution to `python3 08-Squad-Agent/main.py fleet-version "$@"`.

KEY PARAMETERS:
- sys.argv: Command-line arguments forwarded to target script.
"""

import sys
import subprocess
from pathlib import Path

def main() -> None:
    current = Path(__file__).resolve().parent
    vault_root = current.parents[1]
    squad_dir = vault_root / "08-Squad-Agent"
    main_py = squad_dir / "main.py"

    venv_py = squad_dir / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python3")
    py_exec = str(venv_py) if venv_py.exists() else sys.executable

    cmd = [py_exec, str(main_py), "fleet-version"] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)

if __name__ == "__main__":
    main()

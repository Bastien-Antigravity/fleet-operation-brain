#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Audits the Deployment Logs folder and archives historical deployment logs
into the 'deployments/' folder (with context firewall ignore rules).

DATA FLOW:
1. Scans the directory root for *.md log files.
2. Extracts dates from the filenames to determine the latest log.
3. Moves historical logs to deployments/ and updates Deployment-Logs-MOC.md.

KEY PARAMETERS:
- None
"""

# [SCAN] Role: Developer | Source: archive.py (Deployment Logs) | State: Active

from os import name as osName, execl as osExecl
from os.path import (
    dirname as osPathDirname,
    abspath as osPathAbspath,
    exists as osPathExists,
    join as osPathJoin,
    samefile as osPathSamefile,
)
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit
from re import compile as reCompile, match as reMatch
from shutil import move as shutilMove
from pathlib import Path as pathlibPath
from typing import (
    Optional as typingOptional,
    List as typingList,
    Dict as typingDict,
    Any as typingAny,
    Tuple as typingTuple,
)

# -----------------------------------------------------------------------------------------------
# Venv bootstrap
# -----------------------------------------------------------------------------------------------
_venv_dir = osPathDirname(osPathAbspath(__file__))
while _venv_dir and _venv_dir != '/' and not osPathExists(osPathJoin(_venv_dir, ".venv")):
    _parent = osPathDirname(_venv_dir)
    if _parent == _venv_dir:
        break
    _venv_dir = _parent
_venv_python = (
    osPathJoin(_venv_dir, ".venv", "Scripts", "python.exe")
    if osName == "nt"
    else osPathJoin(_venv_dir, ".venv", "bin", "python3")
)
if osPathExists(_venv_python):
    try:
        if not osPathSamefile(sysExecutable, _venv_python):
            osExecl(_venv_python, _venv_python, *sysArgv)
    except OSError:
        pass


# -----------------------------------------------------------------------------------------------

class DeploymentLogsArchiver:
    """
    Manages the lifecycle of deployment logs, ensuring only the most relevant log is in the main context.
    """

    def __init__(self, *, config: typingAny, logger: typingAny, name: typingOptional[str] = None) -> None:
        self.config = config
        self.logger = logger
        self.Name = name or self.__class__.__name__

    # -----------------------------------------------------------------------------------------------

    def run_archive(self) -> None:
        """
        Executes the archive workflow.
        """
        root = pathlibPath(__file__).resolve().parent
        archive_dir = root / "deployments"

        # 1. Ensure archive directory exists
        archive_dir.mkdir(exist_ok=True)

        # 2. Ensure ignore files exist
        self._ensure_firewall(archive_dir=archive_dir)

        # 3. Scan for log files
        targets = [f for f in root.glob("*.md") if f.name != "README.md" and f.name != "Deployment-Logs-MOC.md"]

        if not targets:
            self.logger.info("{0} : ✨ DEPLOYMENT LOGS DIRECTORY IS ALREADY PERFECT!".format(self.Name))
            return

        # 4. Find the latest log
        latest_log, historical_logs = self._identify_logs(targets=targets)

        self.logger.info("{0} : 🌟 ACTIVE DEPLOYMENT LOG RETAINED: {1}".format(self.Name, latest_log["name"]))

        if not historical_logs:
            self.logger.info("{0} : ✨ No historical log files need archiving.".format(self.Name))
        else:
            self._archive_files(historical_logs=historical_logs, archive_dir=archive_dir)

        # 5. Update MOC
        self._update_moc(latest_log=latest_log)
        self.logger.info("{0} : ✅ DEPLOYMENT LOGS HOUSEKEEPING COMPLETE!".format(self.Name))

    # -----------------------------------------------------------------------------------------------

    def _ensure_firewall(self, *, archive_dir: pathlibPath) -> None:
        ignore_files = [".aiignore", ".mcpignore", ".geminiignore"]
        for filename in ignore_files:
            ignore_file = archive_dir / filename
            if not ignore_file.exists():
                try:
                    with open(ignore_file, "w", encoding="utf-8") as f: f.write("*\n")
                    self.logger.info("{0} : ✨ Created context firewall: deployments/{1}".format(self.Name, filename))
                except Exception as e:
                    self.logger.error("{0} : Failed to create firewall {1}: {2}".format(self.Name, filename, e))

    # -----------------------------------------------------------------------------------------------

    def _identify_logs(self, *, targets: typingList[pathlibPath]) -> typingTuple[typingDict[str, typingAny], typingList[typingDict[str, typingAny]]]:
        date_regex = reCompile(r"(\d{4}-\d{2}-\d{2})")
        log_info = []

        for filepath in targets:
            match = date_regex.search(filepath.name)
            date_str = match.group(1) if match else "1970-01-01"
            mtime = filepath.stat().st_mtime
            log_info.append({"path": filepath, "name": filepath.name, "date": date_str, "mtime": mtime})

        log_info.sort(key=lambda x: (x["date"], x["mtime"]), reverse=True)
        return log_info[0], log_info[1:]

    # -----------------------------------------------------------------------------------------------

    def _archive_files(self, *, historical_logs: typingList[typingDict[str, typingAny]], archive_dir: pathlibPath) -> None:
        self.logger.info("{0} : 📦 ARCHIVING {1} HISTORICAL LOG(S):".format(self.Name, len(historical_logs)))
        for log in historical_logs:
            filepath = log["path"]
            dest = archive_dir / filepath.name
            if dest.exists():
                dest = archive_dir / "{0}_{1}{2}".format(filepath.stem, 1, filepath.suffix)

            try:
                shutilMove(str(filepath), str(dest))
                self.logger.info("{0} :   [-] Archived: {1}".format(self.Name, filepath.name))
            except Exception as e:
                self.logger.error("{0} : Failed to archive {1}: {2}".format(self.Name, filepath.name, e))

    # -----------------------------------------------------------------------------------------------

    def _update_moc(self, *, latest_log: typingDict[str, typingAny]) -> None:
        root = pathlibPath(__file__).resolve().parent
        moc_path = root.parent / "Deployment-Logs-MOC.md"
        if moc_path.exists():
            try:
                with open(moc_path, "r", encoding="utf-8") as f:
                    content = f.read()

                fm_match = reMatch(r"^---[\s\S]*?---\n*", content)
                fm = fm_match.group(0) if fm_match else ""

                new_content = (
                    "{0}"
                    "# Deployment Logs MOC\n\n"
                    "### Active Deployment Log\n"
                    "- [[{1}]]\n\n"
                    "### Archived Historical Logs\n"
                    "> Stored in the `deployments/` firewall zone.\n"
                ).format(fm, latest_log["path"].stem)

                with open(moc_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.logger.info("{0} : ✨ Updated Deployment-Logs-MOC.md".format(self.Name))
            except Exception as e:
                self.logger.error("{0} : Failed to update MOC: {1}".format(self.Name, e))


# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    class DefaultLogger:
        def info(self, msg: str) -> None: print(msg)
        def error(self, msg: str) -> None: print(msg)
        def critical(self, msg: str) -> None: print(msg)

    archiver = DeploymentLogsArchiver(config=object(), logger=DefaultLogger())
    archiver.run_archive()

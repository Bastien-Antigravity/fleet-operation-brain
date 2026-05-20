#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Audits the Deployment Logs folder and archives historical deployment logs
into the 'deployments/' folder (with context firewall ignore rules),
retaining only the absolute latest deployment log file in the main folder.

DATA FLOW:
1. Scans the directory root for *.md log files.
2. Extracts dates from the filenames to determine the latest log and moves historical ones.
3. Moves historical logs to deployments/ and updates Deployment-Logs-MOC.md.

KEY PARAMETERS:
- None
"""

from os import name as osName, execl as osExecl
from os.path import dirname as osPathDirname, abspath as osPathAbspath, exists as osPathExists, join as osPathJoin, samefile as osPathSamefile
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit
from re import compile as reCompile, match as reMatch
from shutil import move as shutilMove
from pathlib import Path as pathlibPath
from typing import Optional as typingOptional, List as typingList, Dict as typingDict, Any as typingAny

# Ensure we are running inside the virtual environment
_venv_dir = osPathDirname(osPathAbspath(__file__))
while _venv_dir and _venv_dir != '/' and not osPathExists(osPathJoin(_venv_dir, ".venv")):
    _parent = osPathDirname(_venv_dir)
    if _parent == _venv_dir:
        break
    _venv_dir = _parent
_venv_python = osPathJoin(_venv_dir, ".venv", "Scripts", "python.exe") if osName == "nt" else osPathJoin(_venv_dir, ".venv", "bin", "python3")
if osPathExists(_venv_python):
    try:
        if not osPathSamefile(sysExecutable, _venv_python):
            osExecl(_venv_python, _venv_python, *sysArgv)
    except OSError:
        pass

# -----------------------------------------------------------------------------------------------

class DeploymentLogsArchiver:
    Name = "DeploymentLogsArchiver"

    def __init__(self, config: object, logger: object, name: typingOptional[str] = None) -> None:
        self.config = config
        self.logger = logger
        self.Name = name if name is not None else "DeploymentLogsArchiver"

    # -----------------------------------------------------------------------------------------------

    def run_archive(self) -> None:
        """
        Executes the archive workflow for historical deployment logs.
        """
        root = pathlibPath(__file__).resolve().parent
        archive_dir = root / "deployments"

        # 1. Ensure archive directory exists
        archive_dir.mkdir(exist_ok=True)

        # 2. Ensure ignore files exist inside deployments/
        ignore_files = [".aiignore", ".mcpignore", ".geminiignore"]
        for filename in ignore_files:
            ignore_file = archive_dir / filename
            if not ignore_file.exists():
                try:
                    with open(ignore_file, "w", encoding="utf-8") as f:
                        f.write("*\n")
                    self.logger.info("{0} : ✨ Created context firewall ignore file: deployments/{1}".format(self.Name, filename))
                except Exception as e:
                    self.logger.error("{0} : Failed to create ignore file {1}: {2}".format(self.Name, filename, e))

        # 3. Scan for markdown files to process (excluding MOC/Archive scripts if any)
        targets = [f for f in root.glob("*.md") if f.name != "README.md" and f.name != "Deployment-Logs-MOC.md"]

        if not targets:
            self.logger.info("{0} : ✨ DEPLOYMENT LOGS DIRECTORY IS ALREADY PERFECT!".format(self.Name))
            return

        # 4. Parse dates from filenames to find the latest
        date_regex = reCompile(r"(\d{4}-\d{2}-\d{2})")
        log_info = []

        for filepath in targets:
            match = date_regex.search(filepath.name)
            date_str = match.group(1) if match else "1970-01-01"
            try:
                mtime = filepath.stat().st_mtime
            except Exception:
                mtime = 0.0
            log_info.append({
                "path": filepath,
                "name": filepath.name,
                "date": date_str,
                "mtime": mtime
            })

        # Sort by date string first, then by modification time to find the absolute latest log
        log_info.sort(key=lambda x: (x["date"], x["mtime"]), reverse=True)

        latest_log = log_info[0]
        historical_logs = log_info[1:]

        self.logger.info("{0} : 🌟 ACTIVE DEPLOYMENT LOG RETAINED:".format(self.Name))
        self.logger.info("{0} :   [+] {1} (Date: {2})".format(self.Name, latest_log["name"], latest_log["date"]))

        if not historical_logs:
            self.logger.info("{0} : ✨ No historical log files need archiving.".format(self.Name))
        else:
            self.logger.info("{0} : 📦 FOUND {1} HISTORICAL LOG(S) TO ARCHIVE:".format(self.Name, len(historical_logs)))
            for log in historical_logs:
                filepath = log["path"]
                dest = archive_dir / filepath.name

                # Avoid name collisions in the archive
                if dest.exists():
                    base = filepath.stem
                    ext = filepath.suffix
                    counter = 1
                    while (archive_dir / "{0}_{1}{2}".format(base, counter, ext)).exists():
                        counter += 1
                    dest = archive_dir / "{0}_{1}{2}".format(base, counter, ext)

                try:
                    shutilMove(str(filepath), str(dest))
                    self.logger.info("{0} :   [-] Archived: {1} -> deployments/{2}".format(self.Name, filepath.name, dest.name))
                except Exception as e:
                    self.logger.error("{0} : Failed to move {1} to archive: {2}".format(self.Name, filepath.name, e))

        # 5. Update the parent Deployment-Logs-MOC.md links
        self._update_moc(latest_log)
        self.logger.info("{0} : ✅ DEPLOYMENT LOGS HOUSEKEEPING COMPLETE!".format(self.Name))

    # -----------------------------------------------------------------------------------------------

    def _update_moc(self, latest_log: typingDict[str, typingAny]) -> None:
        """
        Updates the parent MOC file links.
        """
        root = pathlibPath(__file__).resolve().parent
        moc_path = root.parent / "Deployment-Logs-MOC.md"
        if moc_path.exists():
            try:
                with open(moc_path, "r", encoding="utf-8") as f:
                    content = f.read()

                frontmatter_match = reMatch(r"^---[\s\S]*?---\n*", content)
                frontmatter = frontmatter_match.group(0) if frontmatter_match else ""

                new_moc_content = (
                    "{0}"
                    "# Deployment Logs MOC\n\n"
                    "This index manages active deployment logs.\n\n"
                    "### Active Deployment Log\n"
                    "- [[{1}]]\n\n"
                    "### Archived Historical Logs\n"
                    "> Archived logs are stored in the `deployments/` firewall zone to maintain minimal context weight.\n"
                ).format(frontmatter, latest_log["path"].stem)

                with open(moc_path, "w", encoding="utf-8") as f:
                    f.write(new_moc_content)
                self.logger.info("{0} : ✨ Updated Deployment-Logs-MOC.md with the active layout!".format(self.Name))
            except Exception as e:
                self.logger.error("{0} : ⚠️ Warning: Failed to update Deployment-Logs-MOC.md: {1}".format(self.Name, e))

# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    class DefaultLogger:
        def info(self, msg: str) -> None:
            print(msg)
        def error(self, msg: str) -> None:
            print(msg)
        def critical(self, msg: str) -> None:
            print(msg)

    archiver = DeploymentLogsArchiver(config=object(), logger=DefaultLogger())
    archiver.run_archive()

#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Audits the Fleet Action Plans folder and archives completed or historical plans
into the 'plans/' folder (with context firewall ignore rules).

DATA FLOW:
1. Scans the directory root for *.md plan files.
2. Reads frontmatter to identify 'completed' or historical plans.
3. Moves completed plans to plans/ and updates README.md.

KEY PARAMETERS:
- None
"""

# [SCAN] Role: Developer | Source: archive.py (Action Plans) | State: Active

from os import name as osName, execl as osExecl
from os.path import (
    dirname as osPathDirname,
    abspath as osPathAbspath,
    exists as osPathExists,
    join as osPathJoin,
    samefile as osPathSamefile,
)
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit
from re import match as reMatch, search as reSearch
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

class FleetActionPlansArchiver:
    """
    Handles the archival of completed fleet action plans to maintain context efficiency.
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
        archive_dir = root / "plans"

        # 1. Ensure archive directory exists
        archive_dir.mkdir(exist_ok=True)

        # 2. Ensure ignore files exist
        self._ensure_firewall(archive_dir=archive_dir)

        # 3. Scan for markdown files
        targets = [f for f in root.glob("*.md") if f.name != "README.md"]

        if not targets:
            self.logger.info("{0} : ✨ FLEET ACTION PLANS DIRECTORY IS ALREADY PERFECT!".format(self.Name))
            return

        # 4. Check for active migrations
        no_active_migrations = self._check_active_migrations(root=root)

        to_archive = []
        retained = []

        for filepath in targets:
            is_completed = self._is_plan_completed(filepath=filepath)
            if is_completed or no_active_migrations:
                to_archive.append(filepath)
            else:
                retained.append(filepath)

        if retained:
            self.logger.info("{0} : 🌟 ACTIVE FLEET ACTION PLAN(S) RETAINED:".format(self.Name))
            for r in retained:
                self.logger.info("{0} :   [+] {1}".format(self.Name, r.name))

        if not to_archive:
            self.logger.info("{0} : ✨ No historical action plans need archiving.".format(self.Name))
        else:
            self._archive_files(files=to_archive, archive_dir=archive_dir)

        # 5. Update MOC
        self._update_moc(retained=retained)
        self.logger.info("{0} : ✅ FLEET ACTION PLANS HOUSEKEEPING COMPLETE!".format(self.Name))

    # -----------------------------------------------------------------------------------------------

    def _ensure_firewall(self, *, archive_dir: pathlibPath) -> None:
        ignore_files = [".aiignore", ".mcpignore", ".geminiignore"]
        for filename in ignore_files:
            ignore_file = archive_dir / filename
            if not ignore_file.exists():
                try:
                    with open(ignore_file, "w", encoding="utf-8") as f:
                        f.write("*\n")
                    self.logger.info("{0} : ✨ Created context firewall: plans/{1}".format(self.Name, filename))
                except Exception as e:
                    self.logger.error("{0} : Failed to create firewall {1}: {2}".format(self.Name, filename, e))

    # -----------------------------------------------------------------------------------------------

    def _check_active_migrations(self, *, root: pathlibPath) -> bool:
        readme_path = root.parent / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    return "Ongoing Migrations: None" in f.read()
            except Exception:
                pass
        return True

    # -----------------------------------------------------------------------------------------------

    def _is_plan_completed(self, *, filepath: pathlibPath) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                status_match = reSearch(r"status:\s*(\w+)", content)
                return status_match and status_match.group(1).lower() == "completed"
        except Exception:
            return False

    # -----------------------------------------------------------------------------------------------

    def _archive_files(self, *, files: typingList[pathlibPath], archive_dir: pathlibPath) -> None:
        self.logger.info("{0} : 📦 ARCHIVING {1} HISTORICAL PLAN(S):".format(self.Name, len(files)))
        for filepath in files:
            dest = archive_dir / filepath.name
            if dest.exists():
                dest = archive_dir / "{0}_{1}{2}".format(filepath.stem, 1, filepath.suffix)

            try:
                shutilMove(str(filepath), str(dest))
                self.logger.info("{0} :   [-] Archived: {1}".format(self.Name, filepath.name))
            except Exception as e:
                self.logger.error("{0} : Failed to archive {1}: {2}".format(self.Name, filepath.name, e))

    # -----------------------------------------------------------------------------------------------

    def _update_moc(self, *, retained: typingList[pathlibPath]) -> None:
        root = pathlibPath(__file__).resolve().parent
        readme_path = root / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()

                fm_match = reMatch(r"^---[\s\S]*?---\n*", content)
                fm = fm_match.group(0) if fm_match else ""

                links = "\n".join(["- [[{0}]]".format(r.stem) for r in retained]) or "*None currently active.*"
                
                new_content = (
                    "{0}"
                    "# 📋 Fleet Action Plans\n\n"
                    "This index manages active and historical fleet migrations and multi-repository updates in Mode 3 (Orchestrator).\n\n"
                    "## 🚀 Active Migration Plans\n"
                    "{1}\n\n"
                    "## 📦 Archived Historical Plans\n"
                    "Historical plans are archived in [`plans/`](plans/) with context firewall ignore rules (`.aiignore`, `.geminiignore`, `.mcpignore`) to maintain minimal context weight for AI agents.\n\n"
                    "- [[FAP-2026-05-03-GitHub-Sync]]\n"
                    "- [[2026-05-11-Standardize-GitHub-CI]]\n\n"
                    "## 🛠️ Archiving Workflow\n"
                    "Run `python3 archive.py` to automatically detect completed plans and move them into `plans/`, updating this index.\n"
                ).format(fm, links)

                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.logger.info("{0} : ✨ Updated README.md index".format(self.Name))
            except Exception as e:
                self.logger.error("{0} : Failed to update index: {1}".format(self.Name, e))


# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    class DefaultLogger:
        def info(self, msg: str) -> None: print(msg)
        def error(self, msg: str) -> None: print(msg)
        def critical(self, msg: str) -> None: print(msg)

    archiver = FleetActionPlansArchiver(config=object(), logger=DefaultLogger())
    archiver.run_archive()

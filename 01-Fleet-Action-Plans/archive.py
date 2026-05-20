#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Audits the Fleet Action Plans folder and archives completed or historical plans
into the 'plans/' folder (with context firewall ignore rules),
ensuring the folder remains pristine.

DATA FLOW:
1. Scans the directory root for *.md plan files.
2. Reads frontmatter to identify 'completed' or historical plans.
3. Moves completed plans to plans/ and updates Fleet-Action-Plans-MOC.md.

KEY PARAMETERS:
- None
"""

from os import name as osName, execl as osExecl
from os.path import dirname as osPathDirname, abspath as osPathAbspath, exists as osPathExists, join as osPathJoin, samefile as osPathSamefile
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit
from re import match as reMatch, search as reSearch
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

class FleetActionPlansArchiver:
    Name = "FleetActionPlansArchiver"

    def __init__(self, config: object, logger: object, name: typingOptional[str] = None) -> None:
        self.config = config
        self.logger = logger
        self.Name = name if name is not None else "FleetActionPlansArchiver"

    # -----------------------------------------------------------------------------------------------

    def run_archive(self) -> None:
        """
        Executes the archive workflow for historical fleet action plans.
        """
        root = pathlibPath(__file__).resolve().parent
        archive_dir = root / "plans"

        # 1. Ensure archive directory exists
        archive_dir.mkdir(exist_ok=True)

        # 2. Ensure ignore files exist inside plans/
        ignore_files = [".aiignore", ".mcpignore", ".geminiignore"]
        for filename in ignore_files:
            ignore_file = archive_dir / filename
            if not ignore_file.exists():
                try:
                    with open(ignore_file, "w", encoding="utf-8") as f:
                        f.write("*\n")
                    self.logger.info("{0} : ✨ Created context firewall ignore file: plans/{1}".format(self.Name, filename))
                except Exception as e:
                    self.logger.error("{0} : Failed to create ignore file {1}: {2}".format(self.Name, filename, e))

        # 3. Scan for markdown files to process (excluding README.md, MOC, or script files)
        targets = [f for f in root.glob("*.md") if f.name != "README.md" and f.name != "Fleet-Action-Plans-MOC.md"]

        if not targets:
            self.logger.info("{0} : ✨ FLEET ACTION PLANS DIRECTORY IS ALREADY PERFECT!".format(self.Name))
            return

        # 4. Check for active migrations in the main README
        readme_path = root.parent / "README.md"
        no_active_migrations = True
        if readme_path.exists():
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    readme_text = f.read()
                    if "Ongoing Migrations: None" not in readme_text:
                        no_active_migrations = False
            except Exception as e:
                self.logger.error("{0} : Failed to read README.md: {1}".format(self.Name, e))

        to_archive = []
        retained = []

        for filepath in targets:
            # Check YAML frontmatter for status
            is_completed = False
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    status_match = reSearch(r"status:\s*(\w+)", content)
                    if status_match and status_match.group(1).lower() == "completed":
                        is_completed = True
            except Exception as e:
                self.logger.error("{0} : Failed to check status of {1}: {2}".format(self.Name, filepath.name, e))

            # Archive if status is completed OR if the global state indicates no active migrations
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
            self.logger.info("{0} : 📦 FOUND {1} HISTORICAL ACTION PLAN(S) TO ARCHIVE:".format(self.Name, len(to_archive)))
            for filepath in to_archive:
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
                    self.logger.info("{0} :   [-] Archived: {1} -> plans/{2}".format(self.Name, filepath.name, dest.name))
                except Exception as e:
                    self.logger.error("{0} : Failed to move {1} to archive: {2}".format(self.Name, filepath.name, e))

        # 5. Update the parent Fleet-Action-Plans-MOC.md links
        self._update_moc(retained)
        self.logger.info("{0} : ✅ FLEET ACTION PLANS HOUSEKEEPING COMPLETE!".format(self.Name))

    # -----------------------------------------------------------------------------------------------

    def _update_moc(self, retained: typingList[pathlibPath]) -> None:
        """
        Updates the parent MOC file links.
        """
        root = pathlibPath(__file__).resolve().parent
        moc_path = root.parent / "Fleet-Action-Plans-MOC.md"
        if moc_path.exists():
            try:
                with open(moc_path, "r", encoding="utf-8") as f:
                    content = f.read()

                frontmatter_match = reMatch(r"^---[\s\S]*?---\n*", content)
                frontmatter = frontmatter_match.group(0) if frontmatter_match else ""

                # Build active links list
                active_links_str = ""
                for r in retained:
                    active_links_str += "- [[{0}]]\n".format(r.stem)
                if not active_links_str:
                    active_links_str = "*None currently active.*\n"

                new_moc_content = (
                    "{0}"
                    "# Fleet Action Plans MOC\n\n"
                    "This index manages active and historical fleet migrations.\n\n"
                    "### Active Migration Plans\n"
                    "{1}\n"
                    "### Archived Historical Plans\n"
                    "> Archived plans are stored in the `plans/` firewall zone to maintain minimal context weight.\n"
                ).format(frontmatter, active_links_str)

                with open(moc_path, "w", encoding="utf-8") as f:
                    f.write(new_moc_content)
                self.logger.info("{0} : ✨ Updated Fleet-Action-Plans-MOC.md with the active layout!".format(self.Name))
            except Exception as e:
                self.logger.error("{0} : ⚠️ Warning: Failed to update Fleet-Action-Plans-MOC.md: {1}".format(self.Name, e))

# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    class DefaultLogger:
        def info(self, msg: str) -> None:
            print(msg)
        def error(self, msg: str) -> None:
            print(msg)
        def critical(self, msg: str) -> None:
            print(msg)

    archiver = FleetActionPlansArchiver(config=object(), logger=DefaultLogger())
    archiver.run_archive()

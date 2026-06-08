#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Performs a "Nuclear Refresh" of repositories by wiping existing local folders
and re-cloning from source (GitHub or Inventory).

DATA FLOW:
1. Fetches repository lists from either GitHub API or inventory.json.
2. For each repository, performs a targeted deletion of the local folder.
3. Handles Windows-specific read-only file lock issues during deletion.
4. Executes a fresh git clone into the target directory.

KEY PARAMETERS:
- account: The GitHub account to fetch from.
- target: Target directory for clones.
- dry_run: If True, only simulate actions.
- use_inventory: If True, use inventory.json instead of GitHub API.
"""

# [SCAN] Role: Developer | Source: fleet-refresh.py | State: Active

from os import name as osName, execl as osExecl, chmod as osChmod, rename as osRename, makedirs as osMakedirs
from os.path import (
    dirname as osPathDirname,
    abspath as osPathAbspath,
    exists as osPathExists,
    join as osPathJoin,
    samefile as osPathSamefile,
)
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit, stdout as sysStdout
from shutil import rmtree as shutilRmtree
from subprocess import run as subprocessRun
from json import load as jsonLoad, loads as jsonLoads
from time import time as timeTime
from pathlib import Path as pathlibPath
from typing import (
    List as typingList,
    Dict as typingDict,
    Any as typingAny,
    Optional as typingOptional,
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

# Standardize terminal output encoding
if sysStdout.encoding != 'utf-8':
    try:
        sysStdout.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

# ### CONFIGURATIONS ###
DEFAULT_USER = "Bastien-Antigravity"


# -----------------------------------------------------------------------------------------------

class FleetRefresher:
    """
    Core class for performing fresh repository resets across the fleet.
    """

    def __init__(self, *, config: typingAny, logger: typingAny, name: typingOptional[str] = None) -> None:
        self.config = config
        self.logger = logger
        self.Name = name or self.__class__.__name__

    # -----------------------------------------------------------------------------------------------

    def run_refresh(self, *, account: str, target: str, dry_run: bool, use_inventory: bool) -> None:
        """
        Executes the nuclear refresh workflow.
        """
        repos_to_refresh = []

        if use_inventory:
            inventory_path = pathlibPath(__file__).resolve().parent / "inventory.json"
            if not inventory_path.exists():
                self.logger.critical("{0} : [CRITICAL] inventory.json not found at {1}".format(self.Name, inventory_path))
                sysExit(1)

            try:
                with open(inventory_path, "r", encoding='utf-8') as f:
                    inventory = jsonLoad(f)
                    for r in inventory.get("repositories", []):
                        repos_to_refresh.append({
                            "name": r["name"],
                            "clone_url": r["remote"]
                        })
                self.logger.info("{0} : Loaded {1} repos from inventory.".format(self.Name, len(repos_to_refresh)))
            except Exception as e:
                self.logger.critical("{0} : Failed to load inventory: {1}".format(self.Name, e))
                sysExit(1)
        else:
            repos_to_refresh = self.get_github_repos(user=account)

        if repos_to_refresh:
            self.refresh_repos(repos=repos_to_refresh, target_base_dir=target, dry_run=dry_run)
            self.logger.info("{0} : \n--- Fleet Refresh operations finished ---".format(self.Name))
        else:
            self.logger.error("{0} : [ERROR] No repositories found to refresh.".format(self.Name))
            sysExit(1)

    # -----------------------------------------------------------------------------------------------

    def get_github_repos(self, *, user: str) -> typingOptional[typingList[typingDict[str, typingAny]]]:
        """
        Fetches repository list from GitHub API.
        """
        from urllib.request import Request as urllibRequestRequest, urlopen as urllibRequestUrlopen

        self.logger.info("{0} : Step 1: Fetching repositories for '{1}' from GitHub...".format(self.Name, user))
        repos = []
        page = 1
        while True:
            api_url = "https://api.github.com/users/{0}/repos?page={1}&per_page=100".format(user, page)
            try:
                request = urllibRequestRequest(api_url)
                request.add_header('User-Agent', 'Python-Fleet-Refresher')
                with urllibRequestUrlopen(request) as response:
                    page_repos = jsonLoads(response.read().decode('utf-8'))
                    if not page_repos:
                        break
                    repos.extend(page_repos)
                    page += 1
            except Exception as e:
                self.logger.error("{0} :   [CRITICAL] API Error on page {1}: {2}".format(self.Name, page, e))
                return None
        return repos

    # -----------------------------------------------------------------------------------------------

    def refresh_repos(self, *, repos: typingList[typingDict[str, typingAny]], target_base_dir: str = ".", dry_run: bool = False) -> None:
        """
        Strict deletion and re-cloning logic for a list of repositories.
        """
        self.logger.info("{0} : Step 2: Processing {1} repositories in '{2}'...".format(self.Name, len(repos), target_base_dir))

        if dry_run:
            self.logger.info("{0} :   [DRY RUN] No files will be deleted or cloned.".format(self.Name))

        if target_base_dir != "." and not osPathExists(target_base_dir):
            if not dry_run:
                try:
                    osMakedirs(target_base_dir)
                except Exception as e:
                    self.logger.error("{0} : Failed to create target directory {1}: {2}".format(self.Name, target_base_dir, e))
                    return
            self.logger.info("{0} :   [INFO] Target directory ready: {1}".format(self.Name, target_base_dir))

        for repo in repos:
            name = repo['name']
            clone_url = repo['clone_url']
            target_path = osPathJoin(target_base_dir, name)

            if osPathExists(target_path):
                if dry_run:
                    self.logger.info("{0} :   [DRY RUN] Would remove existing folder: {1}".format(self.Name, target_path))
                else:
                    self.logger.info("{0} :   [CLEAN] Removing existing folder: {1}".format(self.Name, target_path))
                    try:
                        shutilRmtree(target_path, onerror=self._handle_remove_readonly)
                    except Exception as e:
                        self.logger.error("{0} :     [WARNING] Initial deletion failed, attempting rename/move: {1}".format(self.Name, e))
                        try:
                            backup_name = "{0}_DEPRECATED_{1}".format(target_path, int(timeTime()))
                            osRename(target_path, backup_name)
                            self.logger.info("{0} :     [INFO] Moved locked folder to {1}".format(self.Name, backup_name))
                        except Exception as e2:
                            self.logger.error("{0} :     [CRITICAL] Failed to clear path for {1}: {2}".format(self.Name, name, e2))
                            continue

            if osPathExists(target_path) and not dry_run:
                continue

            if dry_run:
                self.logger.info("{0} :   [DRY RUN] Would clone {1} into {2}".format(self.Name, name, target_path))
            else:
                self.logger.info("{0} :   [CLONE] Fetching fresh copy of {1}...".format(self.Name, name))
                result = subprocessRun(["git", "clone", clone_url, target_path], capture_output=True, text=True)

                if result.returncode == 0:
                    self.logger.info("{0} :     [SUCCESS] {1} is now up to date.".format(self.Name, name))
                else:
                    self.logger.error("{0} :     [ERROR] Clone failed for {1}: {2}".format(self.Name, name, result.stderr.strip()))

    # -----------------------------------------------------------------------------------------------

    def _handle_remove_readonly(self, func: typingAny, path: str, excinfo: typingAny) -> None:
        """
        Forcefully handles read-only files during deletion.
        """
        try:
            osChmod(path, 0o777)
            func(path)
        except Exception:
            pass


# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    class DefaultLogger:
        def info(self, msg: str) -> None: print(msg)
        def error(self, msg: str) -> None: print(msg)
        def warning(self, msg: str) -> None: print(msg)
        def critical(self, msg: str) -> None: print(msg)

    parser = argparse.ArgumentParser(description="Nuclear Refresh: Wipe and re-clone repositories.")
    parser.add_argument("account", nargs="?", default=DEFAULT_USER, help="GitHub account")
    parser.add_argument("--target", "-t", default=".", help="Target directory")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions")
    parser.add_argument("--inventory", "-i", action="store_true", help="Use inventory.json")

    args = parser.parse_args()

    refresher = FleetRefresher(config=object(), logger=DefaultLogger())
    refresher.run_refresh(
        account=args.account,
        target=args.target,
        dry_run=args.dry_run,
        use_inventory=args.inventory
    )

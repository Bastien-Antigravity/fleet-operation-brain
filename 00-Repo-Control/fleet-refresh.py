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
- DEFAULT_USER: The default GitHub account to fetch from.
- target_base_dir: The root directory for cloning repositories.
"""
import os, sys
# Ensure we are running inside the virtual environment
_venv_dir = os.path.dirname(os.path.abspath(__file__))
while _venv_dir and _venv_dir != '/' and not os.path.exists(os.path.join(_venv_dir, ".venv")):
    _parent = os.path.dirname(_venv_dir)
    if _parent == _venv_dir:
        break
    _venv_dir = _parent
_venv_python = os.path.join(_venv_dir, ".venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join(_venv_dir, ".venv", "bin", "python3")
if os.path.exists(_venv_python):
    try:
        if not os.path.samefile(sys.executable, _venv_python):
            os.execl(_venv_python, _venv_python, *sys.argv)
    except OSError:
        pass


from sys import exit as sysExit, stdout as sysStdout
from os import chmod as osChmod, rename as osRename, makedirs as osMakedirs
from os.path import exists as osPathExists, join as osPathJoin
import shutil
from subprocess import run as subprocessRun
from json import load as jsonLoad, loads as jsonLoads
from time import time as timeTime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Standardize terminal output encoding for Windows
if sysStdout.encoding != 'utf-8':
    try:
        sysStdout.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

# ### CONFIGURATIONS ###

DEFAULT_USER = "Bastien-Antigravity"

# -----------------------------------------------------------------------------------------------

def handle_remove_readonly(func: Any, path: str, excinfo: Any) -> None:
    """
    Forcefully handles read-only files during deletion (common on Windows).
    """
    try:
        osChmod(path, 0o777)
        func(path)
    except Exception:
        pass

# -----------------------------------------------------------------------------------------------

def get_github_repos(user: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches repository list from GitHub API (handles pagination).
    """
    import urllib.request as urllibRequest
    
    print("Step 1: Fetching repositories for '{0}' from GitHub...".format(user))
    repos = []
    page = 1
    while True:
        api_url = "https://api.github.com/users/{0}/repos?page={1}&per_page=100".format(user, page)
        try:
            request = urllibRequest.Request(api_url)
            request.add_header('User-Agent', 'Python-Fleet-Refresher')
            with urllibRequest.urlopen(request) as response:
                page_repos = jsonLoads(response.read().decode('utf-8'))
                if not page_repos:
                    break
                repos.extend(page_repos)
                page += 1
        except Exception as e:
            print("  [CRITICAL] API Error on page {0}: {1}".format(page, e))
            return None
    return repos

# -----------------------------------------------------------------------------------------------

def refresh_repos(repos: List[Dict[str, Any]], target_base_dir: str = ".", dry_run: bool = False) -> None:
    """
    Strict deletion and re-cloning logic for a list of repositories.
    """
    print("Step 2: Processing {0} repositories in '{1}'...".format(len(repos), target_base_dir))
    
    if dry_run:
        print("  [DRY RUN] No files will be deleted or cloned.")

    # Ensure target directory exists
    if target_base_dir != "." and not osPathExists(target_base_dir):
        if not dry_run:
            osMakedirs(target_base_dir)
        print("  [INFO] Target directory ready: {0}".format(target_base_dir))

    for repo in repos:
        name = repo['name']
        clone_url = repo['clone_url']
        target_path = osPathJoin(target_base_dir, name)
        
        # 1. Targeted Deletion
        if osPathExists(target_path):
            if dry_run:
                print("  [DRY RUN] Would remove existing folder: {0}".format(target_path))
            else:
                print("  [CLEAN] Removing existing folder: {0}".format(target_path))
                try:
                    shutil.rmtree(target_path, onerror=handle_remove_readonly)
                except Exception as e:
                    print("    [WARNING] Initial deletion failed, attempting rename/move: {0}".format(e))
                    try:
                        timestamp = int(timeTime())
                        backup_name = "{0}_DEPRECATED_{1}".format(target_path, timestamp)
                        osRename(target_path, backup_name)
                        print("    [INFO] Moved locked folder to {0}".format(backup_name))
                        
                        # SAFETY: Deactivate Git in the deprecated folder
                        git_dir = osPathJoin(backup_name, ".git")
                        if osPathExists(git_dir):
                            try:
                                osRename(git_dir, osPathJoin(backup_name, "DISABLED_GIT_FOLDER"))
                            except Exception:
                                pass
                    except Exception as e2:
                        print("    [CRITICAL] Failed to clear path for {0}: {1}".format(name, e2))
                        continue

        # 2. Pre-Clone Verification
        if osPathExists(target_path) and not dry_run:
            print("  [ERROR] Path {0} still exists! Skipping clone.".format(target_path))
            continue
        
        # 3. Clean Clone
        if dry_run:
            print("  [DRY RUN] Would clone {0} into {1}".format(name, target_path))
        else:
            print("  [CLONE] Fetching fresh copy of {0}...".format(name))
            result = subprocessRun(["git", "clone", clone_url, target_path], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("    [SUCCESS] {0} is now up to date.".format(name))
            else:
                print("    [ERROR] Clone failed for {0}: {1}".format(name, result.stderr.strip()))

# -----------------------------------------------------------------------------------------------

def main() -> None:
    """
    Main entry point for the Fleet Refresh CLI.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Nuclear Refresh: Wipe and re-clone repositories.")
    parser.add_argument("account", nargs="?", default=DEFAULT_USER, 
                        help="GitHub username or organization (default: {0})".format(DEFAULT_USER))
    parser.add_argument("--target", "-t", default=".", 
                        help="Target directory where repos should be cloned (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Show what would be done without making changes")
    parser.add_argument("--inventory", "-i", action="store_true",
                        help="Refresh only repositories listed in inventory.json (ignores GitHub API)")

    args = parser.parse_args()
    
    account = args.account
    target = args.target
    
    repos_to_refresh = []

    if args.inventory:
        # Load from inventory.json
        inventory_path = Path(__file__).resolve().parent / "inventory.json"
        if not inventory_path.exists():
            print("[ERROR] inventory.json not found at {0}".format(inventory_path))
            sysExit(1)
        
        with open(inventory_path, "r", encoding='utf-8') as f:
            inventory = jsonLoad(f)
            for r in inventory.get("repositories", []):
                repos_to_refresh.append({
                    "name": r["name"],
                    "clone_url": r["remote"]
                })
        print("Loaded {0} repos from inventory.".format(len(repos_to_refresh)))
    else:
        # Load from GitHub
        repos_to_refresh = get_github_repos(account)

    if repos_to_refresh:
        refresh_repos(repos_to_refresh, target, args.dry_run)
        print("\n--- Fleet Refresh operations finished ---")
    else:
        print("[ERROR] No repositories found to refresh.")
        sysExit(1)

# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

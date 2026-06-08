#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Scans the workspace and reliably generates inventory.json for the Fleet Manager.

DATA FLOW:
1. Resolves vault & workspace roots via orchestration_lib.
2. Hard-aborts if the tool is invoked from a FORBIDDEN branch (e.g. 'main').
3. Walks every directory looking for .git repos.
4. For each repo, auto-detects compliance exclusions and flags forbidden branches.
5. Merges with existing inventory.json to preserve manual overrides.
6. Writes a clean, sorted inventory.json.

KEY PARAMETERS:
- fleet_name: Written into the "fleet_name" key.
- master_branch: Default and only authorised branch.
- forbidden_branches: Set of branch names that are strictly prohibited.
"""

# [SCAN] Role: Developer | Source: build-inventory.py | State: Active

from os import name as osName, execl as osExecl, walk as osWalk, environ as osEnviron
from os.path import (
    dirname as osPathDirname,
    abspath as osPathAbspath,
    exists as osPathExists,
    join as osPathJoin,
    samefile as osPathSamefile,
)
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit
from json import load as jsonLoad, dump as jsonDump
from pathlib import Path as pathlibPath
from subprocess import run as subprocessRun
from typing import Dict as typingDict, List as typingList, Any as typingAny, Optional as typingOptional

# -----------------------------------------------------------------------------------------------
# Venv bootstrap
# -----------------------------------------------------------------------------------------------
_venv_dir = osPathDirname(osPathAbspath(__file__))
while _venv_dir and _venv_dir != "/" and not osPathExists(osPathJoin(_venv_dir, ".venv")):
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
# Orchestration lib integration
# -----------------------------------------------------------------------------------------------
import sys as _sys
_orch_dir = osPathJoin(osPathDirname(osPathAbspath(__file__)), "..", "..", "..", "obsidian-brain", "00-AI-Orchestration")
_orch_dir_resolved = pathlibPath(_orch_dir).resolve()
if str(_orch_dir_resolved) not in _sys.path:
    _sys.path.insert(0, str(_orch_dir_resolved))

try:
    from lib.orchestration_lib import setup_terminal, resolve_vault_and_workspace
    setup_terminal()
except ImportError:
    def setup_terminal() -> None:
        import sys
        if sys.stdout.encoding != "utf-8":
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except (AttributeError, Exception):
                pass

    def resolve_vault_and_workspace(*, script_file: str):
        current = pathlibPath(script_file).resolve().parent
        vault_root = None
        for parent in [current] + list(current.parents):
            if parent.name == "obsidian-brain":
                vault_root = parent
                break
        if not vault_root:
            vault_root = current
        return vault_root, vault_root.parent

    setup_terminal()


# -----------------------------------------------------------------------------------------------

class MInventoryBuilder:
    """
    Core class responsible for discovering repositories and managing the fleet inventory.
    """

    def __init__(self, *, config: typingAny, logger: typingAny, name: typingOptional[str] = None):
        self.config = config
        self.logger = logger
        self.Name = name or self.__class__.__name__
        self.FleetName = "Bastien-Antigravity"
        self.MasterBranch = "develop"
        self.ForbiddenBranches = frozenset({"main"})
        self.CodeExtensions = {".go", ".rs", ".cpp", ".c", ".java", ".ts", ".js"}
        self.PlainMarkers = [
            "go.mod", "Cargo.toml", "package.json",
            "requirements.txt", "setup.py", "pyproject.toml",
            "CMakeLists.txt", "Makefile",
        ]

    # -----------------------------------------------------------------------------------------------

    def build(self, *, dry_run: bool = False) -> None:
        """
        Executes the full inventory building process.
        """
        # Step 0: Branch Guard
        self._abort_if_self_on_forbidden_branch(script_path=pathlibPath(__file__).resolve())

        # Step 1: Resolve Paths
        _vault_root, workspace_root = resolve_vault_and_workspace(script_file=__file__)
        inventory_path = pathlibPath(__file__).resolve().parent / "inventory.json"

        self.logger.info("{0} : 🔍 Workspace root : {1}".format(self.Name, workspace_root))
        self.logger.info("{0} : 📄 Inventory path : {1}".format(self.Name, inventory_path))
        self.logger.info("{0} : 🔒 Master branch  : {1}".format(self.Name, self.MasterBranch))

        # Step 2: Load existing data
        existing = self._load_existing_inventory(inventory_path=inventory_path)
        manual_overrides = self._build_manual_overrides(existing=existing)
        if manual_overrides:
            self.logger.info("{0} : 🔒 Preserving {1} manual override(s)".format(self.Name, len(manual_overrides)))

        # Step 3: Discover repos
        self.logger.info("{0} : 🔎 Scanning for repositories...".format(self.Name))
        discovered = self._discover_repos(workspace_root=workspace_root)
        self.logger.info("{0} :    Found {1} repositories.".format(self.Name, len(discovered)))

        # Step 4: Final repo list
        repositories = []
        for repo in discovered:
            name = repo["name"]
            raw_path = repo.pop("raw_path")

            if name in manual_overrides:
                exclude = manual_overrides[name]
                source = "manual"
            else:
                exclude = self._is_knowledge_base(repo_path=raw_path, workspace_root=workspace_root)
                source = "auto"

            entry: typingDict[str, typingAny] = {
                "name": name,
                "path": repo["path"],
                "remote": repo["remote"],
                "master_branch": repo["master_branch"],
            }
            if exclude:
                entry["exclude_from_compliance"] = True

            flag_icon = "⛔ EXCLUDED" if exclude else "✅ COMPLIANT"
            self.logger.info("{0} :    {1:<30} {2}  [{3}]".format(self.Name, name, flag_icon, source))
            repositories.append(entry)

        # Step 5: Final doc
        output = {
            "fleet_name": existing.get("fleet_name", self.FleetName),
            "master_branch": self.MasterBranch,
            "repositories": repositories,
        }

        if dry_run:
            self.logger.info("{0} : 🧪 DRY RUN — Would write {1} repos.".format(self.Name, len(repositories)))
            return

        # Step 6: Write
        try:
            with open(inventory_path, "w", encoding="utf-8") as f:
                jsonDump(output, f, indent=2, ensure_ascii=False)
            self.logger.info("{0} : ✅ inventory.json written — {1} repositories registered.".format(self.Name, len(repositories)))
        except Exception as e:
            self.logger.error("{0} : ❌ Failed to write inventory.json: {1}".format(self.Name, e))

    # -----------------------------------------------------------------------------------------------

    def _assert_not_forbidden_branch(self, *, repo_path: pathlibPath, branch: str, repo_name: str) -> str:
        if branch in self.ForbiddenBranches:
            self.logger.warning("{0} : 🚨 FORBIDDEN BRANCH [{1}] in '{2}'".format(self.Name, branch, repo_name))
            return self.MasterBranch
        return branch

    # -----------------------------------------------------------------------------------------------

    def _abort_if_self_on_forbidden_branch(self, *, script_path: pathlibPath) -> None:
        try:
            result = subprocessRun(
                ["git", "-C", str(script_path.parent), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, check=False, timeout=5,
            )
            current_branch = result.stdout.strip()
            if current_branch in self.ForbiddenBranches:
                self.logger.critical("{0} : 💀 HARD ABORT — FORBIDDEN BRANCH DETECTED: {1}".format(self.Name, current_branch))
                sysExit(1)
        except Exception:
            pass

    # -----------------------------------------------------------------------------------------------

    def _run_git(self, *, path: pathlibPath, args: typingList[str]) -> str:
        try:
            result = subprocessRun(
                ["git", "-C", str(path)] + args,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    # -----------------------------------------------------------------------------------------------

    def _has_code_at_root(self, *, repo_path: pathlibPath) -> bool:
        for marker in self.PlainMarkers:
            if (repo_path / marker).exists():
                return True

        try:
            for item in repo_path.iterdir():
                if item.is_file() and item.suffix in self.CodeExtensions:
                    return True
        except PermissionError:
            pass

        for subdir in ["go", "python", "rust", "src", "cmd", "lib"]:
            sub = repo_path / subdir
            if sub.is_dir():
                for marker in self.PlainMarkers:
                    if (sub / marker).exists():
                        return True
                try:
                    for item in sub.iterdir():
                        if item.is_file() and item.suffix in self.CodeExtensions:
                            return True
                except PermissionError:
                    pass
        return False

    # -----------------------------------------------------------------------------------------------

    def _is_knowledge_base(self, *, repo_path: pathlibPath, workspace_root: pathlibPath) -> bool:
        obsidian_brain = workspace_root / "obsidian-brain"
        try:
            if repo_path.resolve() == obsidian_brain.resolve():
                return True
        except Exception:
            pass

        try:
            repo_path.resolve().relative_to(obsidian_brain.resolve())
        except ValueError:
            return False

        return not self._has_code_at_root(repo_path=repo_path)

    # -----------------------------------------------------------------------------------------------

    def _discover_repos(self, *, workspace_root: pathlibPath) -> typingList[typingDict[str, typingAny]]:
        found = []
        root_resolved = workspace_root.resolve()

        for root, dirs, files in osWalk(workspace_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") or d == ".git"]

            if ".git" in dirs or ".git" in files:
                path = pathlibPath(root).resolve()

                if path == root_resolved:
                    dirs[:] = [d for d in dirs if d != ".git"]
                    continue

                remote = self._run_git(path=path, args=["remote", "get-url", "origin"])
                branch = self._run_git(path=path, args=["rev-parse", "--abbrev-ref", "HEAD"])
                if not branch or branch == "HEAD":
                    branch = self.MasterBranch

                branch = self._assert_not_forbidden_branch(repo_path=path, branch=branch, repo_name=path.name)

                try:
                    rel = path.relative_to(root_resolved)
                    rel_path = "./{0}".format(rel.as_posix())
                except ValueError:
                    rel_path = str(path)

                found.append({
                    "name": path.name,
                    "path": rel_path,
                    "raw_path": path,
                    "remote": remote,
                    "master_branch": branch,
                })
                dirs[:] = [d for d in dirs if d != ".git"]

        found.sort(key=lambda x: x["name"])
        return found

    # -----------------------------------------------------------------------------------------------

    def _load_existing_inventory(self, *, inventory_path: pathlibPath) -> typingDict[str, typingAny]:
        if not inventory_path.exists():
            return {"fleet_name": self.FleetName, "master_branch": self.MasterBranch, "repositories": []}
        try:
            with open(inventory_path, "r", encoding="utf-8") as f:
                return jsonLoad(f)
        except Exception as e:
            self.logger.warning("{0} : Could not read existing inventory: {1}".format(self.Name, e))
            return {"fleet_name": self.FleetName, "master_branch": self.MasterBranch, "repositories": []}

    # -----------------------------------------------------------------------------------------------

    def _build_manual_overrides(self, *, existing: typingDict[str, typingAny]) -> typingDict[str, typingOptional[bool]]:
        overrides: typingDict[str, typingOptional[bool]] = {}
        for repo in existing.get("repositories", []):
            name = repo.get("name")
            if name and "exclude_from_compliance" in repo:
                overrides[name] = repo["exclude_from_compliance"]
        return overrides


# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    class DefaultLogger:
        def info(self, msg: str) -> None: print(msg)
        def warning(self, msg: str) -> None: print(msg)
        def error(self, msg: str) -> None: print(msg)
        def critical(self, msg: str) -> None: print(msg)

    parser = argparse.ArgumentParser(description="Build or rebuild inventory.json.")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Scan without writing.")
    args = parser.parse_args()

    builder = MInventoryBuilder(config=object(), logger=DefaultLogger())
    builder.build(dry_run=args.dry_run)

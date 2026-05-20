#!/usr/bin/env python
# coding:utf-8

"""
ESSENTIAL PROCESS:
Orchestrates fleet-wide operations across all repositories in the
Bastien-Antigravity ecosystem, including synchronization, status auditing,
tagging, and restoration.

DATA FLOW:
1. Loads inventory.json to identify the fleet members.
2. Parallelizes Git operations across the fleet using ThreadPoolExecutor.
3. Collects and aggregates logs and status reports.
4. Updates repository states on disk.

KEY PARAMETERS:
- None
"""

from os import name as osName, execl as osExecl, getenv as osGetenv, walk as osWalk, environ as osEnviron
from os.path import dirname as osPathDirname, abspath as osPathAbspath, exists as osPathExists, join as osPathJoin, samefile as osPathSamefile
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit, stdout as sysStdout
from json import load as jsonLoad, dump as jsonDump
from subprocess import run as subprocessRun, TimeoutExpired as subprocessTimeoutExpired
from pathlib import Path as pathlibPath
from concurrent.futures import ThreadPoolExecutor as concurrentThreadPoolExecutor
from shutil import rmtree as shutilRmtree
from typing import List as typingList, Dict as typingDict, Any as typingAny, Optional as typingOptional, Tuple as typingTuple

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

# Standardize terminal output encoding for Windows
if sysStdout.encoding != 'utf-8':
    try:
        sysStdout.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

# -----------------------------------------------------------------------------------------------

class FleetManager:
    Name = "FleetManager"

    def __init__(self, config: object, logger: object, name: typingOptional[str] = None) -> None:
        self.config = config
        self.logger = logger
        self.Name = name if name is not None else "FleetManager"
        self.go_version = "1.25"
        self.python_version = "3.12"
        self.rust_version = "1.91"
        self.cpp_version = "20"

    # -----------------------------------------------------------------------------------------------

    def run_manager(self, command: str, args: typingList[str]) -> None:
        """
        Main runner coordinating the execution of the requested command.
        """
        inventory_path = pathlibPath(__file__).resolve().parent / "inventory.json"
        if not inventory_path.exists():
            self.logger.error("{0} : inventory.json not found.".format(self.Name))
            return

        try:
            with open(inventory_path, "r", encoding='utf-8') as f:
                inventory = jsonLoad(f)
        except Exception as e:
            self.logger.error("{0} : Failed to load inventory: {1}".format(self.Name, e))
            return

        inventory = self._resolve_inventory_paths(inventory)
        num_repos = len(inventory.get("repositories", []))
        optimal_workers = max(5, min(32, num_repos))

        if command in ["sync", "vault-sync", "restore", "tag", "audit", "status", "attach"]:
            self._ensure_auth()

        if command == "discover":
            workspace_root = self._find_workspace_root()
            discovered = self.discover_repos(workspace_root)
            for repo in discovered:
                try:
                    rel = pathlibPath(repo["path"]).relative_to(workspace_root)
                    repo["path"] = "./{0}".format(rel.as_posix())
                except ValueError:
                    pass
            inventory["repositories"] = discovered
            try:
                with open(inventory_path, "w", encoding='utf-8') as f:
                    jsonDump(inventory, f, indent=2)
                self.logger.info("{0} : Discovered and registered {1} repositories.".format(self.Name, len(discovered)))
            except Exception as e:
                self.logger.error("{0} : Failed to save discovered repositories: {1}".format(self.Name, e))

        elif command == "status":
            self.logger.info("{0} : {1:<25} | {2:<15} | {3:<8} | {4:<5} | {5:<5} | {6:<5}".format(self.Name, 'Repository', 'Branch', 'Status', 'Clean', 'Ahead', 'Behind'))
            self.logger.info("{0} : {1}".format(self.Name, "-" * 80))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                results = list(executor.map(self.get_status, inventory["repositories"]))
            for r in results:
                clean = "✅" if r["clean"] else "❌"
                self.logger.info("{0} : {1:<25} | {2:<15} | {3:<8} | {4:<5} | {5:<5} | {6:<5}".format(self.Name, r['name'], r['branch'], r['status'], clean, r['ahead'], r['behind']))

        elif command == "sync":
            self.logger.info("{0} : Starting Global Fleet Sync (with Auto-Attach)...".format(self.Name))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                results = list(executor.map(self.sync_repo, inventory["repositories"]))
            for repo_logs in results:
                for log in repo_logs:
                    self.logger.info("{0} : {1}".format(self.Name, log))

        elif command == "attach":
            self.logger.info("{0} : Attaching fleet to designated branches...".format(self.Name))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                results = list(executor.map(self.attach_repo, inventory["repositories"]))
            for repo_logs in results:
                for log in repo_logs:
                    self.logger.info("{0} : {1}".format(self.Name, log))

        elif command == "audit":
            self.logger.info("{0} : {1:<25} | {2:<4} | {3:<4} | {4:<4} | {5:<20}".format(self.Name, 'Repository', 'CI', 'Dep', 'AI', 'CI Status'))
            self.logger.info("{0} : {1}".format(self.Name, "-" * 75))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                results = list(executor.map(self.audit_repo, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1:<25} | {2:<4} | {3:<4} | {4:<4} | {5:<20}".format(self.Name, r['name'], r['ci'], r['dep'], r['ai'], r['run']))

        elif command == "commit":
            msg = args[0] if args else "chore(fleet): mass sync"
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                def _do_commit(repo: typingDict[str, typingAny]) -> str:
                    path = repo["path"]
                    if not osPathExists(path):
                        return "[ {0} ] MISSING".format(repo['name'])
                    status, _, _ = self.run_git(pathlibPath(path), ["status", "--porcelain"])
                    if not status:
                        return "[ {0} ] CLEAN".format(repo['name'])
                    self.run_git(pathlibPath(path), ["add", "."])
                    _, err, code = self.run_git(pathlibPath(path), ["commit", "-m", msg])
                    return "[ {0} ] COMMITTED".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
                results = list(executor.map(_do_commit, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1}".format(self.Name, r))

        elif command == "tag":
            tag_name = args[0] if args else None
            if not tag_name:
                self.logger.error("{0} : Usage: fleet-manager.py tag <tag_name>".format(self.Name))
                return
            self.logger.info("{0} : Applying tag {1} across the fleet...".format(self.Name, tag_name))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                def _do_tag(repo: typingDict[str, typingAny]) -> str:
                    path = repo["path"]
                    if not osPathExists(path):
                        return "[ {0} ] MISSING".format(repo['name'])
                    self.run_git(pathlibPath(path), ["tag", tag_name])
                    _, err, code = self.run_git(pathlibPath(path), ["push", "origin", tag_name])
                    return "[ {0} ] TAGGED & PUSHED".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
                results = list(executor.map(_do_tag, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1}".format(self.Name, r))

        elif command == "branch":
            branch_name = args[0] if args else None
            if not branch_name:
                self.logger.error("{0} : Usage: fleet-manager.py branch <branch_name>".format(self.Name))
                return
            self.logger.info("{0} : Checking out branch {1} across the fleet...".format(self.Name, branch_name))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                def _do_branch(repo: typingDict[str, typingAny]) -> str:
                    path = repo["path"]
                    if not osPathExists(path):
                        return "[ {0} ] MISSING".format(repo['name'])
                    _, _, code = self.run_git(pathlibPath(path), ["rev-parse", "--verify", branch_name])
                    if code == 0:
                        self.run_git(pathlibPath(path), ["checkout", branch_name])
                        return "[ {0} ] CHECKED OUT EXISTING".format(repo['name'])
                    else:
                        _, err, code = self.run_git(pathlibPath(path), ["checkout", "-b", branch_name])
                        return "[ {0} ] CREATED & CHECKED OUT".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
                results = list(executor.map(_do_branch, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1}".format(self.Name, r))

        elif command == "template":
            templates_dir = pathlibPath(__file__).resolve().parent.parent / "04-Templates"
            self.logger.info("{0} : Applying fleet templates from {1}...".format(self.Name, templates_dir))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                def _do_template(repo: typingDict[str, typingAny]) -> str:
                    return self.template_repo(repo, templates_dir)
                results = list(executor.map(_do_template, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1}".format(self.Name, r))

        elif command == "cleanup":
            self.logger.info("{0} : Starting Global Fleet Cleanup (Hygiene Mode)...".format(self.Name))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                def _do_cleanup(repo: typingDict[str, typingAny]) -> str:
                    return self.cleanup_repo(repo)
                results = list(executor.map(_do_cleanup, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1}".format(self.Name, r))

        elif command == "restore":
            self.logger.info("{0} : Restoring missing repositories in the fleet...".format(self.Name))
            with concurrentThreadPoolExecutor(max_workers=optimal_workers) as executor:
                def _do_restore(repo: typingDict[str, typingAny]) -> str:
                    path = pathlibPath(repo["path"])
                    name = repo["name"]
                    if path.exists():
                        return "[ {0} ] EXISTS".format(name)

                    remote = repo.get("remote")
                    if not remote:
                        return "[ {0} ] ERROR: No remote URL".format(name)

                    self.logger.info("{0} :   [CLONE] Restoring {1}...".format(self.Name, name))
                    res = subprocessRun(["git", "clone", remote, str(path)], capture_output=True, text=True)
                    return "[ {0} ] RESTORED".format(name) if res.returncode == 0 else "[ {0} ] FAILED: {1}".format(name, res.stderr.strip())

                results = list(executor.map(_do_restore, inventory["repositories"]))
            for r in results:
                self.logger.info("{0} : {1}".format(self.Name, r))

        elif command == "vault-sync":
            msg = args[0] if args else "chore(vault): atomic sync via Fleet Manager"
            workspace_root = self._find_workspace_root()
            obsidian_dir = workspace_root / "obsidian-brain"

            if not obsidian_dir.exists():
                self.logger.error("{0} : obsidian-brain not found.".format(self.Name))
                return

            self.logger.info("{0} : 🚀 Starting Atomic Vault Sync...".format(self.Name))

            # 1. Sync all submodules
            submodules = [d for d in obsidian_dir.iterdir() if d.is_dir() and (d / ".git").exists()]
            for sub in submodules:
                name = sub.name
                status, _, _ = self.run_git(sub, ["status", "--porcelain"])
                if status:
                    self.logger.info("{0} : [ {1} ] Committing changes...".format(self.Name, name))
                    self.run_git(sub, ["add", "."])
                    self.run_git(sub, ["commit", "-m", msg])

                self.logger.info("{0} : [ {1} ] Pulling latest...".format(self.Name, name))
                self.run_git(sub, ["pull", "--rebase", "origin", "develop"])

                # 2. Push (Only if ahead)
                ab_out, _, code = self.run_git(sub, ["rev-list", "--left-right", "--count", "origin/develop...HEAD"])
                ahead = 0
                if code == 0:
                    parts = ab_out.split()
                    if len(parts) == 2:
                        ahead = int(parts[1])

                if ahead > 0:
                    self.logger.info("{0} : [ {1} ] Pushing {2} commit(s) to origin...".format(self.Name, name, ahead))
                    _, err, code = self.run_git(sub, ["push", "origin", "develop"])
                    if code != 0:
                        self.logger.error("{0} : [ {1} ] PUSH FAILED: {2}".format(self.Name, name, err))
                    else:
                        self.logger.info("{0} : [ {1} ] SYNCED.".format(self.Name, name))
                else:
                    self.logger.info("{0} : [ {1} ] UP-TO-DATE.".format(self.Name, name))

            # 2. Update parent pointer
            self.logger.info("{0} : [ obsidian-brain ] Updating submodule pointers...".format(self.Name))
            self.run_git(obsidian_dir, ["add", "."])
            status, _, _ = self.run_git(obsidian_dir, ["status", "--porcelain"])
            if status:
                self.run_git(obsidian_dir, ["commit", "-m", "chore(fleet): update submodule pointers"])
                self.logger.info("{0} : [ obsidian-brain ] Pointers committed.".format(self.Name))

            # 3. Final Vault Push (Only if ahead)
            ab_out, _, code = self.run_git(obsidian_dir, ["rev-list", "--left-right", "--count", "origin/develop...HEAD"])
            ahead = 0
            if code == 0:
                parts = ab_out.split()
                if len(parts) == 2:
                    ahead = int(parts[1])

            if ahead > 0:
                self.logger.info("{0} : [ obsidian-brain ] Pushing {1} commit(s) to origin...".format(self.Name, ahead))
                _, err, code = self.run_git(obsidian_dir, ["push", "origin", "develop"])
                if code == 0:
                    self.logger.info("{0} : ✨ Atomic Vault Sync Complete!".format(self.Name))
                else:
                    self.logger.error("{0} : ❌ Vault push failed: {1}".format(self.Name, err))
            else:
                self.logger.info("{0} : ✨ Vault is already up-to-date.".format(self.Name))

        elif command == "refresh":
            refresh_script = pathlibPath(__file__).resolve().parent / "fleet-refresh.py"
            self.logger.info("{0} : Executing Nuclear Refresh via {1}...".format(self.Name, refresh_script.name))
            subprocessRun([sysExecutable, str(refresh_script)] + args)

        else:
            self.logger.error("{0} : Unknown command: {1}".format(self.Name, command))

    # -----------------------------------------------------------------------------------------------

    def get_status(self, repo: typingDict[str, typingAny]) -> typingDict[str, typingAny]:
        """
        Checks the status of a single repository (branch, cleanliness, ahead/behind).
        """
        path = repo["path"]
        name = repo["name"]

        if not osPathExists(path):
            return {"name": name, "status": "MISSING", "branch": "N/A", "clean": False, "ahead": 0, "behind": 0}

        branch_out, _, _ = self.run_git(pathlibPath(path), ["rev-parse", "--abbrev-ref", "HEAD"])
        status_out, _, _ = self.run_git(pathlibPath(path), ["status", "--porcelain"])

        ahead, behind = 0, 0
        remote_branch = repo.get("master_branch", "develop")

        self.run_git(pathlibPath(path), ["fetch", "origin"])

        ab_out, _, code = self.run_git(pathlibPath(path), ["rev-list", "--left-right", "--count", "origin/{0}...HEAD".format(remote_branch)])
        if code == 0:
            parts = ab_out.split()
            if len(parts) == 2:
                behind, ahead = int(parts[0]), int(parts[1])

        return {
            "name": name,
            "status": "OK",
            "branch": branch_out,
            "clean": len(status_out) == 0,
            "ahead": ahead,
            "behind": behind
        }

    # -----------------------------------------------------------------------------------------------

    def sync_repo(self, repo: typingDict[str, typingAny]) -> typingList[str]:
        """
        Performs a pull-update-push sequence for a repository.
        """
        path = repo["path"]
        name = repo["name"]
        target_branch = repo.get("master_branch", "develop")
        logs = []

        if not osPathExists(path):
            logs.append("[ {0} ] ERROR: Path not found".format(name))
            return logs

        status_out, _, _ = self.run_git(pathlibPath(path), ["status", "--porcelain"])
        if len(status_out) > 0:
            logs.append("[ {0} ] SKIP: Uncommitted changes found. Please commit first.".format(name))
            return logs

        current_branch, _, _ = self.run_git(pathlibPath(path), ["rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch != target_branch:
            logs.append("[ {0} ] Branch mismatch (Current: {1}, Target: {2}). Attempting to attach...".format(name, current_branch, target_branch))
            attach_logs = self.attach_repo(repo)
            logs.extend(attach_logs)

            current_branch, _, _ = self.run_git(pathlibPath(path), ["rev-parse", "--abbrev-ref", "HEAD"])
            if current_branch != target_branch:
                logs.append("[ {0} ] SKIP: Could not attach to '{1}'. Skipping sync.".format(name, target_branch))
                return logs

        logs.append("[ {0} ] Pulling {1}...".format(name, target_branch))
        _, err, code = self.run_git(pathlibPath(path), ["pull", "origin", target_branch])
        if code != 0:
            logs.append("[ {0} ] PULL FAILED: {1}".format(name, err))
            return logs

        if osPathExists(osPathJoin(path, ".gitmodules")):
            logs.append("[ {0} ] Updating submodules...".format(name))
            _, err, code = self.run_git(pathlibPath(path), ["submodule", "update", "--init", "--recursive"])
            if code != 0:
                logs.append("[ {0} ] SUBMODULE ERROR: {1}".format(name, err))

        ab_out, _, code = self.run_git(pathlibPath(path), ["rev-list", "--left-right", "--count", "origin/{0}...HEAD".format(target_branch)])
        ahead = 0
        if code == 0:
            parts = ab_out.split()
            if len(parts) == 2:
                ahead = int(parts[1])

        if ahead > 0:
            logs.append("[ {0} ] Pushing {1} ({2} commit(s) ahead)...".format(name, target_branch, ahead))
            _, err, code = self.run_git(pathlibPath(path), ["push", "origin", target_branch])
            if code != 0:
                logs.append("[ {0} ] PUSH FAILED: {1}".format(name, err))
                return logs
            logs.append("[ {0} ] SYNCED & PUSHED ({1})".format(name, target_branch))
        else:
            logs.append("[ {0} ] UP-TO-DATE ({1})".format(name, target_branch))

        return logs

    # -----------------------------------------------------------------------------------------------

    def attach_repo(self, repo: typingDict[str, typingAny]) -> typingList[str]:
        """
        Ensures a repository is on its designated master_branch.
        Handles 'reattaching' from detached HEAD states.
        """
        path = repo["path"]
        name = repo["name"]
        target_branch = repo.get("master_branch", "develop")
        logs = []

        if not osPathExists(path):
            logs.append("[ {0} ] ERROR: Path not found".format(name))
            return logs

        current_branch, _, _ = self.run_git(pathlibPath(path), ["rev-parse", "--abbrev-ref", "HEAD"])

        if current_branch == target_branch:
            logs.append("[ {0} ] Already on {1}".format(name, target_branch))
            return logs

        status_out, _, _ = self.run_git(pathlibPath(path), ["status", "--porcelain"])
        if len(status_out) > 0:
            logs.append("[ {0} ] CANNOT ATTACH: Uncommitted changes found. Please commit or stash first.".format(name))
            return logs

        logs.append("[ {0} ] Attaching to {1}...".format(name, target_branch))
        _, err, code = self.run_git(pathlibPath(path), ["checkout", target_branch])

        if code != 0:
            self.run_git(pathlibPath(path), ["fetch", "origin", target_branch])
            _, err, code = self.run_git(pathlibPath(path), ["checkout", target_branch])

        if code == 0:
            logs.append("[ {0} ] ATTACHED to {1}".format(name, target_branch))
        else:
            logs.append("[ {0} ] ATTACH FAILED: {1}".format(name, err))

        return logs

    # -----------------------------------------------------------------------------------------------

    def audit_repo(self, repo: typingDict[str, typingAny]) -> typingDict[str, typingAny]:
        """
        Audits the repository for CI/CD standards and GitHub Action status.
        """
        from urllib.request import Request as urllibRequestRequest, urlopen as urllibRequestUrlopen
        from urllib.error import HTTPError as urllibErrorHTTPError
        from ssl import _create_unverified_context as sslCreateUnverifiedContext
        from re import search as reSearch

        path = repo["path"]
        name = repo["name"]

        if not osPathExists(path):
            return {"name": name, "ci": "N/A", "dep": "N/A", "ai": "N/A", "run": "UNKNOWN"}

        ci_exists = osPathExists(osPathJoin(path, ".github/workflows/ci.yml"))
        dep_exists = osPathExists(osPathJoin(path, ".github/dependabot.yml"))
        ai_exists = osPathExists(osPathJoin(path, "AI-Init.md"))

        run_status = "UNKNOWN"
        token = self.get_github_token()
        remote_url = repo.get("remote", "")
        match = reSearch(r"github\.com[:/](.+)/(.+)\.git", remote_url)

        if match:
            owner, repo_name = match.group(1), match.group(2)
            url = "https://api.github.com/repos/{0}/{1}/actions/runs?per_page=1".format(owner, repo_name)
            try:
                context = sslCreateUnverifiedContext()
                req = urllibRequestRequest(url)
                if token:
                    req.add_header("Authorization", "token {0}".format(token))
                req.add_header("User-Agent", "Fleet-Manager")
                with urllibRequestUrlopen(req, timeout=10, context=context) as response:
                    data = jsonLoad(response)
                    if data.get("workflow_runs"):
                        last = data["workflow_runs"][0]
                        run_status = last["conclusion"].upper() if last["status"] == "completed" else last["status"].upper()
                    else:
                        run_status = "NONE"
            except urllibErrorHTTPError as e:
                if e.code == 403:
                    run_status = "ERR 403 (Rate Limit)"
                elif e.code == 401:
                    run_status = "ERR 401 (Auth)"
                else:
                    run_status = "ERR {0}".format(e.code)
            except Exception:
                run_status = "ERR NETWORK"

        status_icon = "🔘"
        if run_status == "SUCCESS":
            status_icon = "✅"
        elif run_status in ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"]:
            status_icon = "❌"
        elif run_status in ["IN_PROGRESS", "QUEUED", "WAITING"]:
            status_icon = "⏳"
        elif "ERR" in run_status or run_status == "UNKNOWN":
            status_icon = "⚠️"

        display_status = "{0} {1}".format(status_icon, run_status)

        return {"name": name, "ci": "✅" if ci_exists else "❌", "dep": "✅" if dep_exists else "❌", "ai": "✅" if ai_exists else "❌", "run": display_status}

    # -----------------------------------------------------------------------------------------------

    def template_repo(self, repo: typingDict[str, typingAny], templates_dir: pathlibPath) -> str:
        """
        Applies standard CI/CD templates to a repository with Archetype auto-detection.
        """
        path = pathlibPath(repo["path"])
        name = repo["name"]

        if not path.exists():
            return "[ {0} ] MISSING".format(name)

        if repo.get("exclude_from_compliance", False):
            return "[ {0} ] SKIP (Knowledge-Base)".format(name)

        github_dir = path / ".github"
        workflows_dir = github_dir / "workflows"

        github_dir.mkdir(exist_ok=True)
        workflows_dir.mkdir(exist_ok=True)

        go_path = self._detect_language_path(path, "go")
        python_path = self._detect_language_path(path, "python")
        rust_path = self._detect_language_path(path, "rust")
        cpp_path = self._detect_language_path(path, "cpp")

        is_polyglot = any([python_path, rust_path, cpp_path])
        archetype = "Polyglot" if is_polyglot else "Microservice"
        archetype_dir = templates_dir / archetype

        ci_src = archetype_dir / "ci.yml"
        ci_dst = workflows_dir / "ci.yml"
        if ci_src.exists():
            try:
                with open(ci_src, "r", encoding='utf-8') as src:
                    ci_content = src.read()

                if is_polyglot:
                    langs = []
                    if go_path: langs.append("Go")
                    if python_path: langs.append("Python")
                    if rust_path: langs.append("Rust")
                    if cpp_path: langs.append("C++")
                    label = "Polyglot: " + "+".join(langs)
                else:
                    label = "Microservice"

                header_params = "Go:{0}, Py:{1}, Rust:{2}, C++:{3}".format(self.go_version, self.python_version, self.rust_version, self.cpp_version)
                ci_content = ci_content.replace("# [FLEET-ARCHITECT] Standardized Polyglot CI", "# [FLEET-ARCHITECT] {0} ({1})".format(label, header_params))
                ci_content = ci_content.replace("# [FLEET-ARCHITECT] Standardized Microservice CI", "# [FLEET-ARCHITECT] {0} ({1})".format(label, header_params))

                ci_content = ci_content.replace("{{GO_VERSION}}", self.go_version)
                ci_content = ci_content.replace("{{PYTHON_VERSION}}", self.python_version)
                ci_content = ci_content.replace("{{RUST_VERSION}}", self.rust_version)
                ci_content = ci_content.replace("{{CPP_VERSION}}", self.cpp_version)

                if not is_polyglot and go_path:
                    ci_content = ci_content.replace("{{WORKING_DIR}}", go_path)
                elif not is_polyglot:
                    ci_content = ci_content.replace("{{WORKING_DIR}}", ".")

                if is_polyglot:
                    if go_path:
                        ci_content += self._load_job_fragment("go", go_path, templates_dir)
                    if python_path:
                        ci_content += self._load_job_fragment("python", python_path, templates_dir)
                    if rust_path:
                        ci_content += self._load_job_fragment("rust", rust_path, templates_dir)
                    if cpp_path:
                        ci_content += self._load_job_fragment("cpp", cpp_path, templates_dir)

                with open(ci_dst, "w", encoding='utf-8') as dst:
                    dst.write(ci_content)
            except Exception as e:
                self.logger.error("{0} : Failed to apply CI template for {1}: {2}".format(self.Name, name, e))

        if is_polyglot:
            rel_src = archetype_dir / "release.yml"
            rel_dst = workflows_dir / "release.yml"
            if rel_src.exists():
                try:
                    with open(rel_src, "r", encoding='utf-8') as src, open(rel_dst, "w", encoding='utf-8') as dst:
                        dst.write(src.read())
                except Exception as e:
                    self.logger.error("{0} : Failed to apply release template for {1}: {2}".format(self.Name, name, e))

        dep_src = archetype_dir / "dependabot.yml"
        dep_dst = github_dir / "dependabot.yml"
        if dep_src.exists():
            try:
                with open(dep_src, "r", encoding='utf-8') as src, open(dep_dst, "w", encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception as e:
                self.logger.error("{0} : Failed to apply dependabot template for {1}: {2}".format(self.Name, name, e))

        co_src = templates_dir / "CODEOWNERS"
        co_dst = github_dir / "CODEOWNERS"
        if co_src.exists():
            try:
                with open(co_src, "r", encoding='utf-8') as src, open(co_dst, "w", encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception as e:
                self.logger.error("{0} : Failed to apply CODEOWNERS for {1}: {2}".format(self.Name, name, e))

        pr_src = templates_dir / "PULL_REQUEST_TEMPLATE.md"
        pr_dst = github_dir / "PULL_REQUEST_TEMPLATE.md"
        if pr_src.exists():
            try:
                with open(pr_src, "r", encoding='utf-8') as src, open(pr_dst, "w", encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception as e:
                self.logger.error("{0} : Failed to apply PR template for {1}: {2}".format(self.Name, name, e))

        it_src = templates_dir / "ISSUE_TEMPLATE"
        it_dst = github_dir / "ISSUE_TEMPLATE"
        if it_src.is_dir():
            try:
                it_dst.mkdir(exist_ok=True)
                for tmpl_file in it_src.iterdir():
                    target_file = it_dst / tmpl_file.name
                    with open(tmpl_file, "r", encoding='utf-8') as src, open(target_file, "w", encoding='utf-8') as dst:
                        dst.write(src.read())
            except Exception as e:
                self.logger.error("{0} : Failed to apply issue templates for {1}: {2}".format(self.Name, name, e))

        lint_src = templates_dir / "golangci-global.yml"
        lint_dst = path / ".golangci.yml"
        if lint_src.exists():
            try:
                with open(lint_src, "r", encoding='utf-8') as src, open(lint_dst, "w", encoding='utf-8') as dst:
                    dst.write(src.read())
            except Exception as e:
                self.logger.error("{0} : Failed to apply golangci-lint config for {1}: {2}".format(self.Name, name, e))

        overview_src = templates_dir / "quick-overview"
        overview_dst = path / "quick-overview"
        if overview_src.is_dir():
            try:
                overview_dst.mkdir(exist_ok=True)
                for tmpl_file in overview_src.iterdir():
                    target_file = overview_dst / tmpl_file.name
                    if not target_file.exists():
                        with open(tmpl_file, "r", encoding='utf-8') as src, open(target_file, "w", encoding='utf-8') as dst:
                            dst.write(src.read())
            except Exception as e:
                self.logger.error("{0} : Failed to apply quick-overview for {1}: {2}".format(self.Name, name, e))

        if is_polyglot:
            langs = []
            if go_path: langs.append("Go")
            if python_path: langs.append("Python")
            if rust_path: langs.append("Rust")
            if cpp_path: langs.append("C++")
            label = "Polyglot: " + "+".join(langs)
        else:
            label = "Microservice"

        return "[ {0} ] TEMPLATED ({1})".format(name, label)

    # -----------------------------------------------------------------------------------------------

    def cleanup_repo(self, repo: typingDict[str, typingAny]) -> str:
        """
        Purges legacy CI/CD artifacts and non-standard workflows from a repository.
        Ensures that only the FleetArchitect-approved 'KEEP_FILES' remain.
        """
        path = pathlibPath(repo["path"])
        name = repo["name"]

        if not path.exists():
            return "[ {0} ] MISSING".format(name)

        if repo.get("exclude_from_compliance", False):
            return "[ {0} ] SKIP (Knowledge-Base)".format(name)

        KEEP_FILES = ["ci.yml", "release.yml", "dependabot.yml", "CODEOWNERS", ".golangci.yml"]
        LEGACY_PATTERNS = [".travis.yml", "appveyor.yml", ".circleci", "ci-cd.yml", "Jenkinsfile", ".jenkins", "main.yml", "build.yml"]
        cleaned_items = []

        for pattern in LEGACY_PATTERNS:
            item = path / pattern
            if item.exists():
                try:
                    if item.is_dir():
                        shutilRmtree(item)
                    else:
                        item.unlink()
                    cleaned_items.append(pattern)
                except Exception as e:
                    self.logger.error("{0} : Failed to remove legacy item {1} for {2}: {3}".format(self.Name, pattern, name, e))

        workflow_dir = path / ".github" / "workflows"
        if workflow_dir.exists():
            try:
                for item in workflow_dir.iterdir():
                    if item.name not in KEEP_FILES:
                        if item.is_dir():
                            shutilRmtree(item)
                        else:
                            item.unlink()
                        cleaned_items.append(".github/workflows/{0}".format(item.name))
            except Exception as e:
                self.logger.error("{0} : Failed to clean workflows for {1}: {2}".format(self.Name, name, e))

        if cleaned_items:
            return "[ {0} ] CLEANED: {1}".format(name, ", ".join(cleaned_items))
        return "[ {0} ] ALREADY CLEAN".format(name)

    # -----------------------------------------------------------------------------------------------

    def discover_repos(self, root_dir: pathlibPath) -> typingList[typingDict[str, typingAny]]:
        """
        Scans for all directories containing .git and updates inventory.
        """
        self.logger.info("{0} : Discovering repositories in {1}...".format(self.Name, root_dir))
        found = []
        root_path = root_dir.resolve()

        for root, dirs, files in osWalk(root_dir):
            if ".git" in dirs or ".git" in files:
                path = pathlibPath(root).resolve()

                if path == root_path:
                    if ".git" in dirs:
                        dirs.remove(".git")
                    continue

                remote_out, _, _ = self.run_git(path, ["remote", "get-url", "origin"])
                branch_out, _, _ = self.run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])

                found.append({
                    "name": path.name,
                    "path": str(path.absolute()),
                    "remote": remote_out,
                    "master_branch": branch_out if branch_out else "develop"
                })

                if ".git" in dirs:
                    dirs.remove(".git")

        found.sort(key=lambda x: x["name"])
        return found

    # -----------------------------------------------------------------------------------------------

    def get_github_token(self) -> typingOptional[str]:
        """
        Retrieves the GitHub token from environment variables or a local hidden file.
        """
        token = osGetenv("GITHUB_TOKEN")
        if token:
            return token

        token_path = pathlibPath.home() / ".github_token"
        if token_path.exists():
            try:
                with open(token_path, "r", encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                self.logger.error("{0} : Failed to read .github_token file: {1}".format(self.Name, e))

        return None

    # -----------------------------------------------------------------------------------------------

    def run_git(self, path: pathlibPath, args: typingList[str], timeout: int = 30) -> typingTuple[str, str, int]:
        """
        Executes a Git command in a specific directory.
        Ensures non-interactive execution and injects GITHUB_TOKEN if available.
        """
        env = osEnviron.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        token = self.get_github_token()
        git_base = ["git", "-C", str(path)]

        if token and any(cmd in args for cmd in ["push", "pull", "fetch", "clone"]):
            git_base += [
                "-c", "credential.helper=",
                "-c", "credential.helper=!f() { echo \"username=x-access-token\"; echo \"password={0}\"; }; f".format(token)
            ]

        try:
            result = subprocessRun(
                git_base + args,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
                env=env
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocessTimeoutExpired:
            return "", "Command timed out", -1
        except Exception as e:
            return "", str(e), -1

    # -----------------------------------------------------------------------------------------------

    def _find_workspace_root(self) -> pathlibPath:
        """
        Walk up from this script's location until we find the workspace root.
        """
        current = pathlibPath(__file__).resolve().parent
        for parent in [current] + list(current.parents):
            if list(parent.glob("*.code-workspace")):
                return parent
            if (parent / "obsidian-brain").is_dir() and (parent / "universal-logger").is_dir():
                return parent
        return pathlibPath(__file__).resolve().parents[3]

    # -----------------------------------------------------------------------------------------------

    def _ensure_auth(self) -> str:
        """
        Verifies that a GitHub token is available.
        """
        token = self.get_github_token()
        if not token:
            self.logger.critical("\n" + "!"*60)
            self.logger.critical("🚨 FLEET COMMANDER: AUTHENTICATION REQUIRED")
            self.logger.critical("!"*60)
            self.logger.critical("You are attempting a remote operation that requires GitHub credentials.")
            self.logger.critical("To proceed, please provide a Personal Access Token (PAT).")
            self.logger.critical("\nOption A (Environment Variable):")
            self.logger.critical("   export GITHUB_TOKEN=your_token_here")
            self.logger.critical("\nOption B (Hidden File):")
            self.logger.critical("   echo 'your_token_here' > ~/.github_token")
            self.logger.critical("\nNote: Ensure the token has 'repo' and 'workflow' permissions.")
            self.logger.critical("!"*60 + "\n")
            sysExit(1)
        return token

    # -----------------------------------------------------------------------------------------------

    def _load_job_fragment(self, name: str, working_dir: str, templates_dir: pathlibPath) -> str:
        """Loads a YAML fragment from the templates directory and injects the working directory."""
        frag_path = templates_dir / "Polyglot" / "jobs" / "{0}.yml".format(name)

        if frag_path.exists():
            try:
                with open(frag_path, "r", encoding='utf-8') as f:
                    content = f.read()
                content = content.replace("{{WORKING_DIR}}", working_dir)
                content = content.replace("{{GO_VERSION}}", self.go_version)
                content = content.replace("{{PYTHON_VERSION}}", self.python_version)
                content = content.replace("{{RUST_VERSION}}", self.rust_version)
                content = content.replace("{{CPP_VERSION}}", self.cpp_version)
                return content
            except Exception as e:
                self.logger.error("{0} : Failed to load job fragment {1}: {2}".format(self.Name, name, e))
        return ""

    # -----------------------------------------------------------------------------------------------

    def _detect_language_path(self, repo_path: pathlibPath, lang: str) -> typingOptional[str]:
        """Checks for language folder in root or distconf/ and returns the relative path."""
        if (repo_path / lang).is_dir():
            return lang
        if (repo_path / "distconf" / lang).is_dir():
            return "distconf/{0}".format(lang)
        if (repo_path / "safesock" / lang).is_dir():
            return "safesock/{0}".format(lang)
        if lang == "python":
            if (repo_path / "requirements.txt").exists() or (repo_path / "setup.py").exists():
                return "."
        if lang == "go":
            if (repo_path / "go.mod").exists():
                return "."
            if (repo_path / "go" / "go.mod").exists():
                return "go"
        return None

    # -----------------------------------------------------------------------------------------------

    def _resolve_inventory_paths(self, inventory: typingDict[str, typingAny]) -> typingDict[str, typingAny]:
        """
        Resolves relative paths in inventory.json to absolute paths based on
        the workspace root.
        """
        workspace_root = self._find_workspace_root()

        for repo in inventory.get("repositories", []):
            repo_path = repo.get("path", "")
            if repo_path.startswith("./") or repo_path.startswith("../") or not pathlibPath(repo_path).is_absolute():
                repo["path"] = str((workspace_root / repo_path).resolve())

        return inventory

# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    class DefaultLogger:
        def info(self, msg: str) -> None:
            print(msg)
        def error(self, msg: str) -> None:
            print(msg)
        def warning(self, msg: str) -> None:
            print(msg)
        def critical(self, msg: str) -> None:
            print(msg)

    cmd = sysArgv[1] if len(sysArgv) > 1 else "status"
    cmd_args = sysArgv[2:]

    manager = FleetManager(config=object(), logger=DefaultLogger())
    manager.run_manager(cmd, cmd_args)

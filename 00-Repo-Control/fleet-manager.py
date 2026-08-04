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
- command: The action to perform (sync, status, audit, etc.).
- args: Additional arguments for the command.
"""

# [SCAN] Role: Developer | Source: fleet-manager.py | State: Active

from os import name as osName, execl as osExecl, getenv as osGetenv, walk as osWalk, environ as osEnviron
from os.path import (
    dirname as osPathDirname,
    abspath as osPathAbspath,
    exists as osPathExists,
    join as osPathJoin,
    samefile as osPathSamefile,
)
from sys import executable as sysExecutable, argv as sysArgv, exit as sysExit, stdout as sysStdout
from json import load as jsonLoad, dump as jsonDump
from subprocess import run as subprocessRun, TimeoutExpired as subprocessTimeoutExpired
from pathlib import Path as pathlibPath
from concurrent.futures import ThreadPoolExecutor as concurrentThreadPoolExecutor
from shutil import rmtree as shutilRmtree
from typing import (
    List as typingList,
    Dict as typingDict,
    Any as typingAny,
    Optional as typingOptional,
    Tuple as typingTuple,
)

# -----------------------------------------------------------------------------------------------
# Ecosystem & Venv bootstrap via microservice-toolbox
# -----------------------------------------------------------------------------------------------
_curr_dir = osPathDirname(osPathAbspath(__file__))
_ws_root = pathlibPath(_curr_dir).parents[3]
_mb_path = _ws_root / "microservice-toolbox" / "python"
if _mb_path.exists() and str(_mb_path) not in sys.path:
    sys.path.insert(0, str(_mb_path))

try:
    from microservice_toolbox.utils.bootstrap import bootstrap_microservice
    bootstrap_microservice(__file__, app_name="fleet_manager")
except Exception:
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


# -----------------------------------------------------------------------------------------------

class FleetManager:
    """
    Core orchestrator for fleet-wide Git and maintenance operations.
    """

    def __init__(self, *, config: typingAny, logger: typingAny, name: typingOptional[str] = None) -> None:
        self.config = config
        self.logger = logger
        self.Name = name or self.__class__.__name__

        # Load dynamic toolchain versions from service-registry.json if available
        registry_path = pathlibPath(__file__).resolve().parent / "service-registry.json"
        toolchains = {}
        if registry_path.exists():
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    toolchains = jsonLoad(f).get("toolchains", {})
            except Exception:
                pass

        self.GoVersion = toolchains.get("go", "1.25")
        self.PythonVersion = toolchains.get("python", "3.12")
        self.RustVersion = toolchains.get("rust", "1.91")
        self.CppVersion = toolchains.get("cpp", "20")

    # -----------------------------------------------------------------------------------------------

    def run(self, *, command: str, args: typingList[str], target_repo: typingOptional[str] = None) -> None:
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

        inventory = self._resolve_inventory_paths(inventory=inventory)

        if target_repo:
            all_repos = inventory.get("repositories", [])
            if target_repo.lower() in ["active", "active-workspaces", "workspaces"]:
                active_names = self._resolve_active_workspaces()
                filtered = [r for r in all_repos if r.get("name") in active_names or pathlibPath(r.get("path", "")).name in active_names]
                if filtered:
                    inventory["repositories"] = filtered
                    self.logger.info("{0} : 🎯 Dynamically filtered target to {1} active workspace repository(ies)".format(self.Name, len(filtered)))
                else:
                    self.logger.error("{0} : ❌ No active workspace repositories found.".format(self.Name))
                    return
            else:
                filtered = [r for r in all_repos if target_repo.lower() in r.get("name", "").lower()]
                if filtered:
                    inventory["repositories"] = filtered
                    self.logger.info("{0} : 🎯 Filtered target to {1} repository(ies) matching '{2}'".format(self.Name, len(filtered), target_repo))
                else:
                    self.logger.error("{0} : ❌ Target filter '{1}' matched 0 repositories.".format(self.Name, target_repo))
                    return

        num_repos = len(inventory.get("repositories", []))
        optimal_workers = max(1, min(32, num_repos))

        if command in ["sync", "vault-sync", "restore", "tag", "audit", "status", "attach"]:
            self._ensure_auth()

        # Command Dispatcher
        if command == "discover":
            self._handle_discover(inventory=inventory, inventory_path=inventory_path)
        elif command == "status":
            self._handle_status(inventory=inventory, workers=optimal_workers)
        elif command == "sync":
            self._handle_sync(inventory=inventory, workers=optimal_workers)
        elif command == "attach":
            self._handle_attach(inventory=inventory, workers=optimal_workers)
        elif command == "audit":
            self._handle_audit(inventory=inventory, workers=optimal_workers)
        elif command == "commit":
            self._handle_commit(inventory=inventory, workers=optimal_workers, args=args)
        elif command == "tag":
            self._handle_tag(inventory=inventory, workers=optimal_workers, args=args)
        elif command == "branch":
            self._handle_branch(inventory=inventory, workers=optimal_workers, args=args)
        elif command == "template":
            self._handle_template(inventory=inventory, workers=optimal_workers)
        elif command == "cleanup":
            self._handle_cleanup(inventory=inventory, workers=optimal_workers)
        elif command == "restore":
            self._handle_restore(inventory=inventory, workers=optimal_workers)
        elif command == "vault-sync":
            self._handle_vault_sync(args=args)
        elif command == "refresh":
            self._handle_refresh(args=args)
        else:
            self.logger.error("{0} : Unknown command: {1}".format(self.Name, command))

    # -----------------------------------------------------------------------------------------------

    def get_status(self, *, repo: typingDict[str, typingAny]) -> typingDict[str, typingAny]:
        """
        Checks the status of a single repository.
        """
        path = repo["path"]
        name = repo["name"]

        if not osPathExists(path):
            return {"name": name, "status": "MISSING", "branch": "N/A", "clean": False, "ahead": 0, "behind": 0}

        branch_out, _, _ = self.run_git(path=pathlibPath(path), args=["rev-parse", "--abbrev-ref", "HEAD"])
        status_out, _, _ = self.run_git(path=pathlibPath(path), args=["status", "--porcelain"])

        ahead, behind = 0, 0
        remote_branch = repo.get("master_branch", "develop")

        self.run_git(path=pathlibPath(path), args=["fetch", "origin"])

        ab_out, _, code = self.run_git(
            path=pathlibPath(path),
            args=["rev-list", "--left-right", "--count", "origin/{0}...HEAD".format(remote_branch)]
        )
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

    def sync_repo(self, *, repo: typingDict[str, typingAny]) -> typingList[str]:
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

        status_out, _, _ = self.run_git(path=pathlibPath(path), args=["status", "--porcelain"])
        if len(status_out) > 0:
            logs.append("[ {0} ] SKIP: Uncommitted changes found. Please commit first.".format(name))
            return logs

        current_branch, _, _ = self.run_git(path=pathlibPath(path), args=["rev-parse", "--abbrev-ref", "HEAD"])
        if current_branch != target_branch:
            logs.append("[ {0} ] Branch mismatch (Current: {1}, Target: {2}). Attempting to attach...".format(name, current_branch, target_branch))
            attach_logs = self.attach_repo(repo=repo)
            logs.extend(attach_logs)

            current_branch, _, _ = self.run_git(path=pathlibPath(path), args=["rev-parse", "--abbrev-ref", "HEAD"])
            if current_branch != target_branch:
                logs.append("[ {0} ] SKIP: Could not attach to '{1}'. Skipping sync.".format(name, target_branch))
                return logs

        logs.append("[ {0} ] Pulling {1}...".format(name, target_branch))
        _, err, code = self.run_git(path=pathlibPath(path), args=["pull", "origin", target_branch])
        if code != 0:
            logs.append("[ {0} ] PULL FAILED: {1}".format(name, err))
            return logs

        if osPathExists(osPathJoin(path, ".gitmodules")):
            logs.append("[ {0} ] Updating submodules...".format(name))
            _, err, code = self.run_git(path=pathlibPath(path), args=["submodule", "update", "--init", "--recursive"])
            if code != 0:
                logs.append("[ {0} ] SUBMODULE ERROR: {1}".format(name, err))

        ab_out, _, code = self.run_git(
            path=pathlibPath(path),
            args=["rev-list", "--left-right", "--count", "origin/{0}...HEAD".format(target_branch)]
        )
        ahead = 0
        if code == 0:
            parts = ab_out.split()
            if len(parts) == 2:
                ahead = int(parts[1])

        if ahead > 0:
            logs.append("[ {0} ] Pushing {1} ({2} commit(s) ahead)...".format(name, target_branch, ahead))
            _, err, code = self.run_git(path=pathlibPath(path), args=["push", "origin", target_branch])
            if code != 0:
                logs.append("[ {0} ] PUSH FAILED: {1}".format(name, err))
                return logs
            logs.append("[ {0} ] SYNCED & PUSHED ({1})".format(name, target_branch))
        else:
            logs.append("[ {0} ] UP-TO-DATE ({1})".format(name, target_branch))

        return logs

    # -----------------------------------------------------------------------------------------------

    def attach_repo(self, *, repo: typingDict[str, typingAny]) -> typingList[str]:
        """
        Ensures a repository is on its designated master_branch.
        """
        path = repo["path"]
        name = repo["name"]
        target_branch = repo.get("master_branch", "develop")
        logs = []

        if not osPathExists(path):
            logs.append("[ {0} ] ERROR: Path not found".format(name))
            return logs

        current_branch, _, _ = self.run_git(path=pathlibPath(path), args=["rev-parse", "--abbrev-ref", "HEAD"])

        if current_branch == target_branch:
            logs.append("[ {0} ] Already on {1}".format(name, target_branch))
            return logs

        status_out, _, _ = self.run_git(path=pathlibPath(path), args=["status", "--porcelain"])
        if len(status_out) > 0:
            logs.append("[ {0} ] CANNOT ATTACH: Uncommitted changes found. Please commit or stash first.".format(name))
            return logs

        logs.append("[ {0} ] Attaching to {1}...".format(name, target_branch))
        _, err, code = self.run_git(path=pathlibPath(path), args=["checkout", target_branch])

        if code != 0:
            self.run_git(path=pathlibPath(path), args=["fetch", "origin", target_branch])
            _, err, code = self.run_git(path=pathlibPath(path), args=["checkout", target_branch])

        if code == 0:
            logs.append("[ {0} ] ATTACHED to {1}".format(name, target_branch))
        else:
            logs.append("[ {0} ] ATTACH FAILED: {1}".format(name, err))

        return logs

    # -----------------------------------------------------------------------------------------------

    def audit_repo(self, *, repo: typingDict[str, typingAny]) -> typingDict[str, typingAny]:
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
                run_status = "ERR {0}".format(e.code)
            except Exception:
                run_status = "ERR NETWORK"

        status_icon = "🔘"
        if run_status == "SUCCESS": status_icon = "✅"
        elif run_status in ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"]: status_icon = "❌"
        elif run_status in ["IN_PROGRESS", "QUEUED", "WAITING"]: status_icon = "⏳"
        elif "ERR" in run_status or run_status == "UNKNOWN": status_icon = "⚠️"

        return {"name": name, "ci": "✅" if ci_exists else "❌", "dep": "✅" if dep_exists else "❌", "ai": "✅" if ai_exists else "❌", "run": "{0} {1}".format(status_icon, run_status)}

    # -----------------------------------------------------------------------------------------------

    def template_repo(self, *, repo: typingDict[str, typingAny], templates_dir: pathlibPath) -> str:
        """
        Applies standard CI/CD templates to a repository.
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

        go_path = self._detect_language_path(repo_path=path, lang="go")
        python_path = self._detect_language_path(repo_path=path, lang="python")
        rust_path = self._detect_language_path(repo_path=path, lang="rust")
        cpp_path = self._detect_language_path(repo_path=path, lang="cpp")

        is_polyglot = any([python_path, rust_path, cpp_path])
        archetype = "Polyglot" if is_polyglot else "Microservice"
        archetype_dir = templates_dir / archetype

        # CI Template
        ci_src = archetype_dir / "ci.yml"
        ci_dst = workflows_dir / "ci.yml"
        if ci_src.exists():
            try:
                with open(ci_src, "r", encoding='utf-8') as src:
                    content = src.read()
                
                label = "Polyglot" if is_polyglot else "Microservice"
                params = "Go:{0}, Py:{1}, Rust:{2}, C++:{3}".format(self.GoVersion, self.PythonVersion, self.RustVersion, self.CppVersion)
                content = content.replace("{{GO_VERSION}}", self.GoVersion)
                content = content.replace("{{PYTHON_VERSION}}", self.PythonVersion)
                content = content.replace("{{RUST_VERSION}}", self.RustVersion)
                content = content.replace("{{CPP_VERSION}}", self.CppVersion)
                content = content.replace("{{WORKING_DIR}}", go_path or ".")

                if is_polyglot:
                    for lang, lpath in [("go", go_path), ("python", python_path), ("rust", rust_path), ("cpp", cpp_path)]:
                        if lpath:
                            content += self._load_job_fragment(name=lang, working_dir=lpath, templates_dir=templates_dir)

                with open(ci_dst, "w", encoding='utf-8') as dst:
                    dst.write(content)
            except Exception as e:
                self.logger.error("{0} : Failed to apply CI template for {1}: {2}".format(self.Name, name, e))

        return "[ {0} ] TEMPLATED ({1})".format(name, archetype)

    # -----------------------------------------------------------------------------------------------

    def cleanup_repo(self, *, repo: typingDict[str, typingAny]) -> str:
        """
        Purges legacy CI/CD artifacts.
        """
        path = pathlibPath(repo["path"])
        name = repo["name"]

        if not path.exists():
            return "[ {0} ] MISSING".format(name)

        if repo.get("exclude_from_compliance", False):
            return "[ {0} ] SKIP (Knowledge-Base)".format(name)

        KEEP_FILES = ["ci.yml", "release.yml", "dependabot.yml", "CODEOWNERS", ".golangci.yml"]
        LEGACY_PATTERNS = [".travis.yml", "appveyor.yml", ".circleci", "ci-cd.yml", "Jenkinsfile", ".jenkins", "main.yml", "build.yml"]
        cleaned = []

        for pattern in LEGACY_PATTERNS:
            item = path / pattern
            if item.exists():
                try:
                    if item.is_dir(): shutilRmtree(item)
                    else: item.unlink()
                    cleaned.append(pattern)
                except Exception as e:
                    self.logger.error("{0} : Failed to remove {1} for {2}: {3}".format(self.Name, pattern, name, e))

        return "[ {0} ] CLEANED: {1}".format(name, ", ".join(cleaned)) if cleaned else "[ {0} ] ALREADY CLEAN".format(name)

    # -----------------------------------------------------------------------------------------------

    def discover_repos(self, *, root_dir: pathlibPath) -> typingList[typingDict[str, typingAny]]:
        """
        Scans for all directories containing .git.
        """
        self.logger.info("{0} : Discovering repositories in {1}...".format(self.Name, root_dir))
        found = []
        root_path = root_dir.resolve()

        for root, dirs, files in osWalk(root_dir):
            if ".git" in dirs or ".git" in files:
                path = pathlibPath(root).resolve()
                if path == root_path:
                    if ".git" in dirs: dirs.remove(".git")
                    continue

                remote, _, _ = self.run_git(path=path, args=["remote", "get-url", "origin"])
                branch, _, _ = self.run_git(path=path, args=["rev-parse", "--abbrev-ref", "HEAD"])

                found.append({
                    "name": path.name,
                    "path": str(path.absolute()),
                    "remote": remote,
                    "master_branch": branch or "develop"
                })
                if ".git" in dirs: dirs.remove(".git")

        found.sort(key=lambda x: x["name"])
        return found

    # -----------------------------------------------------------------------------------------------

    def get_github_token(self) -> typingOptional[str]:
        """
        Retrieves the GitHub token.
        """
        token = osGetenv("GITHUB_TOKEN")
        if token: return token
        token_path = pathlibPath.home() / ".github_token"
        if token_path.exists():
            try:
                with open(token_path, "r", encoding='utf-8') as f: return f.read().strip()
            except Exception as e:
                self.logger.error("{0} : Failed to read .github_token: {1}".format(self.Name, e))
        return None

    # -----------------------------------------------------------------------------------------------

    def run_git(self, *, path: pathlibPath, args: typingList[str], timeout: int = 30) -> typingTuple[str, str, int]:
        """
        Executes a Git command.
        """
        env = osEnviron.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        token = self.get_github_token()
        git_base = ["git", "-C", str(path)]

        if token and any(cmd in args for cmd in ["push", "pull", "fetch", "clone"]):
            git_base += [
                "-c", "credential.helper=",
                "-c", "credential.helper=!f() {{ echo \"username=x-access-token\"; echo \"password={0}\"; }}; f".format(token)
            ]

        try:
            result = subprocessRun(git_base + args, capture_output=True, text=True, check=False, timeout=timeout, env=env)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocessTimeoutExpired: return "", "Command timed out", -1
        except Exception as e: return "", str(e), -1

    # -----------------------------------------------------------------------------------------------

    def _handle_discover(self, *, inventory: typingDict[str, typingAny], inventory_path: pathlibPath) -> None:
        try:
            from build_inventory import MInventoryBuilder
            builder = MInventoryBuilder(config=self.config, logger=self.logger)
            builder.build(dry_run=False)
            self.logger.info("{0} : Discovery completed safely via MInventoryBuilder.".format(self.Name))
            return
        except ImportError:
            try:
                import importlib.util
                build_inv_path = pathlibPath(__file__).resolve().parent / "build-inventory.py"
                spec = importlib.util.spec_from_file_location("build_inventory", str(build_inv_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    builder = mod.MInventoryBuilder(config=self.config, logger=self.logger)
                    builder.build(dry_run=False)
                    self.logger.info("{0} : Discovery completed safely via MInventoryBuilder.".format(self.Name))
                    return
            except Exception as ex:
                self.logger.warning("{0} : Could not invoke MInventoryBuilder ({1}), using fallback.".format(self.Name, ex))

        workspace_root = self._find_workspace_root()
        discovered = self.discover_repos(root_dir=workspace_root)
        for repo in discovered:
            try:
                rel = pathlibPath(repo["path"]).relative_to(workspace_root)
                repo["path"] = "./{0}".format(rel.as_posix())
            except ValueError: pass
        inventory["repositories"] = discovered
        try:
            with open(inventory_path, "w", encoding='utf-8') as f: jsonDump(inventory, f, indent=2)
            self.logger.info("{0} : Discovered and registered {1} repositories.".format(self.Name, len(discovered)))
        except Exception as e: self.logger.error("{0} : Failed to save discovery: {1}".format(self.Name, e))

    # -----------------------------------------------------------------------------------------------

    def _handle_status(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        self.logger.info("{0} : {1:<25} | {2:<15} | {3:<8} | {4:<5}".format(self.Name, 'Repository', 'Branch', 'Status', 'Clean'))
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda r: self.get_status(repo=r), inventory["repositories"]))
        for r in results:
            clean = "✅" if r["clean"] else "❌"
            self.logger.info("{0} : {1:<25} | {2:<15} | {3:<8} | {4:<5}".format(self.Name, r['name'], r['branch'], r['status'], clean))

    # -----------------------------------------------------------------------------------------------

    def _handle_sync(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        self.logger.info("{0} : Starting Global Fleet Sync...".format(self.Name))
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda r: self.sync_repo(repo=r), inventory["repositories"]))
        for logs in results:
            for log in logs: self.logger.info("{0} : {1}".format(self.Name, log))

    # -----------------------------------------------------------------------------------------------

    def _handle_attach(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        self.logger.info("{0} : Attaching fleet to designated branches...".format(self.Name))
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda r: self.attach_repo(repo=r), inventory["repositories"]))
        for logs in results:
            for log in logs: self.logger.info("{0} : {1}".format(self.Name, log))

    # -----------------------------------------------------------------------------------------------

    def _handle_audit(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        self.logger.info("{0} : {1:<25} | {2:<4} | {3:<4} | {4:<4} | {5:<20}".format(self.Name, 'Repository', 'CI', 'Dep', 'AI', 'CI Status'))
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda r: self.audit_repo(repo=r), inventory["repositories"]))
        for r in results:
            self.logger.info("{0} : {1:<25} | {2:<4} | {3:<4} | {4:<4} | {5:<20}".format(self.Name, r['name'], r['ci'], r['dep'], r['ai'], r['run']))

    # -----------------------------------------------------------------------------------------------

    def _handle_commit(self, *, inventory: typingDict[str, typingAny], workers: int, args: typingList[str]) -> None:
        msg = args[0] if args else "chore(fleet): mass sync"
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            def _do(repo):
                path = repo["path"]
                if not osPathExists(path): return "[ {0} ] MISSING".format(repo['name'])
                status, _, _ = self.run_git(path=pathlibPath(path), args=["status", "--porcelain"])
                if not status: return "[ {0} ] CLEAN".format(repo['name'])
                self.run_git(path=pathlibPath(path), args=["add", "."])
                _, err, code = self.run_git(path=pathlibPath(path), args=["commit", "-m", msg])
                return "[ {0} ] COMMITTED".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
            results = list(executor.map(_do, inventory["repositories"]))
        for r in results: self.logger.info("{0} : {1}".format(self.Name, r))

    # -----------------------------------------------------------------------------------------------

    def _handle_tag(self, *, inventory: typingDict[str, typingAny], workers: int, args: typingList[str]) -> None:
        tag_name = args[0] if args else None
        if not tag_name: return
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            def _do(repo):
                path = repo["path"]
                if not osPathExists(path): return "[ {0} ] MISSING".format(repo['name'])
                self.run_git(path=pathlibPath(path), args=["tag", tag_name])
                _, err, code = self.run_git(path=pathlibPath(path), args=["push", "origin", tag_name])
                return "[ {0} ] TAGGED".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
            results = list(executor.map(_do, inventory["repositories"]))
        for r in results: self.logger.info("{0} : {1}".format(self.Name, r))

    # -----------------------------------------------------------------------------------------------

    def _handle_branch(self, *, inventory: typingDict[str, typingAny], workers: int, args: typingList[str]) -> None:
        branch_name = args[0] if args else None
        if not branch_name: return
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            def _do(repo):
                path = repo["path"]
                if not osPathExists(path): return "[ {0} ] MISSING".format(repo['name'])
                _, _, code = self.run_git(path=pathlibPath(path), args=["checkout", branch_name])
                return "[ {0} ] CHECKED OUT".format(repo['name']) if code == 0 else "[ {0} ] FAILED".format(repo['name'])
            results = list(executor.map(_do, inventory["repositories"]))
        for r in results: self.logger.info("{0} : {1}".format(self.Name, r))

    # -----------------------------------------------------------------------------------------------

    def _handle_template(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        templates_dir = pathlibPath(__file__).resolve().parent.parent / "04-Templates"
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda r: self.template_repo(repo=r, templates_dir=templates_dir), inventory["repositories"]))
        for r in results: self.logger.info("{0} : {1}".format(self.Name, r))

    # -----------------------------------------------------------------------------------------------

    def _handle_cleanup(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(lambda r: self.cleanup_repo(repo=r), inventory["repositories"]))
        for r in results: self.logger.info("{0} : {1}".format(self.Name, r))

    # -----------------------------------------------------------------------------------------------

    def _handle_restore(self, *, inventory: typingDict[str, typingAny], workers: int) -> None:
        with concurrentThreadPoolExecutor(max_workers=workers) as executor:
            def _do(repo):
                path = pathlibPath(repo["path"])
                if path.exists(): return "[ {0} ] EXISTS".format(repo['name'])
                res = subprocessRun(["git", "clone", repo["remote"], str(path)], capture_output=True, text=True)
                return "[ {0} ] RESTORED".format(repo['name']) if res.returncode == 0 else "[ {0} ] FAILED".format(repo['name'])
            results = list(executor.map(_do, inventory["repositories"]))
        for r in results: self.logger.info("{0} : {1}".format(self.Name, r))

    # -----------------------------------------------------------------------------------------------

    def _handle_vault_sync(self, *, args: typingList[str]) -> None:
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
            status, _, _ = self.run_git(path=sub, args=["status", "--porcelain"])
            if status:
                self.logger.info("{0} : [ {1} ] Committing changes...".format(self.Name, name))
                self.run_git(path=sub, args=["add", "."])
                self.run_git(path=sub, args=["commit", "-m", msg])

            self.logger.info("{0} : [ {1} ] Pulling latest...".format(self.Name, name))
            self.run_git(path=sub, args=["pull", "--rebase", "origin", "develop"])

            # 2. Push (Only if ahead)
            ab_out, _, code = self.run_git(path=sub, args=["rev-list", "--left-right", "--count", "origin/develop...HEAD"])
            ahead = 0
            if code == 0:
                parts = ab_out.split()
                if len(parts) == 2:
                    ahead = int(parts[1])

            if ahead > 0:
                self.logger.info("{0} : [ {1} ] Pushing {2} commit(s) to origin...".format(self.Name, name, ahead))
                _, err, code = self.run_git(path=sub, args=["push", "origin", "develop"])
                if code != 0:
                    self.logger.error("{0} : [ {1} ] PUSH FAILED: {2}".format(self.Name, name, err))
                else:
                    self.logger.info("{0} : [ {1} ] SYNCED.".format(self.Name, name))
            else:
                self.logger.info("{0} : [ {1} ] UP-TO-DATE.".format(self.Name, name))

        # 2. Update parent pointer
        self.logger.info("{0} : [ obsidian-brain ] Updating submodule pointers...".format(self.Name))
        self.run_git(path=obsidian_dir, args=["add", "."])
        status, _, _ = self.run_git(path=obsidian_dir, args=["status", "--porcelain"])
        if status:
            self.run_git(path=obsidian_dir, args=["commit", "-m", "chore(fleet): update submodule pointers"])
            self.logger.info("{0} : [ obsidian-brain ] Pointers committed.".format(self.Name))

        # 3. Final Vault Push (Only if ahead)
        ab_out, _, code = self.run_git(path=obsidian_dir, args=["rev-list", "--left-right", "--count", "origin/develop...HEAD"])
        ahead = 0
        if code == 0:
            parts = ab_out.split()
            if len(parts) == 2:
                ahead = int(parts[1])

        if ahead > 0:
            self.logger.info("{0} : [ obsidian-brain ] Pushing {1} commit(s) to origin...".format(self.Name, ahead))
            _, err, code = self.run_git(path=obsidian_dir, args=["push", "origin", "develop"])
            if code == 0:
                self.logger.info("{0} : ✨ Atomic Vault Sync Complete!".format(self.Name))
            else:
                self.logger.error("{0} : ❌ Vault push failed: {1}".format(self.Name, err))
        else:
            self.logger.info("{0} : ✨ Vault is already up-to-date.".format(self.Name))

    # -----------------------------------------------------------------------------------------------

    def _handle_refresh(self, *, args: typingList[str]) -> None:
        refresh_script = pathlibPath(__file__).resolve().parent / "fleet-refresh.py"
        subprocessRun([sysExecutable, str(refresh_script)] + args)

    # -----------------------------------------------------------------------------------------------

    def _resolve_active_workspaces(self) -> typingAny:
        workspace_root = self._find_workspace_root()
        active = set()

        # 1. Check environment variable
        env_var = osGetenv("ACTIVE_WORKSPACES") or osGetenv("WORKSPACE_PATHS")
        if env_var:
            for item in env_var.split(","):
                if item.strip():
                    active.add(pathlibPath(item.strip()).name)
            if active:
                return active

        # 2. Check *.code-workspace JSON files
        for ws_file in workspace_root.glob("*.code-workspace"):
            try:
                with open(ws_file, "r", encoding="utf-8") as f:
                    data = jsonLoad(f)
                    for folder in data.get("folders", []):
                        p = folder.get("path")
                        if p:
                            active.add(pathlibPath(p).name)
            except Exception:
                pass

        if active:
            return active

        # 3. Fallback: Sibling directories containing .git
        try:
            for item in workspace_root.iterdir():
                if item.is_dir() and (item / ".git").exists():
                    active.add(item.name)
        except Exception:
            pass

        return active

    # -----------------------------------------------------------------------------------------------

    def _find_workspace_root(self) -> pathlibPath:
        current = pathlibPath(__file__).resolve().parent
        for parent in [current] + list(current.parents):
            if (parent / "obsidian-brain").is_dir(): return parent
        return pathlibPath(__file__).resolve().parents[3]

    # -----------------------------------------------------------------------------------------------

    def _ensure_auth(self) -> None:
        if not self.get_github_token():
            self.logger.warning("{0} : NO GITHUB_TOKEN FOUND".format(self.Name))

    # -----------------------------------------------------------------------------------------------

    def _load_job_fragment(self, *, name: str, working_dir: str, templates_dir: pathlibPath) -> str:
        frag_path = templates_dir / "Polyglot" / "jobs" / "{0}.yml".format(name)
        if frag_path.exists():
            try:
                with open(frag_path, "r", encoding='utf-8') as f:
                    content = f.read()
                return content.replace("{{WORKING_DIR}}", working_dir)
            except Exception: pass
        return ""

    # -----------------------------------------------------------------------------------------------

    def _detect_language_path(self, *, repo_path: pathlibPath, lang: str) -> typingOptional[str]:
        if (repo_path / lang).is_dir(): return lang
        if lang == "python" and (repo_path / "requirements.txt").exists(): return "."
        if lang == "go" and (repo_path / "go.mod").exists(): return "."
        return None

    # -----------------------------------------------------------------------------------------------

    def _resolve_inventory_paths(self, *, inventory: typingDict[str, typingAny]) -> typingDict[str, typingAny]:
        workspace_root = self._find_workspace_root()
        for repo in inventory.get("repositories", []):
            repo_path = repo.get("path", "")
            if not pathlibPath(repo_path).is_absolute():
                repo["path"] = str((workspace_root / repo_path).resolve())
        return inventory


# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    class DefaultLogger:
        def info(self, msg: str) -> None: print(msg)
        def error(self, msg: str) -> None: print(msg)
        def warning(self, msg: str) -> None: print(msg)
        def critical(self, msg: str) -> None: print(msg)

    parser = argparse.ArgumentParser(
        description="Fleet Manager: Orchestrates fleet-wide Git, CI/CD, and maintenance operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Commands:
  status       Check branch, clean/dirty state, ahead/behind count across fleet
  sync         Pull, update submodules, and push changes across fleet
  vault-sync   Perform atomic sync of obsidian-brain submodules and parent pointer
  audit        Audit CI/CD workflow status and GitHub Actions status
  commit       Stage and commit changes across fleet (pass message as extra arg)
  tag          Tag and push git tag across fleet (pass tag name as extra arg)
  branch       Checkout target git branch across fleet (pass branch name as extra arg)
  template     Apply standard CI/CD workflow templates across fleet
  cleanup      Purge legacy CI/CD artifacts across fleet
  restore      Git clone any missing fleet repositories from remotes
  discover     Safely scan workspace and update inventory.json
  refresh      Refresh workspace state via fleet-refresh.py
"""
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        choices=[
            "status", "sync", "vault-sync", "audit", "commit",
            "tag", "branch", "template", "cleanup", "restore",
            "discover", "refresh", "attach"
        ],
        help="Command to run (default: status)"
    )
    parser.add_argument(
        "--repo", "-r",
        dest="target_repo",
        default=None,
        help="Filter operations to a specific repository by name or substring"
    )

    cli_args, extra_args = parser.parse_known_args()

    try:
        from microservice_toolbox.config.loader import load_config
        from microservice_toolbox.logger import UniLog
        config = load_config("standalone", input_args=[])
        logger = UniLog(
            app_name="fleet_manager",
            config_profile="standalone",
            logger_profile="devel"
        )
        config.set_logger(logger)
    except Exception:
        config = object()
        logger = DefaultLogger()

    manager = FleetManager(config=config, logger=logger)
    manager.run(command=cli_args.command, args=extra_args, target_repo=cli_args.target_repo)

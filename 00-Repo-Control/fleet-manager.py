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
- inventory_path: Location of the fleet registry.
- optimal_workers: Number of threads for parallel execution.
"""

from sys import argv as sysArgv, executable as sysExecutable, stdout as sysStdout, exit as sysExit
from os import getenv as osGetenv, walk as osWalk
from os.path import exists as osPathExists, join as osPathJoin
from json import load as jsonLoad, dump as jsonDump
from subprocess import run as subprocessRun, TimeoutExpired as subprocessTimeoutExpired
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple

# ### FLEET CONFIGURATION (GLOBAL PARAMETERS) ###
GO_VERSION = "1.25"
PYTHON_VERSION = "3.12"
RUST_VERSION = "1.91"
CPP_VERSION = "20"  # C++ Standard

# Standardize terminal output encoding for Windows
if sysStdout.encoding != 'utf-8':
    try:
        sysStdout.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        pass

def _find_workspace_root() -> Path:
    """
    Walk up from this script's location until we find the workspace root.
    Works from fleet-operation-brain/00-Repo-Control/ (standalone)
    or obsidian-brain/05-Fleet-Operation/00-Repo-Control/ (submodule).
    """
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "Bastien-Antigravity.code-workspace").exists():
            return parent
        if (parent / "obsidian-brain").is_dir() and (parent / "universal-logger").is_dir():
            return parent
    return Path(__file__).resolve().parents[3]

# ### GIT HELPERS ###

def run_git(path: Path, args: List[str], timeout: int = 30) -> Tuple[str, str, int]:
    """
    Executes a Git command in a specific directory.
    Ensures non-interactive execution and injects GITHUB_TOKEN if available.
    """
    import os
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    
    token = get_github_token()
    git_base = ["git", "-C", str(path)]
    
    # If a token is found and we are doing a remote operation, inject it via credential helper
    if token and any(cmd in args for cmd in ["push", "pull", "fetch", "clone"]):
        # Use -c to set a temporary credential helper for this command only
        # This avoids the "Device not configured" error by providing the token
        git_base += [
            "-c", "credential.helper=", 
            "-c", f"credential.helper=!f() {{ echo \"username=x-access-token\"; echo \"password={token}\"; }}; f"
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

def get_status(repo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks the status of a single repository (branch, cleanliness, ahead/behind).
    """
    path = repo["path"]
    name = repo["name"]
    
    if not osPathExists(path):
        return {"name": name, "status": "MISSING", "branch": "N/A", "clean": False, "ahead": 0, "behind": 0}
    
    branch_out, _, _ = run_git(Path(path), ["rev-parse", "--abbrev-ref", "HEAD"])
    status_out, _, _ = run_git(Path(path), ["status", "--porcelain"])
    
    # Check ahead/behind
    ahead, behind = 0, 0
    remote_branch = repo.get("master_branch", "develop")
    
    # Fetch to be sure we have latest remote info
    run_git(Path(path), ["fetch", "origin"]) 
    
    ab_out, _, code = run_git(Path(path), ["rev-list", "--left-right", "--count", "origin/{0}...HEAD".format(remote_branch)])
    if code == 0:
        # Format: "behind\tahead"
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

def sync_repo(repo: Dict[str, Any]) -> List[str]:
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
    
    # 0. Check Cleanliness
    status_out, _, _ = run_git(Path(path), ["status", "--porcelain"])
    if len(status_out) > 0:
        logs.append("[ {0} ] SKIP: Uncommitted changes found. Please commit first.".format(name))
        return logs
        
    # Check branch safety
    current_branch, _, _ = run_git(Path(path), ["rev-parse", "--abbrev-ref", "HEAD"])
    if current_branch != target_branch:
        logs.append("[ {0} ] SKIP: Currently on '{1}', but target is '{2}'. Skipping sync.".format(name, current_branch, target_branch))
        return logs
    
    # 1. Pull
    logs.append("[ {0} ] Pulling {1}...".format(name, target_branch))
    _, err, code = run_git(Path(path), ["pull", "origin", target_branch])
    if code != 0:
        logs.append("[ {0} ] PULL FAILED: {1}".format(name, err))
        return logs
    
    # 2. Submodules
    if osPathExists(osPathJoin(path, ".gitmodules")):
        logs.append("[ {0} ] Updating submodules...".format(name))
        _, err, code = run_git(Path(path), ["submodule", "update", "--init", "--recursive"])
        if code != 0:
            logs.append("[ {0} ] SUBMODULE ERROR: {1}".format(name, err))

    # 3. Push (Only if ahead)
    ab_out, _, code = run_git(Path(path), ["rev-list", "--left-right", "--count", f"origin/{target_branch}...HEAD"])
    ahead = 0
    if code == 0:
        parts = ab_out.split()
        if len(parts) == 2:
            ahead = int(parts[1])

    if ahead > 0:
        logs.append("[ {0} ] Pushing {1} ({2} commit(s) ahead)...".format(name, target_branch, ahead))
        _, err, code = run_git(Path(path), ["push", "origin", target_branch])
        if code != 0:
            logs.append("[ {0} ] PUSH FAILED: {1}".format(name, err))
            return logs
        logs.append("[ {0} ] SYNCED & PUSHED ({1})".format(name, target_branch))
    else:
        logs.append("[ {0} ] UP-TO-DATE ({1})".format(name, target_branch))
        
    return logs

# ### GITHUB API HELPERS ###

def get_github_token() -> Optional[str]:
    """
    Retrieves the GitHub token from environment variables or a local hidden file.
    """
    token = osGetenv("GITHUB_TOKEN")
    if token:
        return token
        
    token_path = Path.home() / ".github_token"
    if token_path.exists():
        with open(token_path, "r", encoding='utf-8') as f:
            return f.read().strip()
            
    return None

def _ensure_auth() -> str:
    """
    Verifies that a GitHub token is available. 
    If not, fails 'loudly' with clear instructions.
    """
    token = get_github_token()
    if not token:
        print("\n" + "!"*60)
        print("🚨 FLEET COMMANDER: AUTHENTICATION REQUIRED")
        print("!"*60)
        print("You are attempting a remote operation that requires GitHub credentials.")
        print("To proceed, please provide a Personal Access Token (PAT).")
        print("\nOption A (Environment Variable):")
        print("   export GITHUB_TOKEN=your_token_here")
        print("\nOption B (Hidden File):")
        print("   echo 'your_token_here' > ~/.github_token")
        print("\nNote: Ensure the token has 'repo' and 'workflow' permissions.")
        print("!"*60 + "\n")
        sysExit(1)
    return token

# -----------------------------------------------------------------------------------------------

def audit_repo(repo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Audits the repository for CI/CD standards and GitHub Action status.
    """
    # Late imports for heavy/specialized libraries
    import urllib.request as urllibRequest
    import urllib.error as urllibError
    import ssl
    import re
    
    path = repo["path"]
    name = repo["name"]
    
    if not osPathExists(path):
        return {"name": name, "ci": "N/A", "dep": "N/A", "ai": "N/A", "run": "UNKNOWN"}
    
    ci_exists = osPathExists(osPathJoin(path, ".github/workflows/ci.yml"))
    dep_exists = osPathExists(osPathJoin(path, ".github/dependabot.yml"))
    ai_exists = osPathExists(osPathJoin(path, "AI-Init.md"))
    
    run_status = "UNKNOWN"
    token = get_github_token()
    remote_url = repo.get("remote", "")
    match = re.search(r"github\.com[:/](.+)/(.+)\.git", remote_url)
    
    if match:
        owner, repo_name = match.group(1), match.group(2)
        url = "https://api.github.com/repos/{0}/{1}/actions/runs?per_page=1".format(owner, repo_name)
        try:
            context = ssl._create_unverified_context()
            req = urllibRequest.Request(url)
            if token: 
                req.add_header("Authorization", "token {0}".format(token))
            req.add_header("User-Agent", "Fleet-Manager")
            with urllibRequest.urlopen(req, timeout=10, context=context) as response:
                data = jsonLoad(response)
                if data.get("workflow_runs"):
                    last = data["workflow_runs"][0]
                    run_status = last["conclusion"].upper() if last["status"] == "completed" else last["status"].upper()
                else:
                    run_status = "NONE"
        except urllibError.HTTPError as e:
            if e.code == 403:
                run_status = "ERR 403 (Rate Limit)"
            elif e.code == 401:
                run_status = "ERR 401 (Auth)"
            else:
                run_status = "ERR {0}".format(e.code)
        except Exception:
            run_status = "ERR NETWORK"
    
    # Map conclusion/status to visual icons
    status_icon = "🔘" # Default for NONE/UNKNOWN
    if run_status == "SUCCESS":
        status_icon = "✅"
    elif run_status in ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"]:
        status_icon = "❌"
    elif run_status in ["IN_PROGRESS", "QUEUED", "WAITING"]:
        status_icon = "⏳"
    elif "ERR" in run_status or run_status == "UNKNOWN":
        status_icon = "⚠️"
    
    # Return formatted status with icon
    display_status = f"{status_icon} {run_status}"
    
    return {"name": name, "ci": "✅" if ci_exists else "❌", "dep": "✅" if dep_exists else "❌", "ai": "✅" if ai_exists else "❌", "run": display_status}

# ### FLEET UTILITIES ###

def _load_job_fragment(name: str, working_dir: str, templates_dir: Path) -> str:
    """Loads a YAML fragment from the templates directory and injects the working directory."""
    frag_path = templates_dir / "Polyglot" / "jobs" / f"{name}.yml"

    if frag_path.exists():
        with open(frag_path, "r", encoding='utf-8') as f:
            content = f.read()
        content = content.replace("{{WORKING_DIR}}", working_dir)
        content = content.replace("{{GO_VERSION}}", GO_VERSION)
        content = content.replace("{{PYTHON_VERSION}}", PYTHON_VERSION)
        content = content.replace("{{RUST_VERSION}}", RUST_VERSION)
        content = content.replace("{{CPP_VERSION}}", CPP_VERSION)
        return content
    return ""


def _detect_language_path(repo_path: Path, lang: str) -> Optional[str]:
    """Checks for language folder in root or distconf/ and returns the relative path."""
    # 1. Check Root Directory
    if (repo_path / lang).is_dir():
        return lang
    # 2. Check distconf/
    if (repo_path / "distconf" / lang).is_dir():
        return f"distconf/{lang}"
    # 3. Special Case: Python in root (detected by requirements.txt or setup.py)
    if lang == "python":
        if (repo_path / "requirements.txt").exists() or (repo_path / "setup.py").exists():
            return "."
    # 4. Special Case: Go (detect go.mod in root or subfolder)
    if lang == "go":
        if (repo_path / "go.mod").exists():
            return "."
        if (repo_path / "go" / "go.mod").exists():
            return "go"
            
    return None


def template_repo(repo: Dict[str, Any], templates_dir: Path) -> str:
    """
    Applies standard CI/CD templates to a repository with Archetype auto-detection.
    """
    path = Path(repo["path"])
    name = repo["name"]
    
    if not path.exists():
        return "[ {0} ] MISSING".format(name)
        
    # Exclusion Rule: Do not template knowledge-base repositories
    excluded_repos = ["obsidian-brain", "01-Strategic-Nexus", "02-Business-BDD", "03-Tech-Stack", "04-Rapid-Prototyping", "05-Fleet-Operation", "07-Core-KMS"]
    if name in excluded_repos:
        return "[ {0} ] SKIP (Knowledge-Base)".format(name)
        
    github_dir = path / ".github"
    workflows_dir = github_dir / "workflows"
    
    github_dir.mkdir(exist_ok=True)
    workflows_dir.mkdir(exist_ok=True)
    
    # Archetype Detection
    go_path = _detect_language_path(path, "go")
    python_path = _detect_language_path(path, "python")
    rust_path = _detect_language_path(path, "rust")
    cpp_path = _detect_language_path(path, "cpp")
    
    is_polyglot = any([python_path, rust_path, cpp_path])
    archetype = "Polyglot" if is_polyglot else "Microservice"
    archetype_dir = templates_dir / archetype
    
    # 1. CI Template
    ci_src = archetype_dir / "ci.yml"
    ci_dst = workflows_dir / "ci.yml"
    if ci_src.exists():
        with open(ci_src, "r", encoding='utf-8') as src:
            ci_content = src.read()
        
        # Injected Archetype Label with detected languages
        if is_polyglot:
            langs = []
            if go_path: langs.append("Go")
            if python_path: langs.append("Python")
            if rust_path: langs.append("Rust")
            if cpp_path: langs.append("C++")
            label = "Polyglot: " + "+".join(langs)
        else:
            label = "Microservice"

        # Update Header and Name
        header_params = f"Go:{GO_VERSION}, Py:{PYTHON_VERSION}, Rust:{RUST_VERSION}, C++:{CPP_VERSION}"
        ci_content = ci_content.replace("# [FLEET-ARCHITECT] Standardized Polyglot CI", f"# [FLEET-ARCHITECT] {label} ({header_params})")
        ci_content = ci_content.replace("# [FLEET-ARCHITECT] Standardized Microservice CI", f"# [FLEET-ARCHITECT] {label} ({header_params})")
        
        # Inject Versions into base if needed
        ci_content = ci_content.replace("{{GO_VERSION}}", GO_VERSION)
        ci_content = ci_content.replace("{{PYTHON_VERSION}}", PYTHON_VERSION)
        ci_content = ci_content.replace("{{RUST_VERSION}}", RUST_VERSION)
        ci_content = ci_content.replace("{{CPP_VERSION}}", CPP_VERSION)
        
        # For Microservices, inject the detected Go path into the base template
        if not is_polyglot and go_path:
            ci_content = ci_content.replace("{{WORKING_DIR}}", go_path)
        elif not is_polyglot:
            ci_content = ci_content.replace("{{WORKING_DIR}}", ".")

        # For Polyglot repos, dynamically append language-specific jobs from fragment templates
        if is_polyglot:
            if go_path:
                ci_content += _load_job_fragment("go", go_path, templates_dir)
            if python_path:
                ci_content += _load_job_fragment("python", python_path, templates_dir)
            if rust_path:
                ci_content += _load_job_fragment("rust", rust_path, templates_dir)
            if cpp_path:
                ci_content += _load_job_fragment("cpp", cpp_path, templates_dir)
        
        with open(ci_dst, "w", encoding='utf-8') as dst:
            dst.write(ci_content)

    # 1.5 Release Template (Polyglot only)
    if is_polyglot:
        rel_src = archetype_dir / "release.yml"
        rel_dst = workflows_dir / "release.yml"
        if rel_src.exists():
            with open(rel_src, "r", encoding='utf-8') as src, open(rel_dst, "w", encoding='utf-8') as dst:
                dst.write(src.read())
            
    # 2. Dependabot Template
    dep_src = archetype_dir / "dependabot.yml"
    dep_dst = github_dir / "dependabot.yml"
    if dep_src.exists():
        with open(dep_src, "r", encoding='utf-8') as src, open(dep_dst, "w", encoding='utf-8') as dst:
            dst.write(src.read())

    # 3. CODEOWNERS Template
    co_src = templates_dir / "CODEOWNERS"
    co_dst = github_dir / "CODEOWNERS"
    if co_src.exists():
        with open(co_src, "r", encoding='utf-8') as src, open(co_dst, "w", encoding='utf-8') as dst:
            dst.write(src.read())
            
    # 4. Global golangci-lint Template
    lint_src = templates_dir / "golangci-global.yml"
    lint_dst = path / ".golangci.yml"
    if lint_src.exists():
        with open(lint_src, "r", encoding='utf-8') as src, open(lint_dst, "w", encoding='utf-8') as dst:
            dst.write(src.read())
    
    # Build the archetype label with detected languages
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

def discover_repos(root_dir: Path) -> List[Dict[str, Any]]:
    """
    Scans for all directories containing .git and updates inventory.
    """
    print("Discovering repositories in {0}...".format(root_dir))
    found = []
    root_path = root_dir.resolve()
    
    for root, dirs, files in osWalk(root_dir):
        # Detect .git directory OR .git file (submodules)
        if ".git" in dirs or ".git" in files:
            path = Path(root).resolve()
            
            # Skip the root directory itself
            if path == root_path:
                if ".git" in dirs: 
                    dirs.remove(".git")
                continue
                
            # Get remote URL
            remote_out, _, _ = run_git(path, ["remote", "get-url", "origin"])
            # Get current branch
            branch_out, _, _ = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
            
            found.append({
                "name": path.name,
                "path": str(path.absolute()),
                "remote": remote_out,
                "master_branch": branch_out if branch_out else "develop"
            })
            
            # Don't recurse into .git
            if ".git" in dirs:
                dirs.remove(".git")
                
    # Sort by name for consistency
    found.sort(key=lambda x: x["name"])
    return found

# ### CORE COMMANDS ###

def _resolve_inventory_paths(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolves relative paths in inventory.json to absolute paths based on
    the workspace root. This makes the inventory portable across platforms.
    """
    workspace_root = _find_workspace_root()
    
    for repo in inventory.get("repositories", []):
        repo_path = repo.get("path", "")
        # If the path is relative (starts with ./ or is not absolute), resolve it
        if repo_path.startswith("./") or repo_path.startswith("../") or not Path(repo_path).is_absolute():
            repo["path"] = str((workspace_root / repo_path).resolve())
    
    return inventory

# -----------------------------------------------------------------------------------------------

def main() -> None:
    """
    Main entry point for the Fleet Manager CLI.
    """
    inventory_path = Path(__file__).resolve().parent / "inventory.json"
    if not inventory_path.exists():
        print("FleetManager: inventory.json not found.")
        return

    with open(inventory_path, "r", encoding='utf-8') as f:
        inventory = jsonLoad(f)
    
    # Resolve relative paths to absolute for this machine
    inventory = _resolve_inventory_paths(inventory)
        
    num_repos = len(inventory.get("repositories", []))
    optimal_workers = max(5, min(32, num_repos))
    
    command = sysArgv[1] if len(sysArgv) > 1 else "status"

    # Commands that require authentication
    if command in ["sync", "vault-sync", "restore", "tag", "audit", "status"]:
        _ensure_auth()

    if command == "discover":
        # Discover in the workspace root
        workspace_root = _find_workspace_root()
        discovered = discover_repos(workspace_root)
        # Store as relative paths for portability
        for repo in discovered:
            try:
                rel = Path(repo["path"]).relative_to(workspace_root)
                repo["path"] = "./{0}".format(rel.as_posix())
            except ValueError:
                pass  # Keep absolute if outside workspace
        inventory["repositories"] = discovered
        with open(inventory_path, "w", encoding='utf-8') as f:
            jsonDump(inventory, f, indent=2)
        print("Discovered and registered {0} repositories.".format(len(discovered)))

    elif command == "status":
        print("{0:<25} | {1:<15} | {2:<8} | {3:<5} | {4:<5} | {5:<5}".format('Repository', 'Branch', 'Status', 'Clean', 'Ahead', 'Behind'))
        print("-" * 80)
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            results = list(executor.map(get_status, inventory["repositories"]))
        for r in results:
            clean = "✅" if r["clean"] else "❌"
            print("{0:<25} | {1:<15} | {2:<8} | {3:<5} | {4:<5} | {5:<5}".format(r['name'], r['branch'], r['status'], clean, r['ahead'], r['behind']))

    elif command == "sync":
        print("Starting Global Fleet Sync...")
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            results = list(executor.map(sync_repo, inventory["repositories"]))
        for repo_logs in results: 
            for log in repo_logs:
                print(log)

    elif command == "audit":
        print("{0:<25} | {1:<4} | {2:<4} | {3:<4} | {4:<20}".format('Repository', 'CI', 'Dep', 'AI', 'CI Status'))
        print("-" * 75)
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            results = list(executor.map(audit_repo, inventory["repositories"]))
        for r in results:
            print("{0:<25} | {1:<4} | {2:<4} | {3:<4} | {4:<20}".format(r['name'], r['ci'], r['dep'], r['ai'], r['run']))

    elif command == "commit":
        msg = sysArgv[2] if len(sysArgv) > 2 else "chore(fleet): mass sync"
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            def _do_commit(repo: Dict[str, Any]) -> str:
                path = repo["path"]
                if not osPathExists(path): 
                    return "[ {0} ] MISSING".format(repo['name'])
                status, _, _ = run_git(Path(path), ["status", "--porcelain"])
                if not status: 
                    return "[ {0} ] CLEAN".format(repo['name'])
                run_git(Path(path), ["add", "."])
                _, err, code = run_git(Path(path), ["commit", "-m", msg])
                return "[ {0} ] COMMITTED".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
            results = list(executor.map(_do_commit, inventory["repositories"]))
        for r in results: 
            print(r)
        
    elif command == "tag":
        tag_name = sysArgv[2] if len(sysArgv) > 2 else None
        if not tag_name:
            print("Usage: fleet-manager.py tag <tag_name>")
            return
        print("Applying tag {0} across the fleet...".format(tag_name))
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            def _do_tag(repo: Dict[str, Any]) -> str:
                path = repo["path"]
                if not osPathExists(path): 
                    return "[ {0} ] MISSING".format(repo['name'])
                run_git(Path(path), ["tag", tag_name])
                _, err, code = run_git(Path(path), ["push", "origin", tag_name])
                return "[ {0} ] TAGGED & PUSHED".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
            results = list(executor.map(_do_tag, inventory["repositories"]))
        for r in results: 
            print(r)

    elif command == "branch":
        branch_name = sysArgv[2] if len(sysArgv) > 2 else None
        if not branch_name:
            print("Usage: fleet-manager.py branch <branch_name>")
            return
        print("Checking out branch {0} across the fleet...".format(branch_name))
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            def _do_branch(repo: Dict[str, Any]) -> str:
                path = repo["path"]
                if not osPathExists(path): 
                    return "[ {0} ] MISSING".format(repo['name'])
                _, _, code = run_git(Path(path), ["rev-parse", "--verify", branch_name])
                if code == 0:
                    run_git(Path(path), ["checkout", branch_name])
                    return "[ {0} ] CHECKED OUT EXISTING".format(repo['name'])
                else:
                    _, err, code = run_git(Path(path), ["checkout", "-b", branch_name])
                    return "[ {0} ] CREATED & CHECKED OUT".format(repo['name']) if code == 0 else "[ {0} ] FAILED: {1}".format(repo['name'], err)
            results = list(executor.map(_do_branch, inventory["repositories"]))
        for r in results: 
            print(r)

    elif command == "template":
        templates_dir = Path(__file__).resolve().parent.parent / "04-Templates"
        print("Applying fleet templates from {0}...".format(templates_dir))
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            def _do_template(repo: Dict[str, Any]) -> str:
                return template_repo(repo, templates_dir)
            results = list(executor.map(_do_template, inventory["repositories"]))
        for r in results: 
            print(r)

    elif command == "restore":
        print("Restoring missing repositories in the fleet...")
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            def _do_restore(repo: Dict[str, Any]) -> str:
                path = Path(repo["path"])
                name = repo["name"]
                if path.exists():
                    return "[ {0} ] EXISTS".format(name)
                
                remote = repo.get("remote")
                if not remote:
                    return "[ {0} ] ERROR: No remote URL".format(name)
                
                print("  [CLONE] Restoring {0}...".format(name))
                res = subprocessRun(["git", "clone", remote, str(path)], capture_output=True, text=True)
                return "[ {0} ] RESTORED".format(name) if res.returncode == 0 else "[ {0} ] FAILED: {1}".format(name, res.stderr.strip())
            
            results = list(executor.map(_do_restore, inventory["repositories"]))
        for r in results: 
            print(r)

    elif command == "vault-sync":
        msg = sysArgv[2] if len(sysArgv) > 2 else "chore(vault): atomic sync via Fleet Manager"
        workspace_root = _find_workspace_root()
        obsidian_dir = workspace_root / "obsidian-brain"
        
        if not obsidian_dir.exists():
            print("FleetManager: obsidian-brain not found.")
            return

        print("🚀 Starting Atomic Vault Sync...")
        
        # 1. Sync all submodules
        submodules = [d for d in obsidian_dir.iterdir() if d.is_dir() and (d / ".git").exists()]
        for sub in submodules:
            name = sub.name
            status, _, _ = run_git(sub, ["status", "--porcelain"])
            if status:
                print(f"[ {name} ] Committing changes...")
                run_git(sub, ["add", "."])
                run_git(sub, ["commit", "-m", msg])
            
            print(f"[ {name} ] Pulling latest...")
            run_git(sub, ["pull", "--rebase", "origin", "develop"])
            
            # 2. Push (Only if ahead)
            ab_out, _, code = run_git(sub, ["rev-list", "--left-right", "--count", "origin/develop...HEAD"])
            ahead = 0
            if code == 0:
                parts = ab_out.split()
                if len(parts) == 2:
                    ahead = int(parts[1])

            if ahead > 0:
                print(f"[ {name} ] Pushing {ahead} commit(s) to origin...")
                _, err, code = run_git(sub, ["push", "origin", "develop"])
                if code != 0:
                    print(f"[ {name} ] PUSH FAILED: {err}")
                else:
                    print(f"[ {name} ] SYNCED.")
            else:
                print(f"[ {name} ] UP-TO-DATE.")

        # 2. Update parent pointer
        print("[ obsidian-brain ] Updating submodule pointers...")
        run_git(obsidian_dir, ["add", "."])
        status, _, _ = run_git(obsidian_dir, ["status", "--porcelain"])
        if status:
            run_git(obsidian_dir, ["commit", "-m", "chore(fleet): update submodule pointers"])
            print("[ obsidian-brain ] Pointers committed.")
        
        # 3. Final Vault Push (Only if ahead)
        ab_out, _, code = run_git(obsidian_dir, ["rev-list", "--left-right", "--count", "origin/develop...HEAD"])
        ahead = 0
        if code == 0:
            parts = ab_out.split()
            if len(parts) == 2:
                ahead = int(parts[1])

        if ahead > 0:
            print(f"[ obsidian-brain ] Pushing {ahead} commit(s) to origin...")
            _, err, code = run_git(obsidian_dir, ["push", "origin", "develop"])
            if code == 0:
                print("✨ Atomic Vault Sync Complete!")
            else:
                print(f"❌ Vault push failed: {err}")
        else:
            print("✨ Vault is already up-to-date.")

    elif command == "refresh":
        refresh_script = Path(__file__).resolve().parent / "fleet-refresh.py"
        args = sysArgv[2:]
        print("Executing Nuclear Refresh via {0}...".format(refresh_script.name))
        subprocessRun([sysExecutable, str(refresh_script)] + args)

    else:
        print("Unknown command: {0}".format(command))

# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

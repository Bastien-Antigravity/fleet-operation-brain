import os
import json
import subprocess
import sys
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# -----------------------------------------------------------------------------------------------

def run_git(path, args):
    try:
        result = subprocess.run(
            ["git", "-C", str(path)] + args,
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1

def get_status(repo):
    path = repo["path"]
    name = repo["name"]
    
    if not os.path.exists(path):
        return {"name": name, "status": "MISSING", "branch": "N/A", "clean": False, "ahead": 0, "behind": 0}
    
    branch_out, _, _ = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    status_out, _, _ = run_git(path, ["status", "--porcelain"])
    
    # Check ahead/behind
    ahead, behind = 0, 0
    remote_branch = repo.get("master_branch", "develop")
    
    # Fetch to be sure we have latest remote info (optional, but status might be stale)
    # run_git(path, ["fetch", "origin"]) 
    
    ab_out, _, code = run_git(path, ["rev-list", "--left-right", "--count", f"origin/{remote_branch}...HEAD"])
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

def sync_repo(repo):
    path = repo["path"]
    name = repo["name"]
    branch = repo.get("master_branch", "develop")
    
    if not os.path.exists(path):
        return f"[ {name} ] ERROR: Path not found"
    
    # 0. Check Cleanliness
    status_out, _, _ = run_git(path, ["status", "--porcelain"])
    if len(status_out) > 0:
        return f"[ {name} ] SKIP: Uncommitted changes found. Please commit first."
    
    # 1. Pull
    print(f"[ {name} ] Pulling {branch}...")
    _, err, code = run_git(path, ["pull", "origin", branch])
    if code != 0:
        return f"[ {name} ] PULL FAILED: {err}"
    
    # 2. Submodules
    if os.path.exists(os.path.join(path, ".gitmodules")):
        print(f"[ {name} ] Updating submodules...")
        _, err, code = run_git(path, ["submodule", "update", "--init", "--recursive"])
        if code != 0:
            print(f"[ {name} ] SUBMODULE ERROR: {err}")

    # 3. Push
    print(f"[ {name} ] Pushing {branch}...")
    _, err, code = run_git(path, ["push", "origin", branch])
    if code != 0:
        return f"[ {name} ] PUSH FAILED: {err}"
    
    return f"[ {name} ] SYNCED ({branch})"

def audit_repo(repo):
    path = repo["path"]
    name = repo["name"]
    
    if not os.path.exists(path):
        return {"name": name, "ci": "N/A", "dep": "N/A", "ai": "N/A", "run": "UNKNOWN"}
    
    ci_exists = os.path.exists(os.path.join(path, ".github/workflows/ci.yml"))
    dep_exists = os.path.exists(os.path.join(path, ".github/dependabot.yml"))
    ai_exists = os.path.exists(os.path.join(path, "AI-Init.md"))
    
    # GitHub CI Status
    import urllib.request
    import json as py_json
    import ssl
    
    run_status = "UNKNOWN"
    token = os.getenv("GITHUB_TOKEN")
    remote_url = repo.get("remote", "")
    match = re.search(r"github\.com[:/](.+)/(.+)\.git", remote_url)
    
    if match:
        owner, repo_name = match.group(1), match.group(2)
        url = f"https://api.github.com/repos/{owner}/{repo_name}/actions/runs?per_page=1"
        try:
            context = ssl._create_unverified_context()
            req = urllib.request.Request(url)
            if token: req.add_header("Authorization", f"token {token}")
            req.add_header("User-Agent", "Fleet-Manager")
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                data = py_json.loads(response.read().decode())
                if data.get("workflow_runs"):
                    last = data["workflow_runs"][0]
                    run_status = last["conclusion"].upper() if last["status"] == "completed" else last["status"].upper()
                else:
                    run_status = "NONE"
        except Exception as e:
            code = getattr(e, 'code', '???')
            run_status = f"ERR {code}"
    
    return {"name": name, "ci": "✅" if ci_exists else "❌", "dep": "✅" if dep_exists else "❌", "ai": "✅" if ai_exists else "❌", "run": run_status}

def discover_repos(root_dir):
    """Scans for all directories containing .git (dir or file) and updates inventory."""
    print(f"Discovering repositories in {root_dir}...")
    found = []
    root_path = Path(root_dir).resolve()
    
    for root, dirs, files in os.walk(root_dir):
        # Detect .git directory OR .git file (submodules)
        if ".git" in dirs or ".git" in files:
            path = Path(root).resolve()
            
            # Skip the root directory itself to avoid registering the workspace root as a repo
            if path == root_path:
                if ".git" in dirs: dirs.remove(".git")
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
            
            # If it's a directory, don't recurse into .git
            if ".git" in dirs:
                dirs.remove(".git")
                
    # Sort by name for consistency
    found.sort(key=lambda x: x["name"])
    return found

def main():
    inventory_path = Path(__file__).parent / "inventory.json"
    with open(inventory_path, "r") as f:
        inventory = json.load(f)
    
    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "discover":
        # Discover in the parent of the parent of the script (Workspace Root)
        workspace_root = Path(__file__).resolve().parents[3]
        discovered = discover_repos(workspace_root)
        inventory["repositories"] = discovered
        with open(inventory_path, "w") as f:
            json.dump(inventory, f, indent=2)
        print(f"Discovered and registered {len(discovered)} repositories.")

    elif command == "status":
        print(f"{'Repository':<25} | {'Branch':<15} | {'Status':<8} | {'Clean':<5} | {'Ahead':<5} | {'Behind':<5}")
        print("-" * 80)
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_status, inventory["repositories"]))
        for r in results:
            clean = "✅" if r["clean"] else "❌"
            print(f"{r['name']:<25} | {r['branch']:<15} | {r['status']:<8} | {clean:<5} | {r['ahead']:<5} | {r['behind']:<5}")

    elif command == "sync":
        print("Starting Global Fleet Sync...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(sync_repo, inventory["repositories"]))
        for r in results: print(r)

    elif command == "audit":
        print(f"{'Repository':<25} | {'CI':<4} | {'Dep':<4} | {'AI':<4} | {'CI Status':<10}")
        print("-" * 65)
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(audit_repo, inventory["repositories"]))
        for r in results:
            print(f"{r['name']:<25} | {r['ci']:<4} | {r['dep']:<4} | {r['ai']:<4} | {r['run']:<10}")

    elif command == "commit":
        msg = sys.argv[2] if len(sys.argv) > 2 else "chore(fleet): mass sync"
        from concurrent.futures import as_completed
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Reusing existing commit logic conceptually but simpler
            def do_commit(repo):
                path = repo["path"]
                if not os.path.exists(path): return f"[ {repo['name']} ] MISSING"
                status, _, _ = run_git(path, ["status", "--porcelain"])
                if not status: return f"[ {repo['name']} ] CLEAN"
                run_git(path, ["add", "."])
                _, err, code = run_git(path, ["commit", "-m", msg])
                return f"[ {repo['name']} ] COMMITTED" if code == 0 else f"[ {repo['name']} ] FAILED: {err}"
            results = list(executor.map(do_commit, inventory["repositories"]))
        for r in results: print(r)
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()

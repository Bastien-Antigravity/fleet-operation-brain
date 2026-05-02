import os
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

def run_git(path, args):
    try:
        result = subprocess.run(
            ["git", "-C", path] + args,
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
        return {"name": name, "status": "MISSING", "branch": "N/A", "clean": False}
    
    branch_out, _, _ = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    status_out, _, _ = run_git(path, ["status", "--porcelain"])
    
    return {
        "name": name,
        "status": "OK",
        "branch": branch_out,
        "clean": len(status_out) == 0
    }

def sync_repo(repo):
    path = repo["path"]
    name = repo["name"]
    branch = repo.get("master_branch", "develop")
    
    if not os.path.exists(path):
        return f"[ {name} ] ERROR: Path not found"
    
    # 1. Pull
    _, err, code = run_git(path, ["pull", "origin", branch])
    if code != 0:
        return f"[ {name} ] PULL FAILED: {err}"
    
    # 2. Push
    _, err, code = run_git(path, ["push", "origin", branch])
    if code != 0:
        return f"[ {name} ] PUSH FAILED: {err}"
    
    return f"[ {name} ] SYNCED ({branch})"

def main():
    inventory_path = os.path.join(os.path.dirname(__file__), "inventory.json")
    with open(inventory_path, "r") as f:
        inventory = json.load(f)
    
    repos = inventory["repositories"]
    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "status":
        print(f"{'Repository':<25} | {'Branch':<15} | {'Status':<10} | {'Clean':<5}")
        print("-" * 65)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(get_status, repos))
            
        for r in results:
            clean_str = "✅" if r["clean"] else "❌"
            print(f"{r['name']:<25} | {r['branch']:<15} | {r['status']:<10} | {clean_str}")

    elif command == "sync":
        print("Starting Global Fleet Sync...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(sync_repo, repos))
        for r in results:
            print(r)
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()

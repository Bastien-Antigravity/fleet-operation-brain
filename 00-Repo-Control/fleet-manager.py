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
    
    # 0. Check Cleanliness
    status_out, _, _ = run_git(path, ["status", "--porcelain"])
    if len(status_out) > 0:
        return f"[ {name} ] SKIP: Uncommitted changes found. Please commit first."
    
    # 1. Pull
    _, err, code = run_git(path, ["pull", "origin", branch])
    if code != 0:
        return f"[ {name} ] PULL FAILED: {err}"
    
    # 2. Push
    _, err, code = run_git(path, ["push", "origin", branch])
    if code != 0:
        return f"[ {name} ] PUSH FAILED: {err}"
    
    return f"[ {name} ] SYNCED ({branch})"

def update_gitignore(repo, template_lines):
    path = repo["path"]
    name = repo["name"]
    gitignore_path = os.path.join(path, ".gitignore")
    
    if not os.path.exists(path):
        return f"[ {name} ] ERROR: Path not found"
    
    current_lines = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            current_lines = [l.strip() for l in f.readlines()]
    
    # Merge and deduplicate
    # We keep current lines and append new ones if they don't exist
    new_lines = current_lines.copy()
    for line in template_lines:
        if line and not line.startswith("#") and line not in current_lines:
            new_lines.append(line)
        elif line.startswith("#"): # Keep headers
            new_lines.append(line)
            
    with open(gitignore_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")
        
    return f"[ {name} ] .gitignore STANDARDIZED"

def commit_repo(repo, message):
    path = repo["path"]
    name = repo["name"]
    
    if not os.path.exists(path):
        return f"[ {name} ] ERROR: Path not found"
    
    # Only commit if there are changes
    status_out, _, _ = run_git(path, ["status", "--porcelain"])
    if len(status_out) == 0:
        return f"[ {name} ] CLEAN: No changes to commit"
        
    run_git(path, ["add", "."])
    _, err, code = run_git(path, ["commit", "-m", message])
    
    if code != 0:
        return f"[ {name} ] COMMIT FAILED: {err}"
        
    return f"[ {name} ] COMMITTED: {message}"

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
    elif command == "gitignore":
        print("Standardizing .gitignore across fleet...")
        template_path = os.path.join(os.path.dirname(__file__), "..", "04-Templates", "gitignore-global")
        with open(template_path, "r") as f:
            template_lines = [l.strip() for l in f.readlines()]
            
        with ThreadPoolExecutor(max_workers=5) as executor:
            # We use a lambda to pass the template_lines
            results = list(executor.map(lambda r: update_gitignore(r, template_lines), repos))
        for r in results:
            print(r)
    elif command == "commit":
        message = sys.argv[2] if len(sys.argv) > 2 else "chore(fleet): mass sync"
        print(f"Executing Mass Commit: {message}")
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda r: commit_repo(r, message), repos))
        for r in results:
            print(r)
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()

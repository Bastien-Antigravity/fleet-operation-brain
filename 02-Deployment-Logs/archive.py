#!/usr/bin/env python
# coding:utf-8
"""
ESSENTIAL PROCESS:
Audits the Deployment Logs folder and archives historical deployment logs
into the 'deployments/' folder (with context firewall ignore rules),
retaining only the absolute latest deployment log file in the main folder.

DATA FLOW:
1. Scans the directory root for *.md log files.
2. Extracts dates from the filenames to determine the latest log.
3. Moves historical logs to the 'deployments/' subdirectory.
4. Generates ignore files (.aiignore, .mcpignore, .geminiignore) inside the deployments/ folder.
5. Updates the Deployment-Logs-MOC.md file.
"""

from re import compile as reCompile, match as reMatch
from shutil import move as shutilMove
from pathlib import Path

def run_archive() -> None:
    root = Path(__file__).resolve().parent
    archive_dir = root / "deployments"
    
    # 1. Ensure archive directory exists
    archive_dir.mkdir(exist_ok=True)
    
    # 2. Ensure ignore files exist inside deployments/
    ignore_files = [".aiignore", ".mcpignore", ".geminiignore"]
    for filename in ignore_files:
        ignore_file = archive_dir / filename
        if not ignore_file.exists():
            with open(ignore_file, "w", encoding="utf-8") as f:
                f.write("*\n")
            print(f"✨ Created context firewall ignore file: deployments/{filename}")

    # 3. Scan for markdown files to process (excluding MOC/Archive scripts if any)
    targets = [f for f in root.glob("*.md") if f.name != "README.md" and f.name != "Deployment-Logs-MOC.md"]
    
    if not targets:
        print("\n✨ DEPLOYMENT LOGS DIRECTORY IS ALREADY PERFECT!")
        return

    # 4. Parse dates from filenames to find the latest
    date_regex = reCompile(r"(\d{4}-\d{2}-\d{2})")
    log_info = []
    
    for filepath in targets:
        match = date_regex.search(filepath.name)
        date_str = match.group(1) if match else "1970-01-01"
        mtime = filepath.stat().st_mtime
        log_info.append({
            "path": filepath,
            "name": filepath.name,
            "date": date_str,
            "mtime": mtime
        })
        
    # Sort by date string first, then by modification time to find the absolute latest log
    log_info.sort(key=lambda x: (x["date"], x["mtime"]), reverse=True)
    
    latest_log = log_info[0]
    historical_logs = log_info[1:]
    
    print(f"\n🌟 ACTIVE DEPLOYMENT LOG RETAINED:")
    print(f"  [+] {latest_log['name']} (Date: {latest_log['date']})")
    
    if not historical_logs:
        print("\n✨ No historical log files need archiving.")
    else:
        print(f"\n📦 FOUND {len(historical_logs)} HISTORICAL LOG(S) TO ARCHIVE:")
        for log in historical_logs:
            filepath = log["path"]
            dest = archive_dir / filepath.name
            
            # Avoid name collisions in the archive
            if dest.exists():
                base = filepath.stem
                ext = filepath.suffix
                counter = 1
                while (archive_dir / f"{base}_{counter}{ext}").exists():
                    counter += 1
                dest = archive_dir / f"{base}_{counter}{ext}"
                
            shutilMove(str(filepath), str(dest))
            print(f"  [-] Archived: {filepath.name} -> deployments/{dest.name}")

    # 5. Update the parent Deployment-Logs-MOC.md links
    moc_path = root.parent / "Deployment-Logs-MOC.md"
    if moc_path.exists():
        try:
            with open(moc_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Replace auto-aggregates list with only the latest active log link
            # Search for the YAML frontmatter block
            frontmatter_match = reMatch(r"^---[\s\S]*?---\n*", content)
            frontmatter = frontmatter_match.group(0) if frontmatter_match else ""
            
            new_moc_content = (
                f"{frontmatter}"
                f"# Deployment Logs MOC\n\n"
                f"This index manages active deployment logs.\n\n"
                f"### Active Deployment Log\n"
                f"- [[{latest_log['path'].stem}]]\n\n"
                f"### Archived Historical Logs\n"
                f"> Archived logs are stored in the `deployments/` firewall zone to maintain minimal context weight.\n"
            )
            
            with open(moc_path, "w", encoding="utf-8") as f:
                f.write(new_moc_content)
            print("\n✨ Updated Deployment-Logs-MOC.md with the active layout!")
        except Exception as e:
            print(f"\n⚠️ Warning: Failed to update Deployment-Logs-MOC.md: {e}")

    print("\n✅ DEPLOYMENT LOGS HOUSEKEEPING COMPLETE!")

if __name__ == "__main__":
    run_archive()

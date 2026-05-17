#!/usr/bin/env python
# coding:utf-8
"""
ESSENTIAL PROCESS:
Audits the Fleet Action Plans folder and archives completed or historical plans
into the 'plans/' folder (with context firewall ignore rules),
ensuring the folder remains pristine.

DATA FLOW:
1. Scans the directory root for *.md plan files.
2. Reads frontmatter to identify 'completed' or historical plans.
3. Moves these plans to the 'plans/' subdirectory.
4. Generates ignore files (.aiignore, .mcpignore, .geminiignore) inside the plans/ folder.
5. Updates the Fleet-Action-Plans-MOC.md file.
"""

from re import match as reMatch, search as reSearch
from shutil import move as shutilMove
from pathlib import Path

def run_archive() -> None:
    root = Path(__file__).resolve().parent
    archive_dir = root / "plans"
    
    # 1. Ensure archive directory exists
    archive_dir.mkdir(exist_ok=True)
    
    # 2. Ensure ignore files exist inside plans/
    ignore_files = [".aiignore", ".mcpignore", ".geminiignore"]
    for filename in ignore_files:
        ignore_file = archive_dir / filename
        if not ignore_file.exists():
            with open(ignore_file, "w", encoding="utf-8") as f:
                f.write("*\n")
            print(f"✨ Created context firewall ignore file: plans/{filename}")

    # 3. Scan for markdown files to process (excluding README.md, MOC, or script files)
    targets = [f for f in root.glob("*.md") if f.name != "README.md" and f.name != "Fleet-Action-Plans-MOC.md"]
    
    if not targets:
        print("\n✨ FLEET ACTION PLANS DIRECTORY IS ALREADY PERFECT!")
        return

    # 4. Check for active migrations in the main README
    readme_path = root.parent / "README.md"
    no_active_migrations = True
    if readme_path.exists():
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_text = f.read()
                if "Ongoing Migrations: None" not in readme_text:
                    no_active_migrations = False
        except Exception:
            pass

    to_archive = []
    retained = []

    for filepath in targets:
        # Check YAML frontmatter for status
        is_completed = False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # Parse frontmatter status
                status_match = reSearch(r"status:\s*(\w+)", content)
                if status_match and status_match.group(1).lower() == "completed":
                    is_completed = True
        except Exception:
            pass
            
        # Archive if status is completed OR if the global state indicates no active migrations
        if is_completed or no_active_migrations:
            to_archive.append(filepath)
        else:
            retained.append(filepath)

    if retained:
        print(f"\n🌟 ACTIVE FLEET ACTION PLAN(S) RETAINED:")
        for r in retained:
            print(f"  [+] {r.name}")
            
    if not to_archive:
        print("\n✨ No historical action plans need archiving.")
    else:
        print(f"\n📦 FOUND {len(to_archive)} HISTORICAL ACTION PLAN(S) TO ARCHIVE:")
        for filepath in to_archive:
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
            print(f"  [-] Archived: {filepath.name} -> plans/{dest.name}")

    # 5. Update the parent Fleet-Action-Plans-MOC.md links
    moc_path = root.parent / "Fleet-Action-Plans-MOC.md"
    if moc_path.exists():
        try:
            with open(moc_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            frontmatter_match = reMatch(r"^---[\s\S]*?---\n*", content)
            frontmatter = frontmatter_match.group(0) if frontmatter_match else ""
            
            # Build active links list
            active_links_str = ""
            for r in retained:
                active_links_str += f"- [[{r.stem}]]\n"
            if not active_links_str:
                active_links_str = "*None currently active.*\n"
                
            new_moc_content = (
                f"{frontmatter}"
                f"# Fleet Action Plans MOC\n\n"
                f"This index manages active and historical fleet migrations.\n\n"
                f"### Active Migration Plans\n"
                f"{active_links_str}\n"
                f"### Archived Historical Plans\n"
                f"> Archived plans are stored in the `plans/` firewall zone to maintain minimal context weight.\n"
            )
            
            with open(moc_path, "w", encoding="utf-8") as f:
                f.write(new_moc_content)
            print("\n✨ Updated Fleet-Action-Plans-MOC.md with the active layout!")
        except Exception as e:
            print(f"\n⚠️ Warning: Failed to update Fleet-Action-Plans-MOC.md: {e}")

    print("\n✅ FLEET ACTION PLANS HOUSEKEEPING COMPLETE!")

if __name__ == "__main__":
    run_archive()

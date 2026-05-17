---
microservice: fleet-operation-brain
type: architecture
status: active
tags:
- '#ai/ignore'
- '#service/fleet-operation-brain'
- '#type/architecture'
- '#state/active'
- '#zone/3-fleet'
---

# ⚙️ Fleet Operation: Features & Behavior

The fleet command center orchestrates multi-repository operations, enforces metadata integrity, and minimizes context overhead dynamically.

---

## 🛠️ Key Workflows & Features

### 1. Dynamic Registry Discovery
- **Action**: Runs `python3 fleet-manager.py discover` to scan the workspace directories.
- **Behavior**: Auto-detects directories containing `.git` folders or submodule files, retrieves remote URLs and active branches, and dynamically updates [inventory.json](file:///Users/imac/Desktop/Bastien-Antigravity/obsidian-brain/05-Fleet-Operation/00-Repo-Control/inventory.json).

### 2. Multi-Repository Synchronization
- **Action**: Runs `python3 fleet-manager.py sync` or `commit "<msg>"`.
- **Behavior**: Standardizes Git states across the active fleet. It pulls updates, stages files, and runs bulk commits safely in parallel, refusing to touch dirty states.

### 3. Compliance Verification & Push Gate (`fleet-commander.py`)
- **Action**: Runs `python3 20-Scripts/fleet-commander.py [--repo <name> | --fleet] -m "<msg>"`.
- **Behavior**: 
  - Verifies presence of standard YAML frontmatter, `AI-*` files, and `quick-overview/` directories before pushing.
  - Automatically reads the inventory registry's `"exclude_from_compliance": true` flag to dynamically bypass strict code-compliance gates for knowledge-base repositories (like `obsidian-brain`, `03-Tech-Stack`, etc.) while still allowing them standard Git commit/push operations!

### 4. Zero-Friction Context Housekeeping (Log & Plan Archivers)
- **Problem**: Historical deployment logs and finalized action plans bloat AI model context windows, increasing latency and token overhead.
- **Solution**: 
  - **Auto-Housekeeping**: `fleet-commander.py` has startup hooks that automatically trigger `archive.py` inside both [02-Deployment-Logs](file:///Users/imac/Desktop/Bastien-Antigravity/obsidian-brain/05-Fleet-Operation/02-Deployment-Logs/) and [01-Fleet-Action-Plans](file:///Users/imac/Desktop/Bastien-Antigravity/obsidian-brain/05-Fleet-Operation/01-Fleet-Action-Plans/).
  - **Context Firewalls**: It moves old logs and completed plans into `deployments/` and `plans/` folders, dynamically generating `.aiignore`, `.mcpignore`, and `.geminiignore` containing `*` to block all model indexing inside these archive directories.
  - **Active MOCs**: Automatically rewrites both MOC indices to only link to currently active logs and migration plans, maintaining pristine and zero-friction graph connections.

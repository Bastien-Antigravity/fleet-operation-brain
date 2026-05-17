---
microservice: fleet-operation-brain
type: architecture
status: active
tags:
- '#ai/ignore'
- '#service/fleet-operation-brain'
---

# 📚 Fleet Operation: General & Misc

Philosophy, operational rules, and development details for maintaining the Bastien-Antigravity fleet command layer.

---

## ⚖️ Core Operating Philosophy

> **"The fleet moves as one, or it does not move at all."**
> Orchestration must favor centralized standardization over isolated, custom, ad-hoc changes.

---

## 🚦 Strategic Principles & Rules

### 1. Dynamic Exclusion Principle
- **Compliance Bypasses**: Strictly avoid hardcoding static exclusion lists in scripts (e.g., `fleet-commander.py`, `fleet-manager.py`). 
- **Centralization**: If a repository does not represent a standard microservice and should bypass strict compliance audits (such as knowledge bases), simply assign `"exclude_from_compliance": true` in [inventory.json](file:///Users/imac/Desktop/Bastien-Antigravity/obsidian-brain/05-Fleet-Operation/00-Repo-Control/inventory.json). The entire command infrastructure evaluates this property at runtime.

### 2. Submodule Pointer Integrity
- **Submodule Changes**: When making changes inside `05-Fleet-Operation` (which is a Git submodule), always commit and push the changes inside `05-Fleet-Operation` first.
- **Parent Synchronization**: After pushing the submodule, immediately run `fleet-commander.py --repo obsidian-brain` to stage, commit, and push the updated submodule hash pointer in the parent repository. This prevents Git drift across workspaces.

### 3. Standardized External Networking
- **Unified Network Bindings**: Across all environments (Local, Sandbox, and Global), all multi-container services must standardise on the external network name: **`teleremote-network`**.
- **Container Connectivity**: Never hardcode container gateway IPs. Services resolve each other by their service names defined under the shared Docker compose network layers.
- **Port Probing**: Use lightweight Netcat (`nc`) probes rather than heavy curl/grpc health checks inside entrypoint wrappers to guarantee non-blocking service start orders.

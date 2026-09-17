---
microservice: fleet-operation-brain
type: governance
status: active
tags:
- '#service/fleet-operation-brain'
- '#type/governance'
- '#state/active'
- '#zone/3-fleet'
---

# 🛰️ Fleet Operation: Repository Control & Data Registry

This directory serves as the **Authoritative Data Registry & Single Source of Truth (SSoT)** for repository discovery and service metadata across the Bastien-Antigravity ecosystem.

---

## 📄 Canonical Data Stores (SSoT)

| File | Purpose | Authoritative Role |
| :--- | :--- | :--- |
| **`inventory.json`** | Central registry of all 31 fleet repositories, their relative paths, git remotes, autorized branches (`develop`), and deployment modes. | **Single Source of Truth for Fleet Inventory**. Symlinked into `docker-deployment/modes/*/inventory.json`. |
| **`service-registry.json`** | Registry of microservice capability names, default network ports, protocols, and toolchain versions (Go, Python, Rust, C++). | Single Source of Truth for service archetypes and canonical port allocations. |

---

## ⚙️ Operational Code Architecture

All active execution logic and Python automation scripts reside natively in the **Engine Room** (`08-Base-Scripts`):

- **Inventory Discovery**: `python3 08-Base-Scripts/main.py build-inventory`
- **Fleet Commander (Status/Sync/Push)**: `python3 08-Base-Scripts/main.py fleet-commander <status|sync|vault-sync|push>`
- **Safe Fleet Refresh**: `python3 08-Base-Scripts/main.py fleet-refresh`
- **Microservice Scaffolder**: `python3 08-Base-Scripts/main.py scaffold-microservice`

> [!NOTE]
> The scripts in this directory (`build-inventory.py`, `fleet-manager.py`, `fleet-refresh.py`) are lightweight backward-compatibility forwarders that delegate directly to `08-Base-Scripts/main.py`.

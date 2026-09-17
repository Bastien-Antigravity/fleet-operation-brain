---
microservice: fleet-operation
type: session-state
status: active
last-updated: 2026-09-16
Mission-ID: FLEET-OPERATION-AUDIT-2026-09-16
tags:
- '#zone/3-fleet'
- '#service/fleet-operation'
- '#type/session-state'
- '#state/active'
---

# 🚢 Fleet Operation - AI Session & State

## 🎯 Active Status
- **Current Mission**: Orchestration control, inventory Single Source of Truth (SSoT) management, and multi-mode deployment support.
- **Inventory Single Source of Truth**: Master `00-Repo-Control/inventory.json` defines all 31 fleet repositories, classifications, `is_core` tags, and `modes` arrays (`local`, `docker`, `production`).
- **Mode Symlinks**: `docker-deployment/modes/*/inventory.json` are authoritative symlinks pointing directly to `00-Repo-Control/inventory.json`.
- **Inventory Builder**: `00-Repo-Control/build-inventory.py` automatically preserves manual attributes and updates the master inventory.

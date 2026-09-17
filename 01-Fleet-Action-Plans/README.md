---
microservice: fleet-operation-brain
type: index
status: active
tags:
- '#service/fleet-operation-brain'
- '#type/index'
- '#state/active'
- '#zone/3-fleet'
---

# 📋 Fleet Action Plans

This index manages active and historical fleet migrations and multi-repository updates in Mode 3 (Orchestrator).

## 🚀 Active Migration Plans
*None currently active.*

## 📦 Archived Historical Plans
Historical plans are archived in [`plans/`](plans/) with context firewall ignore rules (`.aiignore`, `.geminiignore`, `.mcpignore`) to maintain minimal context weight for AI agents.

- [[FAP-2026-05-03-GitHub-Sync]]
- [[2026-05-11-Standardize-GitHub-CI]]

## 🛠️ Archiving Workflow
Run `python3 archive.py` to automatically detect completed plans and move them into `plans/`, updating this index.

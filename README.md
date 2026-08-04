---
microservice: fleet-operation-brain
type: fleet-op
status: active
tags:
- '#service/fleet-operation-brain'
- '#type/fleet-op'
- '#state/active'
- '#zone/3-fleet'
---

# 🛰️ Zone 3: Fleet Operations Brain (Orchestrator Mode)

Welcome to the **Strategic Command Deck**. This brain is the cockpit for mass-execution across the Bastien-Antigravity fleet. It governs scale, synchronization, and automated migrations.

## 🛰️ Orchestrator Workflow
1. **Plan**: Create a **Fleet Action Plan** in `01-Fleet-Action-Plans/` defining the scope (which repos) and the objective.
2. **Execute**: The AI assumes the **Fleet Commander** role and modifies multiple repositories in parallel.
3. **Verify**: Run automated integration tests across the affected fleet.
4. **Log**: Record the outcome and version updates in `02-Deployment-Logs/`.

## 📂 Structure
- `00-Repo-Control/`: Scripts, registries, and configuration control tools for the fleet.
- `01-Fleet-Action-Plans/`: Strategy docs and action plans for multi-repository updates.
- `02-Deployment-Logs/`: Historical audit logs of fleet modifications and deployment reports.
- `05-Fleet-Strategy/`: Global conventions, laws, and CI/CD standardization policies.

## 🛠️ Fleet Manager Quick Reference

| Command | Action Description | Example Usage |
| :--- | :--- | :--- |
| `status` | Audit git branch and dirty/clean status across the fleet | `python3 00-Repo-Control/fleet-manager.py status` |
| `sync` | Perform atomic pull, submodule update, and push across fleet | `python3 00-Repo-Control/fleet-manager.py sync` |
| `vault-sync` | Perform atomic sync of obsidian-brain submodules and parent pointer | `python3 00-Repo-Control/fleet-manager.py vault-sync` |
| `audit` | Check CI/CD workflow status via GitHub API across fleet | `python3 00-Repo-Control/fleet-manager.py audit` |
| `discover` | Scan workspace and update `inventory.json` safely | `python3 00-Repo-Control/fleet-manager.py discover` |
| `--repo / -r` | Target a specific repository or subset | `python3 00-Repo-Control/fleet-manager.py status -r log-server` |

---
> [!IMPORTANT]
> This zone requires **Automated Testing** for every repo touched. There is no manual review for individual lines; the review is at the **Action Plan** level.

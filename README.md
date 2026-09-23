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
- `00-Repo-Control/`: Canonical Data Registry holding `inventory.json` (SSoT) and `service-registry.json`.
- `01-Fleet-Action-Plans/`: Strategy docs and action plans for multi-repository updates.
- `02-Deployment-Logs/`: Historical audit logs of fleet modifications and deployment reports.
- `04-Templates/`: Reusable CI/CD workflows and repository scaffolding templates.
- `05-Fleet-Strategy/`: Global conventions, laws, and CI/CD standardization policies.

## 🧩 Ecosystem Taxonomy Overview

Repositories in the Bastien-Antigravity ecosystem are versioned at `0.0.1` and split into three Tiers:

1. **Shared Libraries (SDKs, Protocols & Toolboxes)**: `microservice-toolbox`, `universal-logger`, `flexible-logger`, `distributed-config`, `safe-socket`.
2. **Level 1 Microservices (Independent Daemons & Apps)**:
   - **Core Platform Daemons (Base 14 Fleet)**: `config-server` (TCP `3306`, gRPC `3307`, REST `3308`), `log-server` (TCP `9020`, gRPC `9021`), `notif-server` (TCP `1026`, gRPC `1027`, REST `1029`), `tele-remote` (gRPC `1863`), `watchdog-agent` (REST `9095`), `web-interface` (HTTP `5000`).
   - **Domain Microservices (Trading & Analytics)**: Domain engines (`data-ingestor`, `enhanced-backtesting`, `ontime-scheduler`, `orderbook-aggregator`, `technical-analysis`, `fundamental-analysis`, `market-observer`, `mt5-gateway`) developed on top of the base platform.
3. **Orchestration & Brains**: `docker-deployment`, `sandbox-testing`, `obsidian-brain`.

For details, see [Ecosystem Taxonomy Guide](../03-Tech-Stack/quick-overview/Ecosystem-Taxonomy-Guide.md) and [Ecosystem Onboarding Guide](quick-overview/Ecosystem-Onboarding-Guide.md).

## 🛠️ Fleet Commander Quick Reference (Engine Room: `08-Base-Scripts`)

All operational automation is unified under `08-Base-Scripts/main.py`:

| Command | Action Description | Canonical Usage |
| :--- | :--- | :--- |
| `status` | Audit git branch and dirty/clean status across the fleet | `python3 08-Base-Scripts/main.py fleet-commander status` |
| `sync` | Perform atomic pull, submodule update, and push across fleet | `python3 08-Base-Scripts/main.py fleet-commander sync` |
| `vault-sync` | Perform atomic sync of obsidian-brain submodules and parent pointer | `python3 08-Base-Scripts/main.py fleet-commander vault-sync` |
| `push` | Compliance audit (docs, isolation zone, workflows) + mass commit & push | `python3 08-Base-Scripts/main.py fleet-commander push -m "chore: update"` |
| `build-inventory`| Scan workspace and update `inventory.json` safely | `python3 08-Base-Scripts/main.py build-inventory` |
| `fleet-refresh`| Safe non-destructive clone and synchronization (anti-data-loss guarded) | `python3 08-Base-Scripts/main.py fleet-refresh` |
| `--repo / -r` | Target a specific repository or active workspaces | `python3 08-Base-Scripts/main.py fleet-commander status -r log-server` |

---
> [!IMPORTANT]
> This zone requires **Automated Testing** for every repo touched. There is no manual review for individual lines; the review is at the **Action Plan** level.

---
microservice: fleet-operation-brain
type: fleet-op
status: active
tags:
- \'#service/fleet-operation-brain\'
- '#type/fleet-op'
- null
- '#state/active'
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

## 🚦 Fleet Status
- **Repositories**: See `00-Repo-Control/inventory.json` for the live registry.
- **Ongoing Migrations**: None.

---
> [!IMPORTANT]
> This zone requires **Automated Testing** for every repo touched. There is no manual review for individual lines; the review is at the **Action Plan** level.

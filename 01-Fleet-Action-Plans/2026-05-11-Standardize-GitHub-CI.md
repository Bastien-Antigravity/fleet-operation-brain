---
microservice: obsidian-brain
type: fleet-op
status: active
tags:
- '#type/fleet-op'
- null
- '#state/active'
---

# Fleet Action Plan: 2026-05-11 Standardize GitHub CI

---
type: fleet-action-plan
status: draft
date: 2026-05-11
scope: [all repositories in inventory.json]
mode: "[[00-AI-Orchestration/MODE-MANUAL]]"
---

## 🎯 Objective
Standardize .github configuration files (CI/CD, Dependabot, CODEOWNERS) across the entire Bastien-Antigravity fleet to ensure consistent governance and automated updates.

## 📦 Scope
| Repository | Branch | Change Type | Status |
|------------|--------|-------------|--------|
| All Repos | develop | config (CI/CD) | ⬜ pending |

## 📋 Steps
1. **Tooling Fix**: Update `fleet-commander.py` to use `inventory.json` and fix `fleet-manager.py` path detection bugs.
2. **Audit**: Run `fleet-manager.py audit` to identify repos missing standards.
3. **Execute**: Run `fleet-manager.py template` to apply standardized templates.
4. **Verify**: Check `web-interface` and `distributed-config` for correct CI job generation.
5. **Sync**: Push changes across the fleet using `fleet-commander.py`.

## 🚦 Rollback Plan
If the action fails on any repository:
1. STOP immediately.
2. Revert the failed repo using `git checkout -- .github`.
3. Log the failure in `02-Deployment-Logs/`.

## 📝 Post-Action
- [ ] All repos pass CI
- [ ] Deployment log created in `02-Deployment-Logs/`
- [ ] **DocMaintainer** updated MOC for `web-interface`
- [ ] **Sentinel** verified session integrity

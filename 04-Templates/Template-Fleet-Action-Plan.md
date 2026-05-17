---
microservice: obsidian-brain
type: fleet-op
status: active
tags:
- \'#service/obsidian-brain\'
- '#type/fleet-op'
- null
- '#state/active'
---

# Fleet Action Plan: [Name]

---
type: fleet-action-plan
status: draft
date: YYYY-MM-DD
scope: [list of target repositories]
mode: "[[00-AI-Orchestration/MODE-MANUAL]]"
---

## 🎯 Objective
Brief description of what this fleet-wide change accomplishes.

## 📦 Scope
| Repository | Branch | Change Type | Status |
|------------|--------|-------------|--------|
| repo-name  | develop | refactor / dependency / config | ⬜ pending |

## 📋 Steps
1. **Pre-Flight**: Run `fleet-manager.py --check` to verify all repos are clean.
2. **Execute**: Describe the changes to apply across the fleet.
3. **Verify**: Run CI/CD and sandbox tests for affected repos.
4. **Tag**: Coordinate version tags if needed.

## 🚦 Rollback Plan
If the action fails on any repository:
1. STOP immediately (Atomic Operations rule).
2. Revert the failed repo to the previous state.
3. Log the failure in `02-Deployment-Logs/`.

## 📝 Post-Action
- [ ] All repos pass CI
- [ ] Deployment log created in `02-Deployment-Logs/`
- [ ] `inventory.json` updated if repos were added/removed
- [ ] **DocMaintainer** notified for documentation sync

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

# 🎯 Fleet Operation: Testing Playbook

Validation strategies and operational audits to ensure safety before executing changes across the Bastien-Antigravity fleet.

---

## 🛡️ Pre-Flight Verification Playbook

Mass git operations and compliance validations must be executed in a safe, traceable sequence.

### Play 1: Run Compliance Audits
- **Action**: Check if a repository is fully compliant with ecosystem rules before attempting any synchronization or pushing.
- **Verification Command**:
  ```bash
  python3 08-Base-Scripts/main.py fleet-commander --repo <repo_name> --dry-run
  ```
- **Audited Zones**: The engine scans for proper YAML frontmatter headers in standard markdown files, validates standard naming conventions, and checks for `[FLEET-ARCHITECT]` signatures in GitHub actions workflow files.

### Play 2: Validate With Dry-Run Simulations
- **Action**: Always simulate global branch checking, tagging, or commits prior to executing destructive actions on GitHub.
- **Verification Command**:
  ```bash
  python3 08-Base-Scripts/main.py fleet-commander --fleet --dry-run -m "chore(fleet): standardizing setup"
  ```
- **Audit Verification**: Verify the generated console output for any errors or blocked repository listings.

### Play 3: Verify Docker Sandbox Integration
- **Action**: Ensure all microservices compile cleanly and external networks link correctly.
- **Verification Commands**:
  ```bash
  # Inside sandbox-testing:
  python3 03-Orchestration/scenario_orchestrator.py run <scenario_name>
  ```
- **Probes**: Ensure netcat TCP socket probes return `0` (success) when verifying inter-service endpoints.

### Play 4: Verify Housekeeping & Context Firewalls
- **Action**: Verify that historical logs and migration plans are properly swept into the archived zones to keep the graph and AI token count lean.
- **Verification Command**:
  - Run `fleet-commander.py` and inspect the output:
  ```
  ✨ Created context firewall ignore file: deployments/.aiignore
  📦 FOUND 13 HISTORICAL LOG(S) TO ARCHIVE:
  [-] Archived: LOG-2026-05-04-Develop-Sync.md -> deployments/LOG-2026-05-04-Develop-Sync.md
  ✨ Updated Deployment-Logs-MOC.md with the active layout!
  ```
- **Firewall Check**: Verify that `deployments/.aiignore` and `plans/.aiignore` contain `*` (which effectively tells Gemini, MCP, and AI models to completely bypass indexing the archive directory).

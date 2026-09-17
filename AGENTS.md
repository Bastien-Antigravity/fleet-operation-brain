# AGENTS.md: 05-Fleet-Operation

## Service Mission & Architecture Role
`05-Fleet-Operation` is the central command deck, fleet orchestration center, and configuration source-of-truth for repository governance and CI/CD standardization in the Bastien-Antigravity ecosystem. It maintains the definitive repository inventory (`inventory.json`), the fleet service capability registry (`service-registry.json`), fleet-wide Git management automation (`fleet-manager.py`), multi-repository migration plans (`01-Fleet-Action-Plans`), deployment audit logs (`02-Deployment-Logs`), and central CI/CD workflow templates (`04-Templates`).

- **Ecosystem Role**: Fleet Orchestration & Multi-Repo Command Center.
- **Primary AI Personas**: `FleetCommander` (Synchronization Officer), `FleetArchitect` (DevOps & CI/CD Guardian).
- **Core Registries**:
  - `00-Repo-Control/inventory.json`: Authoritative list of all 28+ repositories, paths, remotes, branches, and archetypes.
  - `00-Repo-Control/service-registry.json`: Authoritative registry of all shared libraries, infrastructure daemons, and application microservices with canonical ports, protocols, and container images.
- **Configuration Link**: `standalone.yaml -> ../docker-deployment/modes/local/config/native.yaml`

---

## Key Operational Commands

```bash
# Check branch, cleanliness, and ahead/behind status across all repositories
python3 00-Repo-Control/fleet-manager.py status

# Target a specific repository or subset
python3 00-Repo-Control/fleet-manager.py status -r log-server

# Perform synchronized pull, submodule update, and push across fleet
python3 00-Repo-Control/fleet-manager.py sync

# Stage and commit changes across the fleet
python3 00-Repo-Control/fleet-manager.py commit "chore(fleet): standard sync"

# Audit CI/CD workflow health across repositories via GitHub API
python3 00-Repo-Control/fleet-manager.py audit

# Safely scan workspace and discover new or updated repositories
python3 00-Repo-Control/fleet-manager.py discover

# Rebuild inventory.json from workspace scanning
python3 00-Repo-Control/build-inventory.py

# Push changes with automated compliance enforcement (via 08-Base-Scripts router)
python3 ../08-Base-Scripts/main.py fleet-commander --fleet -m "chore(fleet): [FLEET-COMMANDER] update" --dry-run
```

---

## Core Subsystems & Registry Control

1. **Repository Inventory (`00-Repo-Control/inventory.json`)**:
   - Sole authoritative Single Source of Truth (SSoT) for all fleet repositories, branch targets (`develop`), deployment modes (`modes: ["local", "docker", "production"]`), core classification (`is_core: true/false`), and compliance tracking.
   - Symlinked into `docker-deployment/modes/local/inventory.json`, `modes/docker/inventory.json`, and `modes/production/inventory.json`, providing direct cross-mode integration without file duplication.
   - Categorizes repositories into `orchestration`, `library`, and `level1-microservice`.
   - Repositories marked `exclude_from_compliance: true` (e.g. documentation vaults) are protected from automated build enforcement.
   - Rebuilding via `build-inventory.py` preserves `is_core`, `modes`, and compliance overrides automatically.

2. **Service Registry (`00-Repo-Control/service-registry.json`)**:
   - Master capability matrix defining:
     - **Libraries**: `microservice-toolbox`, `universal-logger`, `flexible-logger`, `distributed-config`, `safe-socket`.
     - **Infrastructure**: `timescale-db` (Port `5432`), `nats-server` (Port `4222`, Monitoring `8222`).
     - **Application Microservices**:
       - `config-server`: Ports `3306` (TCP), `3307` (gRPC), `3308` (REST) | Protocol: SafeSocket/gRPC/REST
       - `log-server`: Ports `9020` (TCP), `9021` (gRPC) | Protocol: SafeSocket/gRPC
       - `notif-server`: Port `8095` (REST) | Protocol: REST/OpenMFE
       - `tele-remote`: Port `1863` (gRPC) | Protocol: gRPC/Telegram
       - `watchdog-agent`: Port `8002` (REST) | Protocol: REST/Prometheus
       - `ontime-scheduler`: Port `8080` (HTTP) | Protocol: HTTP
       - `web-interface`: Port `5000` (HTTP) | Protocol: HTTP/OpenMFE

3. **Fleet Action Plans (`01-Fleet-Action-Plans/`)**:
   - Multi-repo migrations or cross-cutting updates must be planned using `04-Templates/Template-Fleet-Action-Plan.md`.
   - Active plans reside in `01-Fleet-Action-Plans/` and are indexed in `01-Fleet-Action-Plans/README.md`. Historical plans are archived in `plans/`.
   - Standard phases: Pre-Flight $\to$ Execution $\to$ Verification $\to$ Tagging $\to$ Post-Action.

4. **Deployment Logging (`02-Deployment-Logs/`)**:
   - Any fleet-wide sync, version tag, or significant deployment must be recorded in `02-Deployment-Logs/LOG-YYYY-MM-DD-<Action>.md`.
   - The latest active log is retained at the folder root and indexed in `02-Deployment-Logs/README.md`. Historical logs are archived in `deployments/`.

5. **CI/CD Master Templates (`04-Templates/`)**:
   - Reusable GitHub Actions workflows (`Microservice/ci.yml`, `Polyglot/ci.yml`).
   - Automated distribution via `python3 00-Repo-Control/fleet-manager.py template`.
   - **LOCKDOWN RULE**: Individual repositories must NEVER alter their `.github/workflows/ci.yml` manually; they inherit from the central reusable master workflows.

---

## The 6 Ecosystem Registration Touchpoints

Whenever a new microservice or capability is created, AI agents must complete all 6 registration touchpoints:

| Touchpoint | Target File | Purpose |
| :--- | :--- | :--- |
| **1. Service Registry** | `05-Fleet-Operation/00-Repo-Control/service-registry.json` | Register service name, image, canonical port, and protocol |
| **2. Repo Inventory** | `05-Fleet-Operation/00-Repo-Control/inventory.json` | Register repository path, remote, branch, and archetype |
| **3. Capability Config** | `docker-deployment/modes/local/config/native.yaml` | Define capability IP (`127.0.0.1`) and port (`${SVC_PORT:-XXXX}`) |
| **4. Container Manifest** | `docker-deployment/docker-compose.yaml` | Add service container, build context, and network alias |
| **5. Symlink Auto-Healer** | `watchdog-agent/src/config/heal.go` | Register `standalone.yaml` symlink path for auto-repair |
| **6. Dynamic UI / Remote** | `web-interface` & `tele-remote` | Register OpenMFE web tab or gRPC tele-remote UI menu (if interactive) |

---

## AI Squad Development Guidelines

1. **No Uncoordinated Direct Git Commands**: AI agents must never run raw `git push --all` or uncoordinated fleet commits. Use `fleet-manager.py` or `08-Base-Scripts/main.py fleet-commander`.
2. **Pre-Task Checkpoints**: Always check git status across target repositories before modifying files (`fleet-manager.py status -r <repo>`).
3. **Atomic Operations & Rollback**: If a fleet migration fails in any repository, halt immediately, restore the clean state, and log the incident in `02-Deployment-Logs/`.
4. **Canonical Port Integrity**: When configuring ports, strictly reference `service-registry.json` and `03-Tech-Stack/02-Project-Architecture/08-Networking-Protocols.md`. Never use hardcoded legacy ports (e.g. `1862`, `1026`, `8000`, `8080`).
5. **Header Ritual**: Source scripts in `00-Repo-Control/` and `01-Fleet-Action-Plans/` must include the Triple-Block header (`ESSENTIAL PROCESS`, `DATA FLOW`, `KEY PARAMETERS`).

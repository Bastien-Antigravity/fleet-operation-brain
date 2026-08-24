---
title: Out-of-the-Box Ecosystem Onboarding & Sharing Guide
version: 0.0.1
classification: Orchestration
last_updated: 2026-08-05
---

# 🚀 Out-of-the-Box Ecosystem Onboarding & Sharing Guide

Welcome to the **Bastien-Antigravity Ecosystem**. This guide explains how the platform works, how to run services out-of-the-box using Docker, and how to share the `obsidian-brain` workspace with new developers and AI coding agents.

---

## 1. Ecosystem Architecture & Taxonomy

The ecosystem is built on a clear 3-Tier taxonomy where all components are standardized at **Version `0.0.1`**:

```
                              ┌─────────────────────────────────────────┐
                              │           obsidian-brain                │
                              │     (AI Knowledge & Fleet Hub)          │
                              └────────────────────┬────────────────────┘
                                                   │
                   ┌───────────────────────────────┴───────────────────────────────┐
                   ▼                                                               ▼
    ┌─────────────────────────────┐                                 ┌─────────────────────────────┐
    │    Tier 1: Shared Libraries │                                 │  Tier 2: Level 1 Services   │
    │  (microservice-toolbox,     │                                 │ (config-server, log-server, │
    │   universal-logger, etc.)   │                                 │  tele-remote, web-interface)│
    └─────────────────────────────┘                                 └─────────────────────────────┘
```

1. **Shared Libraries (SDKs/Protocols)**:
   * `microservice-toolbox`, `universal-logger`, `flexible-logger`, `distributed-config`, `safe-socket`.
   * **Rule**: Reusable packages imported into microservices. They do *not* run as standalone daemons.
2. **Level 1 Microservices (Executable Daemons)**:
   * Independent containers exposing network ports (e.g. `config-server`: 1862, `log-server`: 9020/9021, `notif-server`: 1026, `tele-remote`: 1863, `ontime-scheduler`: 8080, `web-interface`: 5000).
3. **Orchestration & Deployment**:
   * `docker-deployment` (master docker compose), `sandbox-testing` (scenario runner), `obsidian-brain` (central agent workspace).

---

## 2. Quickstart: 3 Steps to Run Out-of-the-Box

### Step 1: Prerequisites & Workspace Structure
Ensure you have:
* **Docker & Docker Compose** (v2.20+)
* **Go 1.25+** (for local development)
* Workspace directory structured with sibling repositories:
  ```
  Bastien-Antigravity/
  ├── config-server/
  ├── log-server/
  ├── notif-server/
  ├── tele-remote/
  ├── watchdog-agent/
  ├── microservice-toolbox/
  ├── universal-logger/
  ├── distributed-config/
  ├── safe-socket/
  ├── flexible-logger/
  ├── docker-deployment/
  └── obsidian-brain/
  ```

---

### Step 2: Option A — Launch Entire Stack (Full Fleet)

To spin up the entire platform (TimescaleDB, NATS, log-server, config-server, notif-server, tele-remote, and scheduler):

```bash
cd Bastien-Antigravity/docker-deployment

# 1. Environment configuration (optional defaults provided)
cp .env.develop .env

# 2. Launch master stack
docker compose -f docker-compose.yaml up -d
```

#### Service Port Resolution
| Service | Host Port | Protocol / Purpose |
| :--- | :--- | :--- |
| `config-server` | `1862` | SafeSocket dynamic config server |
| `log-server` | `9020` / `9021` | SafeSocket / gRPC log aggregator |
| `notif-server` | `1026` | SafeSocket notification dispatcher |
| `tele-remote` | `1863` | gRPC / Telegram admin daemon |
| `ontime-scheduler` | `8080` | HTTP job scheduler daemon |
| `web-interface` | `5000` | Web UI dashboard |
| `timescale-db` | `5432` | PostgreSQL / TimescaleDB |
| `nats-server` | `4222` / `8222` | NATS message broker & monitor |

---

### Step 3: Option B — Launch Standalone Microservice

Each Level 1 Microservice contains a coherent `docker-compose.yml` and `Dockerfile`. You can build and run any individual service standalone:

```bash
# Example: Running tele-remote standalone
cd Bastien-Antigravity/tele-remote

# Build and start container (uses parent context for sibling library inclusion)
docker compose up -d --build
```

---

## 3. How Docker Builds & Multi-Stage Works

Each microservice Dockerfile uses a clean 2-stage build:

1. **Build Stage (`golang:1.25-alpine`)**:
   * Copies required shared library modules (`microservice-toolbox`, `universal-logger`, `distributed-config`, `safe-socket`).
   * Runs `go mod tidy` and compiles static CGO-free Linux binaries (`CGO_ENABLED=0 GOOS=linux`).
2. **Runtime Stage (`alpine:3.20`)**:
   * Copies minimal ca-certificates & timezone data.
   * Copies compiled binary into lightweight (~15MB) container image.

---

## 4. Sharing `obsidian-brain` with New Developers & AI Agents

To share this workspace out-of-the-box with a new contributor or AI coding agent:

1. **Clone `obsidian-brain` with submodules**:
   ```bash
   git clone --recursive https://github.com/Bastien-Antigravity/obsidian-brain.git
   ```
2. **AI Agent Context Files**:
   * AI agents automatically read `AI-Init.md` and `AI-Project-DNA.md` in each repository.
   * Metadata headers explicitly communicate repo classification and version:
     ```markdown
     # Metadata
     - Version: 0.0.1
     - Classification: Level 1 Microservice
     ```
3. **Fleet Manager Utility**:
   * Manage the workspace using [fleet-manager.py](file:///Users/imac/Desktop/Bastien-Antigravity/obsidian-brain/05-Fleet-Operation/00-Repo-Control/fleet-manager.py):
     ```bash
     # Check status of all repos
     python3 obsidian-brain/05-Fleet-Operation/00-Repo-Control/fleet-manager.py status

     # Discover new repos & auto-classify
     python3 obsidian-brain/05-Fleet-Operation/00-Repo-Control/fleet-manager.py discover

     # Audit CI & compliance across fleet
     python3 obsidian-brain/05-Fleet-Operation/00-Repo-Control/fleet-manager.py audit

     # Reset tags to v0.0.1
     python3 obsidian-brain/05-Fleet-Operation/00-Repo-Control/fleet-manager.py tag-reset
     ```

---

## 5. Configuration Profiles (`production`, `staging`, `devel`, `standalone`, `test`)

The platform supports 5 standardized environment configuration profiles managed by `distributed-config` and `microservice-toolbox`:

| Profile | Aliases | Mode / Strategy | Behavior |
| :--- | :--- | :--- | :--- |
| `standalone` | `devel`, `dev`, `development` | Offline local file-based | Loads local `<profile>.yaml` without needing remote `config-server`. |
| `staging` | `stage` | Remote Read-Only | Connects to `config-server` in read-only mode for environment config pull. |
| `production` | `prod` | Remote Read-Write | Connects to `config-server` with dynamic live update broadcasts. |
| `test` | — | In-Memory Mock | Isolated profile used by scenario tests and unit tests. |

### Selecting a Profile at Runtime

1. **Via CLI Flag**:
   ```bash
   ./tele-remote --profile production
   ./config-server --profile staging
   ```
2. **Via Environment Variable**:
   ```bash
   export CONFIG_PROFILE=production
   # or
   export APP_ENV=staging
   ```
3. **Via Code Instantiation**:
   ```go
   // Go / C++ / Python / Rust / VBA
   cfg, err := config.LoadConfig("production", nil)
   ```


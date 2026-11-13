---
title: 'AI Agent Quick Guide: New Repository Creation, Versioning & Makefile Standards'
type: guide
tags:
- '#zone/3-fleet'
- '#type/guide'
- '#tech/git'
- '#state/active'
- '#service/05-Fleet-Operation'
microservice: 05-Fleet-Operation
status: active
---

# 🤖 AI Agent Quick Guide: New Repository, Versioning & Makefile Standards

> [!IMPORTANT]
> **Authoritative Specification**: The single source of truth for repository structure, root files, language anatomy, coding standards, and fleet integration touchpoints is:
> 👉 **[[03-Repository-Structure|03 - Repository Structure & Microservice Creation Standard]]**
> 
> This document serves as a operational quick-reference for AI agents (FleetCommander, Orchestrator, Developer, Architect, Sentinel).

---

## 🏷️ 1. Repository Naming Conventions

All repositories in the `Bastien-Antigravity` GitHub organization MUST follow strict naming patterns:

| Category | Naming Schema | Canonical Examples | Description |
| :--- | :--- | :--- | :--- |
| **Microservices** | `<domain>-server` | `config-server`, `log-server`, `notif-server` | Core backend services with listening ports |
| **Agents & Supervisors** | `<domain>-agent` | `watchdog-agent` | Background processing or monitoring agents |
| **Gateways & Adaptors**| `<domain>-gateway` | `mt5-gateway` | Edge protocol adapters and hardware bridges |
| **User Interfaces** | `<domain>-interface` | `web-interface` | Web frontend / dashboard applications |
| **Domain Processing** | `<domain>-<worker>` | `market-observer`, `fundamental-analysis` | Event-driven processing engines |
| **Shared Libraries** | `<feature>-<type>` | `microservice-toolbox`, `universal-logger`, `distributed-config`, `safe-socket` | Cross-service libraries (Go/Python/Rust/C/C++) |
| **Testing / Verification**| `<domain>-testing` | `sandbox-testing` | E2E integration test scenarios |
| **Knowledge Vaults** | `<number>-<Name>` | `obsidian-brain` | Governance, architecture, and documentation vaults |

---

## 📁 2. Mandatory Repository Elements Checklist

Every repository created by AI agents MUST fulfill the 12 mandatory root elements defined in [[03-Repository-Structure]]:

```text
<repo-name>/
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml                 # Mandatory for ALL code repos
│       └── release.yml            # For Shared Polyglot Libraries
├── quick-overview/                # Mandatory Isolation Zone (human-only, excluded from AI)
│   ├── Architecture-Overview.md
│   ├── Features-Behavior.md
│   ├── Testing-Playbook.md
│   ├── General-Misc.md
│   ├── .geminiignore
│   ├── .mcpignore
│   └── .aiignore
├── .gitignore                     # Standard OS + cache + build protections
├── VERSION.txt                    # Single Source of Truth for Versioning (e.g. 0.0.1)
├── Makefile                       # Standard targets (all, build, test, race, vet, version, clean)
├── AGENTS.md                      # Primary AI agent operating guide & prompt
├── AI-Session-State.md            # Active AI session memory tracker
├── Dockerfile                     # Multi-stage container build
├── docker-compose.yml             # Local compose fragment (teleremote-network)
├── README.md                      # Human & AI entry point linking to AGENTS.md
└── standalone.yaml                # Symlink -> ../docker-deployment/modes/local/config/native.yaml
```

---

## 🔢 3. Versioning & Makefile Standard Rules

### A. Single Source of Truth (`VERSION.txt`)
- Every repository MUST maintain a plain-text file `VERSION.txt` at the root level containing a semver string (e.g., `0.0.1`).
- Initialized repositories start at `0.0.1`.
- All build tools, packages, and `Makefile` scripts MUST read `VERSION.txt` as their single source of truth. Hardcoding version numbers in source code or telemetry endpoints is strictly prohibited (`HARDCODED_VERSION_VIOLATION`).

### B. Standardized `Makefile` Targets (Compiled Languages Only)
> [!IMPORTANT]
> **Python Tooling Purity**: Pure Python repositories **DO NOT** generate a `Makefile`. They rely natively on `pytest`, `requirements.txt`, and virtual environments.

```makefile
VERSION ?= $(shell cat VERSION.txt)
LDFLAGS := -s -w -X 'github.com/Bastien-Antigravity/microservice-toolbox/go/pkg/version.BuildVersion=$(VERSION)'

.PHONY: all build test race vet version clean run

all: build

version:
	@echo $(VERSION)

build:
	@echo "Building repository (version $(VERSION))..."
	@mkdir -p bin
	go build -ldflags="$(LDFLAGS)" -o bin/$(NAME) ./cmd/$(NAME)

test:
	@echo "Running tests (version $(VERSION))..."
	go test -v ./...

race:
	@echo "Running race detector (version $(VERSION))..."
	go test -race -v ./...

vet:
	@echo "Running go vet..."
	go vet ./...

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf bin/ dist/ build/ *.egg-info target/
```

### C. Language-Specific Dynamic Versioning (`appConfig.GetVersion()` / `get_version()`)
Microservices ALWAYS read their version through the dedicated method on their bootstrapped `AppConfig` instance (`VERSION.txt` ONLY; zero `"0.0.1"` fallbacks, zero runtime `APP_VERSION`/`SERVICE_VERSION` overrides, zero bespoke scanning loops):
1. **Go Services**: `appConfig.GetVersion()` (backed internally by `go/pkg/version` + optional `-ldflags="$(LDFLAGS)"` from `VERSION.txt`).
2. **Rust Services**: `app_config.get_version()` (backed internally by `rust/src/version`; if adding a `build.rs` for standalone binaries, fail fast via `.expect(...)` with zero `CARGO_PKG_VERSION` fallback).
3. **Python Services**: `self.config.get_version()` / `app_config.get_version()`.
4. **C++17 Services**: `appConfig->GetVersion()` (optionally compiled with `-DAPP_VERSION=\"$(VERSION)\"` directly from `VERSION.txt`).
5. **VBA Modules**: `appConfig.GetVersion()` (or `appConfig.Version`).

### D. Standard `microservice-toolbox` Tools (`spec`, `contracts`, `wiretap`, `notification`)
- Register declarative `ServiceSpec` + `Contracts` (`ExchangeContract[]`) at startup via `spec.PublishWithLifecycle` / `publish_with_lifecycle` / `SpecPublisher::PublishWithLifecycle` (`BuildSpecFromConfig` automatically fills `version` via `appConfig.GetVersion()`, `URL`, `%s` `Framing` ports, `ports`, `node`, `NavRoute`, `Canvas`, `Health`).
- Build `ContractsEnvelope` using built-in toolbox extractors (`contracts.go`, `contracts.py`, `rust::contracts`, `contracts.hpp`, pure C11 `contracts.h`) and expose `GET /api/v1/contracts` + embedded `mfe.js` (`BastienMFEElement` + `window.BastienMFEContracts` inside `.openmfe-tabs-bar`).
- Use `wiretap` (auto-wired at boot in Go/Python; `ConfigureFromConfig` in C++/Rust), `notification` (`NotificationClient`), `connectivity.Resolver`, and `LifecycleManager` rather than writing custom plumbing.

> [!CAUTION]
> **Strict Error-Masking Prohibition**: Never append `|| true` or pipe to `2>/dev/null` on compilation or test targets. Failures must fail fast.

---

## ⚙️ 4. Standardized GitHub Actions Workflows

### Continuous Integration (`.github/workflows/ci.yml`)
Generated automatically or copied from `05-Fleet-Operation/04-Templates/Microservice/ci.yml`:

```yaml
# [FLEET-ARCHITECT] Continuous Integration
name: Fleet CI
on:
  push:
    branches: [ develop ]
  pull_request:
    branches: [ develop ]

jobs:
  fleet-ci:
    uses: Bastien-Antigravity/fleet-operation-brain/.github/workflows/master-ci.yml@develop
    secrets: inherit
```

---

## 🛡️ 5. Standardized `.gitignore` Rules

When creating or modifying `.gitignore`, ensure standard OS and build caches are protected:

```gitignore
# --- Standard Ecosystem Protections ---
# OS metadata
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes

# Logs and runtime caches
*.log
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
bin/
target/
*.egg-info/
```

---

## 🚀 6. Automated Generation Command

Always use the automated scaffolding tool to generate compliant microservices:

```bash
python3 08-Squad-Agent/main.py scaffold-microservice --name <name> --lang <go|python|rust|cpp> --port <port> --desc "<description>"
```

---
*Reference: [[03-Repository-Structure]], [[11-Microservice-Integration-Standard]], [[12-Docker-Deployment-Standards]]*

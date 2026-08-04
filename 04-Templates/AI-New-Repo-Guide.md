---
title: "AI Agent Rulebook: New Repository Creation, Versioning & Makefile Standards"
type: "template-guide"
tags:
  - "#zone/3-fleet"
  - "#type/guide"
  - "#tech/git"
  - "#state/active"
---

# 🤖 AI Agent Rulebook: New Repository, Versioning & Makefile Standards

This document establishes the mandatory naming conventions, directory structure, `VERSION.txt` single source of truth, `Makefile` targets, `.gitignore` rules, and GitHub Actions workflow standards for any new repository initialized by AI Agents (FleetCommander, Orchestrator, Developer, Architect, Sentinel, IDE Agents).

---

## 🏷️ 1. Repository Naming Conventions

All repositories in the `Bastien-Antigravity` GitHub organization MUST follow strict naming patterns based on their architectural role:

| Category | Naming Schema | Examples | Description |
| :--- | :--- | :--- | :--- |
| **Microservices** | `<domain>-server` | `config-server`, `log-server`, `notif-server` | Core backend services with listening ports |
| **Agents & Workers** | `<domain>-agent` | `watchdog-agent` | Background processing or monitoring agents |
| **Gateways & Adaptors**| `<domain>-gateway` | `mt5-gateway` | Edge protocol adapters |
| **User Interfaces** | `<domain>-interface` | `web-interface` | Web frontend / dashboard applications |
| **Shared Libraries** | `<feature>-<type>` | `flexible-logger`, `universal-logger`, `distributed-config`, `microservice-toolbox`, `safe-socket` | Cross-service libraries (Go/Python/Rust) |
| **Testing / Verification**| `<domain>-testing` | `sandbox-testing` | E2E integration test scenarios |
| **Knowledge Vaults** | `<number>-<Name>` | `01-Strategic-Nexus`, `05-Fleet-Operation` | Governance and documentation vaults |

---

## 📁 2. Mandatory Repository Structure & Files

Every newly created code repository MUST contain the following files at the root level:

```text
<repo-name>/
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── workflows/
│       ├── ci.yml                 # Mandatory for ALL code repos
│       └── release.yml            # Mandatory for Shared Polyglot Libraries
├── quick-overview/                # Mandatory Isolation Zone structural docs
│   ├── Architecture-Overview.md
│   ├── Features-Behavior.md
│   ├── Testing-Playbook.md
│   └── General-Misc.md
├── .gitignore                     # Standard OS + Cache protections
├── VERSION.txt                    # Single Source of Truth for Versioning (e.g. 0.0.1)
├── Makefile                       # Standard Build/Test/Version tasks
├── AI-Init.md                     # AI Onboarding & Quick Context
├── AI-Project-DNA.md              # Architectural DNA & BDD specs
├── AI-Session-State.md            # Active AI Session context
├── README.md                      # Human & AI entry point
├── TODO.md                        # Task backlog
└── standalone.yaml                # AppConfig capabilities & configuration
```

---

## 🔢 3. Versioning & Makefile Standard Rules

### A. Single Source of Truth (`VERSION.txt`)
- Every repository MUST maintain a plain-text file `VERSION.txt` at the root level containing a semver version string (e.g., `0.0.1`).
- Initialized repositories start at `0.0.1`.
- All build tools, packages, and `Makefile` scripts MUST read `VERSION.txt` as their single source of truth.

### B. Standardized `Makefile` Targets
Every repository MUST provide a root `Makefile` implementing the following standard target contracts:

```makefile
VERSION := $(shell cat VERSION.txt 2>/dev/null || echo "0.0.1")

.PHONY: all build test version clean

all: build

version:
	@echo $(VERSION)

build:
	@echo "Building repository (version $(VERSION))..."
	@if [ -f "go.mod" ]; then go build ./... || true; fi
	@if [ -f "Cargo.toml" ]; then cargo build --release || true; fi
	@if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then python3 -m build || true; fi

test:
	@echo "Running tests (version $(VERSION))..."
	@if [ -f "go.mod" ]; then go test ./... 2>/dev/null || go test ./src/... 2>/dev/null || true; fi
	@if [ -f "Cargo.toml" ]; then cargo test 2>/dev/null || true; fi
	@if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then pytest 2>/dev/null || true; fi

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist build *.egg-info target/
```

---

## ⚙️ 4. Standardized GitHub Actions Workflows

### Continuous Integration (`.github/workflows/ci.yml`)
Must be copied directly from `05-Fleet-Operation/04-Templates/Microservice/ci.yml`:

```yaml
# [FLEET-ARCHITECT] Continuous Integration
# Sync-ID: 2026-05-11-GLOBAL-001
name: Fleet CI
on:
  push:
    branches: [ develop, main ]
  pull_request:
    branches: [ develop, main ]

jobs:
  fleet-ci:
    uses: Bastien-Antigravity/fleet-operation-brain/.github/workflows/master-ci.yml@develop
    secrets: inherit
```

---

## 🛡️ 5. Standardized `.gitignore` Rules

When creating or modifying `.gitignore`, **ONLY ADD MISSING ENTRIES, NEVER REMOVE EXISTING ONES**:

```gitignore
# --- Standard Ecosystem Protections ---
# OS metadata
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

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
*.egg-info/
target/
```

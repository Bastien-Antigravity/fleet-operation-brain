---
microservice: obsidian-brain
type: fleet-op
status: active
tags:
- '#service/obsidian-brain'
- '#type/fleet-op'
- '#state/active'
- '#zone/3-fleet'
---

# 📡 Fleet Strategy: CI/CD Standards

## 📜 General Principles
Every CI/CD pipeline in the Bastien-Antigravity fleet MUST adhere to these structural laws to ensure cross-repo maintainability.

## 📁 File Naming & Location
- **Location**: All workflows MUST reside in `.github/workflows/`.
- **Standard Names**:
    - `ci.yml`: For validation on PRs and pushes.
    - `release.yml`: For deployments upon Tag creation.
    - `security.yml`: For Dependabot and security scans.

## 🏗️ Pipeline Structure
1.  **Stage 1: Pre-Flight (Fast)**
    - Linting and formatting checks (Go: `golangci-lint`, Python: `ruff`/`mypy`, Rust: `clippy`).
    - Front-matter & tag taxonomy validation (`ensure-frontmatter --check` and tag consistency against canonical taxonomy to guarantee MCP and RAG index precision).
    - Work-tree cleanliness check for local pre-commit/pre-push executions.
    - Failure here blocks all subsequent stages.
2.  **Stage 2: Verification (Deep)**
    - Unit tests with coverage reporting (target ≥ 80% coverage on core logic).
    - Architecture checks (e.g., Go `errcheck`, Rust `clippy`, port binding checks).
    - Go Module `/vN` validation: verifies that `go.mod` appends `/vN` when semantic version ≥ 2.
    - Branch protection verification: automated audit asserting branch protection rules on `main` and `develop`.
3.  **Stage 3: Integration & Gates (Final)**
    - Sandbox testing or multi-service integration via `sandbox-testing` Docker Compose.
    - **The Purger Gate ("Mister Straight-to-Goal")**: Verifies code economy; PRs must prefer eliminating dead code over adding unnecessary layers.
    - **BDD Spec Alignment**: Verifies that features pass corresponding Gherkin specifications in `02-Business-BDD`.

## 🔐 Secret Management
- **Naming**: Use standardized prefixes:
    - `GLOBAL_GH_PAT`: For cross-repo synchronization.
    - `REGISTRY_TOKEN`: For pushing to GHCR.
- **Scope**: Secrets should be configured at the **Organization Level** wherever possible to avoid manual per-repo configuration.
- **Encrypted Ingestion**: Sensitive values in repository configuration templates must remain `ENC(...)` tokens until runtime decryption.

## 🛑 The "Red Fleet" Protocol
- **Zero Tolerance**: No PR shall be merged if the CI is Red.
- **Fleet Commander Lock**: If `fleet-manager audit` or `validate-compliance` reports a failure, the Fleet Commander MUST prioritize fixing that repository before performing any fleet-wide migrations.

## 🔗 Documentation-to-Code Alignment
- **Traceability Markers**: Architecture documents embed alignment comments (`<!-- register_documentation_link -->`) establishing explicit links between rules and the enforcement scripts residing in `08-Base-Scripts/` and `05-Fleet-Operation/`.
- **Automated Fleet Audits**: Preflight checks (`python3 08-Base-Scripts/main.py preflight-check` and `validate-compliance`) audit frontmatter health (≥ 99% valid), tag conformance, and workflow consistency across the entire fleet.

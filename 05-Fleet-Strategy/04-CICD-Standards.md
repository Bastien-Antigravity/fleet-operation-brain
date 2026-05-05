---
microservice: obsidian-brain
type: fleet-op
status: active
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
    - Linting and Formatting checks.
    - Failure here must block all subsequent stages.
2.  **Stage 2: Verification (Deep)**
    - Unit tests with coverage reporting.
    - Architecture checks (e.g., Go `errcheck`, Rust `clippy`).
3.  **Stage 3: Integration (Final)**
    - Sandbox testing or multi-service integration.

## 🔐 Secret Management
- **Naming**: Use standardized prefixes:
    - `GLOBAL_GH_PAT`: For cross-repo synchronization.
    - `REGISTRY_TOKEN`: For pushing to GHCR.
- **Scope**: Secrets should be configured at the **Organization Level** wherever possible to avoid manual per-repo configuration.

## 🛑 The "Red Fleet" Protocol
- **Zero Tolerance**: No PR shall be merged if the CI is Red.
- **Fleet Commander Lock**: If the `fleet-manager audit` reports a failure, the Fleet Commander MUST prioritize fixing that repository before performing any fleet-wide migrations.

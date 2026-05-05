---
microservice: obsidian-brain
type: fleet-op
status: active
---

# 📡 Fleet Strategy: CI Protocols

> [!NOTE]
> This is the **Execution Layer**. For the architectural definitions and high-level rules, see **[[03-Tech-Stack/04-Project-Deployment/04-CICD-and-Lifecycle|📐 CI/CD and Lifecycle Architecture]]**.

## 🧪 The 3-Stage Pipeline
Every repository must execute these three stages (locally or via GitHub Actions):

### Stage 1: Static Analysis (Pre-Flight)
- **Linting**: Standard linters for each language (Go: `golangci-lint`, Python: `black/mypy`, Rust: `clippy`).
- **Formatting**: Ensure code follows the `03-Tech-Stack` style guides.

### Stage 2: Unit Testing (Isolation)
- **Coverage**: Aim for 80% coverage on core logic.
- **Speed**: Unit tests must run in < 30 seconds.

### Stage 3: Sandbox Integration (Final Verification)
- **Environment**: Launch the `sandbox-testing` Docker Compose environment.
- **BDD Validation**: Execute Gherkin scenarios to verify that the code change hasn't broken the behavior specified in the `02-Business-BDD`.

## 🛑 Failure Protocol
- **Blockers**: Any failure in Stage 1 or 2 blocks the merge.
- **Warning**: Failures in Stage 3 on "non-hardened" repositories may be bypassed with Architect approval, but MUST be logged.

## 🛠️ CI Maintenance & Templates
- **Standard Template**: Every repository MUST use the `.github/workflows/ci-standard.yml` provided in the `04-Templates` folder.
- **Global Updates**: When the Fleet Commander updates the `ci-standard.yml` template, they MUST propagate the change to all repositories in the `inventory.json`.
- **Secrets**: CI workflows must NEVER contain hardcoded tokens. Use `secrets.GITHUB_TOKEN` or Organization-level secrets.

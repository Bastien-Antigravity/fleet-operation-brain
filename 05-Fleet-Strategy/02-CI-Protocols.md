# 📡 Fleet Strategy: CI Protocols

## 🧪 The 3-Stage Pipeline
Every repository must execute these three stages (locally or via GitHub Actions):

### Stage 1: Static Analysis (Pre-Flight)
- **Linting**: Standard linters for each language (Go: `golangci-lint`, Python: `black/mypy`, Rust: `clippy`).
- **Formatting**: Ensure code follows the `tech-stack-brain` style guides.

### Stage 2: Unit Testing (Isolation)
- **Coverage**: Aim for 80% coverage on core logic.
- **Speed**: Unit tests must run in < 30 seconds.

### Stage 3: Sandbox Integration (Final Verification)
- **Environment**: Launch the `sandbox-testing` Docker Compose environment.
- **BDD Validation**: Execute Gherkin scenarios to verify that the code change hasn't broken the behavior specified in the `business-bdd-brain`.

## 🛑 Failure Protocol
- **Blockers**: Any failure in Stage 1 or 2 blocks the merge.
- **Warning**: Failures in Stage 3 on "non-hardened" repositories may be bypassed with Architect approval, but MUST be logged.

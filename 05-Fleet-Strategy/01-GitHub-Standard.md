# 📡 Fleet Strategy: GitHub Standard

## 🎯 Global Branching Model (GitFlow Hybrid)
Every repository in the Bastien-Antigravity fleet MUST follow this branching structure:

1.  **`main` (Protected)**: 
    *   Contains production-ready code.
    *   No direct commits allowed.
    *   Only merges from `develop` via a tagged release.
2.  **`develop` (Active)**:
    *   The primary integration branch.
    *   All features and fixes are merged here first.
3.  **`feature/*` or `fix/*`**:
    *   Short-lived branches for specific tasks.
    *   Must be deleted after merging.

## 🛡️ Repository Governance
- **Remote Naming**: The primary GitHub remote MUST be named `origin`.
- **Sync Rule**: Before starting any task, the Fleet Commander must ensure `develop` is synced with `origin/develop`.
- **Atomic Commits**: Commits should be granular and prefixed with the scope (e.g., `feat(safe-socket): ...`, `fix(config): ...`).

## 🤝 PR & Review Protocol
- **AI-Validation**: No PR should be merged to `develop` without passing the **Sandbox Integration** tests.
- **Spec-First Alignment**: For hardened repositories, the PR description MUST link to the corresponding BDD Spec in the Specifications Brain.

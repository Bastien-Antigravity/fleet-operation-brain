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

# 📡 Fleet Strategy: GitHub Standard

## 🏗️ Repo Creation Protocol
When the Fleet Commander initializes a new repository, it MUST include:
1.  **AI-Init.md**: Context for the AI assistant.
2.  **.github/dependabot.yml**: Standardized Dependabot schema configuration.
3.  **LICENSE & README**: Standardized ecosystem headers.
4.  **Initial Branches**: Create `main` and `develop` immediately.

## 🎯 Global Branching Model (GitFlow Hybrid)
Every repository in the Bastien-Antigravity fleet MUST follow this branching structure:

1.  **`main` (Protected)**: 
    *   Contains production-ready code.
    *   No direct commits allowed.
    *   Only merges from `develop` via a tagged release.
2.  **`develop` (Active)**:
    *   The primary integration branch.
    *   All features and fixes are merged here first.

## 🛡️ GitHub Branch Protection
Every repository MUST have "Branch Protection" enabled on GitHub for `main` and `develop`:
- **No Force Push**: Prevent overwriting history.
- **No Deletion**: Prevent accidental branch removal.
- **Review Required**: Minimum 1 approving review (can be AI-Architect) before merging to `main`.
3.  **`feature/*` or `fix/*`**:
    *   Short-lived branches for specific tasks.
    *   Must be deleted after merging.

## 🛡️ Repository Governance
- **Remote Naming**: The primary GitHub remote MUST be named `origin`.
- **Sync Rule**: Before starting any task, the Fleet Commander must ensure `develop` is synced with `origin/develop`.
- **Atomic Commits**: Commits should be granular and prefixed with the scope (e.g., `feat(safe-socket): ...`, `fix(config): ...`).

## 🐹 Go Module Governance (v2+ Rule)
To avoid the "Go Module Trap", repositories using Go MUST follow these rules when reaching Major Version 2 or higher:
- **Module Path**: The `go.mod` file MUST append `/vN` to the module path (e.g., `module github.com/Bastien-Antigravity/safe-socket/v2`).
- **Imports**: All internal and external imports for that repository MUST be updated to reflect the `/vN` path.
- **Sync**: The Fleet Commander MUST verify `go.mod` consistency before creating a Major tag.

## 📜 The Law of Commitment
To maintain a clean and traceable history, the following rules apply:
1.  **Mandatory Local Commit**: Every task (feat/fix) MUST be committed locally with a descriptive message before any fleet synchronization.
2.  **No Magic Syncs**: The Fleet Manager will REFUSE to sync any repository with uncommitted changes. This prevents generic or "messy" commit messages from entering the history.
3.  **Sync = Delivery**: Synchronization is strictly for pulling remote updates and delivering verified local commits to GitHub.
4.  **Pre-Task Git Checkpoint**: To enable safe rollbacks in case of code generation issues, the AI Squad MUST ensure that the current working directory is clean or has a safety commit (checkpoint) before writing new code. Under Mode 1, this check is blocking; under Mode 2, it is a recommendation; under Mode 4, the agent must warn the user.

## 🤝 PR & Review Protocol
- **AI-Validation**: No PR should be merged to `develop` without passing the **Sandbox Integration** tests.
- **The Purger Gate**: Every significant change MUST pass through the **"Mister Straight-to-Goal"** check. If a fix can be achieved by removing code rather than adding it, that path MUST be chosen.
- **Spec-First Alignment**: For hardened repositories, the PR description MUST link to the corresponding BDD Spec in the Specifications Brain.

# 📡 Fleet Strategy: CD & Lifecycle

## 🚀 Deployment Tiers
1.  **Tier 1: Staging (Live-Beta)**
    *   Triggered automatically upon push to `develop`.
    *   Used for final human-in-the-loop verification.
2.  **Tier 2: Production (Master)**
    *   Triggered by a **Git Tag** (e.g., `v1.2.3`).
    *   Requires a merge from `develop` to `main`.

## 🏷️ Versioning (SemVer)
We follow **Semantic Versioning**:
- **Major**: Breaking architectural changes.
- **Minor**: New features, non-breaking.
- **Patch**: Bug fixes, hardening.

## 🌀 Automated Updates (Watchtower)
- **Standard**: All non-critical microservices (Log, Notif, Market) use `containrrr/watchtower` for automated image pulling.
- **Exceptions**: Databases and the `config-server` are excluded from auto-updates to prevent data corruption.

## 📅 Fleet Sync Ritual
Every Sunday (or before a major release), the **Fleet Commander** performs a global `sync` and `audit` to ensure all repositories are aligned before the production push.

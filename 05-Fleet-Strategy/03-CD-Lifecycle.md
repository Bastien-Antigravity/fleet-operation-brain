---
microservice: obsidian-brain
type: fleet-op
status: active
---

# 📡 Fleet Strategy: CD & Lifecycle

## 🚀 Deployment Tiers
1.  **Tier 1: Staging (Live-Beta)**
    *   Triggered automatically upon push to `develop`.
    *   Used for final human-in-the-loop verification.
2.  **Tier 2: Production (Master)**
    *   Triggered by a **Git Tag** (e.g., `v1.2.3`).
    *   Requires a merge from `develop` to `main`.

## 📦 Container Registry Standard
- **Target**: All fleet images MUST be pushed to **GitHub Container Registry (ghcr.io)**.
- **Naming**: `ghcr.io/Bastien-Antigravity/[microservice-name]:[tag]`.
- **Retention**: Keep only the last 5 tags for non-production images; keep all production tags.

## 📡 CD Orchestration (Fleet Commander)
- **Deployment**: The Fleet Commander is responsible for updating the `docker-compose.yml` and `kubernetes` manifests across the fleet.
- **Verification**: Post-deployment health checks (Stage 3) MUST be verified before considering a CD action complete.

## 🏷️ Versioning (SemVer)
We follow **Semantic Versioning**:
- **Major**: Breaking architectural changes.
- **Minor**: New features, non-breaking.
- **Patch**: Bug fixes, hardening.

## 🎁 Release Management Protocol
The Fleet Commander orchestrates releases using the following steps:
1.  **Changelog Generation**: Aggregate all `feat:` and `fix:` commits since the last tag.
2.  **Tagging**: Apply the SemVer tag to the `main` branch.
3.  **GitHub Release**: Create a formal release on GitHub with the changelog and any compiled binaries (if applicable).
4.  **Announcement**: Log the release in `05-Fleet-Operation/02-Deployment-Logs/`.

## 🌀 Automated Updates (Watchtower)
- **Standard**: All non-critical microservices (Log, Notif, Market) use `containrrr/watchtower` for automated image pulling.
- **Exceptions**: Databases and the `config-server` are excluded from auto-updates to prevent data corruption.

## 📅 Fleet Sync Ritual
Every Sunday (or before a major release), the **Fleet Commander** performs a global `sync` and `audit` to ensure all repositories are aligned before the production push.

---
microservice: fleet-operation-brain
type: fleet-log
status: active
date: 2026-05-11
tags:
- '#fleet-log'
- '#ci-cd'
- '#type/log'
- '#state/active'
---

# Deployment Log: CI Architecture Modernization

**Date**: 2026-05-11
**Objective**: Transition all repositories to use Centralized Reusable Workflows and a Global Linter Configuration.

## Summary of Changes
- **Reusable Workflows**: Deconstructed the monolithic `master-ci.yml` into granular workflow files (`workflow-go.yml`, `workflow-python.yml`, `workflow-rust.yml`, `workflow-cpp.yml`) located in `obsidian-brain/05-Fleet-Operation/.github/workflows/`.
- **Template Updates**: Updated both `Microservice` and `Polyglot` templates to delegate entirely to these reusable workflows, eliminating static duplication of GitHub Actions steps.
- **Global Linter**: Centralized the `golangci-lint` configuration into `.golangci-global.yml`. Modified `fleet-manager.py` to distribute this config as `.golangci.yml` to all 25 fleet repositories.
- **Node.js 24 Migration**: Proactively opted into Node.js 24 for all GitHub Actions by setting `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` in the centralized reusable workflows to avoid upcoming Node.js 20 deprecation issues.
- **Docker Standardization**: Standardized runtime environments (Alpine 3.20) across the fleet while preserving specialized requirements for `orchestrator` (`golang:1.25.4-alpine3.22`) and `enhanced-backtesting` (`python:3.12-slim-bullseye`).
- **Polyglot CI Robustness**: Patched reusable workflows (`workflow-python.yml`, etc.) to correctly build CGO bridges by searching for the root `Makefile` when running in subdirectories. This resolves `FileNotFoundError` for shared libraries in polyglot repos like `safe-socket`.

## Execution
1. Atomic Vault Sync ran for `obsidian-brain` to push workflows.
2. `fleet-manager.py template` ran across the entire fleet.
3. Fleet-wide commit and sync to `develop` completed successfully.

## Verification
- GitHub Actions dynamically inherits from `fleet-operation-brain`.
- All QF1008 `staticcheck` exclusion rules are properly enforced by the `.golangci.yml` file.

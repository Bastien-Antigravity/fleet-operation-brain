---
title: CODEOWNERS Template & Governance Guidelines
type: note
status: active
microservice: 08-Base-Scripts
tags:
- '#service/08-Base-Scripts'
- '#type/note'
- '#state/active'
- '#zone/3-fleet'
---

# 🛡️ CODEOWNERS Template & Governance Guidelines

This document outlines the ownership policies enforced across repositories in the Bastien-Antigravity fleet.

## Purpose & Scope
The `CODEOWNERS` file at `.github/CODEOWNERS` defines the individuals and squads responsible for approving pull requests modifying critical subsystem files, specifically CI/CD workflows, dependabot configs, and core architectural declarations.

## Standard Template
```text
# Restrict CI/CD and Dependabot files to the Architect team
/.github/workflows/ @Bastien-Antigravity/fleet-architects
/.github/dependabot.yml @Bastien-Antigravity/fleet-architects
```

## AI Agent Rule
AI agents generating new microservices must include this template at `.github/CODEOWNERS` during the repository scaffolding lifecycle.
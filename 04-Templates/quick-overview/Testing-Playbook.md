---
microservice: '{{REPO_NAME}}'
type: architecture
status: active
tags:
- '#ai/ignore'
- '#service/{{repo_name}}'
- '#type/architecture'
- '#state/active'
---
# Testing Playbook

Guidelines for verifying and QAing **{{REPO_NAME}}**.

## Local Development
*How to run the tests locally.*
```bash
# Example
make test
```

## Sandbox Integration
*Where are the BDD behavior specs located? How is this service tested in the `sandbox-testing` environment?*
- **Specs**: Point to `02-Business-BDD/02-Behavior-Specs/{{REPO_NAME}}`
- **Sandbox**: Details on the docker-compose setup needed to run this integration.

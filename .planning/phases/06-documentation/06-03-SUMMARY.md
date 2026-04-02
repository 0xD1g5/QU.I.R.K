---
phase: 06-documentation
plan: 03
subsystem: documentation
tags: [aws, azure, docker, syft, semgrep, connectors, iam, rbac, boto3]

requires:
  - phase: 06-documentation/06-01
    provides: docs/ directory structure and entry-point guides
  - phase: 06-documentation/06-02
    provides: configuration reference

provides:
  - docs/connectors/aws.md with least-privilege IAM policy and boto3 credential chain
  - docs/connectors/azure.md with RBAC role assignment and DefaultAzureCredential chain
  - docs/connectors/docker.md with Syft install, crypto lib allowlist, and container_targets config
  - docs/connectors/git.md with semgrep install, p/cryptography ruleset, and source_targets config

affects: [06-documentation, phase-7-packaging, consultant-onboarding]

tech-stack:
  added: []
  patterns:
    - "Connector docs lead with credential/permission block before narrative (D-11/D-12)"
    - "IAM permissions and RBAC roles derived verbatim from connector source code API calls"
    - "Graceful degradation documented per connector — all scanners continue when one dependency is absent"

key-files:
  created:
    - docs/connectors/aws.md
    - docs/connectors/azure.md
    - docs/connectors/docker.md
    - docs/connectors/git.md
  modified: []

key-decisions:
  - "IAM policy JSON derived from exact boto3 calls in quirk/scanner/aws_connector.py — 7 actions across 4 services (ACM, KMS, CloudFront, ELBv2)"
  - "Azure RBAC uses Reader + Key Vault Reader built-in roles at subscription scope — no custom role definition needed"
  - "Docker guide documents CRYPTO_LIB_ALLOWLIST exhaustively — consultants know exactly which packages trigger findings"
  - "Git guide documents p/cryptography semgrep ruleset with anti-pattern table (WEAK_ALGORITHM, HARDCODED_KEY, WEAK_RANDOM, DEPRECATED_PROTOCOL)"

patterns-established:
  - "Connector docs: credential/permission block first, then prerequisites, then config.yaml snippet, then what gets scanned"
  - "Troubleshooting table at end of each guide — symptom, likely cause, fix"

requirements-completed: [DOC-04]

duration: 12min
completed: 2026-03-31
---

# Phase 06 Plan 03: Connector Setup Guides Summary

**Four copy-paste-ready connector guides covering AWS IAM policy (7 actions), Azure RBAC roles, Syft-based container scanning, and semgrep p/cryptography source scanning — all permissions derived from the actual connector source code.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-31T22:31:46Z
- **Completed:** 2026-03-31T22:43:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `docs/connectors/aws.md`: complete least-privilege IAM policy with 7 permissions (ACM, KMS, CloudFront, ELBv2), boto3 credential chain, config.yaml snippet, KMS key spec table, troubleshooting table
- `docs/connectors/azure.md`: RBAC role assignment table, DefaultAzureCredential chain, env var list (AZURE_CLIENT_ID/TENANT_ID/CLIENT_SECRET), config.yaml snippet with azure_keyvault_urls, App Gateway optional dependency documented
- `docs/connectors/docker.md`: Syft install paths (brew/pip/curl), Docker socket access, container_targets config, full CRYPTO_LIB_ALLOWLIST table, private registry auth, graceful degradation
- `docs/connectors/git.md`: semgrep install, source_targets with local/remote/Gitea examples, p/cryptography anti-pattern table, SSH/HTTP auth, .netrc alternative for embedded tokens

## Task Commits

1. **Task 1: Write docs/connectors/aws.md and docs/connectors/azure.md** - `f1b1a7b` (feat)
2. **Task 2: Write docs/connectors/docker.md and docs/connectors/git.md** - `8ea6320` (feat)

**Plan metadata:** (see final commit hash below)

## Files Created/Modified

- `docs/connectors/aws.md` - AWS connector with least-privilege IAM policy JSON, boto3 credential chain, config.yaml snippet
- `docs/connectors/azure.md` - Azure connector with RBAC role assignment, DefaultAzureCredential, env var list, config.yaml snippet
- `docs/connectors/docker.md` - Docker/container connector with Syft install, CRYPTO_LIB_ALLOWLIST, container_targets config
- `docs/connectors/git.md` - Git/source connector with semgrep install, p/cryptography ruleset table, source_targets config

## Decisions Made

- AWS IAM policy derived by reading each `session.client(...).get_paginator(...)` and `describe_*` call in `aws_connector.py` — 7 permissions, no wildcards, no write access
- Azure uses built-in `Reader` + `Key Vault Reader` roles — no custom role definition JSON needed (simpler and more maintainable than a custom role)
- Docker guide tables the full `CRYPTO_LIB_ALLOWLIST` frozenset from `container_scanner.py` so consultants know exactly which packages appear in reports
- Git guide tables the four anti-pattern categories from semgrep `p/cryptography` with example code snippets for immediate recognition

## Deviations from Plan

None — plan executed exactly as written. All content derived from connector source files as specified.

## Issues Encountered

None. The worktree branch (`worktree-agent-a375e6de`) lacked the `docs/` directory (older branch), so `docs/connectors/` was created fresh. The connector source files were read from the main repo at `quirk/scanner/aws_connector.py`, `azure_connector.py`, `container_scanner.py`, and `source_scanner.py` (not `quirk/connectors/` as the plan specified — the connectors live in `quirk/scanner/`).

## User Setup Required

None — no external service configuration required for documentation creation.

## Next Phase Readiness

- All four connector guides are complete and copy-paste-ready
- Remaining 06-documentation plans: chaos-lab guide (06-04), report interpretation (06-05), CBOM guide (06-06)
- No blockers

---
*Phase: 06-documentation*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FOUND: docs/connectors/aws.md
- FOUND: docs/connectors/azure.md
- FOUND: docs/connectors/docker.md
- FOUND: docs/connectors/git.md
- FOUND: .planning/phases/06-documentation/06-03-SUMMARY.md
- FOUND commit: f1b1a7b (Task 1)
- FOUND commit: 8ea6320 (Task 2)
- FOUND commit: 0e057b7 (metadata)

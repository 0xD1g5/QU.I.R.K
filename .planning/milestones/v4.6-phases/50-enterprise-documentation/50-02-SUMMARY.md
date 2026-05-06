---
phase: 50-enterprise-documentation
plan: 02
subsystem: docs
tags: [docs, phase-50, architecture, enterprise]
requires: [50-01]
provides: ["docs/architecture.md", "DOCS-01 (architecture half)"]
affects: ["tests/test_phase50_docs_presence.py (architecture-half now GREEN)"]
tech-stack:
  added: []
  patterns: [enterprise-architect-doc, mermaid-diagrams, repo-doc-no-frontmatter]
key-files:
  created:
    - docs/architecture.md
  modified: []
decisions:
  - "Repo-doc convention: no YAML frontmatter at top of docs/architecture.md (frontmatter added at vault sync time in 50-04)"
  - "Three mermaid diagrams (system overview, data flow sequence, dashboard two-tier) — minimum required by plan"
  - "Connector credential matrix flags Postgres/MySQL plaintext config as the only QUIRK-owned secret store; all others delegate to OS / cloud identity"
metrics:
  duration_minutes: 6
  tasks_completed: 2
  completed_date: 2026-05-05
---

# Phase 50 Plan 02: Enterprise Architecture Reference Summary

Authored `docs/architecture.md` as a single-doc enterprise-architect reference covering scanner-phase model, scan→DB→CBOM→reports data flow, SQLite schema, dashboard two-tier architecture, CBOM pipeline, trust boundaries, and connector credential-storage matrix — closing the architecture half of the 50-01 RED gate.

## Final Section List

1. System Overview (with system-overview mermaid)
2. Trust Boundaries and Network Surface (includes Connector Credential Storage Matrix)
3. Scanner Phase Model (12 scanners + discovery, phase-wrapper invariants)
4. Data Flow: Scan → DB → CBOM → Reports (with sequence-diagram mermaid)
5. SQLite Schema (single `crypto_endpoints` table + idempotent additive migrations)
6. Dashboard Architecture (with two-tier mermaid)
7. CBOM Pipeline (CycloneDX 1.6 + FIPS 203/204/205 PQC naming)
8. Reports Pipeline (single Jinja template + Playwright PDF + versioned constants)
9. Subcommand Routing (CLI) — explains intra-`main()` dispatch for `compliance` / `serve`
10. Versioning and Versioned Constants (PLATFORM_VERSION, SCHEMA_VERSION, INTELLIGENCE_VERSION)
11. References (cross-links to cbom-guide, intelligence-schema, timeout-retry-audit, operators-guide, quirk-overview, cbom-classifier-coverage)

## Mermaid Diagrams

| # | Section | Type | What it shows |
|---|---------|------|---------------|
| 1 | §1 System Overview | flowchart LR | Operator → CLI → discovery / wizard / 12 scanners → SQLite → risk_engine → CBOM + intelligence → reports; dashboard reads SQLite read-only |
| 2 | §4 Data Flow | sequenceDiagram | CLI → discovery → scanner → DB → risk_engine (`_build_finding` + eager `_normalize_for_compliance`) → CBOM builder → reports writer → outputs |
| 3 | §6 Dashboard | flowchart TB | React 19 + Vite 8 SPA (9 routes) → FastAPI routes (health/scan/trends/pdf) → Pydantic DTOs → quirk.db |

## Connector Credential Storage Matrix Rows

| Connector | Source | QUIRK persists? |
|-----------|--------|-----------------|
| AWS | `~/.aws/credentials` (boto3 default chain) | No |
| Azure | DefaultAzureCredential chain | No |
| GCP | Application Default Credentials | No |
| Vault | `VAULT_TOKEN` env or `connectors.vault_token` | No (read once) |
| Kerberos | krb5 ticket cache + impacket fallback | No |
| Database (PG/MySQL) | `connectors.pg_scanner_password` / `mysql_scanner_password` plaintext config ⚠ | No |
| Kubernetes | kubeconfig (`~/.kube/config`) | No |
| Docker | local socket | No |
| Git (semgrep) | local clone + user `git` config | No |

The matrix flags the database connector as the only QUIRK-owned plaintext credential store and recommends a least-privilege read-only DB user paired with config-as-secret handling.

## Grep Gate Results

| Forbidden term / path | Result |
|-----------------------|--------|
| `Kyber` | absent ✓ |
| `Dilithium` | absent ✓ |
| `when standards are adopted` | absent ✓ |
| `quirk/scanners/` (plural) | absent ✓ |

## Required Substring Gate (50-01)

| Needle | Result |
|--------|--------|
| `data flow` | present ✓ |
| `trust boundar` | present ✓ |
| ` ```mermaid ` | 3 fenced blocks ✓ |
| `credential` | present ✓ |

`pytest tests/test_phase50_docs_presence.py::test_required_sections_present` advances past the architecture.md substring set and only fails on `docs/operators-guide.md` (Plan 50-03's responsibility) — the architecture half of the gate is GREEN.

## Deviations from Plan

### Adjustment to Task 2 (atomic-commit step)

**Found during:** Task 2 setup (git status check)
**Issue:** The plan's Task 2 W6 atomicity step instructs committing `tests/test_phase50_docs_presence.py` together with `docs/architecture.md`. However, the parallel-execution context note from the orchestrator stated the test file is already committed at HEAD (commit `3c5433d`, `test(50-01): RED gate test for Phase 50 docs presence/structure`), and `git log -1 -- tests/test_phase50_docs_presence.py` confirmed this. Re-committing the file would either be a no-op (no diff) or attempt to re-create an already-committed artifact.
**Resolution:** Followed the orchestrator's explicit override ("do NOT re-create it") and committed `docs/architecture.md` alone. The W6 atomicity invariant — "no RED CI between waves on QUIRK-v4" — is preserved by 50-01 having already landed the test file in its own commit on the integration branch; the worktree's main-branch base already has both artifacts when this commit lands.
**Files modified:** `docs/architecture.md` (new); test file untouched.
**Commit:** `2386697`

## Commits

| Plan | Commit | Message |
|------|--------|---------|
| 50-02 | `2386697` | `docs(50-02): add architecture.md (DOCS-01 enterprise architecture reference)` |

## Self-Check: PASSED

- [x] `docs/architecture.md` exists at repo root (FOUND)
- [x] Commit `2386697` exists in `git log` (FOUND)
- [x] Three mermaid blocks present (`grep -c` returned 3)
- [x] Four 50-01 architecture substrings present
- [x] Zero forbidden PQC terms or `quirk/scanners/` paths
- [x] `test_required_sections_present` advances past architecture.md substrings (only operators-guide.md remains RED, owned by Plan 50-03)

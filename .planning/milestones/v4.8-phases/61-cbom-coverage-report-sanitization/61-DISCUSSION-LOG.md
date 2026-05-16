# Phase 61: CBOM Coverage + Report Sanitization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 61-cbom-coverage-report-sanitization
**Areas discussed:** Zero-algo data strategy, VAULT Pass-1/2/3 design, Markdown sanitizer scope, CBOM coverage test design

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Zero-algo data strategy | For CONTAINER, DATABASE, S3 — what algorithm value to register when only indirect data is available | ✓ |
| VAULT Pass-1/2/3 design | VAULT has cert_pubkey_alg set but falls through to TLS else; needs own Pass-1 branch + consistent Pass-2/3 | ✓ |
| Markdown sanitizer scope | Shared utility vs inline; technical.py vs executive.py coverage | ✓ |
| CBOM coverage test design | Pure Python synthetic fixtures vs chaos-lab integration | ✓ |

**User's choice:** "Please move forward with recommended actions" — Claude selected recommended approach for all areas.

---

## Zero-algo data strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Parse service_detail | Extract algo from string patterns (MySQL/AES256-SHA-ok → AES256-SHA, S3/sse-s3 → AES-256) | ✓ |
| Populate scanner fields | Update db_connector.py / aws_connector.py to set cert_pubkey_alg | |
| Synthetic sentinel | Emit "UNKNOWN" or "PLAINTEXT" for protocols with no crypto data | |

**User's choice:** Deferred to Claude (recommended actions).
**Notes:** Claude chose parse-service_detail for MYSQL (cipher is in the string), AES-256 mapping for S3 (all encrypted S3 variants use AES-256), and cipher_suite directly for CONTAINER (library name as algo name per CycloneDX 1.6 spec). Plaintext broker protocols (KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN) legitimately skip — coverage test uses KAFKA-TLS instead.

---

## VAULT Pass-1/2/3 design

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated Pass-1 branch only | Add VAULT elif reading cert_pubkey_alg; keep Pass-2/3 skipped via DAR_SKIP_PROTOCOLS | ✓ |
| Full Pass-1/2/3 VAULT branches | Add vault-specific protocol component in Pass-3 | |
| Remove from DAR_SKIP_PROTOCOLS | Allow TLS else branch to handle VAULT | |

**User's choice:** Deferred to Claude (recommended actions).
**Notes:** Dedicated Pass-1 branch (3-line change mirroring SAML/KERBEROS pattern) is sufficient for SC-2. Pass-2/3 stay skipped — VAULT transit keys are not X.509 certs. Golden snapshot compares sorted (name, type) component list serialized to JSON, not full CycloneDX output (UUID instability avoided).

---

## Markdown sanitizer scope

| Option | Description | Selected |
|--------|-------------|----------|
| Shared quirk/reports/_md_escape.py | Single md_cell() utility imported by both report modules | ✓ |
| Inline in technical.py only | Helper function local to technical.py | |
| Apply to executive.py too | Full coverage of all markdown outputs | |

**User's choice:** Deferred to Claude (recommended actions).
**Notes:** Shared private module `_md_escape.py` with `md_cell()` — testable independently, importable from future report modules. executive.py deferred (prose bullets, not table rows — lower risk). Apply to ALL table cell fields in technical.py including Service Inventory, TLS Capabilities, TLS Blockers, and Findings.

---

## CBOM coverage test design

| Option | Description | Selected |
|--------|-------------|----------|
| Pure Python synthetic fixtures | MagicMock or real ORM CryptoEndpoint objects, no Docker | ✓ |
| Chaos-lab integration test | Requires docker-compose profiles running | |
| Mixed (unit + smoke) | Synthetic for CI, chaos-lab smoke optional | |

**User's choice:** Deferred to Claude (recommended actions).
**Notes:** Pure Python parametrized test (`tests/test_cbom_coverage.py`) with named `pytest.param` IDs per protocol family. 14 families covered. No new dependencies. VAULT golden snapshot uses `json.dumps()` serialization of sorted component (name, type) list.

---

## Claude's Discretion

All four gray areas were delegated to Claude with "Please move forward with recommended actions." Decisions captured in CONTEXT.md D-01 through D-14.

## Deferred Ideas

- executive.py markdown injection — deferred to v4.9 tech-debt (prose bullets, lower risk)
- SOURCE DES→3DES alias map fix (CR-03) — separate audit item, no assigned phase
- WR-01/WR-02 PDF render error handling — PDF-layer issues, out of scope
- CLOUD_SQL/KUBERNETES Pass-1 branches — no reliable algo field in scan data today

---
phase: 50-enterprise-documentation
plan: 03
subsystem: docs
tags: [docs, operators-guide, compliance-runbook, phase-50]
requires: [50-01]
provides: [DOCS-02, DOCS-04]
affects: [docs/operators-guide.md]
tech-stack:
  added: []
  patterns: [hybrid-narrative-and-links, compliance-runbook]
key-files:
  created: [docs/operators-guide.md]
  modified: []
decisions:
  - "Hybrid structure: short canonical inline sections + 'See also' links to existing docs (D-01) — avoids duplication"
  - "Excluded `[identity]` from `[all]` recommendation per Phase 45-01 D-07 (impacket downgrades cryptography)"
  - "Compliance runbook cites 5 CI gate test files + STALENESS_THRESHOLD_DAYS=365 + 4 monitor URLs (incl. HHS landing + ECFR canonical)"
metrics:
  duration: ~10 min
  completed: 2026-05-05
---

# Phase 50 Plan 03: Operator's Guide Summary

**One-liner:** Authored the canonical `docs/operators-guide.md` — install/configure/scan/troubleshoot walkthrough plus per-scanner reference and compliance map maintenance runbook with `quirk compliance status`, `STALENESS_THRESHOLD_DAYS`, and quarterly review cadence.

## What Was Built

Single new file: `docs/operators-guide.md` (342 lines, no frontmatter, 7 top-level sections).

### Final section list

| § | Title | Purpose |
|---|-------|---------|
| 1 | Install | `pip install quirk[all]` guidance + `[identity]` carve-out |
| 2 | Configure | `quirk init` subsection (scope addition #2) + extras matrix |
| 3 | Scan | Wizard + non-interactive entry points; output artifact list |
| 4 | Validation / Smoke Test | Chaos-lab pointer |
| 5 | Troubleshooting | 4 areas: scan failures, db/output, dashboard, connector gotchas |
| 6 | Per-Scanner Reference | Compact table (20 rows) + 10 protocol-scanner H4 subsections |
| 7 | Compliance Map Maintenance | Quarterly checklist + 4 monitor URLs + 5 CI gates + worked PCI-DSS upgrade |

### Per-scanner H4 subsection coverage (§6.2)

All 10 protocol scanners that lack a dedicated connector doc have an inline H4:

1. `#### TLS scanner`
2. `#### SSH scanner`
3. `#### JWT/API scanner`
4. `#### Container scanner`
5. `#### Source-code scanner`
6. `#### DNSSEC scanner`
7. `#### Kerberos scanner`
8. `#### SAML scanner`
9. `#### Email scanner`
10. `#### Broker scanner`

Cloud / infra connectors (AWS, Azure, GCP, Database, Object storage, Kubernetes, Vault, Docker, Git) are listed in the §6.1 reference table; the four with dedicated docs (`aws.md`, `azure.md`, `docker.md`, `git.md`) link out per the hybrid structure decision.

### §7.2 Source URLs (verbatim)

- `https://www.pcisecuritystandards.org/document_library/` — PCI Security Standards Council
- `https://www.hhs.gov/hipaa/for-professionals/index.html` — HHS HIPAA landing
- `https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164` — ECFR canonical 45 CFR §164
- `https://csrc.nist.gov/publications/fips` — NIST CSRC FIPS publications

## Verification

### Required substrings (all PRESENT in `docs/operators-guide.md`, case-insensitive)

| Substring | Status |
|-----------|--------|
| `troubleshoot` | OK |
| `compliance map maintenance` | OK |
| `quirk compliance status` | OK |
| `staleness_threshold_days` | OK |
| `tests/test_compliance_freshness.py` | OK |
| `https://www.pcisecuritystandards.org` | OK |
| `https://www.ecfr.gov` | OK |
| `hhs.gov` | OK |
| `https://csrc.nist.gov` | OK |
| `quirk init` | OK |

### Forbidden-term scan (all ZERO hits)

- `Kyber` — 0
- `Dilithium` — 0
- `quirk/scanners/` (wrong package path) — 0
- `when standards are adopted` — 0

### `pytest tests/test_phase50_docs_presence.py`

- `test_required_sections_present` for **`docs/operators-guide.md`** — all 10 required substrings present (verified by direct grep). The test will go GREEN for this doc once Plan 50-02 lands `docs/architecture.md` in the same wave; Plan 50-03's contribution to the gate is fully satisfied.
- `test_required_docs_resolve` — fails on `docs/architecture.md` (out of this plan's scope; owned by 50-02). Expected during parallel wave 2 execution.

## Deviations from Plan

None — plan executed exactly as written. The skeleton/templates from the plan were used verbatim with the inline content fleshed out as instructed.

## Commits

- `860b5c3` — `docs(phase-50): add operators-guide.md (DOCS-02, DOCS-04)`

## Self-Check: PASSED

- File exists: `docs/operators-guide.md` — FOUND
- Commit exists: `860b5c3` — FOUND

# Phase 52: Compliance Uplift & Health Check - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 52-compliance-uplift-health-check
**Areas discussed:** FIPS 140-3 `certified` tier, quirk doctor design, SOC2/ISO mapping breadth

---

## FIPS 140-3 `certified` Tier

| Option | Description | Selected |
|--------|-------------|----------|
| `certified` = never in v4.7 | All components get `approved`/`non-approved` from algorithm classifier; `certified` reserved for future CMVP attestation phase | ✓ |
| `certified` = static allowlist | A small hardcoded set of well-known CMVP-approved algorithms gets `certified` by default | |
| `certified` = from config/attestation flag | Operator declares CMVP-validated endpoints in config.yaml | |

**User's choice:** `certified` never emitted in v4.7
**Notes:** QUIRK scans algorithm names, not hardware modules — `certified` is a different layer than what the classifier knows.

---

### `approved` vs `non-approved` derivation

| Option | Description | Selected |
|--------|-------------|----------|
| nist_level >= 1 → `approved`, nist_level == 0 → `non-approved`, None → `non-approved` | Reuses existing classifier taxonomy | ✓ |
| Separate FIPS allowlist independent of nist_level | More granular but duplicates classifier logic | |

**User's choice:** Map directly from existing `nist_level` field.

---

### Property attachment point

| Option | Description | Selected |
|--------|-------------|----------|
| Inside `_make_algorithm_component()` | Single touch point; nist_level already in scope | ✓ |
| Post-build pass in `build_cbom()` | Iterate registry after Pass-1 and attach properties | |

**User's choice:** Attach inside factory function.

---

## quirk doctor Design

### QRAMM check handling

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful skip if QRAMM not installed | Shows `[!]` informational, never exits 1 | ✓ |
| QRAMM check always present but always `[!]` | Runs unconditionally, always warns in fresh install | |
| Omit QRAMM check from Phase 52 | Add in Phase 55 when model_meta.py is defined | |

**User's choice:** Graceful skip — informational `[!]` only if Phase 51 not present.

---

### Output format

| Option | Description | Selected |
|--------|-------------|----------|
| Rich text only, no --format flag | Exit code is machine-readable signal; YAGNI | ✓ |
| Add --format json | Consistent with `quirk compliance status`, useful for scripting | |

**User's choice:** Rich text only.

---

### Compliance freshness check

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `status_report()` staleness logic | No duplicate logic; consistent with `quirk compliance status` | ✓ |
| Independent check in doctor module | Self-contained but duplicates staleness gate | |

**User's choice:** Delegate to existing `status_report()` logic.

---

## SOC2/ISO Mapping Breadth

### Coverage scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full parity with existing PCI/HIPAA coverage | Every finding with PCI or HIPAA entries gets SOC2/ISO mappings | ✓ |
| TLS/crypto core only | Map only TLS/cert/key-size findings | |
| You decide | Claude picks based on PCI/HIPAA coverage | |

**User's choice:** Full parity — all existing COMPLIANCE_MAP keys extended.

---

### SOC2 control assignment

| Option | Description | Selected |
|--------|-------------|----------|
| CC6.6 + CC6.7 for transport findings, CC6.6 for key/cert findings | Per-domain nuance; matches SOC2 assessor usage | ✓ |
| CC6.7 only (encryption-only) | Simpler but misses SSH/key management scope | |

**User's choice:** CC6.6 + CC6.7 dual-mapping for transport findings; CC6.6 for auth/key/cert findings.

---

### ISO 27001:2022 control assignment

| Option | Description | Selected |
|--------|-------------|----------|
| 8.24 (cryptography) + 8.26 (app security) primary; 8.28 for code findings | Covers all scanner domains with per-domain precision | ✓ |
| 8.24 only (single crypto control) | Simple but loses per-domain nuance | |
| You decide per finding type | Claude maps each finding category to best 8.x clause | |

**User's choice:** 8.24 + 8.26 primary; 8.28 scoped to source-code scanner findings.

---

## Claude's Discretion

- Specific CC6.x control assignments per finding category (Claude will apply the D-06 rule: CC6.7 for transport, CC6.6 for auth/key/cert, both for dual-domain findings)
- Specific 8.x clause per finding category (Claude applies D-08: 8.24 for algorithm/key-size, 8.26 for TLS/protocol, 8.28 for source-code)
- `_fips_status()` helper implementation details in `builder.py`
- SOC2 `source_url` pointing to AICPA Trust Services Criteria publication
- `quirk doctor` Rich Table layout (two-column: Check + Status)

## Deferred Ideas

- `certified` CMVP tier — future phase with CMVP attestation support (config flag or API lookup)
- `quirk doctor --format json` — not needed now; revisit if CI health gate is requested
- SOC2 CC8.x / CC9.x availability/monitoring controls — out of scope for crypto findings

# Phase 80: Windows AD CS Scanner - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. enumerates Active Directory Certificate Services CA configurations and
certificate templates via authenticated LDAP — detecting weak CA signing algorithms,
dangerously permissive template configurations (ESC1–ESC8 observable crypto properties),
and CA reachability — with results in the Identity tab, CBOM, and reports.

**Strictly read-only**: no certificate enrollment, template creation, write operations,
or active exploitation simulation under any code path. ADCS-09 invariant.

Wave A — parallel with Phases 78, 79, 81, 82.

</domain>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 80 section: 5 success criteria
- `.planning/REQUIREMENTS.md` — ADCS-01 … ADCS-09 verbatim
- `.planning/research/SUMMARY.md` — v4.10 research (no certipy-ad rationale)
- `.planning/phases/79-smime-ldap-discovery-scanner/79-CONTEXT.md` — sibling scanner pattern; many decisions carry over
- `quirk/scanner/smime_scanner.py` — JUST landed in Phase 79; cleanest analog for LDAP-based identity scanner
- `quirk/scanner/kerberos_scanner.py` — older ldap3 pattern
- `quirk/util/weak_crypto.py` — shared classifier
- `quirk/intelligence/scoring.py` — SCORE_WEIGHTS (new entries; Phase 83 owns invariant bump)
- `quirk/intelligence/evidence.py` — counter pattern
- `quirk/cbom/builder.py` — Pass-1 emission, lines 528 + 612 inline skip-list tuples
- `quirk/db.py:76-80` — `_IDENTITY_COLUMNS` tuple (additive column)
- `tests/test_scan_error_gate.py` — Phase 59 AST gate model
- `quantum-chaos-enterprise-lab/smime/` — sibling chaos lab profile (full template for adcs/)
- `pyproject.toml` — `[identity]` extras (existing); new `[adcs]` extras group (Phase 80 adds)

</canonical_refs>

<decisions>
## Implementation Decisions

### Area 1 — ESC scope strategy
- **All 8 best-effort:** Implement ESC1–ESC8 checks expressible from LDAP attribute analysis alone (msPKI-Certificate-Name-Flag, msPKI-Enrollment-Flag, pKIExtendedKeyUsage, etc. per ADCS-02). ESC checks that fundamentally need CSR-based testing get a documented `ADCS-COVERAGE-GAP` finding rather than a misconfig finding.
- ESC9–ESC16 explicitly out of scope (REQUIREMENTS).

### Area 2 — LDAP helper
- **Duplicate (do not extract shared helper):** Phase 80's `quirk/scanner/adcs_scanner.py` carries its own bind-and-search scaffolding, mirroring `kerberos_scanner.py`/`saml_scanner.py`/`smime_scanner.py` independence. ~30 lines of acceptable duplication.

### Area 3 — Chaos lab strategy
- **Separate `adcs` profile** on port `38910` using `bitnamilegacy/openldap:2.6.10-debian-12-r4` (parity with smime profile).
- msPKI-* schema loaded via separate LDIF schema file.
- Three deterministic test templates: one ESC1-category misconfig, one ESC4-category misconfig, one safe baseline.
- One-shot `ldapadd -c` seed container for idempotency.

### Area 4 — AST gate scope
- **`certipy-ad` + enrollment APIs** forbidden in `quirk/scanner/adcs_scanner.py`:
  - `certipy_ad` (locked by v4.10-D-02 — pinned cryptography incompat)
  - `cryptography.x509.CertificateSigningRequestBuilder` (no CSR construction)
  - Any impacket modify/add LDAP operations
- AST gate clones SMIME-08 / Phase 59 `test_scan_error_gate.py` shape.

### Cross-cutting (carried from Phase 79 + locked by milestone memory)
- **NO `certipy-ad` dependency** (v4.10-D-02 — would re-pin cryptography~=42.0.8 and break the TLS scanner).
- LDAP enumeration only — authenticated LDAP to AD `CN=Configuration,...` partition.
- `protocol="ADCS"` uppercase on IdentityFinding.
- **DO NOT edit `tests/test_score_weights_invariant.py`** — Phase 83 (CLEAN-01) owns the consolidated bump. Phase 80 adds ~4 new SCORE_WEIGHTS entries; SUM will be 267.0 (after Phase 79) → 275.0 (after Phase 80). Invariant test stays red until Phase 83.
- Singular `quirk/scanner/adcs_scanner.py` path (NOT plural).
- `IDENTITY_SKIP_PROTOCOLS` is two inline tuples at `quirk/cbom/builder.py:528` + `:611`; append `"ADCS"` to both.
- `lab.sh` requires NO edits (runtime profile derivation).
- `_IDENTITY_COLUMNS` is the ORM target — append `adcs_scan_json`.
- `[adcs]` is a new extras group in `pyproject.toml` per ADCS-07 — separate from `[identity]`; CI matrix asserts `cryptography>=44.0` across `[all]` + `[adcs]` combinations.

### Module header invariant (ADCS-09)
The module header of `quirk/scanner/adcs_scanner.py` MUST contain a documented invariant:
"This scanner performs read-only LDAP enumeration of AD CS configuration. No
certificate enrollment, no template creation, no CSR generation, no write
operations under any code path."

### Scoring weights (4 new entries per REQUIREMENTS ADCS-04)
- `identity_adcs_weak_template_count` (ESC misconfig templates)
- `identity_adcs_misconfig_count` (general permissive flags)
- `identity_adcs_weak_signing_count` (CA signing algorithm weakness)
- `identity_adcs_coverage_gap_count` (ESC checks deferred per Area 1 above) — NEW, not in REQUIREMENTS but follows from the "all 8 best-effort" decision
- All four at weight `2.0` under `identity_trust` subscore (matches Phase 79 SMIME pattern).
- **Phase 83 will reconcile**: Phase 79 added +3 weights (+6.0), Phase 80 adds +4 (+8.0). Total SUM after both phases: 261.0 + 6.0 + 8.0 = 275.0.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/scanner/smime_scanner.py` — JUST landed in Phase 79; cleanest LDAP-scanner template
- `quirk/util/weak_crypto.py` — shared signing/key-size classifier
- `quirk/cbom/builder.py` — Pass-1 emit + inline tuple skip-lists (just got `"SMIME"` added; add `"ADCS"`)
- `_IDENTITY_COLUMNS` tuple in `quirk/db.py:76-80` (just got `smime_scan_json`; add `adcs_scan_json`)

### Established Patterns
- One scanner per protocol, no shared helpers
- New ORM column = single tuple append, no breaking migration
- Two inline tuple appends in `cbom/builder.py` for skip-list
- Chaos lab profile = (compose service + seed container + ports + expected_results section + README row)
- AST gate = clone Phase 59 model; FORBIDDEN_ROOTS set

### Integration Points
- `quirk/scanner/adcs_scanner.py` — NEW (singular path)
- `quirk/db.py:76-80` — append `adcs_scan_json` to `_IDENTITY_COLUMNS`
- `quirk/intelligence/scoring.py` — 4 SCORE_WEIGHTS entries
- `quirk/intelligence/evidence.py` — 4 counter accessors
- `quirk/cbom/builder.py:528` + `:611` — append `"ADCS"` to inline skip tuples; Pass-1 emit branch
- `run_scan.py` — `_run_adcs_phase` after `_run_smime_phase` (resume-aware, data_at_rest stage)
- `pyproject.toml` — new `[adcs]` extras group; ldap3 already in `[identity]`
- `quantum-chaos-enterprise-lab/docker-compose.yml` — new `adcs` profile (bitnamilegacy/openldap:2.6.10-debian-12-r4, port 38910)
- `quantum-chaos-enterprise-lab/adcs/` — new dir: openldap config, ldif (schema + templates), README
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — new `adcs` oracle section
- `quantum-chaos-enterprise-lab/README.md` — Profile Summary row
- `tests/test_adcs_scanner.py` — unit tests
- `tests/test_adcs_no_writes.py` — privacy/safety invariant (ADCS-09: no enrollment, no write LDAP ops)
- `tests/test_adcs_ast_gate.py` — ADCS AST CI gate
- `tests/test_extras_install.py` (or new) — `[adcs]` + `[all]` + `[identity]` extras matrix per ADCS-07

</code_context>

<specifics>
## Specific Ideas

- LDAP search base for CA configurations: `CN=Public Key Services,CN=Services,CN=Configuration,<root-DN>`
- Template enumeration: `CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,<root-DN>`
- msPKI attribute names to check:
  - `msPKI-Certificate-Name-Flag` (ESC1: ENROLLEE_SUPPLIES_SUBJECT)
  - `msPKI-Enrollment-Flag` (ESC2: NO_SECURITY_EXTENSION)
  - `msPKI-Certificate-Application-Policy` / `pKIExtendedKeyUsage` (ESC3: client auth + cert-request agent)
  - Template ACLs / nTSecurityDescriptor (ESC4: vulnerable template ACL — observable but interpretation is heuristic)
- Three lab template fixtures:
  - `BadTemplate-ESC1` — ENROLLEE_SUPPLIES_SUBJECT set + any-EKU
  - `BadTemplate-ESC4` — overly permissive ACL on nTSecurityDescriptor
  - `SafeTemplate` — baseline (msPKI-Enrollment-Flag = 0, no ENROLLEE_SUPPLIES_SUBJECT)
- ADCS-UNREACH coverage gap: when LDAP bind fails with bad credentials or connection refused, emit `IdentityFinding` with `severity="LOW"`, `title="AD CS LDAP enumeration failed"`, `protocol="ADCS"` — NO exception propagation to scan session error log (ADCS-04 success criterion #2).

</specifics>

<deferred>
## Deferred Ideas

- ESC9–ESC16 advanced misconfigurations (out of scope per REQUIREMENTS)
- Active enrollment-based ESC verification (CSR submission) — forbidden by ADCS-09
- CA reachability probe outside of LDAP (e.g., DCOM ICertRequest) — out of scope, no certipy-ad

</deferred>

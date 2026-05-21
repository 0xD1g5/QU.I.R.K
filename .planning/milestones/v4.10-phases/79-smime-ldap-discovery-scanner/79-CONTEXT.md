# Phase 79: S/MIME LDAP Discovery Scanner - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. enumerates S/MIME signing certificates stored in Active Directory
`userCertificate` and `userSMIMECertificate` LDAP attributes — detecting weak
signing algorithms, expired certificates, and sub-2048-bit RSA keys — with findings
surfaced in the Identity tab, CBOM output, and reports. **No mailbox content is
accessed at any point. No IMAP code path is introduced.**

Wave A — parallel with Phases 78, 80, 81, 82.

</domain>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 79 success criteria (5 truths)
- `.planning/REQUIREMENTS.md` — SMIME-01 … SMIME-08 verbatim
- `.planning/research/SUMMARY.md` — v4.10 research synthesis (LDAP-only justification)
- `quirk/scanner/kerberos_scanner.py` — existing ldap3 connection path (SMIME-01 says "reuse")
- `quirk/scanner/saml_scanner.py` — pattern for cert parsing + identity finding emission
- `quirk/util/weak_crypto.py` — shared signing algorithm + key size classifier (SMIME-02 mandates reuse)
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` (new counters land in identity_trust)
- `quirk/cbom/builder.py` — `IDENTITY_SKIP_PROTOCOLS` set for Pass-2/3 skip-list
- `quirk/db.py` — `ScanSession` ORM (add `smime_scan_json` column per SMIME-03)
- `tests/test_audit_ledger_zero_open.py` — CI invariant pattern (for SMIME-08 AST gate)
- `tests/test_score_weights_invariant.py` — invariant test updated by Phase 83 (NOT Phase 79)
- `quantum-chaos-enterprise-lab/lab.sh` — runtime profile registration (smime profile)
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — oracle for smime profile
- `quantum-chaos-enterprise-lab/docker-compose.yml` — chaos lab profile additions

</canonical_refs>

<decisions>
## Implementation Decisions

### Area 1 — LDAP enumeration strategy
- **Search base:** Configurable `smime_search_base` defaulting to the AD root DN derived from the Kerberos realm (e.g., realm `QUIRK.LAB` → `DC=quirk,DC=lab`); consultant-tunable in `cfg.scan` config block.
- **Paging:** `ldap3.SUBTREE` scope with paged results, `paged_size=500`; explicit `extend.standard.paged_search` invocation.
- **Attributes queried:** Both `userCertificate` AND `userSMIMECertificate` binary attributes (SMIME-01 explicit).
- **Multi-cert per user:** Iterate all certs in the multi-valued attribute; classify each independently — AD users routinely carry rotated certs.

### Area 2 — Certificate parsing + classification
- **Expired-cert policy:** MEDIUM finding (with severity bumped to HIGH if also using weak algo or sub-2048 RSA).
- **Cert encoding:** DER first (per RFC 4523), fall back to PEM on parse failure for legacy AD environments.
- **Weak-crypto thresholds:** Reuse `quirk/util/weak_crypto.py` shared classifier — same thresholds as TLS/SSH/SAML/Kerberos (SMIME-02 mandates).
- **PQC classification:** Use existing 50-entry NIST PQC lookup table from CBOM Pass-1 — consistent with other identity scanners.

### Area 3 — Chaos lab `smime` profile design
- **Seeding:** One-shot seed container that runs `ldapadd` with deterministic LDIF fixtures: three test users carrying (a) RSA-1024 SHA-1 signed cert (HIGH), (b) RSA-1024 SHA-256 signed cert (HIGH key only), (c) RSA-2048 SHA-256 signed cert (SAFE). Idempotent — must pass `tests/test_chaos_lab_idempotency.py` (CHAOS-04 contract).
- **OpenLDAP image:** `osixia/openldap:1.5.0` — pinned tag, parity with existing identity profiles; passes CHAOS-05 image-pinning gate.
- **Ports:** `38900` (LDAP) + `38901` (LDAPS) — avoids collision with existing `ldaps` profile (38636) and Samba DC (1389/1636).
- **Cert pre-generation:** Pre-built static fixtures committed to `quantum-chaos-enterprise-lab/smime/certs/`; certs are intentionally weak so no rotation needed.

### Area 4 — CBOM + reporting wiring
- **`protocol=` value:** `"SMIME"` uppercase (matches existing `"KERBEROS"`, `"SAML"` literals).
- **CBOM Pass-1:** Emit `algorithm` component per discovered cert with `crypto-properties.algorithm` (RSA/ECDSA + key size) + NIST PQC classification.
- **Pass-2/3 skip-list:** Add `"SMIME"` to `IDENTITY_SKIP_PROTOCOLS` in `quirk/cbom/builder.py` — prevents spurious TLS-style CertificateProperties components.
- **Scoring weights:** Three new counters in `SCORE_WEIGHTS` — `identity_smime_weak_signing_count`, `identity_smime_expired_count`, `identity_smime_weak_key_count` — each at weight `2.0`, aggregating into the existing `identity_trust` subscore. **NO new top-level subscore.**
- **`SCORE_WEIGHTS` invariant test:** Phase 83 owns the invariant-test bump (CLEAN-01 success criterion #1 — "updated exactly once after both scanners landed"). Phase 79 must NOT touch `tests/test_score_weights_invariant.py`.

### Cross-cutting (locked by milestone memory)
- **No IMAP path:** SMIME-08 AST CI gate must exit non-zero if any IMAP envelope-field import (`imaplib`, `email.message.Message`, `email.header.Header`, etc.) appears in `quirk/scanner/smime_scanner.py`. Preventative for future drift.
- **No mailbox content** anywhere — privacy invariant.
- **Path drift correction:** Use `quirk/scanner/smime_scanner.py` (singular) — REQUIREMENTS.md says `quirk/scanners/` but the codebase uses singular `quirk/scanner/` (kerberos_scanner.py, saml_scanner.py both live there).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/scanner/kerberos_scanner.py` — ldap3 connection establishment via `[identity]` extras path
- `quirk/scanner/saml_scanner.py` — X.509 cert parsing via `cryptography.x509.load_der_x509_certificate`; finding emission pattern
- `quirk/util/weak_crypto.py` — shared signing/key-size classifier
- `quirk/cbom/builder.py::IDENTITY_SKIP_PROTOCOLS` — Pass-2/3 skip-list (just needs `"SMIME"` appended)
- `quirk/intelligence/scoring.py::SCORE_WEIGHTS` — three new entries land here

### Established Patterns
- Singular `quirk/scanner/` directory
- Each scanner exports a single `scan_<protocol>(target, cfg, session)` callable
- IdentityFinding emission via `protocol="..."` literal — React tab picks up automatically
- Chaos lab profile = (compose service block + seed container + ports + expected_results section + lab.sh runtime detection)
- Idempotent seeding contract (test_chaos_lab_idempotency.py)

### Integration Points
- `quirk/scanner/smime_scanner.py` — NEW file (singular path)
- `quirk/db.py` — `ScanSession` model: add `smime_scan_json = Column(Text, nullable=True)` (additive only)
- `quirk/intelligence/scoring.py` — three SCORE_WEIGHTS entries
- `quirk/intelligence/evidence.py` — three new counter accessors
- `quirk/cbom/builder.py` — append `"SMIME"` to `IDENTITY_SKIP_PROTOCOLS`
- `quirk/dashboard/api/scan.py` — IdentityFinding pickup (no change needed — protocol-agnostic)
- `pyproject.toml` — `[identity]` extras already include `ldap3` from Phase 25; no new deps needed
- `quantum-chaos-enterprise-lab/docker-compose.yml` — new `smime` profile
- `quantum-chaos-enterprise-lab/smime/` — new directory: openldap-config, certs/, ldif/
- `quantum-chaos-enterprise-lab/lab.sh` — `_derive_all_profiles()` reads compose at runtime; no script edit needed if profile is declared correctly
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — new `smime` oracle section
- `tests/test_smime_scanner.py` — unit tests
- `tests/test_smime_no_envelope_leak.py` — SMIME-04 IMAP-envelope absence test
- `tests/test_smime_ast_gate.py` (or extend existing audit module) — SMIME-08 AST CI gate

</code_context>

<specifics>
## Specific Ideas

- LDIF fixtures in `quantum-chaos-enterprise-lab/smime/ldif/users.ldif`:
  - `uid=alice` with `userSMIMECertificate` = RSA-1024 SHA-1 cert (HIGH finding expected)
  - `uid=bob` with `userSMIMECertificate` = RSA-1024 SHA-256 cert (HIGH finding for key size)
  - `uid=carol` with `userSMIMECertificate` = RSA-2048 SHA-256 cert (SAFE — no finding)
- Pre-build certs with `openssl` and commit DER bytes under `chaos-lab/smime/certs/` for reproducibility.
- SMIME-04 test (`test_smime_no_envelope_leak.py`): construct an IMAP-style mock target object (with To/From/Subject fields), pass it to the scanner, assert `smime_scan_json` output and finding text contain none of those field names.
- SMIME-08 AST gate: walks `quirk/scanner/smime_scanner.py` via `ast.parse`, looks for any `Import`/`ImportFrom` node whose name matches `imaplib` or `email.*`, and fails the test if found.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

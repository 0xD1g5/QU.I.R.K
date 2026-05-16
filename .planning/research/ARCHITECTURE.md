# Architecture Research — v4.10 Launch Readiness Integration

**Domain:** Integration analysis for 5 v4.10 workstreams against mature QUIRK v4.9 architecture
**Researched:** 2026-05-16
**Confidence:** HIGH (based on direct codebase inspection of v4.9-shipped code; no speculative claims)

---

## Existing Architecture Baseline (v4.9, verified)

```
run_scan.py (orchestrator)
  └── _wrapped_phase() for each scanner → CryptoEndpoint rows → SQLite
      ├── tls_scanner        → tls_capabilities_json
      ├── ssh_scanner        → ssh_audit_json
      ├── jwt_scanner        → jwt_scan_json
      ├── container_scanner  → container_scan_json
      ├── source_scanner     → source_scan_json
      ├── aws/azure/gcp_connector → cloud_scan_json / gcs_scan_json
      ├── dnssec_scanner     → dnssec_scan_json   (identity family)
      ├── saml_scanner       → saml_scan_json     (identity family)
      ├── kerberos_scanner   → kerberos_scan_json (identity family)
      ├── email_scanner      → email_scan_json
      ├── broker_scanner     → broker_scan_json
      └── db_connector + vault_connector + k8s_connector → dat_scan_json

quirk/intelligence/
  ├── evidence.py       → build_evidence_summary() counts protocol-keyed endpoints
  │     counters: identity_weak_etype_count, saml_weak_signing_count,
  │               dnssec_weak_algo_count, dar_*, motion_*
  └── scoring.py        → compute_readiness_score() reads evidence → 6 subscores
        SCORE_WEIGHTS sum=261.0 (CI-gated invariant)
        identity_ prefix → multiplied by PROFILE_MULTIPLIERS[profile]["identity_"]

quirk/cbom/
  ├── classifier.py     → classify_algorithm() → (primitive, nist_level, classical_level)
  ├── builder.py        → build_cbom() 3-pass builder
  │     Pass 1: _make_algorithm_component() for each endpoint
  │     Pass 2: _make_certificate_component() — skip if in DAR_SKIP_PROTOCOLS
  │     Pass 3: _make_protocol_component()    — skip if in MOTION_PLAINTEXT_PROTOCOLS
  │     _fips_status(): nist_level>=1 → "approved", else "non-approved"
  │     "certified" tier deferred (Phase 52 D-01 — CMVP attestation hook)
  └── writer.py         → write_cbom_files() JSON+XML output

quirk/reports/
  ├── _md_escape.py     → md_cell() GFM table-cell escaping (Phase 61 REPORT-SAN-01)
  │     Neutralizes: CRLF/LF, pipe injection, ASCII control chars
  │     NOT YET: backtick/asterisk HTML entity escaping (deferred D-11/WR-01)
  ├── technical.py      → md_cell() applied to all table-cell interpolations
  ├── executive.py      → (escaping status TBD — check before HTML hardening phase)
  ├── html_renderer.py  → Jinja2 + autoescape=["html","j2"] for template rendering
  │     render_html_report() → jinja2 Environment(autoescape=select_autoescape())
  │     render_pdf_report()  → Playwright headless Chromium
  └── writer.py         → orchestrates all report types; imports categorize_waves()
                           from quirk/engine/migration_planner.py

quirk/compliance/__init__.py
  ├── COMPLIANCE_MAP: 24 categories → PCI-DSS/HIPAA/FIPS/SOC2/ISO27001 controls
  ├── STALENESS_THRESHOLD_DAYS = 365 (CI gate: tests/test_compliance_freshness.py)
  └── _fips() helper: {framework, control, version, last_verified, source_url}

quirk/dashboard/api/
  ├── schemas.py        → Pydantic models: IdentityFinding, DarFinding, MotionFinding
  │     ScanLatestResponse: identity_findings[], dar_findings[], motion_findings[]
  └── routes/scan.py    → /api/scan/latest populates all three finding families

quirk/models.py (CryptoEndpoint ORM columns — additive only)
  tls, ssh, jwt, container, source, cloud, identity (3 cols), dat, email, broker
  chain_verified (Phase 46)
  [smime_scan_json, adcs_scan_json — NOT YET, v4.10 additions]

quantum-chaos-enterprise-lab/
  18 active profiles (storage deprecated in 999.83):
  broker, cloud, database, dnssec, email, identity, jwt, kerberos, ldaps,
  phaseA, pki, registry, saml, source, ssh-weak, storage-s3, tls-cert-defects, vault
  _derive_all_profiles() reads docker-compose.yml at runtime — no hardcoded list
  Image Pin Policy enforced since 999.83: minor/dated pins required, no floating tags
```

---

## Workstream 1: S/MIME Content Scanning

### Follows identity-scanner pattern exactly

S/MIME is email content-layer cryptography (signed/encrypted message bodies), distinct from email transport TLS already in `email_scanner.py`. The identity-scanner pattern (DNSSEC/SAML/Kerberos) is the correct template:

**New module:** `quirk/scanner/smime_scanner.py`

Protocol label: `"SMIME"` — matches the `_PROTOCOL_KEYS` tuple in `evidence.py` (needs adding there too).

**Scanner approach:** Agentless IMAP connection via `imaplib` (stdlib) or `httpx`-backed IMAP proxy. Fetch a sample of messages from `INBOX` with `Content-Type: multipart/signed` or `application/pkcs7-mime`. Extract embedded X.509 certificates via `cryptography.x509`. Classify signing algorithm (RSA key size, SHA-1 vs SHA-256, EC). No mailbox write access required.

**Alternative for air-gapped/no-IMAP scenarios:** Accept a directory of `.eml` files as a scan target (source-scanner style). This is the offline-capable path that respects the agentless constraint.

**New ORM column:** `smime_scan_json` on `CryptoEndpoint`. Pattern matches `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` — all added in v4.2 Phase 17 as a batch column addition.

**New evidence counters in `evidence.py`:**
- `smime_weak_signing_count` — RSA<2048 or SHA-1 message signing key
- `smime_unencrypted_count` — signed-only (no encryption, quantum-vulnerable data in flight)

These slot naturally into the `identity_` prefix family because PROFILE_MULTIPLIERS already applies `"identity_"` prefix multiplication. No new subscore needed — the identity posture subscore is the correct bucket for message-layer signing keys.

**New SCORE_WEIGHTS entries** (two new weights must be added and the CI invariant test updated):
- `"identity_smime_weak_signing_ratio": 8.0` — same weight as `identity_saml_weak_signing_ratio`
- `"identity_smime_unencrypted_ratio": 6.0` — lighter, informational

**New FastAPI schema field:** `IdentityFinding` in `schemas.py` already supports protocol=`"SMIME"` — no new model needed. `ScanLatestResponse.identity_findings` already carries the list.

**Chaos lab profile:** A mock IMAP server (e.g., `dovecot` or `greenmail` Docker image) pre-seeded with signed `.eml` files using RSA-1024 + SHA-1 (weak) and RSA-2048 + SHA-256 (safe) certificates. Profile name: `smime`. Port: choose one not in use (e.g., `21143` for IMAPS). Seed container drops pre-signed `.eml` files into the inbox via `Maildir`.

**CBOM contribution:** Pass-1 `_make_algorithm_component()` for `SMIME` endpoints with signing algorithm (RSA, SHA-1, etc.). Pass-2 certificate components for the signer cert. Pass-3: protocol component labeled `S/MIME`. No additional skip-list entries needed — S/MIME is not in `DAR_SKIP_PROTOCOLS` or `MOTION_PLAINTEXT_PROTOCOLS`.

**Dependency footprint:** `imaplib` is stdlib. `cryptography` is already a core dep. `email` module is stdlib. No new pip extras required for basic operation. The `[identity]` extras group (`impacket`, `ldap3`) is not needed for S/MIME.

**Extras group:** Create `[smime]` optional extra if IMAP library needs pinning, or absorb into `[motion]` since it's email-layer. Recommendation: `[smime]` stays separate to avoid inflating `[motion]`.

---

## Workstream 2: Windows AD CS Scanner

### Follows identity-scanner pattern with a critical constraint: Windows-only APIs

**New module:** `quirk/scanner/adcs_scanner.py`

AD CS (Active Directory Certificate Services) is a PKI CA built into Windows Server. The interesting attack surface: misconfigured certificate templates that allow privilege escalation (ESC1–ESC8 patterns from the Certify/Certipy research). The agentless scanner approach:

1. **LDAP enumeration** — AD CS publishes template ACLs, enrollment rights, and `msPKI-*` attributes via LDAP under `CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=...`. This is readable without write access using `ldap3` (already in `[identity]` extras). This is the **primary path**.

2. **HTTP/HTTPS enrollment endpoint** — `http://<ca-server>/certsrv/` — NTLM-authenticable. Secondary path; TLS posture of the enrollment endpoint is already covered by `tls_scanner`.

3. **WinRM/RPC stub** — truly Windows-native and requires Windows. **Do not implement.** Keep as a stub comment.

The LDAP path means the v4.10 scanner can operate on any platform (Linux/macOS/Windows) as long as the target AD is LDAP-reachable. The `ldap3>=2.9.1` dep is already in `[identity]` extras.

**New ORM column:** `adcs_scan_json` on `CryptoEndpoint`.

**New evidence counters:**
- `adcs_weak_template_count` — templates allowing requestor-supplied SAN (ESC1) or over-permissive enrollment rights (ESC3/4)
- `adcs_weak_ca_key_count` — CA root key RSA<4096 or using SHA-1

**Subscore routing:** Roll into `identity_trust` subscore alongside SAML/Kerberos/DNSSEC. New SCORE_WEIGHTS entries:
- `"identity_adcs_weak_template_ratio": 10.0` — equivalent to `identity_kerberos_weak_etype_ratio`
- `"identity_adcs_weak_ca_key_ratio": 8.0`

**FastAPI schema:** `IdentityFinding` with `protocol="ADCS"`. No new Pydantic model needed.

**Chaos lab profile — CRITICAL CONSTRAINT:**
AD CS requires a Windows Server CA. Fully authentic Windows containers are not available on macOS Docker Desktop (`--platform linux/amd64` only). Two practical approaches:

- Option A (recommended for v4.10): Ship a **mock LDAP dataset** — a containerized `OpenLDAP` pre-populated with AD CS schema attributes (`msPKI-Certificate-Name-Flag`, `msPKI-Enrollment-Flag`, ACLs) that mimic a misconfigured template. The scanner's LDAP path runs against this mock. Profile name: `adcs`. Port: e.g., `21389` (LDAPS mock).
- Option B (deferred): Samba AD DC (`samba/samba:latest`) extended with AD CS attributes. The kerberos profile already uses Samba DC — this would extend it. However, Samba does not implement AD CS natively; schema-level injection is required. Complexity is high.

Recommendation: Option A (OpenLDAP mock with AD CS attributes) for v4.10. Document that a real Windows AD CS environment is required for production accuracy. This is consistent with the existing kerberos profile using Samba DC as a controlled substitute.

**CBOM contribution:** Pass-1 algorithm components for CA signing key algorithm. Pass-2 certificate components for the CA certificate. Pass-3: no new protocol type needed; treat enrollment endpoint TLS as `TLS` protocol (already handled by `tls_scanner`).

**Dependency footprint:** `ldap3` is already in `[identity]` extras. No new pip deps for the LDAP path.

---

## Workstream 3: Report Injection Hardening

### Where the gaps are (precise layering)

The current escaping state (from Phase 61 REPORT-SAN-01, deferred D-11/WR-01):

| Layer | Current State | Gap |
|-------|--------------|-----|
| GFM table cells | `md_cell()` in `_md_escape.py` — escapes `\|`, CRLF, control chars | Applied in `technical.py`; NOT yet applied to `executive.py` (verify at phase start) |
| HTML template | Jinja2 `autoescape=select_autoescape(["html","j2"])` in `html_renderer.py` | Covers template variable interpolation. Gap: any raw `Markup()` bypass or `| safe` filter use in templates |
| HTML template (finding data) | Finding dicts pass through Jinja2 autoescape | Verify no `| safe` applied to user-controlled fields in `report.html.j2` |
| PDF (Playwright) | Chromium renders the autoescaped HTML | No additional sanitization needed if HTML layer is clean |
| Markdown → HTML conversion | N/A — HTML report is generated directly by Jinja2, not by converting Markdown | No `markdown.convert()` call exists; reports are independent codepaths |

**Where to add escaping (in phase order):**

1. **`executive.py`** — audit for raw f-string interpolation into GFM tables. Apply `md_cell()` to all table-cell strings that contain user-controlled data (org name, domain names, finding titles). `technical.py` is already hardened.

2. **`report.html.j2` template** — audit for `| safe` filter applied to scanner-emitted strings. All finding `.description`, `.remediation`, `.host`, `.title` fields must flow through Jinja2's autoescaping (no `| safe`). Any template variable that takes raw scanner output needs verification.

3. **`executive.py` HTML section** (if executive.py has an HTML output path distinct from `html_renderer.py`) — verify the call chain.

4. **SSRF clamp for PDF** — `render_pdf_report()` in `html_renderer.py` already exists. Verify no `page.goto()` call can be influenced by scanner-emitted URLs (Playwright PDF renders a local file path, not a network URL — confirm this is enforced).

**AST/grep CI gate for regression prevention:**

The existing pattern from Phase 59 (credential leakage AST gate) and Phase 62 (check-cancelled-guards.sh) is the model. For injection hardening:

- **grep gate:** `scripts/check-md-cell-coverage.sh` — enumerate all GFM table-cell interpolation sites in `quirk/reports/*.py` that do NOT call `md_cell()` and fail CI if any are found. This is the same pattern as the Phase 59 AST gate for `scan_error` writes.
- **template audit test:** `tests/test_report_template_no_safe_filter.py` — grep `report.html.j2` for `| safe` applied to scanner-emitted variables; fail if found.

**Build order note:** Report injection hardening is safe to execute in parallel with CMVP attestation (they touch different files). However, if CMVP attestation adds new fields to the HTML report template (e.g., `fips_certified` badges), those new template variables must also be audited for injection. Schedule injection hardening to run either before or in the same phase wave as CMVP attestation template additions.

---

## Workstream 4: CMVP Attestation Feed

### Where it lives in the architecture

**New module:** `quirk/compliance/cmvp.py`

CMVP (Cryptographic Module Validation Program) is the NIST/CCCS database of FIPS 140-2/3 validated modules. The NIST feed is available as a public JSON API: `https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search/api/` (or the equivalent JSON export).

**Integration point with CBOM Pass-1 `_fips_status()`:**

In `quirk/cbom/builder.py`, the `_fips_status()` function currently emits two tiers: `"approved"` and `"non-approved"`. The comment at line 289 explicitly marks:

> "The 'certified' tier is reserved for a future phase with CMVP attestation support (Phase 52 D-01) and is intentionally never emitted in v4.7."

The v4.10 CMVP phase closes this deferred D-01. The integration is:

1. `quirk/compliance/cmvp.py` loads the NIST CMVP feed and builds a lookup: `algorithm_name → [certificate_numbers]`.
2. `_fips_status()` in `builder.py` gains a third tier: `"certified"` — emitted when the algorithm name (e.g., `"AES-256-GCM"`, `"SHA-256"`) has one or more active NIST CMVP certificates in the lookup.
3. The `quirk:fips140-3-status` CBOM `Property` value becomes `"approved"`, `"non-approved"`, or `"certified"`.

**Module design for `cmvp.py`:**

```
quirk/compliance/cmvp.py
  CMVP_FEED_URL = "https://csrc.nist.gov/..."
  STALENESS_THRESHOLD_DAYS = 90   # quarterly cadence (same as qramm model_meta.py)
  last_verified = "YYYY-MM-DD"    # bumped on re-verification
  source_url = CMVP_FEED_URL

  def get_certified_algorithms() -> frozenset[str]: ...
  def is_cmvp_certified(algorithm_name: str) -> bool: ...
```

**Cache strategy (offline-capable constraint is hard):**

The NIST feed must not be fetched at scan time (breaks air-gapped client engagements). Two-tier approach:

- **Bundled cache:** Ship a `quirk/compliance/cmvp_cache.json` as package data, updated at release time. This is the offline path. The staleness CI gate (`tests/test_cmvp_freshness.py`) fails if `last_verified` is > 90 days old.
- **Runtime refresh:** `cmvp.py` exposes a `quirk compliance cmvp refresh` CLI subcommand that fetches the current NIST feed and regenerates `cmvp_cache.json`. Online-only; not called during scan.

**Staleness gate pattern:** Identical to `quirk/qramm/model_meta.py` (`STALENESS_THRESHOLD_DAYS = 90`). CI workflow `python-staleness.yml` already runs `pytest tests/test_qramm_staleness.py tests/test_compliance_freshness.py` — add `tests/test_cmvp_freshness.py` to the same workflow step.

**FIPS 140-3 compliance annotation ripple:**

The `quirk/compliance/__init__.py` COMPLIANCE_MAP has `_fips()` control entries. Adding "certified" tier to CBOM output may surface in the compliance summary section of HTML/PDF reports. The compliance module itself needs no changes — the `fips140-3-status` property is a CBOM-level annotation, not a finding-level compliance mapping.

**Build order note:** CMVP attestation must land before (or in the same phase as) any HTML/PDF template that renders a `fips140-3-status` badge. If the badge template uses the `"certified"` value without the module being present, it renders as "approved" (safe fallback, not broken). CMVP can therefore be scheduled independently of the HTML hardening phase.

---

## Workstream 5: Release Engineering

### Where each artifact lives

**Signed wheel/sdist:** `.github/workflows/release.yml` (new file). The existing `python-staleness.yml` and `dashboard-quality.yml` are the only current CI workflows. Release workflow pattern:

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']
jobs:
  build:   # python -m build → dist/
  sign:    # sigstore or GPG sign → dist/*.sig
  publish: # upload to PyPI or GitHub Releases
```

The sigstore approach (keyless signing via OIDC, `sigstore` Python package) is preferred over GPG for open-source packages in 2026 — no key management burden, GitHub Actions OIDC token is sufficient. GPG is the fallback for air-gapped distribution.

**Version policy doc:** `docs/RELEASING.md` (new file). Documents: version bump procedure, which surfaces to update (6 surfaces currently gated by `tests/test_version.py`), tag naming convention, how to trigger the release workflow, how to verify signed artifacts.

**SECURITY.md:** Repo root (standard GitHub convention for vulnerability disclosure). References `docs/RELEASING.md` for the disclosure-to-release pipeline.

**CODE_OF_CONDUCT.md:** Repo root. Boilerplate Contributor Covenant or equivalent.

**CHANGELOG-driven release script:** The existing `CHANGELOG.md` at repo root + `docs/release-notes/4.4.0.md`, `4.5.0.md`, `4.6.0.md` establish the pattern. A `scripts/generate-release-notes.py` script (or shell script) reads `docs/release-notes/<version>.md` and appends to `CHANGELOG.md`. Used in the release workflow before tagging.

**Version bump surface (currently 6, gated by `tests/test_version.py`):**
1. `pyproject.toml [project] version`
2. `quirk/__init__.py __version__`
3. CBOM `metadata.component.version` (set from `__version__`)
4. HTML report generated_at header (from `__version__`)
5. `CHANGELOG.md` latest entry
6. `docs/release-notes/<version>.md` header

The release engineering phase does not change these surfaces; it adds tooling to update them consistently.

---

## Workstream 6: Chaos Lab Fidelity (Phase 999.83 Lessons)

### What Phase 999.83 taught us

From the SUMMARY files and CONTEXT.md, the concrete lessons are:

**Lesson 1 — `_derive_all_profiles()` runtime-read is sound; image pins are the new risk surface.**

The runtime-read pattern (Phase 40) solved the ALL_PROFILES drift problem permanently. Phase 999.83 confirmed it works: no profile-name drift bugs appeared. The new risk surface is **floating image tags** causing silent behavioral changes between `docker pull` invocations. The Image Pin Policy (added to `README.md` in Plan 05) is the mitigation: minor/dated tags only, no major-only tags.

**Lesson 2 — Seed scripts must be idempotent.**

`source/seed.sh` (gitea-seed) exits 22 on re-runs because `POST /api/v1/user/repos` returns 409 when repos already exist. This is a pre-existing bug (DEF-999.83-C) not fixed in 999.83. The pattern: all seed scripts must check existence before creation. Future chaos lab additions should model this from day one.

**Lesson 3 — The `command:` override in docker-compose.yml bypasses the image entrypoint security steps.**

The gitea root-crash (Bug 1) was caused by `command:` overriding the entrypoint that drops privileges. Pattern: avoid overriding `command:` in any service that has a security-significant entrypoint. Use sidecar init containers or environment variables for post-startup initialization.

**Lesson 4 — macOS bind-mount permission model creates false negatives in lab UAT.**

`ldaps` (openldap chown) and `rabbitmq-broker` (erlang cookie eacces) both fail on macOS due to Docker Desktop's bind-mount uid/gid behavior, unrelated to BACK-90. These are filed as DEF-999.83-A/B. The implication: the UAT criterion for new chaos lab profiles should be "four fix sites PASS" not "zero exits anywhere" — macro-level "zero exits" is unachievable on macOS for some profiles.

**Is `_derive_all_profiles()` sufficient, or do we need per-profile config validation?**

The runtime-read is sufficient for profile-name drift. Per-profile config validation (e.g., a CI check that verifies every profile has a healthcheck and an explicit image pin) would add defense-in-depth. This is a good follow-on but not required for v4.10. The existing `docker-compose ... config --profile <name>` command (used in acceptance criteria of Plan 01) validates YAML syntax at the per-profile level — the CI could call this for all profiles.

**New chaos lab profiles in v4.10 (S/MIME, AD CS mock):**

Both must follow the established pattern:
- `docker-compose.yml`: add profile with explicit image pin (minor/dated tag), healthcheck, seed container dependency chain.
- `lab.sh`: no changes needed — `_derive_all_profiles()` picks up new profiles automatically.
- `README.md`: add row to Profile Summary table (port, services, scanner finding summary).
- `expected_results_v4.md`: add `## Profile: smime` and `## Profile: adcs` sections with expected scanner findings.

---

## Component Integration Map

### New vs Modified Files per Workstream

| Workstream | New Files | Modified Files |
|------------|-----------|----------------|
| S/MIME scanner | `quirk/scanner/smime_scanner.py` | `quirk/models.py` (+smime_scan_json column), `quirk/intelligence/evidence.py` (+2 counters, +SMIME to _PROTOCOL_KEYS), `quirk/intelligence/scoring.py` (+2 SCORE_WEIGHTS), `quirk/cbom/builder.py` (register SMIME in Pass-1/2/3), `quirk/dashboard/api/schemas.py` (no new model, protocol field covers it), `quantum-chaos-enterprise-lab/docker-compose.yml`, `README.md`, `expected_results_v4.md` |
| AD CS scanner | `quirk/scanner/adcs_scanner.py`, chaos lab OpenLDAP mock config | `quirk/models.py` (+adcs_scan_json), `quirk/intelligence/evidence.py` (+2 counters, +ADCS to _PROTOCOL_KEYS), `quirk/intelligence/scoring.py` (+2 SCORE_WEIGHTS), `quirk/cbom/builder.py` (Pass-1), `quantum-chaos-enterprise-lab/docker-compose.yml`, `README.md`, `expected_results_v4.md` |
| Report injection hardening | `scripts/check-md-cell-coverage.sh`, `tests/test_report_template_no_safe_filter.py` | `quirk/reports/executive.py` (apply md_cell to table cells), `report.html.j2` (audit/remove any `| safe` on scanner data), `.github/workflows/dashboard-quality.yml` (add grep gate step) |
| CMVP attestation | `quirk/compliance/cmvp.py`, `quirk/compliance/cmvp_cache.json`, `tests/test_cmvp_freshness.py` | `quirk/cbom/builder.py` (_fips_status adds "certified" tier), `quirk/compliance/__init__.py` (may need CMVP section), `.github/workflows/python-staleness.yml` (add test_cmvp_freshness.py), `quirk/cli/` (new `compliance cmvp refresh` subcommand) |
| Release engineering | `.github/workflows/release.yml`, `docs/RELEASING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `scripts/generate-release-notes.py` | `pyproject.toml` (sigstore/build tooling in `[dev]` extras), `.github/workflows/python-staleness.yml` (version check on tag push) |
| Chaos lab fidelity | Per-bug seed scripts, init containers | `quantum-chaos-enterprise-lab/docker-compose.yml`, seed scripts for DEF-999.83-A/B/C, `expected_results_v4.md`, `README.md` |

### migration_planner.py Removal

`quirk/engine/migration_planner.py` contains only one function (`categorize_waves`) with 12 lines. It is imported in exactly one place: `quirk/reports/writer.py`. The function is trivially relocatable to `quirk/intelligence/roadmap.py` (which already handles phased roadmap logic) or inlined into `writer.py`. Tests mock `categorize_waves` at `quirk.reports.writer.categorize_waves` — the mock path must be updated. No architectural risk; pure housekeeping.

---

## Data Flow Changes

### S/MIME and AD CS follow the same flow as identity scanners

```
run_scan.py
  └── _wrapped_phase("smime", scan_smime_targets, ...)
       └── scan_smime_targets(cfg) → [CryptoEndpoint(protocol="SMIME", smime_scan_json=...)]

evidence.py build_evidence_summary()
  └── proto == "SMIME" → increment smime_weak_signing_count | smime_unencrypted_count

scoring.py compute_readiness_score()
  └── identity_trust_score -= ratio(smime_weak_signing_count) * w["identity_smime_weak_signing_ratio"]

cbom/builder.py build_cbom()
  └── Pass 1: SMIME endpoints → _make_algorithm_component(signing algo)
  └── Pass 2: SMIME endpoints → _make_certificate_component(signer cert)
  └── Pass 3: SMIME endpoints → _make_protocol_component("S/MIME")

dashboard/api/routes/scan.py /api/scan/latest
  └── identity_findings: IdentityFinding(protocol="SMIME", algorithm="RSA-1024", severity="HIGH")
```

### CMVP flow (CBOM annotation only, no scoring impact)

```
quirk/compliance/cmvp.py (loaded at import time, uses bundled cache)
  └── is_cmvp_certified(algo_name) → bool

quirk/cbom/builder.py _fips_status()
  └── if is_cmvp_certified(name): return "certified"
  └── elif nist_level >= 1:       return "approved"
  └── else:                       return "non-approved"

CycloneDX CBOM output
  └── <property name="quirk:fips140-3-status">certified</property>
```

---

## Build Order and Parallelization

### Wave A: Independent (can parallelize)

| Phase | Work | Parallelizable? | Dependency |
|-------|------|----------------|------------|
| A1: S/MIME scanner | New scanner module + ORM column + evidence counters | Yes | None |
| A2: AD CS scanner | New scanner module + ORM column + evidence counters | Yes | None |
| A3: Report injection hardening | Escaping audit + CI gates | Yes | None |
| A4: CMVP attestation | New compliance module + CBOM `_fips_status` 3rd tier | Yes | None |
| A5: Chaos lab fidelity (999.83 deferred) | DEF-999.83-A/B/C fixes | Yes | None |

All five A-wave workstreams touch disjoint code paths. They can execute in parallel across sub-agents.

### Wave B: Integration (requires A-wave completion)

| Phase | Work | Dependency |
|-------|------|------------|
| B1: S/MIME + AD CS scoring weight CI gate | Update `tests/test_score_weights_invariant.py` for new SCORE_WEIGHTS sum | A1 + A2 both complete (sum changes twice) |
| B2: Report template CMVP badge rendering | If HTML report gains a CMVP badge, template change requires both CMVP module (A4) and injection hardening (A3) to be reviewed together | A3 + A4 |
| B3: Release engineering | Signed artifact workflow should gate on all A-wave work being merged | All A-wave phases complete |
| B4: Chaos lab profiles for S/MIME + AD CS | New `smime` and `adcs` profiles in docker-compose.yml | A1 + A2 (scanner must exist before expected_results oracle can be written) |

### Wave C: Polish + verification (sequential)

| Phase | Work |
|-------|------|
| C1: migration_planner.py removal | Inline/relocate `categorize_waves`, update mock paths in 7 test files |
| C2: public-launch polish | Homebrew formula, Docker image, quickstart, marketing README, demo script — all require stable release-engineered artifacts |
| C3: upgrade migration docs | v4.x → v4.10 migration guide; requires knowing what schema columns changed |

---

## Scalability and Schema Constraints

The `additive-only schema` constraint (no breaking migrations in v1) means `smime_scan_json` and `adcs_scan_json` follow the exact pattern of every prior column addition: `Column(Text, nullable=True)` appended to `CryptoEndpoint`. SQLite `ALTER TABLE ADD COLUMN` is supported; `quirk/db.py` `init_db()` handles idempotent column additions if it uses `CREATE TABLE IF NOT EXISTS` (confirm pattern before executing).

The SCORE_WEIGHTS sum invariant (`tests/test_score_weights_invariant.py`) currently expects sum=261.0. Adding 4 new weights (2 for S/MIME, 2 for AD CS) changes the expected sum. This test must be updated as a final integration step after both scanner phases complete — or each scanner phase updates it independently with the expected sum after their additions.

---

## Sources

- `quirk/intelligence/evidence.py` — direct inspection, evidence counter families
- `quirk/intelligence/scoring.py` — SCORE_WEIGHTS dict (sum=261.0), PROFILE_MULTIPLIERS
- `quirk/cbom/builder.py` — `_fips_status()` docstring (Phase 52 D-01 CMVP deferred comment at line 289)
- `quirk/reports/_md_escape.py` — Phase 61 REPORT-SAN-01 escaping scope and documented deferral of HTML-entity escaping
- `quirk/reports/html_renderer.py` — Jinja2 autoescape configuration
- `quirk/models.py` — full CryptoEndpoint column inventory
- `quirk/dashboard/api/schemas.py` — IdentityFinding, MotionFinding, DarFinding models
- `quirk/compliance/__init__.py` — COMPLIANCE_MAP, STALENESS_THRESHOLD_DAYS, _fips() helper
- `.planning/PROJECT.md` — v4.10 milestone context, out-of-scope promotions, key decisions log
- `.planning/phases/999.83-chaos-lab-service-config-drift/CONTEXT.md` — decisions and root-causes
- `.planning/phases/999.83-chaos-lab-service-config-drift/999.83-01-SUMMARY.md` — gitea init-sidecar pattern
- `.planning/phases/999.83-chaos-lab-service-config-drift/999.83-05-SUMMARY.md` — deferred items, image pin policy, macOS bind-mount lessons
- `run_scan.py` — `_wrapped_phase()` pattern, scanner invocation order
- `quantum-chaos-enterprise-lab/lab.sh` — `_derive_all_profiles()` runtime-read pattern (confirmed working)
- `quantum-chaos-enterprise-lab/docker-compose.yml` — 18 active profiles confirmed

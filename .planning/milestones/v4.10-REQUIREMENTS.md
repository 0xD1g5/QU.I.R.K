# QU.I.R.K. v4.10 Requirements

**Milestone:** v4.10 Launch Readiness — Coverage, Hardening, Release Engineering
**Opened:** 2026-05-16
**Phase numbering:** continues from Phase 77 (Phase 78+)

Closes remaining v4.x security/correctness backlog, expands identity-protocol
coverage with S/MIME and Windows AD CS (both LDAP-discovered, agentless),
brings chaos-lab fidelity gaps to closure, and stands up the release-engineering
+ public-launch foundation needed for a future v5.0 GA tag.

Research synthesized at `.planning/research/SUMMARY.md` (committed `c5d1d61`).

---

## Active Requirements

### HARDEN — Report Injection Hardening (audit D-06 deferred from v4.8)

- [x] **HARDEN-01**: All markdown table cells emitted in `quirk/reports/executive.py` and any remaining unguarded paths use `md_cell()` for consistent escape parity with `technical.py`.
- [x] **HARDEN-02**: All Jinja2 templates run with `autoescape=True`; every `| safe` filter usage is documented with a justification comment AND wraps a value that has already been sanitized through `nh3.clean()` (allowlist policy defined once in `quirk/util/sanitize.py`).
- [x] **HARDEN-03**: Scanner-emitted free-text fields (certificate CNs/SANs, target names, error messages, finding descriptions) are run through `nh3` sanitization before reaching HTML / PDF rendering.
- [x] **HARDEN-04**: Playwright PDF rendering disables JavaScript execution AND uses a no-network context; PDF metadata (Title/Author) is set from constants, never from scan content.
- [x] **HARDEN-05**: CI grep/AST gate enforces no new `| safe` filter usages without a paired `nh3.clean()` call upstream; modeled on Phase 59 `safe_str` AST gate.
- [x] **HARDEN-06**: `nh3>=0.2.17` added as core dependency (replaces `bleach` if present); `pyproject.toml` `[project] dependencies` section updated.

### SMIME — S/MIME LDAP Discovery Scanner (promoted from out-of-scope; agentless via LDAP)

- [x] **SMIME-01**: New `quirk/scanners/smime_scanner.py` scans the AD LDAP `userCertificate` and `userSMIMECertificate` binary attributes via the existing `ldap3` connection used by the Kerberos scanner; no IMAP, no mailbox content access.
- [x] **SMIME-02**: Each retrieved certificate is parsed via `cryptography.x509.load_der_x509_certificate`, then classified for signing algorithm, key size, expiry, and NIST PQC quantum-safety using the shared `quirk/util/weak_crypto.py` helper.
- [x] **SMIME-03**: New ORM column `smime_scan_json` added to `ScanSession` (additive only — no breaking schema migration).
- [x] **SMIME-04**: New evidence counters `identity_smime_weak_signing_count`, `identity_smime_expired_count`, `identity_smime_weak_key_count` slot into the existing `identity_trust` subscore via `quirk/intelligence/scoring.py` `SCORE_WEIGHTS`.
- [x] **SMIME-05**: New `IdentityFinding` entries emitted with `protocol="SMIME"` (no new Pydantic model needed); React Identity tab automatically picks them up via the existing list rendering.
- [x] **SMIME-06**: CBOM integration — Pass 1 emits algorithm components for each S/MIME certificate; Pass 2/3 skip-list extended for SMIME endpoints to avoid spurious TLS-style components.
- [x] **SMIME-07**: Chaos lab profile `smime` — Linux-native OpenLDAP container pre-populated with deterministic test users carrying RSA-1024 (HIGH), SHA-1-signed (HIGH), and RSA-2048-SHA-256 (SAFE) S/MIME certs in `userSMIMECertificate`; `expected_results_v4.md` oracle updated.
- [x] **SMIME-08**: AST CI check forbids logging any IMAP envelope fields or mailbox content paths from the S/MIME scanner module (privacy invariant — even though current design doesn't touch IMAP, the gate is preventative for future drift).

### ADCS — Windows AD CS Scanner (promoted from v2 backlog; LDAP enumeration, no certipy-ad)

- [x] **ADCS-01**: New `quirk/scanners/adcs_scanner.py` enumerates AD CS Enrollment Services and Certificate Templates via authenticated LDAP queries to the AD `CN=Configuration,...` partition, using the existing `ldap3` path from `[identity]` extras; **no `certipy-ad` dependency** (would re-trigger the impacket/cryptography conflict).
- [x] **ADCS-02**: ESC1, ESC2, ESC3, ESC4, ESC5, ESC6, ESC7, ESC8 misconfiguration findings emitted per template via deterministic LDAP-attribute-driven checks (`msPKI-Certificate-Name-Flag`, `msPKI-Enrollment-Flag`, `pKIExtendedKeyUsage`, etc.); ESC9–ESC16 explicitly out of scope.
- [x] **ADCS-03**: New ORM column `adcs_scan_json` added to `ScanSession`. (Phase 80-01, commit 9ed0cd0)
- [x] **ADCS-04**: New evidence counters `identity_adcs_weak_template_count`, `identity_adcs_misconfig_count`, `identity_adcs_weak_signing_count` slot into the existing `identity_trust` subscore.
- [x] **ADCS-05**: New `IdentityFinding` entries emitted with `protocol="ADCS"`.
- [x] **ADCS-06**: CBOM integration — Pass 1 emits algorithm components for CA signing certs and discovered templates; Pass 2/3 skip-list extended for ADCS endpoints.
- [x] **ADCS-07**: New `[adcs]` extras group in `pyproject.toml` (separated from `[identity]`); CI matrix pip-install job asserts `cryptography>=44.0` survives every extras combination including `[all]` + `[adcs]`.
- [x] **ADCS-08**: Chaos lab profile `adcs` — Linux-native OpenLDAP container with `msPKI-*` schema attributes mimicking deliberately misconfigured templates (one ESC1, one ESC4, one safe baseline); `expected_results_v4.md` oracle updated; docs note that real Windows AD CS validation requires a customer environment.
- [x] **ADCS-09**: Active exploitation simulation (e.g., template enrollment requests, certificate signing requests) explicitly disallowed — scanner is read-only LDAP enumeration only. Documented in scanner module header.

### CMVP — CMVP Attestation Feed (Phase 52 D-01 deferred — third FIPS 140-3 tier)

- [x] **CMVP-01**: New `quirk/compliance/cmvp.py` module with a curated static JSON table (`cmvp_cache.json`) covering ~50 common cryptographic modules used in the field; module includes `last_verified` date + `STALENESS_THRESHOLD_DAYS = 90` matching `model_meta.py` cadence.
- [x] **CMVP-02**: CI staleness gate fails if `cmvp_cache.json::last_verified` is older than 90 days (matches existing QRAMM staleness CI workflow).
- [x] **CMVP-03**: `quirk compliance cmvp refresh` CLI fetches the latest NIST CMVP validated-modules HTML page via `httpx` + `beautifulsoup4`, parses into the cache schema, and writes back with a fresh `last_verified` date; offline-capable constraint preserved (bundled cache is always present).
- [x] **CMVP-04**: `beautifulsoup4>=4.13.0` added as core dependency (used only by the refresh CLI; LXML parser already present).
- [x] **CMVP-05**: CBOM Pass-1 `_fips_status()` in `quirk/cbom/classifier.py` extended to emit `coverage` (informational list of CMVP modules that *cover* the algorithm) — never emits `certified: true`. The decision to omit `certified` is logged to PROJECT.md Key Decisions as v4.10 D-NN before any code is written.
- [x] **CMVP-06**: HTML/PDF reports gain a "CMVP Coverage" column in the compliance section showing the coverage list per algorithm; missing-coverage cases render as "Not in CMVP catalog" (never as "Not certified").
- [x] **CMVP-07**: Negative test asserts that no code path emits `certified: true` for any algorithm; this is a permanent CI invariant.

### CHAOS — Chaos Lab Fidelity (Phase 999.83 deferred items)

- [x] **CHAOS-01**: DEF-999.83-A — `ldaps` / `openldap` profile macOS bind-mount path resolved (named volume + idempotent seed script); chaos lab `ldaps` and `openldap` profiles bring up cleanly on macOS Docker Desktop with `./lab.sh up` and never produce permission-denied seed errors.
- [x] **CHAOS-02**: DEF-999.83-B — `rabbitmq` Erlang cookie reliability fixed; chaos lab `broker` profile RabbitMQ container survives `./lab.sh down && ./lab.sh up` cycles without cookie-mismatch failures.
- [x] **CHAOS-03**: DEF-999.83-C — `gitea-seed` made idempotent; re-running `./lab.sh up --profile source` on an already-seeded gitea profile is a no-op (no duplicate-org/duplicate-repo errors).
- [x] **CHAOS-04**: New v4.10 chaos lab profiles (`smime`, `adcs`) are seeded idempotently from day one — both pass an explicit "re-up after up" regression test (`tests/test_chaos_lab_idempotency.py`).
- [x] **CHAOS-05**: Image pin policy enforced — every new service in `docker-compose.yml` must use a fully qualified image tag with sha256 digest (lab.sh check fails CI on `:latest` or untagged image).
- [x] **CHAOS-06**: `lab.sh` `ALL_PROFILES` runtime-read pattern continues to pass all parity tests after the two new profiles land; `expected_results_v4.md` oracle covers `smime` and `adcs`.

### CLEAN — Dead Code Removal (standing future requirement)

- [x] **CLEAN-01**: `quirk/intelligence/migration_planner.py` removed; its single import in `quirk/reports/writer.py` inlined or relocated; seven `quirk.reports.writer.categorize_waves` test mocks updated; no test regressions.

### RELENG — Release Engineering (toward v5.0 GA)

- [x] **RELENG-01**: PyPI distribution name verified — `pip index versions quirk` checked; if `quirk` is taken, an alternate name (e.g. `quirk-scan`, `qu-i-r-k`) is selected AND a v4.10 D-NN decision is logged before any release commits land.
- [x] **RELENG-02**: PyPI Trusted Publishers configured via GitHub OIDC (no stored API tokens); workflow `.github/workflows/release.yml` publishes wheel + sdist on tag push.
- [x] **RELENG-03**: Sigstore attestations automatically generated by the PyPI publish action (Trusted Publishers includes attestation by default); attestation verification documented in `docs/release-process.md`.
- [x] **RELENG-04**: `towncrier` configured for CHANGELOG automation; per-PR news fragments under `news/`; `towncrier build` is the release-script entry point that consumes `docs/release-notes/*.md` shape into the top-level `CHANGELOG.md`.
- [x] **RELENG-05**: `SECURITY.md` published at repo root — defines vuln disclosure SLA (90 days), GitHub private vulnerability reporting enabled, point of contact, scope statement (in-scope vs out-of-scope vulnerability classes).
- [x] **RELENG-06**: `CODE_OF_CONDUCT.md` published at repo root (Contributor Covenant v2.1 or equivalent).
- [x] **RELENG-07**: `docs/release-process.md` documents the version policy (semver commitments, EOL cadence, what triggers a major/minor/patch bump) and the step-by-step release runbook.
- [x] **RELENG-08**: Single source of truth for version string — `quirk/__init__.py::__version__` is the canonical source; `pyproject.toml`, CLI banner, dashboard footer, CBOM metadata, and CHANGELOG all derive from it; `tests/test_version.py` enforces parity.

### LAUNCH — Public-Launch Polish

- [x] **LAUNCH-01**: Marketing-grade README at repo root — badges (CI/PyPI/license/security), 3-command quickstart, hero screenshot of dashboard, animated demo asset link, one-paragraph value proposition for each user persona.
- [x] **LAUNCH-02**: Homebrew tap formula (personal/org tap, not homebrew-core) — installs latest PyPI release in a `pipx`-managed venv; `brew install <org>/quirk/quirk` runs cleanly on macOS arm64.
- [x] **LAUNCH-03**: GHCR-published Docker image — multi-arch (linux/amd64 + linux/arm64); Dockerfile audited against current project structure; `docker run ghcr.io/<org>/quirk:latest --help` works.
- [x] **LAUNCH-04**: Upgrade guide `docs/upgrade-guide.md` covers v4.x → v4.10 SQLite schema migrations (additive only — already constrained); includes `quirk db migrate` command that no-ops on already-current schemas.
- [x] **LAUNCH-05**: Sample CBOM outputs published under `examples/` — one per major scan profile (TLS-only, identity, data-at-rest, data-in-motion); checked into repo as deterministic fixtures.
- [x] **LAUNCH-06**: Quickstart polish in `docs/getting-started.md` — three-step path (install → scan → view dashboard) tested end-to-end on a clean macOS arm64 machine before release.
- [x] **LAUNCH-07**: `curl | bash` installer explicitly NOT shipped (anti-feature for a security tool); documented in `docs/release-process.md` as a deliberate non-decision.

---

## Future Requirements (deferred to v4.11+ or v5.0)

| Item | Reason |
|------|--------|
| AD CS ESC9–ESC16 misconfiguration detection | ~60% implementation cost for ~5% additional field coverage; ESC1–ESC8 covers the prevalence-weighted majority |
| Active S/MIME signing-policy enforcement scanning (CRLs, OCSP for S/MIME certs) | First need to validate the LDAP-only path with real consulting engagements; revocation checking is a separate scoped surface |
| CMVP `certified: true` attestation tier | Requires algorithm-to-module mapping rigor that NIST does not publish in machine-readable form; revisit if NIST publishes a machine-readable feed |
| Live AD CS exploitation simulation / certificate enrollment | Out of scope per consulting-deliverable model; contradicts read-only audit posture |
| homebrew-core formula submission | Requires sustained maintainer commitment; personal/org tap is the v4.10 path |
| `curl \| bash` installer | Anti-feature for a security tool — never |
| SaaS multi-tenant platform | Future milestone (post-v5.0) per PROJECT.md SaaS Platform section |
| S/MIME mailbox-content scanning (signed/encrypted email bodies via IMAP) | Privacy + agentless-model constraint; LDAP path covers algorithmic posture without touching mailbox content |
| HTML/PDF injection hardening for non-Jinja2 surfaces (markdown report only) | v4.10 covers Jinja2 + markdown table cells; if new non-Jinja2 rendering surfaces emerge, address per surface |

---

## Out of Scope (v4.10)

| Feature | Reason |
|---------|--------|
| `certipy-ad` adoption | Re-triggers the impacket/pyOpenSSL/cryptography transitive conflict logged in PROJECT.md Key Decisions (v4.2); LDAP enumeration via existing `impacket` covers ESC1–ESC8 with zero conflict risk |
| Live NIST CMVP API client | NIST CMVP has no public REST API; HTML scrape with curated static cache + offline-capable bundle is the design |
| Mailbox content / IMAP envelope scanning | Privacy liability + agentless model; LDAP `userCertificate` covers the algorithmic posture surface without touching mailbox content |
| Windows containers in chaos lab | Docker Desktop on macOS is Linux/amd64 only; OpenLDAP `msPKI-*` schema mock is the correct platform-independent approach |
| `bleach` for HTML sanitization | Officially deprecated since January 2023; `nh3` (Rust-backed Ammonia binding) is the actively maintained replacement |
| Real-time continuous monitoring | SaaS milestone, not v1 (carried forward from prior milestones) |
| Network traffic capture (Zeek/Wireshark) | Requires passive tap; out of scope for agentless model |

---

## Traceability

Finalized by roadmapper 2026-05-16. 52 requirements mapped across 8 phases — 100% coverage, zero orphans.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARDEN-01 | Phase 78 — HTML/PDF Injection Hardening | Pending |
| HARDEN-02 | Phase 78 — HTML/PDF Injection Hardening | Pending |
| HARDEN-03 | Phase 78 — HTML/PDF Injection Hardening | Pending |
| HARDEN-04 | Phase 78 — HTML/PDF Injection Hardening | Pending |
| HARDEN-05 | Phase 78 — HTML/PDF Injection Hardening | Pending |
| HARDEN-06 | Phase 78 — HTML/PDF Injection Hardening | Pending |
| SMIME-01 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-02 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-03 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-04 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-05 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-06 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-07 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| SMIME-08 | Phase 79 — S/MIME LDAP Discovery Scanner | Pending |
| ADCS-01 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-02 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-03 | Phase 80 — Windows AD CS Scanner | Complete (80-01) |
| ADCS-04 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-05 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-06 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-07 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-08 | Phase 80 — Windows AD CS Scanner | Pending |
| ADCS-09 | Phase 80 — Windows AD CS Scanner | Pending |
| CMVP-01 | Phase 81 — CMVP Attestation Feed | Pending |
| CMVP-02 | Phase 81 — CMVP Attestation Feed | Pending |
| CMVP-03 | Phase 81 — CMVP Attestation Feed | Pending |
| CMVP-04 | Phase 81 — CMVP Attestation Feed | Pending |
| CMVP-05 | Phase 81 — CMVP Attestation Feed | Pending |
| CMVP-06 | Phase 81 — CMVP Attestation Feed | Pending |
| CMVP-07 | Phase 81 — CMVP Attestation Feed | Pending |
| CHAOS-01 | Phase 82 — Chaos Lab Fidelity | Pending |
| CHAOS-02 | Phase 82 — Chaos Lab Fidelity | Pending |
| CHAOS-03 | Phase 82 — Chaos Lab Fidelity | Pending |
| CHAOS-04 | Phase 82 — Chaos Lab Fidelity (Wave B gate — after Phases 79, 80) | Pending |
| CHAOS-05 | Phase 82 — Chaos Lab Fidelity | Pending |
| CHAOS-06 | Phase 82 — Chaos Lab Fidelity (Wave B gate — after Phases 79, 80) | Pending |
| CLEAN-01 | Phase 83 — Integration Gate + Cleanup | Pending |
| RELENG-01 | Phase 84 — Release Engineering | Pending |
| RELENG-02 | Phase 84 — Release Engineering | Pending |
| RELENG-03 | Phase 84 — Release Engineering | Pending |
| RELENG-04 | Phase 84 — Release Engineering | Pending |
| RELENG-05 | Phase 84 — Release Engineering | Pending |
| RELENG-06 | Phase 84 — Release Engineering | Pending |
| RELENG-07 | Phase 84 — Release Engineering | Pending |
| RELENG-08 | Phase 84 — Release Engineering | Pending |
| LAUNCH-01 | Phase 85 — Public-Launch Polish | Pending |
| LAUNCH-02 | Phase 85 — Public-Launch Polish | Pending |
| LAUNCH-03 | Phase 85 — Public-Launch Polish | Pending |
| LAUNCH-04 | Phase 85 — Public-Launch Polish | Pending |
| LAUNCH-05 | Phase 85 — Public-Launch Polish | Pending |
| LAUNCH-06 | Phase 85 — Public-Launch Polish | Pending |
| LAUNCH-07 | Phase 85 — Public-Launch Polish | Pending |

**Coverage:** 52/52 requirements mapped (100%) — no orphans, no duplicates.

**Wave gating summary:**

| Wave | Phases | Gate condition |
|------|--------|----------------|
| A | 78, 79, 80, 81, 82 (partial) | Run in parallel; Phase 78 starts first |
| B | 82 (CHAOS-04, CHAOS-06), 83, 84 | All Wave A phases complete |
| C | 85 | Phase 84 complete |

---

*Last updated: 2026-05-16 — v4.10 roadmap finalized*

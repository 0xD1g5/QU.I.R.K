# Project Research Summary

**Project:** QU.I.R.K. v4.10 Launch Readiness — Coverage, Hardening, Release Engineering
**Domain:** Cryptographic inventory scanner — identity protocol expansion, report hardening, CMVP attestation, release engineering, public-launch polish
**Researched:** 2026-05-16
**Confidence:** HIGH

## Executive Summary

QU.I.R.K. v4.10 is a tightly-scoped milestone that closes five concrete gaps before a future v5.0 GA tag: it hardens the HTML/PDF reporting pipeline against injection, expands identity coverage to S/MIME and Windows AD CS, fixes three outstanding chaos-lab service-config drift bugs (DEF-999.83-A/B/C), establishes signed-artifact release engineering, and polishes the public install experience. The product is a mature Python + FastAPI + React scanner at v4.9 with over 750 tests and a well-defined architecture. All five workstreams integrate into existing patterns — there are no greenfield components. The primary implementation risk is not novelty; it is a cluster of known traps (impacket/cryptography transitive conflict, CMVP false-attestation, Jinja2 `| safe` bypass, PyPI name collision) that the research has fully mapped.

The recommended approach is a three-wave execution. Wave A runs five workstreams in parallel because their code paths are fully disjoint: S/MIME scanner, AD CS scanner, HTML/PDF injection hardening, CMVP attestation feed, and chaos-lab fidelity fixes. Wave B handles integration tasks that require Wave A output: a single SCORE_WEIGHTS invariant test update (after both scanners are complete), the CMVP badge template integration, and the GitHub Actions release workflow. Wave C delivers public-launch polish (Homebrew tap, Docker image, upgrade guide, marketing README) that depends on stable release-engineered artifacts. This wave gating mirrors the v4.8 Wave A/B split that proved effective.

Two decisions must be locked before planning begins. First, the CMVP `certified: true` question deferred in Phase 52 D-01 must be resolved upfront: the research concludes the only safe answer for v4.10 is "coverage list, not attestation" — emitting `certified: true` from algorithm-name matching alone is a false attestation that destroys consultant credibility in a federal audit. Second, the PyPI package name `quirk` must be verified available via `pip index versions quirk` before any release-engineering work begins; if taken, the distribution name must be changed to `quirk-scanner` in `pyproject.toml` before any packaging automation is written.

## Key Findings

### Recommended Stack

The v4.10 stack change is minimal by design: exactly two new pip packages added to `[project.dependencies]`. `nh3>=0.2.17` (Rust-backed Ammonia binding) replaces the deprecated `bleach` for HTML sanitization in the Jinja2 report pipeline. `beautifulsoup4>=4.13.0` is needed to parse the NIST CSRC CMVP HTML table (using the already-present `lxml` backend, so no additional parser package is required). All other v4.10 features use existing dependencies: `cryptography>=44.0` and `asn1crypto` (transitive) cover S/MIME PKCS7 parsing; `impacket>=0.13.0,<0.14` (already in `[identity]`) covers AD CS LDAP enumeration; `httpx` (already in core) handles the CMVP NIST CSRC fetch. Release engineering tooling (`sigstore`, `towncrier`, `build`, `twine`) is dev-only and must never appear in `[project.dependencies]`.

The `certipy-ad` library must not be added under any circumstances. It pins `cryptography~=42.0.8`, which would downgrade from `>=44.0` and break the TLS scanner — the same class of conflict already documented in the Key Decisions table. The existing impacket LDAP path covers ESC1-ESC4 detection without certipy-ad. S/MIME discovery must be via `userCertificate`/`userSMIMECertificate` LDAP attributes (agentless), not IMAP mailbox content scanning — this sidesteps the PII/privacy pitfall entirely and requires zero new dependencies.

**Core new technologies:**
- `nh3>=0.2.17`: HTML sanitization — Rust-backed, actively maintained, replaces deprecated bleach; pre-built wheels for all platforms including macOS arm64
- `beautifulsoup4>=4.13.0`: CMVP HTML table parsing — uses existing `lxml` as parser backend
- `cryptography>=44.0` (existing): S/MIME PKCS7 parsing via `pkcs7_decrypt_smime()` and `pkcs7.load_pem_pkcs7_certificates()`
- `asn1crypto~=1.5.1` (existing transitive): BER-tolerant CMS parsing for real-world mail client messages from Thunderbird/Outlook
- `impacket>=0.13.0,<0.14` (existing `[identity]`): AD CS LDAP enumeration; no new extras group needed
- `sigstore>=4.2.0` (dev-only): Keyless OIDC signing via GitHub Actions ambient credentials; Rekor v2 transparency log
- `towncrier>=24.8.0` (dev-only): News-fragment-based CHANGELOG generation

**What NOT to add:**
- `certipy-ad` — cryptography version conflict, pins `~=42.0.8`, no stable library API
- `bleach` — deprecated January 2023, depends on unmaintained html5lib
- `M2Crypto` — no macOS arm64 wheel, requires OpenSSL dev headers at build time
- `impacket-ADCS` (micahvandeusen fork) — unmaintained since 2021, not on PyPI

### Expected Features

**Must have (P1 — blocking launch readiness):**
- HTML/PDF report injection hardening — Jinja2 autoescape audit + `nh3.clean()` at `_build_finding` chokepoint; CI grep gate for `| safe` on scanner-output variables; unit test `<script>` tag renders as `&lt;script&gt;`
- S/MIME LDAP discovery — `userCertificate`/`userSMIMECertificate` attributes on AD users; agentless; cert chain extraction, algorithm classification, expiry detection; CBOM Pass-1/2/3 integration
- AD CS CA discovery + template enumeration — ESC1/ESC2/ESC3/ESC4/ESC6 via impacket LDAP; findings scoped to observable crypto properties only (no ESC-numbered findings without `--adcs-deep` flag)
- CMVP attestation feed — static curated table + `certified` CBOM tier (coverage list, not attestation); 90-day staleness gate; `quirk compliance cmvp refresh` CLI; bundled offline snapshot
- PyPI Trusted Publishers + Sigstore attestations — GitHub Actions OIDC-based; SECURITY.md first
- SECURITY.md + CODE_OF_CONDUCT.md — launch gate; GitHub Advisory private reporting enabled
- `migration_planner.py` removal — 12 lines + 1 import + 7 test mock paths; pure housekeeping

**Should have (P2):**
- Homebrew tap (`homebrew-quirk` org tap, not homebrew-core)
- Docker image on GHCR (`ghcr.io/quantum-apps/quirk:v4.10.0`)
- `docs/upgrade-guide.md` + `quirk db migrate` CLI (additive-only; no DROP in v4.x)
- Marketing README with badges (PyPI version, CI status, license) and 3-command quickstart
- Sample CBOM outputs + HTML/PDF report in `examples/`
- CHANGELOG-driven GitHub Release automation

**Defer to v5.0 (P3):**
- ESC5/ESC7/ESC9-16 AD CS coverage — rarer in field; require ACL+RPC verification; high false-positive risk without `--adcs-deep`
- Live CMVP lookup (cached, optional) — online-only value; bundled snapshot covers air-gapped model
- CycloneDX SBOM for QU.I.R.K. itself (dogfooding)
- Homebrew homebrew-core submission (slow review process; private tap ships immediately)
- `quirk doctor` version check vs PyPI latest

**Anti-features (explicit no):**
- IMAP mailbox content scanning for S/MIME — breaks agentless model, PII exposure; LDAP cert discovery sidesteps this
- `curl | bash` installer — contradicts tool's security posture messaging
- ESC-numbered findings without ACL verification — false positives destroy consultant credibility
- `certified: true` in CBOM from algorithm-name matching — false attestation

### Architecture Approach

All five v4.10 workstreams integrate into existing patterns with no architectural invention required. S/MIME and AD CS follow the identity-scanner pattern established in v4.2 (Phases 17-24): new scanner modules, additive ORM columns (`smime_scan_json`, `adcs_scan_json`), new evidence counters in `evidence.py` (four total), new SCORE_WEIGHTS entries (four total), and CBOM Pass-1/2/3 registration. CMVP attestation lives in `quirk/compliance/cmvp.py` following the `compliance/__init__.py` staleness-gate pattern, with `_fips_status()` in `builder.py` gaining a third `"certified"` tier. HTML/PDF injection hardening audits the existing Jinja2 templates and adds `nh3.clean()` at the `_build_finding` chokepoint.

**Major components and new responsibilities:**
1. `quirk/scanner/smime_scanner.py` — LDAP discovery of S/MIME certs from `userCertificate`/`userSMIMECertificate`; BER-tolerant CMS parsing via `asn1crypto`; privacy-safe (no envelope headers stored); `service_detail="SMIME-SIGN"` to avoid CBOM collision with transport TLS
2. `quirk/scanner/adcs_scanner.py` — impacket LDAP queries against `CN=Certificate Templates` and `CN=Certification Authorities`; credential-optional (`ADCS-UNREACH` coverage-gap finding on auth failure); no Windows containers; `[adcs]` extras group isolated from `[identity]`
3. `quirk/compliance/cmvp.py` — bundled `cmvp_cache.json` offline snapshot; 90-day `STALENESS_THRESHOLD_DAYS`; `is_cmvp_certified()` for `_fips_status()` third tier; structural assertion on feed parse with fallback to snapshot
4. `quirk/reports/` hardening — `nh3.clean()` at `_build_finding`; `md_cell()` extended to `executive.py`; CI grep gate for `| safe` on scanner-output variables; Playwright PDF `<title>` sanitization
5. `.github/workflows/release.yml` — PyPI Trusted Publishers; Sigstore attestations automatic via `pypa/gh-action-pypi-publish`; gated on `v*` tag; `GITHUB_ACTIONS` guard required before signing

### Critical Pitfalls

1. **S/MIME transport/content CBOM collision** — Two CryptoEndpoint records share the same host:port (IMAP transport TLS + S/MIME signing cert). Must use `service_detail="SMIME-SIGN"` prefix and a distinct `smime_scan_json` ORM column. Failure signal: duplicate `bom-ref` errors in `test_cbom_writer_validation.py`.

2. **S/MIME mailbox privacy** — The IMAP FETCH path traverses envelope metadata (From, To, Subject). Never store any envelope header in `smime_scan_json`, findings, or reports. The LDAP-only discovery path via `userCertificate` sidesteps this entirely. Gate with `test_smime_no_envelope_leak.py`.

3. **AD CS impacket/cryptography transitive conflict** — Placing AD CS connector in `[identity]` risks impacket pulling in a pyOpenSSL pin that downgrades `cryptography` below `44.0` and breaks the TLS scanner. Use a separate `[adcs]` extras group. Run CI matrix asserting `cryptography.__version__ >= "44.0"` across all extras combinations.

4. **AD CS ESC false positives from LDAP-only evidence** — `nTSecurityDescriptor` ACL parsing is required to verify low-priv enrollment (ESC1 condition 3). Do not emit ESC-numbered findings in v4.10. Scope to observable crypto properties only: `ADCS-01: Weak template key size`, `ADCS-02: CA uses SHA-1`. Gate ESC chain findings behind `--adcs-deep` in v5.0.

5. **CMVP false attestation** — Algorithm-name to CMVP certificate mapping is many-to-many and ambiguous. Never emit `certified: true` from the CMVP module alone. Emit a `fips_140_3_coverage` informational property with a disclaimer. Negative CI test required.

6. **PyPI name collision** — `pypi.org/project/quirk/` exists as a different project. Run `pip index versions quirk` and attempt a `test.pypi.org` upload before any production publish. If taken, rename to `quirk-scanner` in `pyproject.toml`. This is the first task of the release engineering phase.

7. **Jinja2 `| safe` bypass** — `html_renderer.py` enables `autoescape` but any `| safe` filter or `Markup()` wrap on scanner-controlled fields bypasses it. The v4.8 Playwright SSRF clamp blocks outbound navigation but does not block inline script execution. CI grep gate and unit test `<script>` to `&lt;script&gt;` required.

8. **Sigstore requires GitHub Actions OIDC** — Cosign keyless signing requires an OIDC token that only exists in GHA. Gate signing behind `GITHUB_ACTIONS` env check. Local builds produce unsigned artifacts via `make dist` only. SECURITY.md documents signing identity before first signed release.

## Implications for Roadmap

Based on combined research, the phase structure follows three natural waves derived from code-path disjointness and dependency ordering. Phase numbering continues from Phase 77.

### Wave A: Parallel Independent Workstreams

#### Phase 78: HTML/PDF Injection Hardening (start first in Wave A)

**Rationale:** Gates every downstream scanner phase that writes new fields to reports. Running first ensures all subsequent scanner template additions inherit a hardened environment. Closes v4.8 D-06.

**Delivers:** `nh3>=0.2.17` added to core deps; `nh3.clean()` at `_build_finding` chokepoint; `executive.py` `md_cell()` coverage extension; `report.html.j2` audit (zero `| safe` on scanner-output variables); Playwright PDF `<title>` sanitization; CI grep gate + unit test `<script>` to `&lt;script&gt;`

**Addresses:** Report Injection Hardening (P1); Pitfalls 7, 8, 9 from PITFALLS.md

**Research flag:** Standard pattern — Jinja2 autoescape and `nh3` API well-documented; no additional research needed

#### Phase 79: S/MIME LDAP Discovery Scanner (parallel with 78, 80, 81, 82)

**Rationale:** Follows the established identity-scanner pattern exactly (v4.2 Phases 17-24). LDAP discovery via `userCertificate`/`userSMIMECertificate` requires no new pip dependencies.

**Delivers:** `quirk/scanner/smime_scanner.py`; `smime_scan_json` ORM column; `smime_weak_signing_count` + `smime_unencrypted_count` evidence counters; two new SCORE_WEIGHTS entries; CBOM Pass-1/2/3 integration; `smime` chaos lab profile with BER-encoded fixture; `test_smime_no_envelope_leak.py` privacy gate

**Addresses:** S/MIME identity coverage (P1); Pitfalls 1, 2, 3 from PITFALLS.md

**Research flag:** Low-risk overall; BER fixture in chaos lab must be an explicit success criterion in the PLAN (standard DER fixtures miss real-world Thunderbird/Outlook messages)

#### Phase 80: Windows AD CS Scanner (parallel with 78, 79, 81, 82)

**Rationale:** Uses the same impacket LDAP infrastructure as the Kerberos scanner. Must use Linux-native OpenLDAP mock for chaos lab; Windows containers do not run on macOS Docker Desktop.

**Delivers:** `quirk/scanner/adcs_scanner.py`; `adcs_scan_json` ORM column; `adcs_weak_template_count` + `adcs_weak_ca_key_count` evidence counters; two new SCORE_WEIGHTS entries; `[adcs]` extras group (isolated from `[identity]`); CA discovery + template enumeration (crypto-property findings only); `ADCS-UNREACH` coverage-gap finding on credential failure; `adcs` chaos lab profile (OpenLDAP with msPKI-* schema); CI matrix pip-install test asserting `cryptography>=44.0` across all extras combinations

**Addresses:** AD CS identity coverage (P1); Pitfalls 4, 5, 6, 7 from PITFALLS.md

**Research flag:** MEDIUM — CI matrix test must be the first plan task before any `pyproject.toml` edit; `[adcs]` extras group isolation is the structural protection for the impacket conflict

#### Phase 81: CMVP Attestation Feed (parallel with 78, 79, 80, 82)

**Rationale:** Closes Phase 52 D-01. The `certified: true` scope decision must appear in the PLAN as an explicit success criterion: coverage list only, not attestation.

**Delivers:** `quirk/compliance/cmvp.py`; bundled `cmvp_cache.json` offline snapshot; `is_cmvp_certified()` function; `_fips_status()` third tier `"certified"` in `builder.py`; 90-day staleness CI gate (`tests/test_cmvp_freshness.py`); `quirk compliance cmvp refresh` CLI; structural assertion on feed parse with offline snapshot fallback; negative CI test asserting `certified` never set by CMVP module alone; `beautifulsoup4>=4.13.0` added to core deps

**Addresses:** CMVP attestation (P1); Phase 52 D-01 closure; Pitfalls 10, 11 from PITFALLS.md

**Research flag:** MEDIUM — CMVP feed has no schema version; structural assertion pattern must be designed before any algorithm-mapping logic

#### Phase 82: Chaos Lab Fidelity — DEF-999.83 Deferred Items (parallel with 78, 79, 80, 81)

**Rationale:** Fixes three DEF-999.83 items (ldaps macOS bind-mount, rabbitmq erlang cookie, gitea-seed idempotency). All are Docker Compose configuration fixes with full root-cause analysis already documented.

**Delivers:** Docker Compose fixes for DEF-999.83-A/B/C; named volumes replacing bind mounts for affected profiles; idempotent gitea seed script; explicit image pins (minor/dated tags, no floating `:latest`); `./lab.sh down --volumes` UAT documented in README; golden-snapshot pytest fixture for `expected_results_v4.md` finding-content validation

**Addresses:** Chaos-lab fidelity; Pitfalls 15, 16 from PITFALLS.md

**Research flag:** Standard pattern — root causes fully documented in DEF-999.83 CONTEXT.md; no additional research needed

---

### Wave B: Integration and Release (requires Wave A complete)

#### Phase 83: Integration Gate

**Rationale:** One primary coordination task requires both S/MIME and AD CS scanners: updating `tests/test_score_weights_invariant.py` with the new SCORE_WEIGHTS sum (current: 261.0 + four new weights). Running this once after both scanners merge is cleaner than updating twice mid-milestone. Also handles `migration_planner.py` removal and S/MIME + AD CS chaos lab profile additions.

**Delivers:** `SCORE_WEIGHTS` sum updated once in `test_score_weights_invariant.py`; S/MIME and AD CS chaos lab profiles added to `docker-compose.yml` with oracle entries in `expected_results_v4.md`; CMVP badge template integration reviewed alongside hardening audit; `migration_planner.py` removal (inline `categorize_waves` into `quirk/reports/writer.py`; update 7 test mock paths)

**Addresses:** Score invariant coordination; chaos lab new profiles; migration_planner.py housekeeping (P1)

**Research flag:** No additional research needed; all tasks are bookkeeping and wiring

#### Phase 84: Release Engineering

**Rationale:** Must follow Wave A completion (stable codebase). PyPI name check is the absolute first task. SECURITY.md must be written before the first signed release is published. `importlib.metadata` migration resolves the pre-existing version string drift.

**Delivers:** `pip index versions quirk` name check (rename to `quirk-scanner` if taken); `SECURITY.md` (coordinated disclosure + signing identity); `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1); `.github/workflows/release.yml` (PyPI Trusted Publishers + Sigstore attestations); `docs/RELEASING.md`; `importlib.metadata` as single version source of truth; `test_version.py` updated to identity check; `test.pypi.org` successful test upload before production push

**Addresses:** Release engineering (P1); Pitfalls 12, 13, 14 from PITFALLS.md

**Research flag:** MEDIUM — PyPI Trusted Publishers setup requires repository admin access; verify the OIDC publisher setup process before writing automation

---

### Wave C: Public-Launch Polish (requires Phase 84 complete)

#### Phase 85: Public-Launch Polish

**Rationale:** Depends on stable release-engineered artifacts. Homebrew formula sha256 is computed from the PyPI sdist. Docker image references the published version.

**Delivers:** Homebrew tap formula (`homebrew-quirk` org tap); Docker multi-stage image on GHCR (`ghcr.io/quantum-apps/quirk:v4.10.0`); `docs/upgrade-guide.md` (additive-only schema audit; no DROP migrations); marketing README with shields.io badges + 3-command quickstart; sample CBOM JSON+XML + HTML/PDF report in `examples/`; `scripts/demo.sh` quickstart demo

**Addresses:** Public-launch polish P1 and P2 features

**Research flag:** Standard pattern; Docker multi-stage and Homebrew tap formula are well-documented

---

### Phase Ordering Rationale

- Wave A parallelism is grounded in disjoint file paths: Phases 78-82 touch entirely separate modules with no coordination needed between them.
- Phase 78 (injection hardening) is recommended to start first in Wave A — not a hard dependency but ensures all subsequent scanner template additions inherit a hardened environment from day one.
- Phase 83 waits for Phases 79 + 80 because the SCORE_WEIGHTS sum update requires knowing all four new weight values simultaneously.
- Phase 84 (release engineering) waits for all Wave A work — a signed release should reflect the complete milestone.
- Phase 85 waits for Phase 84 — the Homebrew formula sha256 references the PyPI sdist and the Docker image tag references the published version.

### Research Flags

Phases requiring careful planner attention:

- **Phase 79 (S/MIME):** BER-encoded CMS fixture must be present in the chaos lab. Standard DER-only fixtures miss real-world Thunderbird/Outlook messages. The PLAN must call this out explicitly as a success criterion.
- **Phase 80 (AD CS):** The CI matrix pip-install test asserting `cryptography>=44.0` must be the first plan task, before any `pyproject.toml` edit. The `[adcs]` extras group isolation is the structural protection.
- **Phase 81 (CMVP):** The `certified: true` scope decision must be stated in the PLAN as a success criterion with a negative CI test. If left ambiguous, the phase will fail review.
- **Phase 84 (Release):** PyPI name check is the first task. If `quirk` is taken, the distribution name rename cascades to all install documentation, Homebrew formula, and Docker image tags.

Phases with standard, well-documented patterns (skip additional research):

- **Phase 78 (Injection Hardening):** Jinja2 autoescape and `nh3` API well-understood.
- **Phase 82 (Chaos Lab Fidelity):** Root causes fully documented; fixes are Docker Compose config changes.
- **Phase 83 (Integration Gate):** All tasks are bookkeeping and wiring after Wave A.
- **Phase 85 (Launch Polish):** Homebrew tap formula and Docker multi-stage are standard patterns.

## Cross-Cutting Recommendations

These findings converged independently from multiple research threads and must survive into roadmap phase planning:

1. **Report Injection MUST be Phase 78 (first in Wave A)** — gates every downstream scanner phase that writes new fields to reports.

2. **NO certipy-ad** — pins `cryptography~=42.0.8`, downgrades from `>=44.0`, breaks TLS scanner. Use existing impacket LDAP directly. ESC scope: ESC1-ESC4 via LDAP properties; ESC5-ESC8 deferred; ESC9-ESC16 are anti-features for v4.10.

3. **S/MIME is LDAP-discovered, not IMAP-content** — `userCertificate`/`userSMIMECertificate` attributes on AD users; agentless; no mailbox content; sidesteps privacy pitfall entirely; zero new dependencies.

4. **CMVP `certified: true` answer is "coverage only"** — Phase 52 D-01 left this open. v4.10 answer: emit `fips_140_3_coverage` informational property, not `certified: true`. Must appear in Phase 81 PLAN as an explicit success criterion with a negative CI test.

5. **2 new core pip deps total** — `nh3>=0.2.17` and `beautifulsoup4>=4.13.0`. All other v4.10 features use existing dependencies.

6. **PyPI name `quirk` is likely taken — check first** — `pip index versions quirk` is the first task of Phase 84 before any packaging automation. If taken, rename distribution to `quirk-scanner`.

7. **AD CS chaos lab = Linux-native OpenLDAP mock with msPKI-* schema** — Windows containers do not run on macOS Docker Desktop. Design Linux-native from day one; do not attempt Windows and retrofit.

8. **SCORE_WEIGHTS invariant test updates ONCE, after both scanners** — the primary coordination point in Wave B Phase 83.

9. **`migration_planner.py` removal is 12 lines + 1 import + 7 test mocks** — schedule in Phase 83 Wave B alongside other integration tasks.

10. **Wave gating: A (parallel) then B (integration + release) then C (polish)** — mirrors v4.8 Wave A/B split; do not collapse waves.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All decisions grounded in PyPI version inspection and confirmed conflict analysis; certipy-ad exclusion is definitive; nh3 vs bleach is definitive |
| Features | HIGH | S/MIME via RFC 8551 + CA/B Forum primary sources; AD CS via Certipy source + SpecterOps whitepaper; CMVP via NIST CSRC primary source |
| Architecture | HIGH | Based on direct v4.9 codebase inspection; all integration points confirmed against existing code; no speculative claims |
| Pitfalls | HIGH | Grounded in QUIRK historical Key Decisions (impacket conflict already burned once); CMVP false-attestation rationale is complete; BER parsing failure mode confirmed in asn1crypto issue #18 |

**Overall confidence:** HIGH

### Gaps to Address

- **PyPI name availability:** Unknown until `pip index versions quirk` is run. If taken, the distribution name rename cascades to all documentation and tooling. Resolve in Phase 84 task 1 before any packaging work.

- **CMVP NIST CSRC feed structure:** No published schema version. The structural assertion pattern (check top-level keys post-parse, fall back to bundled snapshot on failure) is the mitigation. Bundled `cmvp_cache.json` must be verified against the current live feed structure before Phase 81 completes.

- **AD CS chaos lab profile fidelity:** The OpenLDAP mock with msPKI-* schema must expose enough attributes for ESC1-ESC4 detection. Expected-results oracle must document which ESC/crypto properties the mock exposes. Requires a lab design decision during Phase 80 planning.

- **`smime` extras group dependency footprint:** STACK.md recommends `[smime] = []` (empty; zero new deps). If S/MIME always uses the existing `[identity]` LDAP path, no new extras group is needed for functionality — only for `quirk doctor` advisory surfacing. Clarify during Phase 79 planning.

- **Version source of truth:** `pyproject.toml` shows `version = "4.4.0"` while v4.9 has shipped; `test_version.py` is pinned to a stale literal. The `importlib.metadata` migration in Phase 84 resolves this. Planner must be aware the current state is already inconsistent.

## Sources

### Primary (HIGH confidence)
- `pyca/cryptography` via Context7 — pkcs7 module coverage, PKCS7SignatureBuilder confirmed current
- pypi.org/project/certipy-ad — version 5.0.4, Python >=3.12, `cryptography~=42.0.8` pin confirmed
- deepwiki.com/ly4k/Certipy — full dependency table including impacket~=0.13.0 confirmed
- pypi.org/project/sigstore — version 4.2.0, keyless OIDC signing, Rekor v2
- pypi.org/project/nh3 — version 0.3.3, Rust binding to Ammonia, replaces deprecated bleach
- github.com/mozilla/bleach/issues/698 — official deprecation notice January 2023
- csrc.nist.gov CMVP validated modules — HTML-only, no API; one bulk request feasible
- RFC 8551 — S/MIME Version 4.0 Message Specification
- CA/Browser Forum S/MIME Baseline Requirements v1.0 (2023)
- SpecterOps "Certified Pre-Owned" whitepaper — ESC1-ESC8 definitions
- QUIRK codebase direct inspection (evidence.py, scoring.py, builder.py, html_renderer.py, _md_escape.py, models.py, schemas.py, compliance/__init__.py) — v4.9 state confirmed 2026-05-16

### Secondary (MEDIUM confidence)
- github.com/hackIDLE/nist-cmvp-api — weekly-refreshed static JSON; community project; advisory-only
- pypi.org/project/towncrier — latest August 2025, used by pip/pytest/attrs
- SSL.com LDAP + S/MIME certificate publishing — LDAP `userCertificate` attribute confirmed
- AD CS ESC1-ESC8 (Vaadata blog) — ESC technique survey; cross-referenced with Certipy source

### Tertiary (LOW confidence)
- asn1crypto issue #18 — CMS indefinite-length BER from Thunderbird; community-confirmed but not officially documented
- impacket issue #1716 — pyOpenSSL PKCS12 removal breaking ntlmrelayx; active conflict evidence but version-specific

---
*Research completed: 2026-05-16*
*Ready for roadmap: yes*

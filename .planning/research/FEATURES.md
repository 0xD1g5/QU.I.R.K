# Feature Research

**Domain:** Launch Readiness — S/MIME, AD CS, Report Hardening, CMVP Attestation, Release Engineering, Public-Launch Polish for QU.I.R.K. v4.10
**Researched:** 2026-05-16
**Confidence:** HIGH (S/MIME RFC/CA-B-Forum primary sources), HIGH (AD CS via Certipy source + ADCS wiki), HIGH (CMVP NIST primary source + third-party JSON API), MEDIUM (release engineering patterns, PyPI trusted publishers), MEDIUM (launch polish conventions)

---

## Existing Baseline (Do Not Rebuild)

Already shipped and stable — these are the integration points, not rebuild candidates:

- Email transport scanning (SMTP/SMTPS/IMAP/POP3, STARTTLS detection) — v4.4 Phase 32
- Identity protocol scanning (SAML/OIDC, Kerberos, DNSSEC) with CBOM integration — v4.2
- CycloneDX 1.6 CBOM pipeline with Pass-1 algorithm components, Pass-2/3 skip-lists, CI schema validation — v4.5 Phase 42
- Compliance mapping module (`quirk/compliance/`) with staleness CI gate — v4.6 Phase 49
- FastAPI dashboard with 6-pillar scoring, HTML/PDF reports — v4.0+
- `_build_finding` chokepoint enforcing non-empty description/remediation — v4.6 Phase 48
- Error code registry (`quirk/errors.py`, 50 codes) — v4.8 Phase 68
- QRAMM maturity assessment with evidence bridge — v4.7 Phases 51–53
- `safe_str(exc)` credential-leakage scrubber — v4.8 Phase 59
- Markdown report injection hardening (REPORT-SAN-01 tables only) — v4.9 Phase 61
- v4.8 D-06 open WARNING rows: HTML/PDF injection for non-table contexts (target names, CNs, error messages in Jinja templates) — **this is the v4.10 starting point**

---

## Feature Landscape

### Workstream 1: S/MIME Content Scanning

S/MIME (RFC 8551, CA/B Forum Baseline Requirements v1.0 effective 2023-09-01) is the dominant enterprise standard for signed and encrypted email. Consultants running post-quantum readiness assessments need to know whether email signing keys use quantum-vulnerable algorithms (RSA-2048, ECDSA P-256, SHA-1, MD5) and whether certificates are expiring.

**Discovery approach (agentless):** S/MIME user certificates are published to LDAP/Active Directory in the `userCertificate` and `userSMIMECertificate` attributes. This is the same LDAP path QU.I.R.K. already traverses for Kerberos (ldap3, `[identity]` extras). No mailbox access required.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| LDAP discovery of S/MIME certs from AD `userCertificate` / `userSMIMECertificate` attributes | Agentless model; LDAP path already wired for Kerberos | MEDIUM | Existing ldap3 `[identity]` extras, LDAP connection in Kerberos scanner |
| Certificate chain extraction (subject, issuer, serial, notBefore/notAfter) | Consultants need to know who issued the cert and when it expires | LOW | Python `cryptography` library already in core deps |
| Signing algorithm classification (SHA-1, SHA-256, SHA-384, SHA-512, MD5) | SHA-1 and MD5 are MUST-NOT per RFC 8551 S/MIME 4.0; table-stakes finding | LOW | Existing NIST PQC lookup table + weak_crypto.py (v4.9 Phase 73) |
| Encryption algorithm classification (DES, 3DES, RC2, AES-128, AES-256) | 3DES/RC2 still appear in enterprise S/MIME; critical finding in PCI-DSS scope | LOW | Existing algorithm classifier |
| Key type and size (RSA key size, EC curve) | RSA<2048 and EC<256 are HIGH findings matching existing TLS rules | LOW | Existing `cert_pubkey_alg` extraction logic |
| Expiry detection and CRITICAL/HIGH/MEDIUM severity tiering | Consultant handoff requires expired-cert identification | LOW | Existing TLS expiry logic |
| CBOM integration — Pass-1 algorithm component per S/MIME cert | Consistent with all other identity scanners | MEDIUM | Existing CBOM Pass-1/2/3 pipeline |
| `[identity]` extras group opt-in (no new top-level dep) | S/MIME discovery reuses ldap3 and impacket-free path | LOW | Existing extras group |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Quantum-safety classification per signing/encryption algorithm | Consultant deliverable context — "SHA-1 RSA-2048 is quantum-vulnerable" with NIST PQC tier | LOW | Reuses existing lookup table; no new logic |
| Weak-cipher S/MIME findings surfaced in Identity tab | Zero new UI work; findings slot into existing IdentityFinding model | LOW | Add smime_weak_* evidence counters like existing identity counters |
| CA/B Forum S/MIME Baseline Requirements compliance note | Post-2023-09-01 certificates must conform; flag non-conforming legacy certs | MEDIUM | CA/B Forum v1.0 effective date check in classifier |
| S/MIME capability extension parsing (`smimeCapabilities`) | Lists algorithms the sender can accept for encryption reply; exposes weak preferences | HIGH | OpenSSL CMS / `cryptography` ASN.1 extension parsing |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Mailbox content scanning (reading signed/encrypted emails) | "Full S/MIME audit" | Requires authenticated mailbox access (IMAP/Exchange), breaks agentless model, credential scope creep, PII exposure risk | Cert-level discovery via LDAP covers the cryptographic posture question without touching message content |
| PGP key discovery | Email security completeness | Different keyserver/WKD infrastructure; separate scanner; doubles complexity | Defer to a dedicated PGP phase if demand emerges |
| ACME automation audit | S/MIME auto-renewal | Out of scope for readiness scanner; management-plane concern | Document as manual remediation step |

---

### Workstream 2: Windows AD CS Scanning

AD CS (Active Directory Certificate Services) is the PKI backbone for most enterprise Windows environments. It is a critical surface for post-quantum readiness: CA signing algorithms, template key requirements, and enrollment configurations determine whether an org can migrate to PQC without a full PKI rebuild.

**Discovery approach:** Certipy (Python, `certipy-ad` on PyPI) and the underlying Certify (C#) both use unauthenticated LDAP enumeration of the `CN=Public Key Services,CN=Services` container in AD, querying certificate template objects and CA objects. QU.I.R.K. already uses ldap3 + impacket for Kerberos. AD CS enumeration is the same LDAP path, same credential model.

**ESC numbering:** SpecterOps "Certified Pre-Owned" whitepaper (2021) defined ESC1–ESC8; Certipy has since extended to ESC16. ESC1–ESC8 are the established industry baseline; ESC9–ESC16 are post-2022 additions with lower prevalence in field reports.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| Enterprise CA discovery via LDAP (`CN=Certification Authorities`) | Every enterprise AD CS audit starts here; CA list + signing algorithm + validity | MEDIUM | ldap3 + impacket (existing `[identity]` extras) |
| Certificate template enumeration (`CN=Certificate Templates`) — name, EKU, enrollment rights, subject-name flags | Templates define what an org can issue; determines PQC migration scope | MEDIUM | ldap3 LDAP queries |
| Signing algorithm per CA — SHA-1, SHA-256, RSA key size, EC curve | If the root CA uses SHA-1/RSA-2048, all issued certs are quantum-vulnerable | LOW | Existing cert algorithm classifier |
| Expiry detection for CA certs (root + intermediate) | Expired CA cert = broken PKI; HIGH finding | LOW | Existing expiry logic |
| ESC1: template allows requester-supplied SAN + dangerous EKU + low-priv enrollment | Most common privilege-escalation misconfiguration; all consulting tools flag it | HIGH | Template enumeration + rights evaluation |
| ESC2: any-purpose EKU or no EKU (certificate usable for any purpose) | Broad auth abuse; HIGH severity | MEDIUM | EKU flag check |
| ESC3: certificate request agent EKU (enrollment-on-behalf-of abuse) | Domain escalation path; HIGH | MEDIUM | EKU flag check |
| ESC4: template write permissions to low-priv users | Write → modify template to ESC1; HIGH | MEDIUM | ACL enumeration on template objects |
| ESC6: CA `EDITF_ATTRIBUTESUBJECTALTNAME2` flag enabled | CA-level flag enabling SAN in any template; domain compromise | MEDIUM | CA flags enumeration |
| ESC8: HTTP enrollment interface without HTTPS (NTLM relay to ADCS) | NTLM relay attack surface; HIGH | MEDIUM | HTTP probe to CA enrollment endpoint |
| CBOM integration — CA cert algorithm components | Consistent with all other identity scanner outputs | MEDIUM | CBOM Pass-1 pipeline |
| `[identity]` extras group (no new top-level dep) | Reuses existing ldap3 + impacket path | LOW | Existing extras group |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| ESC5: ACL on AD CS object container itself (AD object write abuse) | Less commonly reported but high impact | HIGH | Requires reading ACLs on `CN=Public Key Services` container |
| ESC7: CA management role misconfiguration (ManageCA/ManageCertificates) | Grants ability to approve pending requests; audit of role assignments | HIGH | CA role enumeration |
| Quantum-safety scoring for the CA hierarchy | If root CA is RSA-2048, entire PKI has a PQC migration problem — quantify it | MEDIUM | Existing 6-pillar scoring; add `adcs_*` evidence counters |
| PQC migration blockers — templates requiring RSA/ECDSA, flag templates that block PQC enrollment | Forward-looking consultant value: "these 7 templates cannot issue ML-DSA certs" | HIGH | Template key spec analysis |
| BloodHound-compatible JSON output (optional) | Enterprise AD teams already use BloodHound; Certipy outputs BloodHound JSON | HIGH | Separate output path; risky scope expansion |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| ESC9–ESC16 full coverage | "Complete AD CS audit" | Post-2022 ESCs require increasingly complex attack-chain context (shadow credentials, weak certificate mappings, relay targets); adds 60%+ implementation cost for ~5% additional client coverage | Implement ESC1–ESC8 for v4.10; flag ESC9+ as "extend in v5.0" |
| Active exploitation / certificate request simulation | Prove the misconfiguration is exploitable | Crosses into offensive tooling; contradicts consulting deliverable model; legal risk for consultants | Report misconfiguration existence with severity; leave exploitation to dedicated pentest tools |
| NTLM credential capture | ESC8 proof | Offensive only; breaks agentless posture | Flag the HTTP enrollment endpoint existence; severity-map based on CA config |
| Windows CA agent / DCOM interface | Deep CA health check | Requires local agent on CA server; breaks agentless model | LDAP-only enumeration covers 90% of audit surface |

---

### Workstream 3: Report Injection Hardening

QU.I.R.K. generates HTML reports (Jinja2 templates) and PDFs (Playwright headless Chrome rendering the HTML). The v4.9 audit (D-06) flagged that non-table contexts — target hostnames, certificate CNs, error messages, finding titles — were not escaped in Jinja2 templates. This is an active WARNING row carried into v4.10.

**Attack surface:** A target hostname like `"><img src=x onerror=alert(1)>` or a certificate CN containing `<script>` is user-supplied data that flows through scan → SQLite → Jinja2 → HTML → PDF. The Playwright PDF renderer runs Chromium; XSS in the HTML template becomes client-side JS execution in the rendered PDF in certain viewers.

**Industry standard:** Mature reporting tools (Hashicorp Vault audit logs, Burp Suite reports, Nessus XML export) always HTML-entity-encode every data-derived string before rendering. Jinja2 provides `autoescape` but QU.I.R.K. templates currently use `autoescape=False` (common in Markdown-first tools that need `<br>` tags).

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| Jinja2 `autoescape=True` for all HTML report templates | Industry baseline; any security tool that generates HTML reports from user-controlled data must escape by default | LOW | Existing Jinja2 template rendering path; audit of which templates use Environment() |
| Explicit `{{ value \| e }}` or `Markup()` escaping for intentional HTML in templates | Some fields are intentionally rendered as HTML (e.g., markdown-to-HTML finding descriptions); must use `Markup()` whitelist pattern | MEDIUM | Audit of all `{{ }}` usages in report templates |
| Target hostname / IP address escaping in all report contexts (header, findings table, cert inventory) | Hostile target names are the primary attack vector | LOW | Template variable audit + autoescape enabling |
| Certificate CN / SAN / issuer escaping | Cert field values can contain angle brackets and quotes; certificate CNs from adversarial test environments may be crafted | LOW | Same autoescape fix |
| Error message / scan error escaping in error summary sections | `scan_error` strings stored in SQLite are `safe_str(exc)` scrubbed for credentials but not HTML-escaped for rendering | LOW | Apply `| e` filter or autoescape to error display blocks |
| PDF SSRF prevention (already in v4.8 Phase 58) — verify no regression | Playwright PDF renderer — file:// URI and internal IP ranges blocked | LOW | Existing PDF SSRF clamp; regression test |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Content Security Policy header on dashboard HTML serve path | Defense-in-depth for dashboard XSS; not just reports | MEDIUM | FastAPI middleware; add `Content-Security-Policy` response header |
| Test fixture with adversarial strings (XSS polyglot, SQL injection attempt, path traversal) as target/cert CN | Regression prevention; proves hardening works against real payloads | LOW | Add to existing pytest fixtures; assert escaped in rendered output |
| Sanitization applied to CBOM JSON output fields (algorithm names, component names) | CBOM consumers may render component names in their own UI | LOW | CycloneDX component `name` field — algorithm names are internal constants, not user-supplied; low risk but worth noting |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Stripping HTML tags from all inputs at ingestion time | "Sanitize on write, not on read" | Destroys legitimate data (certificate CNs with angle brackets are valid); breaks round-trip fidelity in CBOM | Escape on render only; store raw values in SQLite |
| DOMPurify or bleach-based sanitization library | "Belt and suspenders" | Adds a new dependency; the problem is Jinja2 autoescape being disabled, not missing a sanitizer; autoescape fixes the root cause | Enable Jinja2 autoescape + `Markup()` for intentional HTML |
| HTML-to-PDF renderer replacement (e.g., WeasyPrint instead of Playwright) | Avoid Chromium XSS surface | Major architecture change; Playwright already ships; WeasyPrint has weaker CSS support affecting report layout | Fix the Jinja2 autoescape gap; Playwright PDF SSRF already clamped |

---

### Workstream 4: CMVP Attestation Feed

Phase 52 (D-01) deferred FIPS 140-3 `certified` annotation from two-tier (approved/non-approved) to a full CMVP attestation lookup. Consultants presenting CBOM reports to federal or DoD clients need to show whether the cryptographic module implementing an algorithm has an active NIST CMVP certificate.

**How CMVP works:** NIST maintains the Cryptographic Module Validation Program (CMVP) database at csrc.nist.gov. The authoritative source is a web search UI (not a public REST API). However, a third-party project (`hackIDLE/nist-cmvp-api` on GitHub) auto-updates weekly JSON exports of the CMVP database via GitHub Actions — this is the de-facto programmatic interface used by security tools.

**Algorithm → module mapping:** The CMVP database is module-centric (a module contains multiple certified algorithms). The mapping direction QU.I.R.K. needs is: "given algorithm string X found in a scan, which CMVP module certificates cover it?" This requires either the third-party JSON API or a curated static table.

**Scope reality check:** CMVP covers the *module* (e.g., "OpenSSL FIPS Object Module 3.0"), not the *algorithm* in isolation. A finding like "AES-256-GCM" maps to multiple CMVP certificates across vendors. The practical consulting output is: "this system uses AES-256-GCM which is covered by CMVP certificate #4735 (OpenSSL FIPS module)."

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| FIPS 140-3 two-tier annotation already in CBOM (`approved` / `non-approved`) | Shipped in Phase 52; this is the baseline that D-01 extends | — | Already exists |
| Static curated CMVP attestation table (algorithm → representative CMVP cert #, status: active/historical/revoked) | Federal clients expect "cite the certificate number"; static table is offline-capable and covers 95% of cases | MEDIUM | Existing `quirk/compliance/` pattern; mirror staleness gate approach |
| `certified` tier in CBOM FIPS annotation (`approved` / `certified` / `non-approved`) | Phase 52 D-01 explicitly deferred this third tier | LOW | Existing two-tier annotation in CBOM builder |
| Staleness CI gate for CMVP table (90-day cadence matching QRAMM model) | CMVP certificates do expire and get revoked; stale table misleads clients | LOW | Existing staleness gate pattern from `model_meta.py` |
| `quirk compliance status` output includes CMVP attestation coverage | Consultant CLI workflow; shows which algorithms have CMVP citations | LOW | Existing `compliance status` command |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live CMVP lookup option (cached, offline-fallback) | For clients with internet access, validate certificate status at scan time against NIST CSRC or third-party JSON API | HIGH | `hackIDLE/nist-cmvp-api` weekly JSON — fetch + cache locally; network call gated by config flag |
| CMVP certificate URLs in CBOM `externalReferences` | CycloneDX supports `externalReferences` per component; link to the NIST certificate page | MEDIUM | CBOM builder Pass-1 enrichment |
| PQC algorithm CMVP coverage tracking (ML-KEM, ML-DSA, SLH-DSA) | NIST PQC standards (FIPS 203/204/205) are new; CMVP is still validating modules; surface "no CMVP cert yet" status | MEDIUM | Add PQC entries to static table with `status: pending_validation` |
| Module-level grouping in CBOM — "5 algorithms covered by same module cert" | Reduces CBOM noise; shows common module ancestry | HIGH | CBOM builder restructuring; possible CycloneDX schema constraint |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time NIST CSRC web scraping | "Always current" | NIST CSRC HTML structure changes without notice; violates offline requirement for air-gapped engagements; brittle | Static table with 90-day staleness gate + optional cached JSON API lookup |
| Full CMVP database download on install | Comprehensive | CMVP DB is large (thousands of modules); slows install; most entries irrelevant to a given client | Curated static table of ~50 commonly encountered modules + algorithm-to-module mapping |
| Automatic CMVP status in real-time reports | "Zero-latency attestation" | CMVP web interface is not a public API; scraping rate-limited; breaks air-gapped model | Cache-first with manual refresh (`quirk compliance refresh-cmvp`) |

---

### Workstream 5: Release Engineering

Mature Python security tools use a consistent release engineering pattern: signed artifacts, a machine-readable CHANGELOG, a public vulnerability disclosure policy, and supply-chain provenance. This is the foundation for a future v5.0 GA tag.

**Industry standard (2025/2026):** PyPI Trusted Publishers (OIDC-based, no stored tokens) + `sigstore-python` attestations + `pyproject.toml`-driven build. CPython itself adopted Sigstore for artifact signing starting in Python 3.11. Homebrew formulas for Python tools use the `sha256` of the PyPI sdist tarball.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| `SECURITY.md` with coordinated disclosure policy and contact | GitHub "Security" tab grays out without it; reporters have no channel; standard for any public tool | LOW | None; write-only |
| `CODE_OF_CONDUCT.md` (Contributor Covenant or equivalent) | Required by most OSS community standards; GitHub shows warning without it | LOW | None; write-only |
| `CHANGELOG.md` in Keep-a-Changelog format (existing, started in v4.4) | Already exists; needs consistent maintenance and versioning discipline | LOW | Existing `CHANGELOG.md` |
| Semver version policy document (`docs/version-policy.md`) | Consultants need to know what constitutes a breaking change; clients on older versions need upgrade confidence | LOW | None; write-only |
| PyPI Trusted Publishers (OIDC, no stored API tokens) | Industry baseline; eliminates long-lived token risk in GitHub Actions secrets | MEDIUM | GitHub Actions release workflow; PyPI project settings |
| Signed wheel + sdist via `sigstore-python` attestations | Sigstore attestations are now on-by-default for Trusted Publisher releases on PyPI; no extra work beyond Trusted Publishers setup | LOW | Trusted Publishers — attestations are automatic |
| `tests/test_version.py` version-lock already in CI | Already shipped in v4.4; ensure it gates the release workflow | LOW | Existing test |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| GitHub Release automation script (CHANGELOG-driven) | Parse CHANGELOG.md for the current version's section → auto-populate GitHub Release description; reduces manual error | MEDIUM | GitHub CLI or GitHub Actions `gh release create` |
| GitHub Environments for PyPI production publish (separate from test) | Prevents accidental TestPyPI → PyPI publish; requires reviewer approval gate | LOW | GitHub Actions environment protection rules |
| GitHub Security Advisories (private reporting enabled) | GitHub-native private vulnerability reporting; researchers can report without emailing | LOW | Repository settings toggle |
| CycloneDX SBOM for QU.I.R.K. itself (dogfooding) | Ship QU.I.R.K.'s own CBOM as a release artifact — demonstrates the product + supply chain transparency | MEDIUM | Run `quirk` against its own repo source scanner output |
| `migration_planner.py` removal | Dead module flagged in v4.9 backlog; clean codebase before GA | LOW | Verify no imports; delete + CI gate |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| GPG key signing (traditional) | "Industry standard signing" | GPG web-of-trust is operationally complex; Sigstore keyless signing is the 2025 Python ecosystem standard; PyPI attestations via Trusted Publishers are automatic | Use Sigstore via PyPI Trusted Publishers; GPG optional addendum only |
| Semantic Release (automated version bumping from commit messages) | Reduces manual version management | Conventional Commit discipline across all contributors is hard to enforce; false-positive version bumps; opaque to reviewers | Manual version bump in pyproject.toml + `tests/test_version.py` lock — already working |
| Separate release branch (`release/v4.10`) | "Clean separation" | QU.I.R.K. is single-maintainer; branch-per-release adds merge overhead without value | Tag-based releases from `main`; protect main branch |

---

### Workstream 6: Public-Launch Polish

This is the "feel primetime" workstream. Consultants evaluate tools quickly — a broken quickstart or missing Docker image signals amateur tooling. The v4.10 goal is to make `pip install quirk` and `docker pull` paths feel as polished as mature tools like `truffleHog`, `Semgrep`, or `Trivy`.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| Published Docker image on Docker Hub or GHCR (`ghcr.io/org/quirk:v4.10.0`) | Consultants on locked-down machines (no pip) need `docker run quirk`; standard for security tools | MEDIUM | Dockerfile (verify current state), GitHub Actions release workflow |
| `docs/upgrade-guide.md` — v4.x to v4.10 migration path | Database schema changes across milestones (new columns, new tables); consultants upgrading need a single reference | MEDIUM | Audit schema changes since v4.0; `quirk db migrate` command or manual ALTER TABLE instructions |
| Marketing README — value prop, badges (PyPI version, CI status, license), quickstart in 3 commands | GitHub README is the first impression; security tools without badges and a working quickstart feel abandoned | LOW | Existing README; add shields.io badges + quickstart block |
| Sample CBOM output files in `examples/` | Consultants want to see the output before running a scan; reduces sales friction | LOW | Run `quirk` against chaos lab; save JSON+XML outputs |
| Homebrew tap (`homebrew-quirk` repo with formula) | macOS is the dominant consultant laptop OS; `brew install quirk` is a one-command install | MEDIUM | PyPI sdist sha256; Homebrew Ruby formula; separate tap repo |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Quickstart demo script (`scripts/demo.sh`) that spins up chaos lab + runs scan + opens dashboard | Shows the full product loop in < 2 minutes; conference/sales demo | MEDIUM | Wraps existing chaos lab + `quirk` CLI; requires lab.sh working cleanly |
| Sample HTML/PDF report in `examples/` | Visual evidence of report quality without running the tool; reduces friction for procurement | LOW | Run against chaos lab; save report artifact |
| `quirk doctor` upgrade check (version comparison vs PyPI latest) | Operators know when they're behind; reduces support burden | LOW | Existing `quirk doctor`; add `pip index versions quirk` check or PyPI JSON API call |
| Asciinema / terminal recording for README | Shows real CLI experience; embedding a terminal recording in README is now standard for CLI tools | LOW | Record `quirk` run against chaos lab |
| `v4.x → v4.10` migration: `quirk db migrate` CLI command | SQLite `ALTER TABLE ADD COLUMN` for new columns; idempotent; safer than manual SQL for operators | MEDIUM | Audit missing columns per version; implement migration runner |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Homebrew `homebrew-core` submission (official tap) | Maximum discoverability | Review process is slow (weeks), requires formula passes `brew audit --strict`; a third-party tap ships immediately and is simpler to maintain | Ship personal/org tap first; homebrew-core as future milestone |
| Interactive installer script (`curl | bash`) | Zero-friction install | Security tools should not encourage `curl | bash`; contradicts the tool's security posture messaging | `pip install quirk[all]` + Docker + Homebrew tap covers all install paths |
| SaaS signup / account registration in launch polish | "Complete product launch" | SaaS platform is explicitly a future milestone; adding registration flow now creates abandoned infrastructure | Document the SaaS roadmap in README; defer account management |
| Breaking DB migration (DROP/RENAME columns) | "Clean schema" | v4.x users have existing `quirk.db` files; breaking migration destroys scan history | Additive-only migrations (`ADD COLUMN` with defaults); never DROP in v4.x |
| Windows MSI / NSIS installer | Windows consultant support | Python pip on Windows works fine; MSI adds significant packaging complexity for no meaningful improvement over `pip install` | Document Windows pip install + PowerShell quickstart |

---

## Feature Dependencies

```
S/MIME Scanner
  └──requires──> ldap3 + impacket [identity] extras (existing, Phase 17)
  └──requires──> Python `cryptography` cert parsing (existing, core)
  └──requires──> CBOM Pass-1 pipeline (existing, Phase 35/42)
  └──enhances──> CMVP attestation (S/MIME signing algo → CMVP lookup)

AD CS Scanner
  └──requires──> ldap3 + impacket [identity] extras (existing, Phase 17/20)
  └──requires──> S/MIME cert classifier (shares algorithm classification)
  └──enhances──> CBOM Pass-1 (CA cert algorithm components)
  └──enhances──> 6-pillar scoring (new adcs_* evidence counters in identity pillar)

Report Injection Hardening
  └──requires──> Audit of all Jinja2 templates (one-time analysis task)
  └──enhances──> all report outputs (HTML, PDF, dashboard API)
  └──no new deps

CMVP Attestation
  └──requires──> Existing CBOM Phase-52 two-tier annotation (foundation)
  └──requires──> Existing compliance staleness gate pattern
  └──enhances──> CBOM Pass-1 (adds `certified` tier + externalReferences URL)
  └──enhances──> `quirk compliance status` CLI

Release Engineering
  └──requires──> PyPI project admin access
  └──requires──> GitHub repository settings (trusted publishers, environments, private reporting)
  └──enhances──> all downstream install paths (Homebrew formula reads PyPI sdist sha256)

Public-Launch Polish
  └──requires──> Release Engineering (Docker image + Homebrew formula need signed release first)
  └──requires──> Upgrade Guide (needs schema audit, done alongside DB migration work)
  └──enhances──> `quirk doctor` (version check is an additive feature)
```

### Dependency Notes

- **AD CS requires S/MIME cert classifier:** Both scanners parse X.509 certs via `cryptography`; implement S/MIME classifier first, then AD CS reuses the shared cert-parsing helper.
- **CMVP attestation requires Phase 52 baseline:** The two-tier `approved/non-approved` annotation must stay intact; CMVP adds a third tier, not a replacement.
- **Release Engineering gates Public-Launch Polish:** The Homebrew formula sha256 is computed from the PyPI sdist; Release Engineering must ship first in the milestone.
- **Report Injection Hardening is independent:** Can be implemented in any order; no scanner dependencies.

---

## v4.10 Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Report Injection Hardening | HIGH (security correctness) | LOW | P1 |
| SECURITY.md + CODE_OF_CONDUCT.md | HIGH (launch gate) | LOW | P1 |
| S/MIME LDAP discovery + cert classifier | HIGH (identity coverage gap) | MEDIUM | P1 |
| AD CS CA discovery + ESC1/ESC2/ESC3/ESC4/ESC6/ESC8 | HIGH (enterprise coverage) | HIGH | P1 |
| CMVP static attestation table + `certified` CBOM tier | HIGH (federal/compliance client value) | MEDIUM | P1 |
| PyPI Trusted Publishers + Sigstore attestations | HIGH (supply chain) | MEDIUM | P1 |
| Marketing README + badges | MEDIUM (launch polish) | LOW | P1 |
| Sample CBOM outputs in `examples/` | MEDIUM (sales friction) | LOW | P1 |
| Homebrew tap formula | MEDIUM (macOS install UX) | MEDIUM | P2 |
| Docker image (GHCR) | MEDIUM (locked-down env support) | MEDIUM | P2 |
| `docs/upgrade-guide.md` + `quirk db migrate` | MEDIUM (operator UX) | MEDIUM | P2 |
| CHANGELOG-driven GitHub Release automation | LOW (maintainer UX) | MEDIUM | P2 |
| Demo script + sample HTML/PDF report | MEDIUM (sales) | LOW | P2 |
| ESC5/ESC7 AD CS coverage | LOW (rarer in field) | HIGH | P3 |
| Live CMVP lookup (cached, optional) | LOW (online-only value) | HIGH | P3 |
| CMVP `externalReferences` URLs in CBOM | LOW | MEDIUM | P3 |
| CycloneDX SBOM for QU.I.R.K. itself | LOW | MEDIUM | P3 |
| Asciinema terminal recording | LOW | LOW | P3 |
| `quirk doctor` version check vs PyPI | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for v4.10 — blocking launch readiness goal
- P2: Should have in v4.10 — materially improves consultant and operator experience
- P3: Nice to have — defer to v5.0 or as a fast follow if bandwidth allows

---

## Competitor / Reference Tool Analysis

| Feature | Certipy (AD CS) | DigiCert S/MIME Linter | Trivy (release model) | QU.I.R.K. v4.10 Approach |
|---------|-----------------|------------------------|----------------------|--------------------------|
| AD CS template enumeration | Via LDAP, full ESC1–ESC16 | N/A | N/A | LDAP ESC1–ESC8 subset; offensive exploitation excluded |
| S/MIME cert analysis | No | Yes (linter, web UI) | N/A | LDAP discovery + cryptography lib parsing; agentless |
| FIPS/CMVP annotation | No | No | No | Static curated table + `certified` CBOM tier |
| Signing | No | No | Sigstore keyless | Sigstore via PyPI Trusted Publishers (automatic) |
| Homebrew | No (pip only) | N/A | Yes (homebrew-core) | Personal/org tap first |
| Docker image | No | N/A | Yes (official image) | GHCR in v4.10 |
| CHANGELOG | Minimal | N/A | Keep-a-Changelog | Existing `CHANGELOG.md` (started v4.4); enforce discipline |
| Vulnerability disclosure | No SECURITY.md | N/A | SECURITY.md present | Add SECURITY.md + GitHub private reporting |

---

## Sources

- RFC 8551 — S/MIME Version 4.0 Message Specification: https://datatracker.ietf.org/doc/html/rfc8551
- CA/Browser Forum S/MIME Baseline Requirements v1.0 (2023): https://cabforum.org/smime-br/
- DigiCert S/MIME Certificate Linter: https://www.digicert.com/smime-certificate-linter
- LDAP + S/MIME certificate publishing (SSL.com): https://www.ssl.com/how-to/ldap-integration-with-s-mime-certificates/
- Certipy (Python AD CS tool, certipy-ad on PyPI): https://github.com/ly4k/Certipy
- Certipy find — certificate enumeration (DeepWiki): https://deepwiki.com/ly4k/Certipy/2.1-find-certificate-enumeration
- AD CS ESC1–ESC8 (Vaadata blog): https://www.vaadata.com/blog/ad-cs-security-understanding-and-exploiting-esc-techniques/
- ESC9–ESC15 (SpecterOps GhostPack/Certify wiki + ly4k/Certipy wiki): https://github.com/ly4k/Certipy/wiki/06-%E2%80%90-Privilege-Escalation
- NIST CMVP validated modules search: https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules
- Third-party CMVP JSON API (hackIDLE/nist-cmvp-api): https://github.com/hackIDLE/nist-cmvp-api
- PyPI Trusted Publishers (OIDC): https://docs.pypi.org/trusted-publishers/
- Sigstore Python artifact signing: https://www.python.org/downloads/metadata/sigstore/
- PyPA pypi-publish GitHub Action: https://github.com/pypa/gh-action-pypi-publish
- Homebrew Releaser GitHub Action: https://github.com/marketplace/actions/homebrew-releaser
- Homebrew formula automation (Simon Willison): https://til.simonwillison.net/homebrew/auto-formulas-github-actions
- GitHub coordinated vulnerability disclosure: https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/about-coordinated-disclosure-of-security-vulnerabilities
- PDF injection via HTML rendering (HackTricks): https://book.hacktricks.xyz/pentesting-web/xss-cross-site-scripting/pdf-injection
- SSRF via PDF generators (Intigriti): https://www.intigriti.com/researchers/blog/hacking-tools/exploiting-pdf-generators-a-complete-guide-to-finding-ssrf-vulnerabilities-in-pdf-generators
- Post-Quantum S/MIME (DEV Community): https://dev.to/certera_/post-quantum-cryptography-for-dkim-pgp-and-smime-3ohm
- Chainguard FIPS 140-3 overview: https://www.chainguard.dev/supply-chain-security-101/fips-140-3-everything-you-need-to-date

---
*Feature research for: QU.I.R.K. v4.10 Launch Readiness*
*Researched: 2026-05-16*

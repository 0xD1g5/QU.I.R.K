# Stack Research — v4.10 Launch Readiness (NEW additions only)

**Domain:** Cryptographic inventory scanner — identity protocol expansion, report hardening, release engineering
**Researched:** 2026-05-16
**Confidence:** HIGH for S/MIME parsing, HTML sanitization, sigstore, CMVP feed; MEDIUM for AD CS (certipy conflict analysis); LOW for certipy programmatic API (CLI-centric design, no confirmed module-level API)

> This file covers ONLY new library additions for v4.10. The existing validated stack (sslyze, impacket, cyclonedx-python-lib, FastAPI, React + shadcn/ui, SQLite, etc.) is documented in PROJECT.md Key Decisions and is NOT repeated here.

---

## Feature Area 1: S/MIME Content Scanning

### Approach: `cryptography` pkcs7 module + stdlib `email` + `asn1crypto`

S/MIME messages are CMS-wrapped PKCS#7 structures. The `cryptography` package (already in core deps at `>=44.0`) gained full PKCS7SignatureBuilder and `pkcs7_decrypt_smime` support — **no new library is needed for the structural parsing layer.** `asn1crypto` (already a transitive dep of `cryptography`) provides lower-level `cms.ContentInfo.load()` for cases where `cryptography`'s high-level API doesn't expose an accessor (e.g., reading the `digestAlgorithms` field directly from `SignedData`).

IMAP retrieval uses stdlib `imaplib` + `email` (both stdlib, Python 3.11+, zero new deps). `.eml` corpus parsing also uses `email.message_from_bytes()`. The `email.generator` / `email.policy` APIs handle RFC 2822 multipart unwrapping to reach the `application/pkcs7-mime` or `application/pkcs7-signature` part.

### New Core Dep: None (zero new packages for S/MIME content parsing)

The parsing path uses:
- `cryptography>=44.0` (already in `[project.dependencies]`) — `pkcs7.load_pem_pkcs7_certificates()`, `pkcs7_decrypt_smime()`
- `asn1crypto==1.5.1` (already a transitive dep of `cryptography`) — `cms.ContentInfo.load()` for raw DER SignedData traversal; provides direct access to `signed_data['digest_algorithms']`, `signer_infos`, embedded cert list
- `imaplib` + `email` (stdlib) — IMAP fetch + MIME multipart unwrapping

**Why not M2Crypto:** Requires compiled OpenSSL bindings, no wheel on PyPI for macOS arm64, hostile to offline installs. The existing `cryptography` lib's hazmat PKCS7 API covers the same surface with pure-Python portability.

**Why not `python-smime` / `smime` on PyPI:** Last release 2017/2019; no longer maintained; asn1crypto-based but adds nothing beyond what is already available via direct asn1crypto access.

**Why not `endesive`:** Broader PDF/XAdES signing library; brings unnecessary scope; the scanner only needs to READ signed content, not produce it.

### New `[smime]` extras group

```toml
smime = []   # zero new pip deps — scanning uses cryptography + asn1crypto (transitive)
```

The extras group is declared to allow `quirk[smime]` to appear in documentation and `quirk doctor` output. The implementation note is that this extra is intentionally empty.

---

## Feature Area 2: Windows AD CS Live Connector

### Approach: impacket LDAP (already in `[identity]`) — no certipy-ad

**Decision: Do NOT add certipy-ad as a dependency.** Here is why:

certipy-ad 5.0.4 pins `cryptography~=42.0.8` and requires `Python>=3.12`. QUIRK currently requires `Python>=3.10` and pins `cryptography>=44.0`. The `~=42.0.8` pin from certipy-ad would **downgrade cryptography from 44.x to 42.x**, which is exactly the class of transitive conflict already documented in Key Decisions for the impacket/pyOpenSSL issue. Additionally, certipy-ad's programmatic API surface is CLI-centric — its internal modules are not designed for library import and there is no documented stable API.

**Decision: Use impacket LDAP directly** (already in `[identity]` extras at `impacket>=0.13.0,<0.14`) to query `CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=...` and enumerate CA objects at `CN=Certification Authorities`. This covers ESC1–ESC4 detection (the template-ACL and SAN-supply conditions) without needing certipy-ad. ESC5–ESC8 require either live RPC calls (DCOM/MSRPC) or relaying, which are offensive techniques not appropriate for QUIRK's read-only audit posture.

**What impacket LDAP covers for AD CS (read-only audit):**
- `msDS-OIDToGroupLink`, `msPKI-Certificate-Name-Flag`, `msPKI-Enrollment-Flag`, `msPKI-RA-Signature`, `pkiExtendedKeyUsage` attributes on template objects — sufficient for ESC1/ESC2/ESC3/ESC4 detection
- `cACertificate`, `cRLDistributionPoint`, `dNSHostName` on CA objects — CA discovery
- Enrollment ACLs via `nTSecurityDescriptor` — low-priv enrollment detection (ESC1 condition 3)

**New ldap_result to ADCS finding path:** The existing Kerberos scanner already authenticates via impacket AS-REQ. The AD CS scanner extends that to a subsequent LDAP bind (same credential flow) and performs paged LDAP searches.

### New package needed: None

`impacket>=0.13.0,<0.14` is already in `[identity]`. The AD CS scanner is added to the `identity` scanner surface. No new extras group needed — it is implicitly part of `[identity]`.

### Alternatives evaluated and rejected

| Approach | Problem |
|----------|---------|
| certipy-ad | Python 3.12+ required; pins `cryptography~=42.0.8` (would downgrade from 44.x); no stable library API |
| impacket-ADCS (micahvandeusen fork) | Unmaintained fork; last commit 2021; targets older impacket API; not on PyPI |
| certihound | Tiny project, no release activity 2024–2025; wraps certipy internals |

---

## Feature Area 3: HTML/PDF Report Injection Hardening

### Approach: `nh3` for HTML sanitization in Jinja2 template pipeline

The existing `_md_escape.py` (Phase 61 / REPORT-SAN-01) covers GFM markdown table cells. The deferred attack surface is adversary-controlled strings being passed to Jinja2 templates as `|safe` or rendered inside `<script>`/`<style>` contexts in `report.html.j2`. The fix has two layers:

**Layer 1 — Input sanitization at `_build_finding` chokepoint:** Add `nh3.clean()` call on `description`, `remediation`, and `service_detail` fields before they enter the finding dict. This is defense-in-depth: even if Jinja2 autoescape is correctly configured, no raw HTML from scanner output reaches the template.

**Layer 2 — Jinja2 autoescape audit:** The existing `html_renderer.py` already passes `select_autoescape(["html", "j2"])` to `Environment`. The audit confirms there are no `|safe` filters applied to scanner-controlled content. Any discovered `|safe` on user-controlled fields is replaced with explicit `nh3.clean()` before the `Markup()` wrapper.

### New Core Dep: `nh3>=0.2.17`

**Why nh3 over bleach:** bleach was officially deprecated January 2023. It continues to receive minimal security updates (latest 6.3.0, October 2025) but sits on top of `html5lib` which is also inactive. `nh3` is a Rust binding to the Ammonia sanitizer — approximately 20x faster than bleach, actively maintained (latest 0.3.3, February 2026), no C compile step needed (ships pre-built wheels for all major platforms including macOS arm64, Linux x86_64/aarch64, Windows). Same allowlist-based API as bleach.

**Why not lxml.html.clean.Cleaner:** `lxml>=6.0` is already in core deps but `lxml.html.clean` was **removed from lxml 5.2** and split into a separate package `lxml_html_cleaner` (which adds a new dep). nh3 is the cleaner path.

**Why not MarkupSafe.escape() alone:** `markupsafe.escape()` HTML-encodes everything including `<`, `>`, `&` — correct for plain-text values injected into HTML attributes. But remediation text may legitimately contain `<code>...</code>` markup in future reports. An allowlist sanitizer (nh3) is the durable choice.

```toml
# Add to [project.dependencies]
"nh3>=0.2.17",
```

No new extras group — this goes in core deps because all reports (TLS-only install) can potentially be injected.

---

## Feature Area 4: CMVP Attestation Feed

### Approach: httpx-based scraper against NIST CSRC HTML + hackIDLE/nist-cmvp-api static JSON as fallback

**Primary:** NIST CSRC does not expose a public JSON/REST API for CMVP. The validated modules search at `csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search/all` serves approximately 1,086 entries as an HTML table. QUIRK will scrape this via `httpx` (already in core deps at `>=0.28.0`) with BeautifulSoup4 for DOM parsing, caching the result locally in a JSON file with a 7-day TTL.

**Fallback / offline mode:** The community-maintained `nist-cmvp-api` project (hackIDLE/nist-cmvp-api) hosts a weekly-refreshed static JSON at `https://hackidle.github.io/nist-cmvp-api/api/modules.json` with per-certificate records including certificate number, vendor, module name, FIPS level, validation date, status (Active/Historical/Revoked), and extracted algorithm list. QUIRK can fall back to this endpoint when the NIST CSRC scrape fails or in offline mode. This is a third-party community scrape — rated MEDIUM confidence for production use, and its cache should be treated as advisory-only when the primary NIST scrape is available.

**What "CMVP attestation" means for QUIRK:** Phase 52 D-01 deferred `certified: true` annotations. The implementation adds a `_cmvp_lookup(vendor: str, module: str) -> Optional[CmvpRecord]` helper that returns certificate number, validation date, FIPS level, and active status when a match is found. Finding dicts get `"cmvp_cert"`, `"cmvp_status"`, `"cmvp_fips_level"` fields. Report templates render a "FIPS Validated" badge vs "FIPS Annotated" distinction.

### New Core Dep: `beautifulsoup4>=4.13.0`

httpx is already in core deps. BeautifulSoup4 is needed to parse the NIST CSRC HTML table.

```toml
# Add to [project.dependencies]
"beautifulsoup4>=4.13.0",
```

Note: `lxml` (already a core dep) can serve as the BS4 parser via `BeautifulSoup(html, "lxml")` — no additional parser package needed.

**Rate limiting:** NIST CSRC has no published rate limit. The scraper will use a single bulk fetch of the `/all` endpoint (one HTTP request) and cache aggressively (7-day TTL, stored in `~/.quirk/cmvp_cache.json`). This is far safer than per-certificate polling.

**Staleness gate:** The CMVP cache file carries a `last_fetched` ISO timestamp. The existing staleness CI pattern from `quirk/compliance/__init__.py` (365-day cadence, `STALENESS_THRESHOLD_DAYS`) is extended to also gate the CMVP cache via `quirk/qramm/model_meta.py`-style enforcement.

---

## Feature Area 5: Release Engineering

### Approach: sigstore + GitHub Actions + towncrier (dev-only tools)

**Artifact signing:** Use `sigstore>=4.2.0` CLI + `gh-action-sigstore-python` GitHub Action. Sigstore 4.2.0 (January 2026) supports Rekor v2 transparency log and keyless OIDC signing via GitHub Actions ambient credentials — no GPG key management, no key rotation ceremony. PyPI's `pypa/gh-action-pypi-publish` automatically attaches Sigstore attestations when publishing from a trusted publisher (zero extra configuration in the publish step).

**Changelog tooling:** Use `towncrier>=24.8.0`. towncrier is used by pip, pytest, attrs, and Twisted — it is the dominant CHANGELOG automation tool in the CPython ecosystem. News fragments go in `changelog.d/`, towncrier merges them into `CHANGELOG.md` at release time. This aligns with the existing `CHANGELOG.md` established in Phase 37.

**Version policy:** `pyproject.toml` already uses `version = "4.4.0"` (static). The release script will use `python -m build` + `twine check dist/*` + `sigstore sign dist/*`. No version plugin needed — static version string is updated by the release script and locked by `tests/test_version.py`.

**SECURITY.md + CODE_OF_CONDUCT.md:** Plain Markdown files at repo root. No tooling needed. SECURITY.md follows the GitHub advisory format; CODE_OF_CONDUCT.md follows Contributor Covenant 2.1.

### New Dev Dependencies (never in `[project.dependencies]`)

| Tool | Version | Purpose |
|------|---------|---------|
| sigstore | >=4.2.0 | Keyless wheel + sdist signing via Rekor v2 |
| towncrier | >=24.8.0 | News-fragment-based CHANGELOG generation |
| build | >=1.2.0 | PEP 517 sdist + wheel builder (`python -m build`) |
| twine | >=6.1.0 | Pre-publish artifact validation (`twine check`) |

None of these are added to `pyproject.toml` `[project.optional-dependencies]`. They are installed in CI and documented in `docs/release-process.md` for human release engineers.

**Why not hatch/flit as build backend:** `pyproject.toml` already uses `setuptools>=68` as build backend. Switching backends is a v5 concern, not v4.10.

**Homebrew formula:** A private tap (`homebrew-quirk`) is the target. Formula structure wraps `pip install quirk[all]` inside a virtualenv using Homebrew's standard Python formula pattern. The formula references the PyPI-published wheel — it is NOT a source build. Implementation is a single `Formula` Ruby file. No new Python tooling needed.

**Docker image:** Multi-stage Dockerfile: `python:3.11-slim` base, `pip install quirk[all]` in runtime layer, ENTRYPOINT `["quirk"]`. Published to GHCR (`ghcr.io/quantum-apps/quirk`). No new Python deps. The existing `quantum-chaos-enterprise-lab/` lab Dockerfile pattern provides the precedent.

---

## Feature Area 6: Chaos Lab Fidelity (Phase 999.83)

No new Python library additions required. The 4 bugs (gitea root-user crash, minio-seed KMS, vault-seed rsa-1024, mysql `--skip-ssl` removed) are all Docker Compose configuration fixes. The fixes already have full root-cause analysis in `.planning/phases/999.83-chaos-lab-service-config-drift/CONTEXT.md`.

**Docker image pins being formalized:**
- `gitea/gitea:1.21` (or newer explicit pin, no `:latest`)
- `minio/minio:RELEASE.2024-*` (explicit release tag)
- `mysql:8.0` (pinned; avoids 8.4 `--skip-ssl` removal)
- `hashicorp/vault:1.15` or similar (explicit pin)

These are Docker Compose `image:` values, not Python deps.

---

## Summary: New Python Packages for v4.10

| Package | Version | New/Existing | Extra | Rationale |
|---------|---------|-------------|-------|-----------|
| `nh3` | `>=0.2.17` | **NEW core dep** | (core) | HTML sanitization for report injection hardening; replaces deprecated bleach |
| `beautifulsoup4` | `>=4.13.0` | **NEW core dep** | (core) | CMVP HTML table scraping; uses existing lxml parser backend |
| `cryptography` | `>=44.0` (existing) | Existing | (core) | S/MIME PKCS7 parsing; pkcs7 module already covers the need |
| `asn1crypto` | `~=1.5.1` (transitive) | Existing transitive | — | Raw CMS SignedData field access; no explicit dep needed |
| `impacket` | `>=0.13.0,<0.14` (existing) | Existing | `[identity]` | AD CS LDAP enumeration |
| `httpx` | `>=0.28.0` (existing) | Existing | (core) | CMVP NIST CSRC HTTP fetch |

**New extras groups:**
- `smime = []` — declared but empty; zero new pip deps; surface for `quirk doctor` advisory

**Total new pip deps: 2** (`nh3`, `beautifulsoup4`)

---

## Version Compatibility Matrix

| Package | QUIRK Constraint | Conflict Risk |
|---------|-----------------|--------------|
| `cryptography>=44.0` | Core dep (existing) | certipy-ad pins `~=42.0.8` — **certipy-ad EXCLUDED for this reason** |
| `impacket>=0.13.0,<0.14` | `[identity]` extras (existing) | certipy-ad pins `~=0.13.0` — compatible range but moot since certipy-ad is excluded |
| `nh3>=0.2.17` | New core dep | No known conflicts; pure Rust wheel, no C deps |
| `beautifulsoup4>=4.13.0` | New core dep | No conflicts; lxml already present as parser backend |
| `lxml>=6.0` | Core dep (existing) | `lxml.html.clean` removed in 5.2+ — do NOT use lxml for sanitization; use nh3 instead |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `certipy-ad` | Python 3.12+ required; `cryptography~=42.0.8` pin downgrades from 44.x; CLI-centric, no library API | `impacket` LDAP queries against AD CS LDAP schema directly |
| `bleach` | Deprecated January 2023; depends on unmaintained `html5lib` | `nh3>=0.2.17` |
| `lxml.html.clean` / `lxml_html_cleaner` | `lxml.html.clean` removed from lxml 5.2+; separate package adds unnecessary dep | `nh3` |
| `M2Crypto` | No pre-built wheel for macOS arm64; hostile to offline installs; requires OpenSSL dev headers at build time | `cryptography` pkcs7 module (already in core) |
| `python-smime`, `smime` PyPI packages | Last released 2017–2019; unmaintained | `cryptography` + `asn1crypto` (already present) |
| `hatch` / `flit` as build backend | Switching build backend is disruptive; setuptools>=68 is already validated | Keep setuptools; use `python -m build` frontend |
| `towncrier` in `pyproject.toml` optional-dependencies | It is a dev tool, not a runtime library | Document in `docs/release-process.md`; install via CI step |
| `impacket-ADCS` (micahvandeusen fork) | Unmaintained since 2021; not on PyPI; targets stale impacket API | Upstream `impacket` LDAP with direct schema queries |
| Per-certificate CMVP polling | NIST has no documented API; per-cert HTTP polling of ~4000+ certificates would be aggressive and fragile | Bulk fetch of `/all` endpoint (one request), 7-day cache |

---

## React Frontend: No Changes

v4.10 does not introduce new React routes or components beyond integration of AD CS and S/MIME findings into the existing identity tab and findings table. The existing `package.json` stack (React 19, Recharts, Cytoscape, shadcn/ui Radix primitives, Vitest, MSW) is sufficient.

AD CS findings surface on the existing `/identity` route. S/MIME findings follow the same `identity_findings[]` Pydantic pattern established in Phase 21. No new npm packages are needed.

---

## Sources

- `/pyca/cryptography` via Context7 — pkcs7 module coverage, PKCS7SignatureBuilder, pkcs7_decrypt_smime confirmed current (HIGH confidence)
- pypi.org/project/certipy-ad — version 5.0.4, Python >=3.12, `cryptography~=42.0.8` pin confirmed (HIGH confidence)
- deepwiki.com/ly4k/Certipy/1.1-installation-and-dependencies — full dependency table including impacket~=0.13.0 confirmed (HIGH confidence)
- pypi.org/project/sigstore — version 4.2.0 (January 2026), Python >=3.10, keyless OIDC signing confirmed (HIGH confidence)
- pypi.org/project/nh3 — version 0.3.3 (February 2026), Rust binding to Ammonia, replaces deprecated bleach (HIGH confidence)
- github.com/mozilla/bleach/issues/698 — official deprecation notice January 2023 (HIGH confidence)
- github.com/hackIDLE/nist-cmvp-api — weekly-refreshed static JSON, latest release May 15 2026, confirmed fields (MEDIUM confidence — community project)
- csrc.nist.gov validated modules /all endpoint — HTML-only, no API; ~1,086 entries, one bulk request feasible (HIGH confidence)
- pypi.org/project/asn1crypto — version 1.5.1, no external deps, production/stable (HIGH confidence)
- pypi.org/project/towncrier — latest August 2025, used by pip/pytest/attrs (HIGH confidence)

---

*Stack research for: QU.I.R.K. v4.10 Launch Readiness*
*Researched: 2026-05-16*

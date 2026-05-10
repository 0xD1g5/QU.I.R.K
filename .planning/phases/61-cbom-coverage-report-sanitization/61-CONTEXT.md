# Phase 61: CBOM Coverage + Report Sanitization - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 61 closes audit blockers CR-01, CR-02, and CR-07 by addressing two
distinct sub-problems in the CBOM pipeline and report renderer:

- **CBOM-COVER-01 (CR-01):** `quirk/cbom/builder.py` Pass-1 currently
  registers zero algorithm components for 12+ protocol families (database,
  registry/container, source, ssh-weak, storage-s3, broker subfamilies, email
  subfamilies, vault, identity-secondary). Each family needs a dedicated or
  corrected Pass-1 branch that extracts the best available algorithm name from
  the endpoint's fields.

- **CBOM-COVER-02 (CR-02):** VAULT endpoints fall through to the TLS `else`
  branch in Pass-1 (instead of a dedicated VAULT branch) and are skipped
  entirely by DAR_SKIP_PROTOCOLS in Pass-2/3. The fix gives VAULT its own
  Pass-1 branch; Pass-2/3 remain correctly skipped (transit keys are not X.509
  certificates).

- **REPORT-SAN-01/02 (CR-07):** `quirk/reports/technical.py:97` directly
  interpolates adversary-controllable fields (host, title, description,
  recommendation) into GFM table rows with no escaping. A shared escape
  utility and a pytest corpus fixture close the injection surface.

**In scope:** `quirk/cbom/builder.py` (Pass-1 branches), `quirk/reports/technical.py`
(escape), `quirk/reports/_md_escape.py` (new utility), targeted scanner-level
field population (`db_connector.py`, `aws_connector.py`) for DATABASE/S3 where
no algo field exists today; new tests in `tests/`.

**Out of scope:** CBOM Pass-2/3 structural changes beyond VAULT consistency,
executive.py table injection (prose bullets, lower risk, deferred), HTML/PDF
rendering injection (`cbom-intel-reports/WR-01/WR-02` deferred), SOURCE rule-ID
DES→3DES mapping fix (CR-03 deferred — separate phase).

</domain>

<decisions>
## Implementation Decisions

### D-01: VAULT Pass-1 Branch

Add a dedicated `elif ep.protocol == "VAULT":` branch in Pass-1 immediately
before the `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", ...) pass` block.
Read `ep.cert_pubkey_alg` directly (vault_connector.py already populates it with
the transit key type, e.g. `"rsa-2048"`, `"aes256-gcm96"`, `"ed25519"`):

```python
elif ep.protocol == "VAULT":
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

This mirrors the SAML/KERBEROS/DNSSEC pattern exactly (lines 432–441 in
builder.py). VAULT stays in `DAR_SKIP_PROTOCOLS` for Pass-2 and Pass-3
(no cert/protocol components — transit keys are not X.509 certs). This makes
all three passes consistent: Pass-1 has its own VAULT branch; Pass-2/3 skip it
via `DAR_SKIP_PROTOCOLS`.

### D-02: VAULT Golden Snapshot

The SC-2 "byte-identical" requirement is satisfied by comparing the **sorted
list of `(component.name, str(component.type))` tuples** from the CBOM's
component list — not the full JSON (which includes non-deterministic UUIDs/
`serialNumber`). The fixture creates 3 deterministic VAULT endpoints:
- `cert_pubkey_alg="rsa-2048"`, `cert_pubkey_size=2048`
- `cert_pubkey_alg="aes256-gcm96"`, `cert_pubkey_size=256`
- `cert_pubkey_alg="ed25519"`, `cert_pubkey_size=None`

Call `build_cbom(endpoints)`, extract the sorted component name/type list,
serialize to `tests/fixtures/cbom_vault_golden.json` using `json.dumps()`,
then assert identity on re-run. Test file: `tests/test_cbom_vault_consistency.py`.

### D-03: CONTAINER Pass-1

Change the CONTAINER branch from `pass` to register `ep.cipher_suite`
(the crypto library name, e.g. `"openssl"`, `"libssl"`) as the algorithm name:

```python
elif ep.protocol == "CONTAINER":
    if ep.cipher_suite:
        _register_algorithm(ep.cipher_suite, algo_registry)
```

CycloneDX 1.6 allows algorithm component names to reference library names
(the presence of a crypto library IS the cryptographic asset). The `cipher_suite`
field is already set to the library name by `container_scanner.py:100`.

### D-04: DATABASE (MYSQL / POSTGRESQL / RDS)

**MYSQL:** `db_connector.py` stores the SSL cipher in `service_detail` as
`"MySQL/<cipher>-ok"` or `"MySQL/<cipher>-weak"`. Extract the cipher in the
builder by parsing `service_detail` in a new MYSQL branch:

```python
elif ep.protocol == "MYSQL":
    detail = ep.service_detail or ""
    if "/" in detail:
        cipher_part = detail.split("/", 1)[1]  # "AES256-SHA-ok"
        cipher_name = cipher_part.rsplit("-", 1)[0] if cipher_part.endswith(("-ok", "-weak")) else cipher_part
        if cipher_name and cipher_name.upper() not in ("SSL-OFF", "UNSPECIFIED"):
            _register_algorithm(cipher_name, algo_registry)
```

**POSTGRESQL:** PostgreSQL endpoints don't carry the negotiated cipher. Use
`ep.cert_pubkey_alg` if set (RDS populates it; bare Postgres may not). If
neither field is available on a given endpoint, skip cleanly:

```python
elif ep.protocol in ("POSTGRESQL", "RDS"):
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

Remove MYSQL/POSTGRESQL/RDS from the explicit `pass` elif. They stay in
`DAR_SKIP_PROTOCOLS` for Pass-2/3.

### D-05: S3 / AZURE_BLOB

AWS S3 stores the encryption posture in `service_detail` ("S3/sse-s3",
"S3/sse-kms-aws", "S3/sse-kms-cmk", "S3/unencrypted"). Map encrypted
variants to `"AES-256"` in a dedicated Pass-1 branch:

```python
elif ep.protocol in ("S3", "AZURE_BLOB"):
    detail = ep.service_detail or ""
    if "unencrypted" not in detail.lower():
        _register_algorithm("AES-256", algo_registry)
```

`"S3/unencrypted"` legitimately has no crypto to catalog — skip rather than
emit a sentinel. AZURE_BLOB uses the same convention (CMEK → AES-256 at rest).

Remove `"S3"` and `"AZURE_BLOB"` from the `pass` elif. Keep both in
`DAR_SKIP_PROTOCOLS` for Pass-2/3.

### D-06: SOURCE Fallback

`_extract_algo_from_rule_id()` returns `None` for rule IDs it doesn't
recognize. Add a fallback: if `algo_hint is None` and `ep.cipher_suite` is
non-empty, register `ep.cipher_suite` directly (the raw semgrep rule ID
fragment). This ensures SOURCE always emits something when the scanner found
a rule, even for rules not yet in the hint map:

```python
elif ep.protocol == "SOURCE":
    algo_hint = _extract_algo_from_rule_id(ep.cipher_suite)
    algo_to_register = algo_hint or ep.cipher_suite  # fallback to raw rule ID
    if algo_to_register:
        _register_algorithm(algo_to_register, algo_registry)
```

### D-07: SSH Branch Fallback

The SSH branch already handles `ssh_audit_json` correctly. Add a supplemental
registration at the end of the SSH block: also register `ep.cert_pubkey_alg`
if set (the SSH host key algorithm). This ensures ssh-weak endpoints that have
a non-empty `cert_pubkey_alg` but a null/empty `ssh_audit_json` still emit at
least one component:

```python
# After the section loop (still inside elif ep.protocol == "SSH":):
if ep.cert_pubkey_alg:
    _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

`algo_registry` deduplicates by `bom_ref`, so registering the same algorithm
from both sources is harmless.

### D-08: Broker Plaintext Subfamilies

KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN currently fall to the TLS `else` branch
with no cipher data. These protocols legitimately have no cryptographic
algorithm to catalog (no encryption is the finding). Add them to the
`MOTION_PLAINTEXT_PROTOCOLS` frozenset as a Pass-1 skip guard to be explicit
(they are already in the set — confirm this is handled before the else branch
or add an explicit elif before the else that `continue`s). The per-family
coverage test for the "broker" family uses a **KAFKA-TLS** endpoint (which DOES
produce algo components via the TLS else branch using `ep.cipher_suite`).

### D-09: Markdown Escape Utility

Create `quirk/reports/_md_escape.py` with a single function:

```python
def md_cell(value) -> str:
    """Escape a value for safe interpolation into a GFM table cell."""
    if value is None:
        return ""
    text = str(value)
    # Collapse newlines to space (row-break injection)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    # Escape pipe (column-break injection)
    text = text.replace("|", "\\|")
    # Strip ASCII control chars (keep printable + space)
    text = "".join(c for c in text if c == " " or c >= "\x20")
    return text
```

### D-10: Apply md_cell in technical.py

Apply `md_cell()` to every adversary-controllable field interpolated into
markdown table rows in `technical.py`. The safe-vs-unsafe boundary:

- **Safe (no escaping needed):** static strings from `cfg` (assessment name,
  owner), computed booleans ("YES"/"NO"), numeric counts/scores, Python
  datetime strings.
- **Unsafe (must wrap in `md_cell()`):** `e.host`, `e.port` (when string),
  `e.tls_version`, `e.cipher_suite` sample, `e.tls_supported_versions`,
  `e.tls_enum_notes`, `e.scan_error`, blocker strings, `_service_detail(e)`,
  and ALL finding fields: `host`, `title`, `desc`, `rec`, `description`.

The primary target is the Findings table row (line 97 in current code). Also
apply to the Service Inventory, TLS Capabilities, and TLS Blockers table rows
since these all interpolate `e.host` and other scan data.

### D-11: executive.py — Deferred

`executive.py` uses bullet-point prose, not table rows. The migration
recommendation section (lines 228–232) interpolates `r.get('host')` into a
bullet, which is lower risk (pipe injection in prose renders as a literal
character, not a broken table). Defer executive.py escaping to v4.9 tech-debt
unless the REPORT-SAN-02 adversarial corpus test finds a concrete break.

### D-12: REPORT-SAN-02 Adversarial Corpus Test

Create `tests/test_report_sanitization.py`. Build adversarial scan data where:
- `host = "bad.host.com|injected-col"`
- `title = "Finding\nWith Newline"`
- `description = "Desc with | multiple | pipes"`
- `recommendation = "Fix\r\nwith CRLF"`

Call `build_tech_markdown(cfg, [ep], [finding])` and assert:
1. Output contains no unescaped bare `|` in data cells.
2. Every line that starts with `|` is a valid table row (split by `|` has
   consistent column count).
3. The output parses as valid GFM (a simple column-count check — no new
   dependency needed).

### D-13: CBOM Coverage Test Structure

Create `tests/test_cbom_coverage.py`. Use a **parametrized pytest fixture**
over the 12+ protocol families. For each family, construct a minimal synthetic
`CryptoEndpoint` object (using the ORM class or a `MagicMock` with the relevant
fields set), call `build_cbom([ep])`, and assert `len(algo_components) >= 1`
where `algo_components` are the `CRYPTOGRAPHIC_ASSET` type components.

**No chaos lab required** — pure Python fixtures, deterministic, runs in CI.

The families to parametrize over (each as a named `pytest.param` with `id=`):
`database-mysql`, `database-postgres`, `database-rds`, `container`, `source`,
`ssh-weak`, `storage-s3`, `storage-azure`, `kafka-tls`, `email-starttls`,
`vault`, `dnssec`, `saml`, `kerberos`

### D-14: Audit Ledger Updates

After phase completion, flip these rows to `[x] closed` in
`.planning/audit-2026-05-08/AUDIT-TASKS.md`:
- `cbom-intel-reports/CR-01` (CBOM Pass-1 zero algo)
- `cbom-intel-reports/CR-02` (VAULT TLS branch fallthrough)
- `cbom-intel-reports/CR-07` (markdown injection)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CBOM Pipeline
- `quirk/cbom/builder.py` — Pass-1 dispatch chain (lines 375–463); protocol
  constants `DAR_SKIP_PROTOCOLS` and `MOTION_PLAINTEXT_PROTOCOLS` (lines 45–54);
  `_register_algorithm()` helper (lines 340–348); `_decompose_cipher_suite()`
  for TLS else branch
- `quirk/cbom/classifier.py` — upstream classifier that produces `CryptoEndpoint`
  protocol labels; consult when verifying what protocol string each scanner produces
- `quirk/cbom/writer.py` — CycloneDX 1.6 JSON/XML serializer; UUID/`serialNumber`
  instability means golden snapshots must compare component data, not full output

### Scanner Field Conventions (for CBOM coverage fixes)
- `quirk/scanner/vault_connector.py` — sets `cert_pubkey_alg` to transit key
  type (e.g., "rsa-2048", "aes256-gcm96"); `cert_pubkey_size` also populated
- `quirk/scanner/container_scanner.py:100` — sets `cipher_suite=name`
  (library name like "openssl"), `tls_version=version`
- `quirk/scanner/db_connector.py` — MySQL: cipher in `service_detail` as
  `"MySQL/<cipher>-ok"` (lines ~244–258); PostgreSQL: no cipher field, only
  ssl-enforced/ssl-off status in `service_detail`; `cert_pubkey_alg` not set
  for bare Postgres
- `quirk/scanner/aws_connector.py` — S3: encryption posture in `service_detail`
  as "S3/sse-s3", "S3/sse-kms-aws", "S3/sse-kms-cmk", "S3/unencrypted"
  (lines ~252–263); `cert_pubkey_alg` not set for S3 endpoints

### Report Renderer
- `quirk/reports/technical.py` — `build_tech_markdown()` (lines 24–100);
  Findings table row at line 97 is the primary injection point; Service
  Inventory, TLS Capabilities, and TLS Blockers tables also interpolate scan data
- `quirk/reports/executive.py` — prose/bullet output; lower injection risk;
  `r.get('host')` in migration recs (line 231) is deferred per D-11

### Audit + Requirements
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — CR-01, CR-02, CR-07 rows
  (lines 141–147); flip to `[x] closed` after phase
- `.planning/REQUIREMENTS.md` — CBOM-COVER-01, CBOM-COVER-02, REPORT-SAN-01,
  REPORT-SAN-02 (lines 56–59)
- `.planning/ROADMAP.md` §Phase 61 — Success Criteria 1–4 are the acceptance
  gates

### Existing Tests to Extend
- Check for `tests/test_cbom_builder.py` — avoid duplicating existing Pass-1
  fixtures; extend with new protocol families rather than replacing
- Check for `tests/test_report_*.py` — check for existing report render tests
  before creating new file

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_register_algorithm(name, registry, key_size=None)` at builder.py:340 — the
  canonical algo registration helper; call it from every new Pass-1 branch
- `_decompose_cipher_suite(cipher)` — already handles TLS cipher strings in the
  TLS else branch; reusable for any branch that has a standard TLS cipher string
- SAML/KERBEROS/DNSSEC Pass-1 branches (builder.py:432–441) — the exact 3-line
  pattern to copy for VAULT: single `if ep.cert_pubkey_alg:` guard wrapping one
  `_register_algorithm()` call

### Established Patterns
- All 12+ zero-algo families have their best-available algo data in ONE of:
  `ep.cert_pubkey_alg` (VAULT, SSH fallback, RDS, DNSSEC), `ep.cipher_suite`
  (CONTAINER library name, SOURCE rule ID fallback), or `ep.service_detail`
  (MYSQL cipher, S3 encryption posture). No new scanner fields needed.
- `md_cell()` is a new utility; the import pattern in reports modules is
  `from quirk.reports._md_escape import md_cell` (private module by convention)
- The `MOTION_PLAINTEXT_PROTOCOLS` frozenset (builder.py:45) already
  distinguishes plaintext broker protocols — adding an explicit guard for them
  in Pass-1 is additive and doesn't touch Pass-2/3 logic

### Integration Points
- `build_cbom()` in builder.py is the sole entry point called by `writer.py`
  and `scan.py`; all Pass-1 changes are internal to `build_cbom()` with no
  caller API changes
- `build_tech_markdown()` in technical.py is called from `quirk/reports/writer.py`
  (report generation); adding `md_cell()` wrapping is transparent to callers
- CycloneDX 1.6 schema validation runs in `writer.py:70` — any new algorithm
  component must pass schema validation; verify by running the existing CBOM
  test suite after changes

</code_context>

<specifics>
## Specific Ideas

- The VAULT golden snapshot (D-02) compares a sorted list of `(name, type)`
  tuples serialized to JSON — this sidesteps the non-deterministic `serialNumber`
  UUID in the CycloneDX output without any special patching.
- `md_cell()` is named for clarity: "a value safe for a markdown table cell".
  The function handles `None` → `""` so callers don't need pre-guards.
- The per-family coverage test (D-13) should use `@pytest.mark.parametrize`
  with named IDs (e.g., `pytest.param(..., id="vault")`) so failures identify
  the specific protocol family by name in CI output.
- The adversarial corpus fixture (D-12) does NOT need an external markdown
  parser — a column-count check (split row by `|`, assert consistent count)
  is sufficient and adds no new dependencies.

</specifics>

<deferred>
## Deferred Ideas

- **executive.py markdown injection (D-11):** `r.get('host')` and bullet prose
  interpolation deferred to v4.9 tech-debt unless the REPORT-SAN-02 corpus test
  finds a concrete break in the executive report.
- **SOURCE DES→3DES mapping fix (CR-03):** The rule-ID hint map in
  `_extract_algo_from_rule_id()` maps DES variants incorrectly. This requires
  careful remapping and is a separate audit item (CR-03 has no assigned phase).
- **cbom-intel-reports/WR-01/WR-02 (PDF render errors):** PDF-layer issues,
  not CBOM or markdown report issues. Out of scope for this phase.
- **CLOUD_SQL / KUBERNETES Pass-1 branches:** No reliable algo field in scan
  data today. Revisit if a future scanner phase populates those fields.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 61-cbom-coverage-report-sanitization*
*Context gathered: 2026-05-10*

# Phase 57: Scanner Security Hardening - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 57 closes the six audit blockers (`scanners-protocol/CR-01..CR-06`) so every protocol
scanner is safe to point at an untrusted target. The phase delivers:

- **CR-01 (HARDEN-SCAN-01):** JWKS fetch in the JWT scanner uses TLS verification by default;
  disabling it requires an explicit YAML opt-in *and* emits a HIGH advisory finding.
- **CR-04 (HARDEN-SCAN-02):** SAML metadata fetcher routes through a shared URL-allowlist
  helper that rejects RFC1918, link-local, loopback, `file://`, and cloud-metadata IPs unless
  `--allow-internal-targets` is set.
- **CR-02 (HARDEN-SCAN-03):** Source scanner validates `repo_path` against shared
  subprocess-input helper before invoking semgrep.
- **CR-03 (HARDEN-SCAN-04):** Container scanner validates `image_ref` (registry/image:tag
  regex, no `dir:/`, `file://`, no shell metacharacters) before invoking syft.
- **CR-05 (HARDEN-SCAN-05):** Broker scanner ships **no** default credentials. `guest:guest`
  Basic-auth is removed; per-target opt-in lives in YAML keyed by `host:port`, with passwords
  pulled from environment variables.
- **CR-06 (HARDEN-SCAN-06):** Broker management API + Redis probes default to TLS-required;
  `ssl_cert_reqs="none"` is removed; cleartext probes require `--allow-cleartext-broker-probe`
  and emit a HIGH advisory finding per affected target.

**In scope:** the six requirements above and any wiring needed to surface their findings,
config knobs, and rejection rows.

**Out of scope:** Dashboard API hardening (Phase 58), scanner CBOM coverage gaps (different
phase), refactoring scanners not on the CR-01..CR-06 list.

</domain>

<decisions>
## Implementation Decisions

### Shared Helpers (Area 1)

- **D-01:** Create `quirk/util/url_allowlist.py` with `validate_external_url(url, *,
  allow_internal: bool = False) -> ValidationResult`. Used by both the SAML scanner
  (CR-04) and the broker management-API probe (CR-06). Rejects RFC1918, link-local,
  loopback, `file://`, and cloud-metadata IPs (`169.254.169.254`, `fd00:ec2::254`)
  unless `allow_internal=True`. Single test suite covers all forbidden categories once.
- **D-02:** Create `quirk/util/subprocess_input.py` with two sibling functions:
  `validate_repo_path(p) -> ValidationResult` (no shell metacharacters, no `..`, must be
  an existing local directory) and `validate_image_ref(r) -> ValidationResult` (regex
  registry/image:tag form, no `dir:/`, no `file://`, no shell metacharacters). Different
  threat models, shared module — no `kind` enum.
- **D-03:** ValidationResult shape is consistent across both helpers: `(ok: bool,
  reason: str, redacted_preview: str)`. Reason codes are a fixed enum (e.g.
  `shell_metachar`, `path_traversal`, `scheme_prefix`, `internal_ip`,
  `metadata_service_ip`, `loopback`, `nonexistent_path`).

### Config Knob Shape (Area 2)

- **D-04:** YAML-first with CLI override. Add a `security:` block to
  `quirk/config_template.yaml`:
  ```yaml
  security:
    allow_internal_targets: false
    allow_cleartext_broker_probe: false
    allow_insecure_jwks: false
  ```
  Each YAML knob has a matching CLI flag (`--allow-internal-targets`, etc.) that
  overrides per-run. Pattern matches the existing `apply_targets_file_override` precedent
  in `quirk/util/targets.py`.
- **D-05:** Broker credentials use a YAML map keyed by `host:port`. Default behavior
  probes anonymously; credentials are sent **only** to listed hosts. Passwords are
  pulled from environment variables, never inline in YAML:
  ```yaml
  broker_credentials:
    "rabbit.lab:15672":
      user: "admin"
      pass_env: "RABBIT_LAB_PASS"
  ```
  No CLI override for credentials — this is intentional to keep secrets out of shell
  history. If `pass_env` is unset at scan time, the credential probe is skipped (not
  errored — the host falls back to anonymous probing).

### Rejection Rows (Area 3)

- **D-06:** Reuse the existing `CryptoEndpoint.scan_error_category` column (Phase 41 D-11).
  Add `invalid_input` as a fifth allowed value alongside
  `missing_extra|timeout|exception|config`. No new table, no migration beyond extending the
  doc-string.
- **D-07:** Rejected inputs write a `CryptoEndpoint` row with `target=<redacted preview>`,
  `scan_error_category="invalid_input"`, and `scan_error="<reason_code>"`. The subprocess
  is **never invoked** for rejected inputs.
- **D-08:** Stored value is reason code + 32-character redacted preview (control chars
  stripped, then truncated). Forensically useful, but bounded to prevent accidental
  exfiltration of pasted secrets or full traversal payloads.

### HIGH Advisory Findings (Area 4)

- **D-09:** Each opt-out emits a finding with a distinct `service_detail` string,
  matching the existing per-scanner pattern (e.g. `aws_connector.py` writes
  `"S3/unencrypted"`):
  - `JWKS/verify-disabled` (CR-01 opt-in)
  - `SAML/internal-target-fetched` (CR-04 opt-in)
  - `BROKER/cleartext-mgmt-api` (CR-06 opt-in)
  - `BROKER/credential-probe` (CR-05 per-target credential use)
  No new shared `operator-disabled-safety` enum; no new column.
- **D-10:** Advisories fire **once per affected target**, not once per scan. Operators see
  exactly which JWKS URL / SAML host / broker host was probed unsafely. Aligns with
  ROADMAP success criterion 1 ("naming the affected JWKS URL").

### ROADMAP Drift Correction

- **D-11:** ROADMAP.md and HARDEN-SCAN-01 reference `quirk/scanner/api_scanner.py`, but
  the actual JWKS fetch sites live in `quirk/scanner/jwt_scanner.py` (lines 56 and 67).
  Planning + execution targets `jwt_scanner.py`. The planner should include a one-line
  ROADMAP correction in its plan tasks.

### Claude's Discretion

- Exact regex patterns for `validate_image_ref` (registry/image:tag form). Plan should cite
  a reference (e.g. OCI distribution spec) but pick the regex.
- Internal exception types and their hierarchy under `quirk/util/`.
- Whether the YAML `security:` block is loaded eagerly at config-parse time or lazily on
  first opt-out check.
- Test layout: per-helper unit tests in `tests/util/`, plus integration tests in
  `tests/scanner/` that assert end-to-end behavior (rejected input → no subprocess call,
  forbidden URL → no HTTP request).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit drivers (locked findings)

- `.planning/audit-2026-05-08/scanners-protocol/REVIEW.md` §CR-01..CR-06 — verbatim audit
  findings with proof-of-concept attack chains. Source of truth for what each requirement
  must mitigate.
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — audit ledger; rows for CR-01..CR-06 must
  flip to `[x] closed` when this phase completes.

### Roadmap + requirements

- `.planning/ROADMAP.md` §Phase 57 — phase scope, success criteria.
- `.planning/REQUIREMENTS.md` §HARDEN-SCAN-01..HARDEN-SCAN-06 — requirement language.

### Affected source files

- `quirk/scanner/jwt_scanner.py` — CR-01 sites at lines 56, 67 (`verify=False` on JWKS
  fetches). **Note:** ROADMAP says `api_scanner.py`; the real file is `jwt_scanner.py`.
- `quirk/scanner/saml_scanner.py` — CR-04 site in `_fetch_metadata` (line ~57) and any
  OIDC discovery fetcher.
- `quirk/scanner/source_scanner.py` — CR-02 site (semgrep subprocess invocation).
- `quirk/scanner/container_scanner.py` — CR-03 site (syft subprocess invocation).
- `quirk/scanner/broker_scanner.py` — CR-05 hardcoded `guest:guest` at line 313;
  CR-06 `ssl_cert_reqs="none"` at line 640.

### Existing patterns to extend

- `quirk/models.py` — `CryptoEndpoint.scan_error_category` column (Phase 41 D-11). Add
  `invalid_input` to the docstring enum comment.
- `quirk/util/targets.py` — `apply_targets_file_override` is the YAML+CLI override pattern
  to mirror for the new `security:` config block.
- `quirk/config_template.yaml` — add the `security:` and `broker_credentials:` blocks here.
- `quirk/scanner/aws_connector.py` — example of `service_detail` HIGH advisory shape
  (`"S3/unencrypted"`) the new opt-out advisories should match.

### Codebase architecture

- `.planning/codebase/STRUCTURE.md` — package layout for `quirk/util/` placement.
- `.planning/codebase/CONVENTIONS.md` — module + test conventions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `CryptoEndpoint.scan_error_category` column — already used by Phase 41 D-11 for
  `missing_extra|timeout|exception|config`. Drop-in extension target for `invalid_input`.
- `apply_targets_file_override` (`quirk/util/targets.py`) — proven YAML+CLI override
  pattern; the planner should mirror its shape for the new `security:` block.
- `service_detail` HIGH-severity finding pattern (see `aws_connector.py`) — direct
  template for the four new opt-out advisory strings.

### Established Patterns

- `quirk/util/` is the canonical home for shared, scanner-agnostic helpers. Two new
  modules (`url_allowlist.py`, `subprocess_input.py`) belong there.
- Scanner findings flow through `CryptoEndpoint` rows (model in `quirk/models.py`); no
  separate "scan rejection" or "advisory" tables exist, and this phase does not add any.
- HIGH severity is set as a string literal (`severity = "HIGH"`); no enum to extend.

### Integration Points

- Each scanner's entrypoint (`scan(...)` function) needs to call the relevant validator
  *before* its current network/subprocess work, and write the rejection row on failure.
- The CLI layer (`quirk/cli/`) needs three new flags: `--allow-internal-targets`,
  `--allow-cleartext-broker-probe`, `--allow-insecure-jwks`. The config loader
  (`quirk/config.py`) needs the `security:` block and `broker_credentials:` map.

</code_context>

<specifics>
## Specific Ideas

- The ROADMAP file-path drift (`api_scanner.py` → `jwt_scanner.py`) should be corrected
  in the same PR that closes CR-01, ideally as a single-line edit in `.planning/ROADMAP.md`
  alongside the code fix.
- All four HIGH-advisory `service_detail` strings should be added as constants somewhere
  greppable so QRAMM/remediation copy can reference them by name.
- Tests must include the chaos-lab smoke (`./lab.sh up && quirk scan --target <lab>`) as
  the integration check (per ROADMAP success criterion 5).

</specifics>

<deferred>
## Deferred Ideas

- A unified "operator-safety override" finding type with a subtype field. Discussed and
  rejected for this phase (D-09) because it breaks from the per-scanner `service_detail`
  pattern. If a future phase introduces an enum-based finding model, revisit.
- A dedicated `ScanRejection` table separate from `CryptoEndpoint`. Rejected here (D-06)
  to avoid migration overhead. Revisit if rejection-row volume becomes a query problem.
- CLI override for broker credentials. Intentionally excluded from D-05 to keep secrets
  out of shell history. Revisit if operators report friction during one-off lab runs.

</deferred>

---

*Phase: 57-scanner-security-hardening*
*Context gathered: 2026-05-09*

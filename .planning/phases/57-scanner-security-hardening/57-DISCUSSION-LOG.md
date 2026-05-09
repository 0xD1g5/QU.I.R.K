# Phase 57: Scanner Security Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 57-scanner-security-hardening
**Areas discussed:** Shared helpers vs per-scanner, Config knob shape for opt-outs, How invalid_input rejections surface, HIGH advisory finding shape

---

## Shared helpers vs per-scanner

### URL/SSRF allowlist helper (CR-04 SAML + CR-06 broker mgmt API)

| Option | Description | Selected |
|--------|-------------|----------|
| New `quirk/util/url_allowlist.py` | One shared module exposing `validate_external_url(url, allow_internal=False)`. Single test suite covers all forbidden categories once. | ✓ |
| Inline in each scanner | Each scanner gets its own RFC1918/loopback/metadata-IP guard. Smallest diff per scanner but risks drift. | |
| Extend `quirk/util/targets.py` | Add URL-allowlist functions to existing `targets.py`. Keeps `quirk/util/` flatter but mixes concerns. | |

**User's choice:** New `quirk/util/url_allowlist.py` (Recommended)

### Subprocess input validators (CR-02 repo_path / CR-03 image_ref)

| Option | Description | Selected |
|--------|-------------|----------|
| Two helpers in `quirk/util/subprocess_input.py` | `validate_repo_path(p)` and `validate_image_ref(r)` as sibling functions. Different validators, shared module. | ✓ |
| Inline in `source_scanner.py` / `container_scanner.py` | Local `_validate_*` functions per scanner. Smallest diff, no reuse for future subprocess scanners. | |
| Single shared validator with `kind` enum | One `validate_subprocess_input(value, kind=...)`. Most DRY, but couples two threat models. | |

**User's choice:** Two helpers in `quirk/util/subprocess_input.py` (Recommended)

---

## Config knob shape for opt-outs

### Three opt-out flags

| Option | Description | Selected |
|--------|-------------|----------|
| YAML config + CLI override | Knobs in `config_template.yaml` under `security:` block; CLI flags override per-run. Matches existing `targets_file` precedent. | ✓ |
| CLI flags only | No YAML knobs — operator must pass `--allow-internal-targets` each invocation. Breaks scheduled/CI runs. | |
| YAML only | Operator must edit YAML; no CLI override. Hardest to misuse; requires file edits for one-off scans. | |

**User's choice:** YAML config + CLI override (Recommended)

### Broker credentials per-target opt-in (CR-05)

| Option | Description | Selected |
|--------|-------------|----------|
| YAML map keyed by `host:port` | `broker_credentials: {'rabbit.lab:15672': {user, pass_env}}`. Default anonymous; creds only sent to listed hosts; password from env var. | ✓ |
| CLI flag `--broker-creds host:port:user:env_var` | Repeatable flag, per-run. Verbose, prone to shell-history leak. | |
| Both CLI and YAML | YAML defaults + CLI override per-run. | |

**User's choice:** YAML map keyed by `host:port` (Recommended)

---

## How invalid_input rejections surface

### Rejection row shape

| Option | Description | Selected |
|--------|-------------|----------|
| `CryptoEndpoint` row with `scan_error_category='invalid_input'` | Reuse existing column (Phase 41 D-11). Surfaces in existing scan-error reporting paths. | ✓ |
| New `ScanRejection` table | Dedicated table; cleaner separation; adds migration overhead. | |
| Stderr + structured log only | No DB row. Print structured JSON to stderr; invisible to dashboard / CBOM. | |

**User's choice:** `CryptoEndpoint` row with `scan_error_category='invalid_input'` (Recommended)

### Raw value retention

| Option | Description | Selected |
|--------|-------------|----------|
| Store reason + redacted preview | Reason code + sanitized 32-char preview; control chars stripped. Forensic, bounded. | ✓ |
| Store full raw value | Verbatim rejected input. Maximum forensic detail; risk of pasted-credential leakage. | |
| Reason code only | Just the category code; debugging legitimate-rejection cases is harder. | |

**User's choice:** Store reason + redacted preview (Recommended)

---

## HIGH advisory finding shape

### Finding modeling

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct `service_detail` per opt-out | Each opt-out emits its own `service_detail` string (`JWKS/verify-disabled`, `SAML/internal-target-fetched`, `BROKER/cleartext-mgmt-api`, `BROKER/credential-probe`). Matches `aws_connector.py` pattern. | ✓ |
| Shared `'operator-disabled-safety'` type with subtype field | Uniform reporting; needs new column or convention; breaks from current per-scanner labelling pattern. | |
| Inline in existing scanner finding rows | Add an `operator_override` flag to normal findings; conflates target-side and operator-side issues. | |

**User's choice:** Distinct `service_detail` per opt-out (Recommended)

### Cardinality

| Option | Description | Selected |
|--------|-------------|----------|
| Once per affected target | Each target reached unsafely produces its own HIGH advisory. Aligns with success criterion 1. | ✓ |
| Once per scan (summary) | Single summary finding; loses per-target attribution; contradicts success criterion 1. | |

**User's choice:** Once per affected target (Recommended)

---

## Claude's Discretion

- Exact regex pattern for `validate_image_ref` (registry/image:tag form).
- Internal exception types and their hierarchy under `quirk/util/`.
- Eager vs lazy load of the YAML `security:` block.
- Test file layout under `tests/util/` and `tests/scanner/`.

## Deferred Ideas

- Unified "operator-safety override" finding type with subtype field — rejected for D-09; revisit if a future phase introduces enum-based findings.
- Dedicated `ScanRejection` table — rejected for D-06 to avoid migration overhead; revisit if rejection-row volume becomes a query problem.
- CLI override for broker credentials — intentionally excluded from D-05 to keep secrets out of shell history; revisit if operators report friction.

## ROADMAP Drift Noted

- `quirk/scanner/api_scanner.py` (in ROADMAP + HARDEN-SCAN-01) does not exist; the JWKS fetch sites are in `quirk/scanner/jwt_scanner.py` lines 56, 67. Fold a one-line ROADMAP correction into the same PR (D-11).

# Phase 94: OpenAPI & Bearer Token Analysis - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Passive (no active traffic to targets) analysis of two API-surface artifacts:
1. **Bearer/JWT tokens** — a standalone `--analyze-token` command that decodes and
   classifies a token (algorithm, key size, expiry, quantum-safety) and flags
   `alg:none` CRITICAL; plus CBOM classification of the operator-supplied
   `--auth-bearer` credential captured during an authenticated scan.
2. **OpenAPI/Swagger specs** — local-file (and scope-gated URL) parsing to inventory
   declared API crypto posture (security schemes, plaintext `servers`, unauthenticated
   endpoints), hardened against `$ref` SSRF and oversized-spec DoS.

Introduces the `[api]` extras group (`openapi-spec-validator`) and advances
SCORE_WEIGHTS +10.0 → 293.0 via the existing `agility_signals` subscore (no 7th pillar).

Requirements: SPEC-01, SPEC-02, SPEC-03, TOKEN-01, TOKEN-02, TOKEN-03,
SCORE-01 (partial), PKG-01.
</domain>

<decisions>
## Implementation Decisions

### `--analyze-token` command UX
- Input forms: positional token arg + `@file` reference + stdin (reuses Phase 93's
  reference-not-secret `@file` model; avoids argv leakage of the token).
- Output: human-readable report by default; `--json` flag for machine-readable output
  (mirrors existing `errors --dump-md`/report style).
- DB persistence: standalone analyzer writes nothing to the scan DB — the token is
  never persisted (consistent with AUTH-02).
- `alg:none` (case-insensitive: none/None/NONE/NonE) flagged CRITICAL; command exits
  non-zero on a CRITICAL finding so it can gate CI.

### OpenAPI spec analysis
- Spec source: `--openapi-spec <file|url>` CLI flag AND an `openapi:` config block.
- URL fetch only when the URL is within configured scan-target scope (SPEC-02);
  out-of-scope URL rejected with a clear error before any network request.
- Findings mapping: emit as `CryptoEndpoint` rows (protocol `OpenAPI`) into the
  existing findings table — no new findings surface.
- Size gate: 10 MB hard cap checked BEFORE parse; oversized → `SpecParsingError` (SPEC-03 DoS guard).
- `$ref` resolution is local-only; an internal-network `$ref` (e.g. `http://169.254.169.254/`)
  raises `SpecParsingError` rather than making an outbound request (SPEC-03 SSRF; CI fixture test).
- Validator: lenient parse-what-we-can with graceful degradation (matches other scanners);
  validate structure, not strict spec compliance.

### Bearer-token CBOM classification (TOKEN-02)
- Token source: only the operator-supplied `--auth-bearer` credential from Phase 93
  (passive; no sniffing of tokens in scan responses).
- CBOM label: exactly `declared_algorithm (unverified)` — never treated as enforced.
- Quantum-safety classification reuses the existing JWT / `quirk/util/weak_crypto.py`
  alg-classification tables (single source of truth).

### Scoring & packaging
- API spec + token findings feed the existing `agility_signals` subscore; SCORE_WEIGHTS
  walks +10.0 → 293.0 (locked; no 7th pillar, no rollup-denominator change). Invariant
  test expected-sum bumped this phase.
- `[api]` extras contains `openapi-spec-validator` only; `schemathesis` is added in
  Phase 96 (excluded from `[all]`).
- New CI guard test mirrors `tests/test_install_all_excludes_impacket.py`, asserting
  `pip install quirk[all]` does not pull `schemathesis`.

### Claude's Discretion
- Module placement, exact report layout, and internal helper structure are at Claude's
  discretion, following codebase conventions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/util/url_allowlist.py::validate_external_url(url, *, allow_internal=False)` →
  `ValidationResult(ok, reason_code, preview)` with RC_INTERNAL_IP / RC_LOOPBACK /
  RC_LINK_LOCAL / RC_METADATA_SERVICE_IP / RC_SCHEME_PREFIX. Reuse for SPEC-02 scope
  gate and SPEC-03 `$ref` SSRF guard (metadata IP rejected even with allow_internal).
- `quirk/scanner/jwt_scanner.py` — existing JWKS/JWT algorithm handling; source of
  alg-classification patterns to reuse for token analysis.
- `quirk/util/weak_crypto.py` — consolidated weak-crypto/quantum-safety helper (Phase 73).
- `quirk/models.py::CryptoEndpoint` — the findings-table row model (protocol field).
- `quirk/util/safe_exc.py::safe_str` — scrub exceptions before logging/persisting (AUTH-02).

### Established Patterns
- CLI subcommands registered via argparse `add_subparsers` in `run_scan.py`
  (e.g. `comp`, `cmvp`, `db` subcommands) — `--analyze-token` joins this surface.
- Extras groups in `pyproject.toml` `[project.optional-dependencies]`; `[all]`
  intentionally OMITS dangerous extras (impacket pattern, Phase 45/D-01).
- Scanners degrade gracefully when an optional dep is missing (e.g. HTTPX_AVAILABLE).

### Integration Points
- `pyproject.toml` `[project.optional-dependencies]` — add `api = [...]`.
- `run_scan.py` argparse — new `--analyze-token` command + `--openapi-spec` flag.
- SCORE_WEIGHTS (invariant test must bump expected sum to 293.0).
- CBOM builder — bearer-token component with `declared_algorithm (unverified)` label.
</code_context>

<specifics>
## Specific Ideas

- CI guard test must mirror `tests/test_install_all_excludes_impacket.py` structure
  (pip dry-run resolve + assert dependency absent).
- Token `@file` and `--openapi-spec` `@file`/URL paths reuse the Phase 93 path-traversal
  and scope guards rather than inventing new ones.
</specifics>

<deferred>
## Deferred Ideas

- Active REST fuzzing (`schemathesis`) → Phase 96.
- Sniffing/classifying bearer tokens observed in scan responses → out of scope (passive only).
- mTLS client-cert analysis → deferred (v5.2 per milestone scope).
</deferred>

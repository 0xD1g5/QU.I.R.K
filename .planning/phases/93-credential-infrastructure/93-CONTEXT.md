# Phase 93: Credential Infrastructure - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the **ephemeral credential subsystem** for QU.I.R.K.: a `CredentialContext` built once per scan run that lets a consultant supply Bearer/OAuth2, API-key (header or query), or HTTP Basic credentials for a *single* authenticated scan, plus the security controls that guarantee those credentials never reach a stored or rendered surface (scrubbing, scheduler rejection, and a committed security-review gate).

**In scope (AUTH-01..05):** credential model + input surface; in-memory-only handling; scheduler rejection of authenticated configs; the security-review gate deliverable; extension of `safe_str()` + the AST CI gate to credential/token field shapes. The existing API/JWT scanner is wired to consume credentials to prove the seam end-to-end.

**Out of scope (later phases):** OpenAPI spec analysis + bearer-token classification/CBOM labeling (Phase 94); code-signing inventory (Phase 95); active REST fuzzing (Phase 96); any *new* finding types from authenticated requests; mTLS client certs (deferred milestone-wide); persisted/scheduled authenticated scans (architecturally prohibited).
</domain>

<decisions>
## Implementation Decisions

### Credential Input Surface & Precedence
- **D-01:** CLI flags carry a **reference, never an inline secret**. `--auth-bearer` / `--auth-api-key` / `--auth-basic` accept an env-var name or `@file` path, or — when given bare — trigger an interactive `getpass` prompt. A raw secret value must never appear as an argv token (it would leak into `ps`, shell history, and process listings, defeating "ephemeral"). Reuse the existing hardened `@file` reader + path-traversal guard from v4.8 Phase 58 rather than building a new file-read path.
- **D-02:** Source precedence when more than one is present: **interactive prompt > env var > flag-supplied reference**. Favors the most-deliberate, least-loggable source.
- **D-03:** API-key scheme covers **both header and query-param** placement (per locked milestone scope). Query-param API keys are themselves a leak risk (URLs land in logs/CBOM endpoint labels) — the scrubbing work in D-08 must cover query-param key shapes, not just headers.

### In-Memory Handling / Zeroization
- **D-04:** **Hybrid bytearray model.** Store the secret as a `bytearray` inside `CredentialContext`; overwrite it in a `finally` block (`buf[:] = b"\x00" * len(buf)`); materialize a `str` only at the unavoidable httpx header-injection boundary. Do NOT thread `bytearray` through every scanner call (full-bytearray-everywhere is diminishing returns since httpx forces a `str` eventually).
- **D-05:** Accept and document that this is **best-effort, not provable** — Python interns/copies strings and GC can retain heap copies. The security-review gate deliverable (D-06) must state this limitation explicitly; "ephemeral" means *never persisted*, not *provably erased*.

### Security-Review Gate Deliverable (AUTH-04)
- **D-06:** AUTH-04 is satisfied by **two committed artifacts**:
  1. A **markdown audit** in the phase dir enumerating the 11 credential-leakage surfaces (SQLite columns, CBOM JSON/XML, dashboard `/api/scan/latest`, PDF export, debug logs, WAL file, error/traceback text, etc.), each marked with *how* it is controlled, plus the best-effort-zeroization caveat from D-05.
  2. An **automated leak-detection test suite** that injects a known sentinel credential value and asserts it appears in **none** of the stored/rendered surfaces (SQLite row, CBOM output, dashboard API response, log files).
- **D-07:** This is the gate that must be GREEN before any later phase sends authenticated traffic to a live target — it is the milestone's committed security-review gate, not just a phase task.

### Scrubbing & Regression Guards (AUTH-02 / AUTH-05)
- **D-08:** Extend `safe_str()` in `quirk/util/safe_exc.py` `_SENSITIVE_PATTERNS` to cover API-key header shapes (`X-Api-Key`, `X-Auth-Token`, etc.) and query-param API-key shapes — `Authorization: Bearer` is already covered.
- **D-09:** Extend the AST CI gate deny-list to flag `bearer`, `api_key`, `authorization`, `token`, `password`, `credential` field names reaching `json.dumps()` / `model_dump()`. Add a schema-level CI assertion that no `scheduled_scans` / `scan_checkpoints` column is named `key`/`token`/`password`/`secret`/`credential`.
- **D-10:** Disable httpx debug-level logging of `Authorization`/auth headers (it emits full header values at DEBUG by default) — strip auth headers via a request `event_hooks` filter before any log handler sees them.

### Scheduler Rejection (AUTH-03)
- **D-11:** `quirk schedule add` with `enable_authenticated_mode: true` exits with stable error code **`QRK-SCHED-AUTH-001`** and a clear human-readable message (credentials can't be persisted, so authenticated scheduled scans are prohibited). Register the code in `quirk/errors.py`.

### Phase-93 Consumption Scope
- **D-12:** In Phase 93 the credential consumer is the **existing Phase-3 API/JWT scanner only** — it attaches auth headers (via `CredentialContext.as_headers()`) to its live requests, proving the seam end-to-end. No new finding types in this phase (those land in Phase 94). Do NOT broaden to generic HTTP/TLS endpoint probes in 93.

### Claude's Discretion
- **D-13 (planner to confirm):** Module path — recommend **`quirk/auth/credentials.py`** (new subdirectory signals a distinct concern boundary, more discoverable) over `quirk/util/credentials.py`. Research split on this (STACK vs ARCHITECTURE); planner confirms and records in PLAN.
- **D-14:** `CredentialContext` must have **zero imports from scanner modules** (prevents circular deps) — built in `run_scan.py` after config load, captured into the existing `_wrapped_phase()` lambda closures without changing that helper's signature.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope & locked decisions
- `.planning/PROJECT.md` §"Current Milestone: v5.1" — milestone goal, locked scope decisions, ephemeral-only invariant.
- `.planning/REQUIREMENTS.md` §"Authenticated Scanning — Credential Model" — AUTH-01..05 + the locked Scope Decisions table.
- `.planning/ROADMAP.md` §"Phase 93: Credential Infrastructure" — goal + 5 success criteria.

### Research (HIGH confidence, live-source-grounded)
- `.planning/research/SUMMARY.md` — synthesized findings; "Implications for Roadmap → Phase 93" section + the 5 open-decision items.
- `.planning/research/PITFALLS.md` — the 11 leakage surfaces, Python zeroization limits, `safe_token_repr()` pattern (Pitfalls 1, 2, 6, 9). **Most load-bearing ref for the security-review gate.**
- `.planning/research/ARCHITECTURE.md` — `CredentialContext` placement, closure-capture into `_wrapped_phase`, scheduler-rejection seam.
- `.planning/research/STACK.md` — credential handling needs zero new deps (stdlib `getpass` + `os.environ`); `keyring` is the critical AVOID.

### Existing code seams to reuse (verified by research)
- `quirk/util/safe_exc.py` — `safe_str()` + `_SENSITIVE_PATTERNS` (extend per D-08); already strips `Authorization: Bearer`.
- `run_scan.py` — `_wrapped_phase()` BaseException helper (credential closures capture here, signature unchanged — D-14).
- `quirk/scanner/jwt_scanner.py` — `scan_jwt_targets()`; the Phase-93 credential consumer (D-12).
- `quirk/config.py` — `ConnectorsCfg` (add `enable_authenticated_mode: bool = False`).
- `quirk/errors.py` — stable error-code registry (register `QRK-SCHED-AUTH-001` — D-11).
- v4.8 Phase 58 `@file` reader + path-traversal guard — reuse for reference-only flags (D-01). (Locate during planning; cited in PROJECT.md Key Decisions / Phase 58 artifacts.)
- The existing AST credential-gate test (from v4.8 LEAK-03) — extend deny-list (D-09).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `safe_str()` / `_SENSITIVE_PATTERNS` (`quirk/util/safe_exc.py`): the established secret-scrubbing chokepoint — extend, don't replace.
- `_wrapped_phase()` (`run_scan.py`): uniform per-scanner error capture; credentials are captured into its lambda closures, never passed into the helper itself.
- v4.8 hardened `@file` reader with path-traversal guard: directly reusable for reference-only credential flags.
- `quirk/errors.py` stable error-code registry: the home for `QRK-SCHED-AUTH-001`.
- Existing AST CI gate (LEAK-03, v4.8): extend its deny-list rather than authoring a new gate.

### Established Patterns
- Additive-only SQLite schema (no breaking migrations) — Phase 93 adds NO credential columns anywhere; the schema-CI assertion (D-09) enforces that.
- `ConnectorsCfg` boolean opt-in flags (e.g. prior `enable_*` fields) — `enable_authenticated_mode` follows the same shape.
- nmap probe-budget gate as the canonical "intrusive behavior is opt-in + confirmed" pattern (relevant later in Phase 96; here the analog is the scheduler hard-rejection).

### Integration Points
- `run_scan.py` config-load → build `CredentialContext` → capture into `_wrapped_phase` closures → API/JWT scanner consumes via `as_headers()`.
- `quirk schedule add` validation path → reject `enable_authenticated_mode: true` with `QRK-SCHED-AUTH-001`.
- httpx client construction → `event_hooks` request filter stripping auth headers from logs (D-10).
</code_context>

<specifics>
## Specific Ideas

- "Flags take a reference, not the secret" is a deliberate, slightly-unconventional UX choice — the planner should make the help text and error messages teach the consultant *why* (`--auth-bearer @token.txt` or `--auth-bearer MY_ENV_VAR` or bare `--auth-bearer` to prompt), not just accept it.
- The leak-detection test should use a distinctive sentinel value (e.g. `QUIRK_SENTINEL_CRED_d41d8cd9`) so a grep across every output artifact is unambiguous.
</specifics>

<deferred>
## Deferred Ideas

- mTLS client-certificate auth — deferred milestone-wide (PROJECT.md).
- OAuth2 client-credentials token *acquisition* (vs. accepting a supplied token) — Future Requirements; conflicts with ephemeral-only unless revisited.
- Authenticated *scheduled* scans — architecturally prohibited while credentials are ephemeral-only (this phase actively rejects them).
- `MADV_DONTDUMP` / core-dump protection for credential pages — raised in PITFALLS open questions; out of scope for the consulting use case unless a client requires it.

None of the above belong in Phase 93.
</deferred>

---

*Phase: 93-credential-infrastructure*
*Context gathered: 2026-05-22*

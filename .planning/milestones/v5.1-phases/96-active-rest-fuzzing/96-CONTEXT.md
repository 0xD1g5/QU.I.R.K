# Phase 96: Active REST Fuzzing - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's sharpest edge: **opt-in, defensively-gated ACTIVE (non-passive) traffic**
to a target for crypto-posture fuzzing. Off by default. Probes: TLS downgrade, cipher
acceptance, HSTS, HTTP-only credential transmission, and (behind a dedicated sub-flag) a
JWT RS256→HS256 alg-confusion probe. Every probe is gated behind an explicit `CONFIRM`
prompt, a bounded request budget, a hard non-TTY abort, and six safety guardrails.

Depends on Phase 93 (ephemeral creds) + Phase 94 (OpenAPI endpoint discovery). All
guardrails must be complete and reviewed before the first fuzz request hits a live target
(v5.1-D-03). Finalizes SCORE_WEIGHTS (+4.0 → 303.0) and chaos-lab coverage (LAB-01 final).

Requirements: FUZZ-01, FUZZ-02, FUZZ-03, FUZZ-04, SCORE-01 (final), LAB-01 (final).
</domain>

<decisions>
## Implementation Decisions

### Fuzzer engine & probe types
- Engine: `schemathesis` drives request dispatch against Phase-94-discovered OpenAPI
  endpoints; custom crypto-posture assertions are applied to responses/connection.
- **Day-1 task:** verify `schemathesis Case.as_transport_kwargs()` httpx dispatch
  integration before building on it (carried-over gap note).
- Probe set (FUZZ-01): TLS downgrade, cipher acceptance, HSTS, HTTP-only credential
  transmission — reuse existing TLS scanner capabilities for the crypto checks.
- Endpoint source: Phase 94 OpenAPI endpoint discovery + `cfg.targets`; no fuzzing
  without a discovered, in-scope endpoint.

### Six safety guardrails (FUZZ-02)
1. GET-only by default; other HTTP methods require explicit opt-in.
2. Hard budget ceiling: default 50, hard max 500 — exceeding aborts.
3. Rate cap: 5 req/s default (reuse the nmap TokenBucket pattern).
4. `CONFIRM` prompt (see below).
5. Target-scope enforcement: every request URL validated via `validate_external_url` +
   `cfg.targets` before dispatch.
6. 5xx-cascade pause: pause and warn after 3 consecutive 5xx responses.

### CONFIRM gate + non-TTY abort (FUZZ-01, FUZZ-03)
- TTY: present a budget summary and require the user to type the literal word `CONFIRM`;
  any other input (including bare Enter) aborts cleanly with NO requests sent.
- Non-TTY (piped stdin / CI): hard-abort BEFORE sending any request, printing a clear
  non-interactive-mode error. Fuzzing never runs headless. (Note: differs from nmap,
  which auto-proceeds in non-TTY — fuzzing HARD-ABORTS.)

### JWT alg-confusion probe (FUZZ-04)
- RS256→HS256 confusion probe behind a dedicated `--fuzz-jwt-alg-confusion` sub-flag.
- Reuse Phase 93 bearer credential + Phase 94 token decode/classify.
- Produces a finding when the target server accepts the forged token.
- Severity: alg-confusion acceptance → CRITICAL; TLS downgrade / weak cipher → HIGH.

### Packaging, chaos lab, scoring
- `schemathesis` added to the `[api]` extras group (v5.1-D-05; excluded from `[all]`);
  the CI guard `tests/test_install_all_excludes_schemathesis.py` already enforces this.
- Chaos lab (LAB-01 final): a NEW isolated `fuzz-target` profile — a deliberately-weak
  REST target. Per CLAUDE.md, `lab.sh` needs NO ALL_PROFILES edit — `_derive_all_profiles()`
  reads `profiles:` from docker-compose.yml dynamically at runtime, so adding the `fuzz-target`
  profile to compose satisfies CLAUDE.md's intent; update the chaos
  README, and `expected_results_*.md` in the SAME change.
- Scoring: fuzzing findings feed `agility_signals`; SCORE_WEIGHTS +4.0 → 303.0. Update
  BOTH the sum AND count invariant assertions together (recurring lesson).

### Claude's Discretion
- Exact evidence counter key(s) for the fuzzing agility signal, the weight split, module
  structure, and CONFIRM prompt wording are at Claude's discretion, following conventions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- nmap probe-budget + `is_tty` pattern (run_scan.py ~960, `is_tty=sys.stdin.isatty()`) —
  the cited analog for the budget/confirm gate.
- `quirk/util/url_allowlist.py::validate_external_url` — scope/SSRF gate for every request.
- Phase 94 OpenAPI endpoint discovery (`quirk/scanner/openapi_scanner.py`) — endpoint source.
- Phase 93 `CredentialContext` (`quirk/auth/credentials.py`) + Phase 94 `analyze_token`
  JWT decode — for the alg-confusion forged-token construction.
- TLS scanner capabilities (downgrade/cipher/HSTS checks) — reuse for crypto assertions.
- nmap TokenBucket rate-limiter pattern — for the 5 req/s cap.
- `tests/test_install_all_excludes_schemathesis.py` — existing CI guard (extend to confirm
  schemathesis present in `[api]` once added).
- `quirk/intelligence/evidence.py` `_PROTOCOL_KEYS` + `scoring.py` SCORE_WEIGHTS (299.0/40).

### Established Patterns
- `--fuzz` / `--fuzz-jwt-alg-confusion` argparse flags wired in run_scan.py; opt-in scan phase.
- Protocol values UPPERCASE; new CBOM/evidence branch keys exact-match.
- Chaos lab: new profile → lab.sh ALL_PROFILES (dynamic `_derive_all_profiles`) + compose
  profiles list + README + expected_results in the same change.

### Integration Points
- pyproject.toml `[api]` extras — add `schemathesis`.
- run_scan.py — `--fuzz` flag, CONFIRM/non-TTY gate, fuzzing scan phase feeding findings.
- chaos lab docker-compose.yml — new `fuzz-target` profile.
- SCORE_WEIGHTS invariant (303.0 / count).
</code_context>

<specifics>
## Specific Ideas

- The CONFIRM gate and non-TTY hard-abort are the most safety-critical code in the
  milestone — they must be proven by tests BEFORE any request-dispatch code (test-first).
- The non-TTY abort must fire before ANY network request — assert zero requests via mock.
- Budget enforcement must be a hard ceiling (500) the user cannot exceed via config.
</specifics>

<deferred>
## Deferred Ideas

- POST/PUT/DELETE fuzzing by default → out of scope (GET-only default; opt-in only).
- Generic schema-validation fuzzing beyond crypto-posture probes → not this phase.
- Fuzzing without a discovered/scoped endpoint (ad-hoc URL) → out of scope.
</deferred>

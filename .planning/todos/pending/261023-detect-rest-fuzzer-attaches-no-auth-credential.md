---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-03 (plan 230-03 observation; the original jwks-auth-hook todo's second sentence)
priority: medium
area: quirk/scanner/rest_fuzzer.py
status: pending
resolves_phase: null
owner: "999.136"
---

# The REST fuzzer never attaches the operator's `--auth-*` credential to its probes

DETECT-03 made `--auth-*` credentials reach the JWKS target. The REST fuzzer still attaches none to its ordinary
probes. Observed in plan 230-03: `scan_rest_fuzz` accepts `cred_ctx` (`quirk/scanner/rest_fuzzer.py:444`) but uses it
only for the bearer alg-confusion branch (`:521-526`) and the `http_creds` advisory presence check (`:702`);
`as_headers` is never called from this module, and the only request carrying an `Authorization` header (`:726`) holds a
forged JWT. So an API that requires authentication is fuzzed unauthenticated: every probe sees 401, and the
authenticated surface (the part an authenticated scan exists to reach) goes untested.

- [ ] Attach `cred_ctx.as_headers()` (and the query parameter for `api_key_query`) to ordinary fuzz probes, never to the forged-JWT probe, and never log it.
- [ ] Wire-level test with a local server that returns 401 without the credential and asserts the header on every non-forged probe.
- [ ] Re-check `tests/test_credential_leakage.py` and the DEBUG-log redaction filter pattern from `jwt_scanner.py`.

## Feasibility & Effort

- **CONFIRMED** by `grep -n "as_headers\|cred_ctx" quirk/scanner/rest_fuzzer.py`: 444, 463, 521-526, 702 only.
- **LIKELY** effort **M**: the fuzzer builds requests in several places; the 230-03 `tests/jwks_wire_helpers.py` server harness can be reused.
- **UNKNOWN**: whether fuzz findings change for an authenticated target (more 2xx bodies to analyse), and the fuzz request budget (`test_fuzz_budget_docs_agree`).
- **Spike**: no. Owner 999.136 (scan engine and config plumbing) is OPEN (read 2026-10-23).

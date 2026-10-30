---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Authenticated Scanning)
priority: high
area: quirk/scanner/jwt_scanner.py
status: completed
completed: 2026-10-23
resolves_phase: 230
owner: DETECT-03
---

# `--auth-*` credentials never reach the JWKS target

The JWKS fetch installs `_strip_auth_from_log` as an httpx **request** hook
(`quirk/scanner/jwt_scanner.py:164`). It pops `Authorization`, `X-Api-Key` and `X-Auth-Token` (`:46-48`)
and replaces an `api_key` query value with `REDACTED` (`:54-58`). The comment at `:52-53` assumes "httpx
event hooks run after the request is sent". That is false: request hooks run before the request is
sent. So every `--auth-*` scheme is stripped before it reaches the wire.

Observed (fork probe, local HTTP server): no credential arrived for any of the four schemes. The REST
fuzzer attaches no credential to its probes either. docs/configuration.md (Authenticated Scanning and
the `--auth-*` table) now says the credential does not reach the target.

- [x] Redact in a logging filter or a response hook, not the request hook, and add a wire-level test that
      asserts the header arrives at a local server.
- [x] Re-check `tests/test_credential_leakage.py` so it still proves no log leak after the move.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (live probe, and the hook is at `quirk/scanner/jwt_scanner.py:164`).
- **Effort: S.**
- **Unknowns:** whether anything else depends on the in-place URL redaction (redirect logging).
- **Spike:** no.

## Resolution (Phase 230, 2026-10-23)

- Fix: `0e8074ca` deletes the httpx request hook that stripped `Authorization`, `X-Api-Key`, `X-Auth-Token` and rewrote `?api_key=` before send. Redaction is now a `_RedactKeyQueryFilter` on the `httpx`, `httpcore` and module loggers (idempotent across reload); `follow_redirects=False` retained. `c45c0d45` drops an `importorskip` on core dependency httpx in the wire test.
- Proof: `tests/test_jwks_auth_wire.py::test_credential_reaches_wire_and_not_logs` (x4 schemes) asserts the received header or query at a local server and the absence of the credential in DEBUG logs; `tests/test_jwt_scanner.py::test_redact_filter_*` (3). `tests/test_credential_leakage.py` and `tests/test_credential_no_leak_guard.py` stay green (83 passed, 6 xfailed in the plan set). Fail-first: 8 failed pre-fix. Mutations: the filter-removed mutation turns the query log assertion red; the old request hook restored turns all 4 wire cases red. UAT-230-04.
- Not done (recorded): the REST fuzzer still attaches no operator credential to its ordinary probes; filed as `261023-detect-rest-fuzzer-attaches-no-auth-credential`.
- 999.125 item 1 fixed.

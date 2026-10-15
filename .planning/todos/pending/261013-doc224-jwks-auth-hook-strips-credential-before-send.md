---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Authenticated Scanning)
priority: high
area: quirk/scanner/jwt_scanner.py
status: pending
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

- [ ] Redact in a logging filter or a response hook, not the request hook, and add a wire-level test that
      asserts the header arrives at a local server.
- [ ] Re-check `tests/test_credential_leakage.py` so it still proves no log leak after the move.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (live probe, and the hook is at `quirk/scanner/jwt_scanner.py:164`).
- **Effort: S.**
- **Unknowns:** whether anything else depends on the in-place URL redaction (redirect logging).
- **Spike:** no.

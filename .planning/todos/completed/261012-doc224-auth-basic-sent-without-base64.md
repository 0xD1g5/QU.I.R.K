---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-A-* (configuration.md Authenticated Scanning)
priority: medium
area: quirk/auth/credentials.py
status: completed
completed: 2026-10-23
resolves_phase: 230
owner: DETECT-04
---

# `--auth-basic` sends the resolved secret verbatim as `Authorization: Basic <secret>` (no base64)

`CredentialContext.as_headers()` builds `{"Authorization": f"Basic {secret}"}` for the `basic` scheme
(`quirk/auth/credentials.py`). HTTP Basic requires `base64(user:password)`, but nothing in `from_cli()` or
`as_headers()` encodes it, and no caller does (`grep -rn "b64\|base64" quirk/auth quirk/scanner/jwt_scanner.py` finds
only an unrelated JWK decode). Reproduced 2026-10-12: with `BV=user:pass`, `CredentialContext.from_cli(basic='BV')
.as_headers()` returns `{'Authorization': 'Basic user:pass'}`, which a standards-compliant server rejects. The help
text and the old `docs/configuration.md` row both said the flag takes `user:password` and adds `Authorization: Basic
<b64>`. `docs/configuration.md` now says the secret is sent as given, so the operator must pre-encode it.

- [x] Decide the contract: accept `user:password` and encode it in `as_headers()`, or keep verbatim and rename the
      flag help to "base64(user:password)".
- [x] Add a test that the emitted header decodes to the supplied `user:password`.
- [x] Then update `docs/configuration.md` (the `--auth-basic` row) and the `--auth-basic` help text.

## Feasibility & Effort

**CONFIRMED** (live call above). Effort **S**: one `base64.b64encode` in the `basic` branch plus a test; the choice
of contract is the only decision. No spike needed.

## Resolution (Phase 230, 2026-10-23)

- Contract chosen: `--auth-basic` takes `user:password` and `as_headers()` base64-encodes it (UTF-8), per RFC 7617. A value without a colon raises a fixed-text `ValueError` that never echoes the value; a pre-encoded value is therefore rejected. This is a behaviour change, called out in `changelog.d/phase-230.bugfix.md`.
- Fix: `3c42b21c` (with the shared wire harness). `--help` and the getpass prompt now say `user:password`; `docs/configuration.md` updated in `40297bbd`.
- Proof: `tests/test_jwks_auth_wire.py::test_basic_header_decodes_to_user_password`, `::test_basic_without_colon_raises_from_cli`, `::test_basic_without_colon_raises_from_as_headers`, `::test_auth_basic_help_text`, `tests/test_credential_context.py::TestAsHeaders::test_basic_scheme`, `::test_basic_scheme_rejects_pre_encoded_value` (6 passed, observed 2026-10-23). Reverting `as_headers` to verbatim turns 3 red. UAT-230-05.
- 999.125 item 2 fixed.

---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-A-* (configuration.md Authenticated Scanning)
priority: medium
area: quirk/auth/credentials.py
status: pending
resolves_phase: null
---

# `--auth-basic` sends the resolved secret verbatim as `Authorization: Basic <secret>` (no base64)

`CredentialContext.as_headers()` builds `{"Authorization": f"Basic {secret}"}` for the `basic` scheme
(`quirk/auth/credentials.py`). HTTP Basic requires `base64(user:password)`, but nothing in `from_cli()` or
`as_headers()` encodes it, and no caller does (`grep -rn "b64\|base64" quirk/auth quirk/scanner/jwt_scanner.py` finds
only an unrelated JWK decode). Reproduced 2026-10-12: with `BV=user:pass`, `CredentialContext.from_cli(basic='BV')
.as_headers()` returns `{'Authorization': 'Basic user:pass'}`, which a standards-compliant server rejects. The help
text and the old `docs/configuration.md` row both said the flag takes `user:password` and adds `Authorization: Basic
<b64>`. `docs/configuration.md` now says the secret is sent as given, so the operator must pre-encode it.

- [ ] Decide the contract: accept `user:password` and encode it in `as_headers()`, or keep verbatim and rename the
      flag help to "base64(user:password)".
- [ ] Add a test that the emitted header decodes to the supplied `user:password`.
- [ ] Then update `docs/configuration.md` (the `--auth-basic` row) and the `--auth-basic` help text.

## Feasibility & Effort

**CONFIRMED** (live call above). Effort **S**: one `base64.b64encode` in the `basic` branch plus a test; the choice
of contract is the only decision. No spike needed.

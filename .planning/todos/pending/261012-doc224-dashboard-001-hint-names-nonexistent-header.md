---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-B-* (configuration.md Dashboard Authentication)
priority: low
area: quirk/errors.py (DASHBOARD-001), docs/error-codes.md (generated)
status: pending
resolves_phase: null
---

# QRK-DASHBOARD-001 tells operators to send a header that does not exist

`quirk/errors.py` defines `DASHBOARD-001` with `fix="Send the dashboard auth token in the X-Quirk-Auth header."`. No code
reads an `X-Quirk-Auth` header: `quirk/dashboard/api/middleware/auth.py` accepts `X-API-Key` (preferred) or
`Authorization: Bearer <token>`. `grep -rn 'X-Quirk-Auth' quirk src/dashboard/src` finds only the error text itself. A
client that follows the 401 hint can never authenticate. The hint is copied into `docs/error-codes.md`, which is generated
(`python run_scan.py errors --dump-md`, gated by `tests/test_error_codes_freshness.py`).

`docs/configuration.md` now says the hint is wrong and names the real headers.

- [ ] Change the `fix` text to name `X-API-Key` / `Authorization: Bearer`.
- [ ] Regenerate `docs/error-codes.md` and `docs/quirk-master-guide.md` if affected; check the freshness gates.
- [ ] Drop the caveat sentence from `docs/configuration.md`.

## Feasibility & Effort

**CONFIRMED** by the grep above. Effort **S** (one string, one regenerate). No unknowns beyond any test that pins the old
wording; `grep -rn 'X-Quirk-Auth' tests` before editing.

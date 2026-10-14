---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS; ledger row DCL-OPS-C-0029 (docs/operators-guide.md Command Reference, `quirk token rotate`)
priority: high
area: quirk/cli/token_cmd.py (generate/rotate), quirk/dashboard/api/middleware/auth.py (_get_configured_token)
status: completed
completed: 2026-10-14
resolves_phase: 225.1
---

# `token rotate` can leave the old token valid when the server has `QUIRK_API_TOKEN` set

Finding from a live probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-token-rotate-probe.py`,
TestClient against `create_app()`, GET `/api/merge/latest`, which has router-level `require_auth`):

```
template config + security.api_token=OLD:       OLD -> 200   WRONG -> 401
token rotate --config <same file>:               OLD -> 401   NEW -> 200
server env QUIRK_API_TOKEN=OLD, after rotate:    OLD -> 200   NEW -> 401
rotate run from a shell without the env var:     prints no precedence note
```

**Env precedence.** `_get_configured_token` (`quirk/dashboard/api/middleware/auth.py:20-21`) returns
`QUIRK_API_TOKEN` before reading YAML. `rotate` only writes YAML (`token_cmd.py:99-103`). Its precedence note
(`token_cmd.py:104-108`) checks the *rotating shell's* environment, not the server's, so an operator who rotates from
a different shell than the one that started `serve` (the normal case) gets no warning and the old token stays valid.
The help string (`token_cmd.py:78`, "old token invalid immediately") overstates this. The operators-guide Command
Reference row is now narrowed; the CLI help string still says it.

- [x] Change the rotate help text, and have `rotate` say that a server-side `QUIRK_API_TOKEN` is unaffected.
- [x] Test: rotating with a server-side `QUIRK_API_TOKEN` set produces the warning.

## Feasibility & Effort

- **CONFIRMED** by the live probe above and by reading `quirk/dashboard/api/middleware/auth.py:14-21`
  and `quirk/cli/token_cmd.py:75-108`.
- **LIKELY** effort **S**: help text and one extra message. No spike needed.

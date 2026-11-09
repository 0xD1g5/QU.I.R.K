---
type: todo
created: 2026-11-09
title: Re-verify the CMVP catalog by hand before it goes red on 2026-11-24
source: v5.28.2 milestone audit (staleness clock)
priority: high
area: quirk/compliance/cmvp_cache.json, quirk/compliance/cmvp.py
status: pending
resolves_phase: null
owner: null
due: 2026-11-23
---

# Re-verify the CMVP catalog by hand before it goes red on 2026-11-24

Kind: human (dated)

Ledger row: `261109-cmvp-manual-reverify-before-2026-11-24` in `.planning/LEDGER.md`.

## Observed

`quirk/compliance/cmvp_cache.json` has `last_verified: 2026-08-25` on a 90-day cadence, so
`tests/test_cmvp_freshness.py` goes red on 2026-11-24. That gate runs on every PR, every push to `main`, and the
weekly cron. The next one to trip is `quirk/scanner/hw_cve.py` (2026-10-29, 30-day cadence) on about 2026-11-28.

## How to do it (CLAUDE.md § Staleness Review Cadence)

1. Re-verify the cache entries against the `source_url` (NIST CSRC CMVP validated-modules search).
2. **Never run `quirk compliance cmvp refresh`.** It has corrupted the cache before (RVW-022, `a7cf302`).
   Hand-edit any entry that changed.
3. Bump `last_verified` only after that check. Bumping it to clear the gate fabricates the attestation.
4. Commit `chore: re-verify CMVP catalog (YYYY-MM-DD)`.

If it cannot be done by 2026-11-23, record the deferral in STATE.md instead of bumping the date.

## Feasibility & Effort

Small (about 1 hour of reading against the CSRC search). No code change.

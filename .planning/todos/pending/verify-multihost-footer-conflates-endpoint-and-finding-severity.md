# `verify_multihost_scan.py`'s severity footer conflates endpoint severity with finding severity

**Filed:** 2026-09-17 (demo-prep)
**Priority:** P3 — cosmetic, but actively misleading in a demo context
**Status:** open

## What happens

The verifier's footer prints, e.g.:

```
726 endpoints total | severities: HIGH=7, MEDIUM=2, CRITICAL=2
```

while the same scan's own summary reports **CRITICAL 5 / HIGH 21 / MEDIUM 39**.

Both numbers are correct and they count different things. The footer counts the `severity` column
on rows in `crypto_endpoints`. QU.I.R.K.'s summary counts **findings**, which are derived and
aggregated from those endpoints at report time — there is no findings table in `quirk/models.py`,
so one endpoint can contribute several findings and some findings come from analysis rather than
from a single row.

## Why it matters

The two appear side by side when the verifier is run straight after a scan, and the footer reads
as if it were disputing the headline figure. In a demo or a handover that is a distraction at
best. The operator hit exactly this and asked which number was right.

## Fix

Relabel the line so it cannot be read as a finding count — e.g.
`726 endpoint rows | endpoint-level severity column: ...` — and add a one-line note that the
authoritative CRITICAL/HIGH/MEDIUM counts are the scan summary's, not this script's. Alternatively
drop the severity line entirely; the 14 pass/fail checks are the script's actual job.

---
type: todo
created: 2026-09-12
source: phase-202 plan 01/02/06 (D-06); filed at plan 202-08 close
priority: medium
requirement: none (latent trap surfaced by STORY-01/STORY-02, not itself a requirement)
---

# `FindingItem.id` is not a unique finding identifier — a latent trap for any future per-finding feature

`FindingItem.id` is actually `CryptoEndpoint.id`, not a per-finding identifier.
`_derive_findings()` (`quirk/dashboard/api/routes/scan.py`) emits multiple `FindingItem`s per
endpoint inside one `for ep in endpoints:` loop — there are 9 distinct `title=` emission sites, all
carrying `id=ep.id`. One TLS endpoint routinely yields 2-4 findings sharing a single `id`.

## Why this phase did not fix it

`202-CONTEXT.md`'s D-06 confirms this was found and deliberately **not** resolved by giving findings
a genuinely unique identifier: "the blast radius is wider than Phase 202 needed." Instead, Phase 202
worked around it by keying its new endpoint on the `(CryptoEndpoint.id, title)` compound pair —
`GET /api/findings/{id}/storyline?title=<finding title>`, with `title` required and the client
already holding both values from the row it clicked. This is a correct, narrow fix for STORY-01's
one endpoint, not a fix for the underlying non-uniqueness.

## Why this matters beyond Phase 202

Any future feature that needs to address, link to, bookmark, cache, or persist a reference to "this
specific finding" (not "this endpoint") will hit the same trap `FindingItem.id` presents today:
using `id` alone silently returns or acts on the wrong finding whenever an endpoint has 2+ findings.
The `(id, title)` compound-key workaround is not general — it assumes the caller already has both
values in hand, which is true for a click-through UI action but would not be true for, e.g., a
persisted bookmark, a ticketing-system cross-reference, or a URL a user could share.

## What a real fix would look like

Giving findings a genuinely unique identifier (e.g., a stable synthetic id derived from
`(endpoint_id, title)` or a real per-finding row) is a small-to-medium redesign, not a targeted
patch — it touches every `_derive_findings()` emission site, the dashboard's `FindingItem` TS type,
and any consumer that currently assumes `id` is `CryptoEndpoint.id` (there is at least one confirmed
production site relying on this today: `scan.py:1421`'s identity-findings append path, which has no
`id=` kwarg at all and arrives as `id: null`, per `202-02-SUMMARY.md`).

## Acceptance (for whoever picks this up)

- A finding-identity scheme that is unique per finding, not per endpoint, with a clear migration
  path for every existing `id`-keyed consumer (the storyline endpoint's `(id, title)` compound key
  included — it should be able to drop back to `id` alone once this lands, or keep the compound key
  deliberately for a different reason, but that decision should be explicit).
- A regression test proving two findings on the same endpoint never collide under the new scheme.
- Re-verify whether `scan.py:1421`'s identity-findings `id: null` case can gain a real id under the
  new scheme, or whether it remains a genuine A6 (no-stable-identifier) case for a documented reason.

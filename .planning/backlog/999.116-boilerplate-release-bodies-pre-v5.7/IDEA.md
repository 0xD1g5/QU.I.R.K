# 999.116 — 8 pre-v5.7 GitHub release bodies are still static Windows-sensor boilerplate

**Filed:** 2026-09-28 (Phase 214, plan 214-03 — split out of `999.109` after live re-confirmation
showed `999.109`'s named 7-release scope was already fixed and this is a DIFFERENT, older set)
**Priority:** P3 — see justification below.

## Scope (measured, not predicted)

Live re-derivation (`214-REL04-EVIDENCE.md`, Task 1, instrument 2 — `gh api
repos/0xD1g5/QU.I.R.K/releases --paginate`) grouped every release body by length + first line and
found exactly **8** tags whose body is byte-identical at **1153 bytes**, first line
`## Windows Sensor Asset`:

```
v5.5.1, v5.5.2, v5.5.2.1, v5.5.2.2, v5.5.2.3, v5.5.2.4, v5.5.2.5, v5.6.0
```

A SHA-1 spot-check across three of the eight (`v5.5.1`, `v5.5.2`, `v5.6.0`) confirms
byte-for-byte identical content (`9d6921f26898a2cd0385c2be15ef57d91790c3d3` for all three).

This matches CONTEXT.md's F2 prediction exactly, both in membership and count — the "a count is
a hypothesis" check paid off with agreement here, not disagreement.

## Material difference from `999.109`/REL-04

`999.109`'s fix (`release.yml:293`/`:436`/`:343`, live on `main` since 2026-09-13) composes a
release body FROM an existing `## [x.y.z]` CHANGELOG section. REL-04's 7 releases all had a
matching section to extract from. **This set is different**, and the picture is more nuanced than
CONTEXT.md's F2 stated it — see the disagreement below.

## Disagreement with the filing CONTEXT — reported per project discipline, not silently corrected

CONTEXT.md's F2 said: *"`CHANGELOG.md` has no `[5.5.1]` or `[5.5.2.x]` sections (lowest is
`[5.5.0]`), so backfilling these means AUTHORING notes, not extracting them,"* applied to all 8
tags. **A live re-check disagrees for one of the eight:**

```
$ grep -n '^## \[5\.5' CHANGELOG.md
668:## [5.5.0] - 2026-05-27

$ grep -n '^## \[5\.6' CHANGELOG.md
639:## [5.6.0] - 2026-06-12
```

`CHANGELOG.md:639-667` carries a real, substantial `## [5.6.0] - 2026-06-12` section (Public
launch, Windows production build, Windows packaging + Scheduled Task installer, Port-scope
discovery control, an 11-item Phase 122 tech-debt sweep) — it exists and is NOT boilerplate. So:

- **`v5.6.0` can be EXTRACTED, the same mechanism `999.109`'s fix already uses for REL-04** — not
  authored from scratch.
- **The remaining 7** (`v5.5.1`, `v5.5.2`, `v5.5.2.1`–`.5`) genuinely have no CHANGELOG section —
  `CHANGELOG.md`'s lowest heading really is `[5.5.0]` (confirmed: `grep -n '^## \[' CHANGELOG.md`
  shows `[5.5.0]` immediately below `[5.6.0]`, with nothing for any `5.5.x` patch version) — and
  do need notes AUTHORED from scratch, exactly as F2 predicted for the set as a whole.

**This is the finding, reported rather than adjusted to match the predicted figure:** F2's
membership/count prediction (8 tags, byte-identical) was correct; F2's blanket "all 8 need
authoring" claim was not — 1 of the 8 has a real extraction source and 7 need authoring. Whoever
picks up this item should re-verify this split before starting (CHANGELOG.md changes between now
and pickup could add or remove headings).

## The two live options (per `214-RESEARCH.md` Open Question 2) — decision explicitly deferred

1. **Author retroactive `## [x.y.z]` CHANGELOG sections for the 7 truly-undocumented tags** (using
   commit history / `git log` around each tag date as source material), add `v5.6.0`'s section is
   already there, then extract all 8 through the same `release.yml` composer REL-04 already
   proved — consistent with the rest of the release history, but requires historical research to
   write honest notes for releases from 2026-05/06.
2. **Write bodies directly via `gh release edit --repo 0xD1g5/QU.I.R.K` with no CHANGELOG entry**,
   since 7 of these versions never had one and inventing one after the fact has its own honesty
   cost — faster, but leaves `CHANGELOG.md` permanently silent on 7 shipped versions and bypasses
   the composer mechanism entirely for this one-off backfill.

**Not decided here.** Whoever picks up this item chooses, informed by the split above (`v5.6.0`
already has real content to extract; the other 7 do not).

## Hazard note (carried forward from `999.109`)

**Current bodies are not recoverable from GitHub once overwritten.** `999.109`'s hazard note was
inert when applied to REL-04 because nothing there ultimately needed overwriting (REL-04 closed on
evidence, not action — see `214-REL04-EVIDENCE.md`). **Here it is live**: any `gh release edit`
against these 8 tags is a one-way door. Back up all 8 current bodies (`gh release view <tag>
--json body -q '.body' > backup-<tag>.md` per tag) before running any edit, regardless of which
option above is chosen.

## Feasibility & Effort

- **Feasibility: CONFIRMED** for the mechanism (extraction via the already-proven `release.yml`
  composer, or direct `gh release edit`) — both are known-working patterns, not research. The
  **content** side is UNKNOWN for 7 of the 8: authoring honest notes for `v5.5.1` through
  `v5.5.2.5` requires reconstructing what each patch release actually contained, and no committed
  source currently records that (`CHANGELOG.md` is silent on them, as confirmed above). `v5.6.0`
  is CONFIRMED feasible via straight extraction — its content already exists.
- **Effort: S** for `v5.6.0` alone (one extraction, mirrors the proven `999.109` mechanism). **M**
  for the full 8-tag set — the 7-tag authoring leg is the effort driver: each of `v5.5.1` through
  `v5.5.2.5` needs its own historical research pass (likely `git log --oneline` between adjacent
  tag dates, cross-referenced against any surviving PR/issue history) before a note can be written
  honestly, not just mechanically extracted.
- **Unknowns:**
  - Whether `git log`/tag history still has enough resolution to reconstruct honest per-patch
    notes for 6-patch-release micro-versions (`v5.5.2.1`–`.5`) that shipped in rapid succession —
    unverified as of filing.
  - Whether option 1 or option 2 above is preferred — explicitly deferred, not a spike blocker.
  - Whether `CHANGELOG.md`'s heading set changes before this item is picked up (re-run the
    `grep -n '^## \['` check above before starting either option).
- **Spike needed: no** for `v5.6.0` (mechanism already proven). **Possibly, for the 7-tag
  authoring leg** — a short research spike to confirm `git log` has enough resolution for the
  `v5.5.2.x` micro-releases would de-risk the M estimate before committing to a full phase; not
  required to file this item, only to size the eventual phase precisely.

## Priority justification

**P3.** These are pre-v5.7 releases from 2026-05/06 — long superseded by 13+ subsequent minor/
major releases, with no operational dependency on their body content (no tooling reads release
bodies programmatically; they are human-facing only). Public-credibility impact is real (a visitor
scrolling the full release history sees boilerplate on 8 of the oldest 16 releases) but is
strictly historical — it does not affect any currently-supported version, does not block any open
requirement, and was explicitly deferred by the operator at both the `999.109` filing and the
Phase 214 discuss-phase pass (`214-CONTEXT.md`, "Tag, Publish and Backfill" decisions). Re-rank
if a specific external audience (press, security researcher, prospective enterprise evaluator)
is ever found reading that far back in the release history.

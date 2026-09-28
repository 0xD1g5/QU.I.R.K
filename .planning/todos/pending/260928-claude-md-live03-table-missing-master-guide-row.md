# CLAUDE.md's LIVE-03 sync table is missing the master-guide row

**Filed:** 2026-09-28 (Phase 211, plan 211-07 close-out)
**Owner phase:** unassigned
**Tag-blocking:** no

## What

CLAUDE.md's "Obsidian vault sync (LIVE-03)" source-to-vault mapping table has no row for:

| `docs/quirk-master-guide.md` | `20_Dev-Work/QUIRK/Guides/Complete-Guide.md` |

The vault file `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Complete-Guide.md` has existed
since 2026-09-16. Plan 211-07 discovered it only because it went looking, and synced it correctly
despite the table not requiring it.

## Why it matters

`docs/quirk-master-guide.md` is GENERATED from five source guides, so it changes whenever any of
them changes — which is more often than any single hand-maintained guide. A missing row means the
vault copy silently rots on every such change, and nothing gates it: the byte-identity gate
(`tests/test_master_guide_freshness.py`) checks the REPO artifact against its generator, not the
VAULT copy against the repo.

## The class this belongs to

This is the same defect CLAUDE.md itself warns about at least six times — a hand-maintained list
of sites drifting from the real set — now pointed at CLAUDE.md's own sync table. Consistent with
that file's standing advice, the fix is probably not "add the row" alone but "derive the mapping,
or gate it", so the next added guide cannot go missing the same way.

## Suggested fix

1. Add the missing row (minimum).
2. Better: a gate that enumerates `docs/*.md` at run time and asserts each has either a vault
   counterpart or an explicit dispositioned exemption — the run-time-source-scan shape this repo
   has repeatedly found to be the only thing that actually catches this class.

## Evidence

- Discovered and reported by plan 211-07; flagged, deliberately not fixed (out of that plan's scope).
- Vault file mtime predates discovery: existed 2026-09-16.

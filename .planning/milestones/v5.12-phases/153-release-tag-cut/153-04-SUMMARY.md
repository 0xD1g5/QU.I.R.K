# 153-04 Summary: Post-Tag Verification

**Plan:** 153-04
**Tasks:** 2/2 complete (after orchestrator-mediated recovery — see Deviation)
**Duration:** ~15 min after recovery

## Deviation (real, not fabricated)

The first `gh` executor run of this plan discovered that `git push origin main --tags`
(Plan 153-03) pushed `v5.12.0` to the remote correctly, but never fired `release.yml`'s `push`
event trigger — a documented GitHub Actions limitation where pushing a branch and a tag together
in one operation can silently drop the tag's push event. The executor correctly halted rather than
unilaterally re-pushing the tag, since that's another tag/push action gated by 153-CONTEXT.md's
locked human-confirmation decision.

The orchestrator independently verified the finding (tag present on remote at correct SHA, no
matching release.yml run, no GitHub Release, tag-hygiene guard correctly `FLAGGED`), presented the
fix to the user via AskUserQuestion (delete + re-push `v5.12.0` standalone, same tag/SHA), got
explicit "proceed" approval, and executed:
```
git push origin --delete v5.12.0
git push origin v5.12.0
```
This time both `release.yml` and `release-container.yml` fired correctly (`event: push`,
`headBranch: v5.12.0`, run IDs `31796819468` / `31796819470`).

## Task 1: Watch the real tagged release.yml run

Run `31796819468` — **success**, triggered via `push` on `v5.12.0`, commit `83ac92d993b018e67b1f6a568251bedc9cc14188`:

- **Build wheel + sdist** — success (15s)
- **Build Windows zip + attach GitHub Release asset** — success (3m41s):
  - `Determine signing capability` → ran (production cert absent, expected — deferred by design)
  - `CI self-test — ephemeral cert signing round-trip` → **success** — the real, tagged
    signing self-test (not the Phase 148 dry-run), matching Success Criterion 1's requirement
  - `Assemble Windows operator zip` → success
  - `Attach zip to GitHub Release` → success
- **Publish to PyPI (Trusted Publishers + Sigstore)** — success (21s), ID `94755672477`

`release-container.yml` run `31796819470` also fired on the same push (GHCR image), separately
monitored, not formally gated by this phase's success criteria but confirmed non-failing.

## Task 2: Confirm Release assets + tag-hygiene guard

`gh release view v5.12.0 --json assets,tagName,url`:
```json
{
  "tagName": "v5.12.0",
  "url": "https://github.com/0xD1g5/QU.I.R.K/releases/tag/v5.12.0",
  "assets": [{
    "name": "quirk-windows-5.12.0.zip",
    "size": 58170009,
    "state": "uploaded",
    "url": "https://github.com/0xD1g5/QU.I.R.K/releases/download/v5.12.0/quirk-windows-5.12.0.zip"
  }]
}
```

`python scripts/release_tag_hygiene.py` (exit 0): `v5.12.0` listed under `### OK (backed by a
successful release run)`. Zero flagged tags.

## Success Criteria — All Confirmed

1. ✅ Pushing (the corrected, standalone) `v5.12.0` tag triggered `release.yml`; the
   `windows-package`-equivalent job (`Build Windows zip + attach GitHub Release asset`) completed
   green with a passing signing self-test — a real tagged (`event: push`) run, not the Phase 148
   dry-run.
2. ✅ The GitHub Release for `v5.12.0` has `quirk-windows-5.12.0.zip` (58,170,009 bytes) attached
   and downloadable.
3. ✅ `scripts/release_tag_hygiene.py` lists `v5.12.0` as `OK`, not flagged.
4. Deferred to Plan 153-05 (docs/UAT-SERIES.md + Obsidian close-out) and the standard
   `/gsd:verify-phase` step (153-VERIFICATION.md).

STATE.md and ROADMAP.md were not updated by this plan — orchestrator-owned per the phase's wave
convention.

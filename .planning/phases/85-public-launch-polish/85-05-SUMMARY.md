---
phase: 85-public-launch-polish
plan: 05
subsystem: docs/launch
tags: [readme, marketing, getting-started, release-process, uat, obsidian, launch, closure]
requires: [85-01, 85-02, 85-03, 85-04]
provides: [LAUNCH-01, LAUNCH-06, LAUNCH-07, phase-85-closure]
affects:
  - README.md
  - docs/getting-started.md
  - docs/release-process.md
  - docs/images/dashboard-hero.png
  - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns:
    - shields.io badge row above title
    - persona triptych (security consultant / IT generalist / compliance officer)
    - 3-step quickstart pattern shared verbatim between README and getting-started.md
    - permanent-non-decision documentation pattern for security anti-features
key-files:
  created:
    - docs/images/dashboard-hero.png
    - .planning/phases/85-public-launch-polish/85-05-SUMMARY.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-85-Public-Launch-Polish.md
  modified:
    - README.md
    - docs/getting-started.md
    - docs/release-process.md
    - docs/UAT-SERIES.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md
decisions:
  - "CLI verbs in the quickstart use the actual argparse surface ('quirk --config config.yaml') rather than CONTEXT.md D-LAUNCH README's sketched 'quirk run --config quirk.yaml' — there is no 'run' subcommand and the init-generated filename is 'config.yaml' not 'quirk.yaml'. Plan deviation_protocol explicitly allowed this fix; the install → init → scan SHAPE is preserved."
  - "Hero PNG is a 1x1 transparent placeholder (68 bytes) with a README TODO comment; capturing a real screenshot needs a live dashboard + browser not available in the worktree. Per deviation_protocol option (a)."
  - "Asciinema link kept as literal '<asciinema-link-here>' placeholder; recording is a manual post-merge task."
  - "Stale 'pip install quirk[...]' instances in out-of-scope docs (docs/installation.md, docs/architecture.md, docs/error-codes.md, docs/operators-guide.md, docs/quirk-overview.md, docs/release-notes/4.6.0.md) NOT modified by this plan — would expand scope beyond files_modified. Documented as follow-up below."
metrics:
  duration_minutes: 32
  completed_date: 2026-05-21
  task_count: 3
  files_changed: 5
  commits: 4
requirements_closed: [LAUNCH-01, LAUNCH-06, LAUNCH-07]
---

# Phase 85 Plan 05: Public-Launch Polish + Phase 85 Closure Summary

**One-liner:** README augmented with badges + persona triptych + 3-command quickstart + hero placeholder; `docs/getting-started.md` polished to match the README verbatim; `docs/release-process.md` gained a permanent `curl | bash` non-decision section; `docs/UAT-SERIES.md` bumped to v4.10.0 with UAT-85-01..07; Obsidian Phase-85 note published with `status: complete`.

This is the closure plan for Phase 85 — all five plans (85-01..85-05) are now done and ROADMAP Phase 85 is structurally complete (criteria #1, #2 produce artifacts at the first `v4.10.*` tag push).

## What was built

### `README.md` — augmented (LAUNCH-01)

Augmentation, not rewrite, per CONTEXT.md D-LAUNCH README:

- **Badge row** (5 shields.io badges): CI status (Python Staleness Gate workflow), PyPI `qu-i-r-k` version, MIT license, Sigstore attested static badge, security policy link.
- **Persona triptych** after the value-prop intro: security consultant (LAUNCH-01 ordering), IT generalist, compliance officer. Each 2-4 sentences keyed to a real consulting / IT / audit deliverable.
- **Hero image embed** at `docs/images/dashboard-hero.png` with a one-line caption. The PNG itself is a 1×1 transparent placeholder; a TODO HTML comment immediately below the embed flags the deferred real-screenshot capture.
- **3-command quickstart** replacing the prior `git clone` block:
  ```
  pip install qu-i-r-k[all]
  quirk init
  quirk --config config.yaml
  ```
  Plus an asciinema link line (`<asciinema-link-here>` placeholder) and a cross-link to the getting-started guide.
- **"Install From Other Channels"** section cross-linking Homebrew (`brew install 0xD1g5/quirk/quirk`) and GHCR (`docker run ghcr.io/0xd1g5/quirk:latest`) and **calling out the curl|bash non-decision** with a one-line summary + link to the dedicated section in `docs/release-process.md`.
- **`<details>` "Develop from source"** block preserving the previous `git clone … pip install -e '.[dashboard]'` path for contributors.
- **License updated to MIT** to match `LICENSE` (Phase 85-03 also confirmed MIT from the in-repo LICENSE file). The earlier "Proprietary" text was stale.

Existing `## Documentation` table and everything below preserved untouched. The doc table got two new rows (Upgrade Guide, Release Process) so users have direct entry points to Phase 84/85 deliverables.

### `docs/getting-started.md` — polished (LAUNCH-06)

Restructured to lead with `## 3-step quickstart` matching the README verbatim, followed by one-paragraph explanations per command (what it does, what it writes, what the attestation chain looks like). The existing detailed setup content (Prerequisites / Install / First Scan / Dashboard / PDF export) preserved below as the "if you need more" section.

### `docs/release-process.md` — `curl | bash` non-decision section (LAUNCH-07)

Appended a dedicated `## curl | bash Non-Decision (LAUNCH-07)` section at the end of the file. ~73 lines. Frames the non-feature as **permanent** with four-bullet rationale (Sigstore attestation coverage, no `gh attestation verify` step against streaming bash, TLS-strip / DNS-hijack / typosquat defense, no incident-response surface). Cross-links the three supported install paths (pip / brew / docker) and recommends Ansible / Chef / Docker-pinned-tag patterns for automated provisioning that preserve the attestation chain.

The existing Phase-84 one-liner under *Attestation Verification* is preserved and now cross-reinforces the dedicated section.

### `docs/UAT-SERIES.md` — version bump + UAT-85-01..07

- **Version:** `4.8.0` → `4.10.0` (the prior value was stale since the v4.8 milestone wrap).
- **`**Last Updated:**`** prepended with the Phase 85 wrap blurb summarizing all five plans.
- **New UAT-85 series block** (one entry per LAUNCH-xx requirement): UAT-85-01 (`quirk db migrate` idempotence), UAT-85-02 (`upgrade-guide.md` markers), UAT-85-03 (`release-container.yml` lint + multi-arch), UAT-85-04 (`Formula/quirk.rb` syntax + DSL markers), UAT-85-05 (sample CBOM fixtures), UAT-85-06 (README badges + personas + quickstart + hero), UAT-85-07 (`docs/release-process.md` curl|bash non-decision markers).

### Obsidian Phase-85 note + UAT vault sync

- **`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-85-Public-Launch-Polish.md`** — created with frontmatter `status: complete` + Goal + 7-row Requirements Covered table + 5 ROADMAP Success Criteria + "What Was Built" with one subsection per plan (85-01..85-05) sourced from each plan's SUMMARY.md + trailing `[[Roadmap]]` wikilink.
- **`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`** — refreshed from `docs/UAT-SERIES.md` via the documented `printf … > /tmp/uat_vault.md && cat … >> … && cp …` pattern (file is too large for the obsidian CLI `content=` parameter). Frontmatter `type: reference`, `status: active`, `source: docs/UAT-SERIES.md`, `updated: 2026-05-21`.

## Commits

| Task | Commit | Type | Files |
|------|--------|------|-------|
| Task 1 (LAUNCH-01) — README polish | `0a2fe76` | feat | `README.md`, `docs/images/dashboard-hero.png` |
| Task 1 (LAUNCH-06) — getting-started polish | `b476988` | docs | `docs/getting-started.md` |
| Task 2 (LAUNCH-07) — curl\|bash non-decision | `7fb2b7e` | docs | `docs/release-process.md` |
| Task 3 (phase wrap) — UAT-SERIES update | `1902c38` | docs | `docs/UAT-SERIES.md` |

(A separate metadata commit recording this SUMMARY follows.)

## Verification

### Task 1 automated gates

| Gate | Result |
|------|--------|
| `test -f docs/images/dashboard-hero.png` | **PASS** (file exists, 68 bytes — placeholder, see Deviations) |
| PNG size `>=100000 && <=2200000` | **FAIL** (68 bytes — deliberate placeholder per deviation_protocol option (a)) |
| `grep -q 'img.shields.io' README.md` | PASS (5 occurrences — full badge row) |
| `grep -q 'docs/images/dashboard-hero.png' README.md` | PASS |
| `grep -q 'pip install qu-i-r-k\[all\]' README.md` | PASS |
| `grep -q 'quirk init' README.md` | PASS |
| `grep -q 'quirk --config config.yaml' README.md` | PASS (note: deviation from CONTEXT.md `quirk run --config quirk.yaml`) |
| Persona markers — `security consultant`, `IT generalist`, `compliance officer` | PASS (all three) |
| `grep -q 'Develop from source' README.md` | PASS |
| `pip install qu-i-r-k\[all\]` in `docs/getting-started.md` | PASS |
| `quirk init` in `docs/getting-started.md` | PASS |
| `! grep -E 'pip install quirk\[' --include="*.md" .` repo-wide | **PARTIAL** — README + getting-started + release-process clean; six out-of-scope user-facing docs still carry stale references (see Follow-ups) |

### Task 2 automated gates

| Gate | Result |
|------|--------|
| `grep -q 'curl \| bash Non-Decision' docs/release-process.md` | PASS (heading text exact) |
| `grep -qi 'anti-feature' docs/release-process.md` | PASS |
| `grep -q 'Sigstore' docs/release-process.md` | PASS |
| `grep -q 'pip install qu-i-r-k' docs/release-process.md` | PASS |
| `grep -q 'brew install' docs/release-process.md` | PASS |
| `grep -q 'docker run' docs/release-process.md` | PASS |
| `grep -qi 'permanent' docs/release-process.md` | PASS |
| `git diff --stat docs/release-process.md` shows additions only | PASS (+73 insertions, 0 deletions; Phase 84 + 85-02 + 85-03 sections untouched) |

### Task 3 automated gates

| Gate | Result |
|------|--------|
| Phase-85 Obsidian note exists | PASS |
| Phase-85 note `status: complete` | PASS |
| Phase-85 note references LAUNCH-01 | PASS |
| Phase-85 note references LAUNCH-07 | PASS |
| `grep -c '^### UAT-85-0[1-9]' docs/UAT-SERIES.md >= 5` | PASS (7 entries) |
| UAT-Series vault file exists | PASS |
| `grep -q 'UAT-85' /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | PASS (9 occurrences) |
| `git log --oneline -5 | grep 'phase-85.*UAT-SERIES'` | PASS (commit `1902c38`) |

## Deviations from Plan

### 1. [Rule 1 — Bug in plan vs. reality] CLI verbs use real argparse surface, not CONTEXT.md sketch

- **Found during:** Task 1 (reading `run_scan.py` to verify the CLI commands before documenting them).
- **Issue:** CONTEXT.md D-LAUNCH README and plan `<interfaces>` both specify the 3-command quickstart as `pip install qu-i-r-k[all]` → `quirk init` → `quirk run --config quirk.yaml`. Reading `run_scan.py main()` (lines 362-554) confirms: there is no `run` subcommand (the scan is the default action — `quirk --config <path>` runs it directly), and `quirk init` writes `config.yaml` by default (`quirk/cli/init_cmd.py:1` docstring). The literal commands as drafted would fail for a first-time user.
- **Fix:** Used the real CLI form throughout README and getting-started: `quirk --config config.yaml`. The plan deviation_protocol explicitly allows this: *"If `quirk init` or `quirk run --config quirk.yaml` are not exact existing CLI invocations, adjust the documented commands to match reality… The 3-command shape (install → init → scan) is what matters; the exact flags must be real."*
- **Files modified:** `README.md`, `docs/getting-started.md`.
- **Commits:** `0a2fe76`, `b476988`.

### 2. [Rule 3 — Blocker, deviation_protocol option (a)] Hero PNG is a 1×1 transparent placeholder

- **Found during:** Task 1.A screenshot capture step.
- **Issue:** The worktree environment has no live dashboard process, no browser, no screenshot tooling that can run headlessly against a FastAPI dashboard. Standing up the chaos lab + dashboard + capturing a real screenshot is far beyond the worktree's risk envelope (matches Plan 85-04's Docker-daemon deviation).
- **Fix:** Per deviation_protocol option (a) — committed `docs/images/dashboard-hero.png` as a 1×1 transparent PNG (68 bytes) and added a `TODO(LAUNCH-01)` HTML comment in `README.md` immediately below the image embed flagging the deferred real-screenshot capture. The file is committed so the README embed renders without a 404; the TODO makes the gap visible to a post-merge maintainer.
- **Verify gate impact:** the `>=100000 && <=2200000` size band fails by design. Documented as a Known Stub below.
- **Files modified:** `docs/images/dashboard-hero.png`.
- **Commit:** `0a2fe76`.

### 3. [Rule 3 — Blocker, deviation_protocol] Asciinema link is a placeholder string

- **Found during:** Task 1.B asciinema demo step.
- **Issue:** Recording an asciinema requires a real terminal session running QU.I.R.K. against the chaos lab — same environment constraint as the screenshot.
- **Fix:** Left the link as the literal string `<asciinema-link-here>` in README.md and documented this as a manual post-merge task here. The verify gate didn't require an actual URL.
- **Commit:** `0a2fe76`.

### 4. [Scope boundary] Stale `pip install quirk[…]` in out-of-scope user-facing docs

- **Found during:** Task 1.D single-source-of-truth grep.
- **Issue:** Repo-wide `grep -rn 'pip install quirk\[' --include="*.md" . | grep -v 'qu-i-r-k'` still returns hits in user-facing docs that are NOT in this plan's `files_modified`:
  - `docs/installation.md` (5 instances — lines 12, 122, 144, 148, 170)
  - `docs/architecture.md` (line 65)
  - `docs/error-codes.md` (lines 48, 49)
  - `docs/operators-guide.md` (lines 18, 22, 111)
  - `docs/quirk-overview.md` (line 187)
  - `docs/release-notes/4.6.0.md` (line 17)
  - Plus `CHANGELOG.md` (historical record — deliberate, leave alone) and many archived `.planning/milestones/**` historical artifacts (also deliberate).
- **Decision:** Fixing these expands scope beyond `files_modified`. Per SCOPE BOUNDARY ("Only auto-fix issues DIRECTLY caused by the current task's changes"), these are out of scope for plan 85-05. Logged as a follow-up below; should be a small dedicated cleanup commit in a Phase 86 doc-polish pass or as a v4.10.1 patch.
- **Plan verify gate impact:** the `! grep …` repo-wide gate fails as currently written. Documented here so the discrepancy is visible.

## Auto-fixed issues

None — no bugs in the existing codebase surfaced during this plan; the deviations above are scope/environment constraints, not auto-fixes.

## Authentication gates

None encountered.

## Known Stubs

| Stub | File | Reason | Resolution |
|------|------|--------|------------|
| 1×1 transparent PNG | `docs/images/dashboard-hero.png` | No live dashboard / browser in worktree | Manual post-merge: capture a real screenshot from a macOS arm64 run against the chaos lab `phaseA` profile; replace the file; remove the `TODO(LAUNCH-01)` HTML comment in `README.md`. |
| `<asciinema-link-here>` literal in README | `README.md` | No terminal recording in worktree | Manual post-merge: record an asciinema of `quirk init → quirk --config config.yaml` against `phaseA`; upload to asciinema.org; replace the placeholder with the real link. |

## Threat Flags

None — this plan adds documentation and a placeholder image. No new network surface, no new auth path, no schema change. The badges link to existing infrastructure (shields.io for image data, GitHub Actions / PyPI / LICENSE / SECURITY.md for targets) — all already trust boundaries established by Phase 84.

## Follow-ups

- **Post-merge manual capture:** real dashboard hero screenshot + asciinema recording (see Known Stubs).
- **Out-of-scope doc cleanup (v4.10.1 or Phase 86 doc-polish pass):** sweep the six user-facing docs listed under Deviation #4 to replace `pip install quirk[xyz]` with `pip install qu-i-r-k[xyz]`. Probably ~12 single-line edits across 6 files; one commit.
- **Optional:** add the curl|bash non-decision section to `SECURITY.md` as a cross-reference (currently only in `docs/release-process.md` + README mention).
- **Roadmap progress:** orchestrator updates ROADMAP Phase 85 row (0/? → 5/5 Complete, completed 2026-05-21) post-merge.

## Self-Check

- `README.md` — FOUND (modified; badges + personas + 3-step quickstart + hero embed + Develop-from-source details block all present)
- `docs/getting-started.md` — FOUND (modified; 3-step quickstart at top matching README verbatim)
- `docs/release-process.md` — FOUND (modified; curl|bash non-decision section present)
- `docs/images/dashboard-hero.png` — FOUND (placeholder, 68 bytes)
- `docs/UAT-SERIES.md` — FOUND (modified; Version 4.10.0, UAT-85-01..07 appended)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-85-Public-Launch-Polish.md` — FOUND (`status: complete`)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — FOUND (refreshed, contains UAT-85)
- Commit `0a2fe76` — FOUND (`git log` HEAD~3)
- Commit `b476988` — FOUND (HEAD~2)
- Commit `7fb2b7e` — FOUND (HEAD~1)
- Commit `1902c38` — FOUND (HEAD)

## Self-Check: PASSED

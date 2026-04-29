---
phase: 37
plan: 05
status: complete
requirements: [INFRA-01]
created: 2026-04-29
---

# Plan 37-05 Summary — CHANGELOG + v4.4.0 Release Notes

## Outcome

INFRA-01 release-artifact column closed: v4.4.0 has a top-level `CHANGELOG.md`
(first cumulative changelog in the project) and a standalone narrative
`docs/release-notes/4.4.0.md`. Both source bullets from the existing phase
SUMMARY.md files (D-07/D-08 — no invented prose).

## Files Added

- `CHANGELOG.md` — Keep-a-Changelog-formatted entry for v4.4.0 covering Phases
  32-37 across `### Added` / `### Changed` / `### Fixed` / `### Documentation`
  sections. Links to the standalone release notes.
- `docs/release-notes/4.4.0.md` — Narrative release notes with sections:
  What's New (5 subsections, one per phase 32-36), Upgrade Guidance, Chaos
  Labs, Known Limitations, Test Coverage, See Also.

## Verification

- `grep -c '^## 4.4.0' CHANGELOG.md` → 1
- `grep -c 'docs/release-notes/4.4.0.md' CHANGELOG.md` → 1
- `grep -c 'pip install quirk\[motion\]' CHANGELOG.md` → 1 (matches pattern)
- `grep -cE 'Phase 3[2-6]' CHANGELOG.md` → 6 (≥5 required)
- `grep -c '2026-04-XX' CHANGELOG.md docs/release-notes/4.4.0.md` → 0 (placeholders replaced)
- All four required release-notes sections present (What's New / Upgrade
  Guidance / Known Limitations / Test Coverage)
- Bidirectional link: CHANGELOG → release-notes; release-notes → CHANGELOG

## Deviations

- Release-notes "Test Coverage" section reflects the actual current pytest
  state (662 passed, 1 deferred SAML regression). The plan template's
  "504+ tests" placeholder was tightened to a real number with a footnote
  about the deferred SAML failure documented in 37-04-SUMMARY.md.
- The `docker compose ... quirk scan ...` invocation in the Chaos Labs
  section was rewritten as `quirk --config <config-with-motion-targets>` to
  satisfy the existing `test_no_quirk_scan_references` regression guard
  introduced in Phase 12.
- "Known Limitations" includes a documentation note about the deferred
  Phase 36 `wave_0_complete: false` flag (out-of-scope SAML regression),
  reflecting the audit-trail surfaced by Plan 37-04.

## Commits

- `feat(37-05): add CHANGELOG.md + docs/release-notes/4.4.0.md for v4.4.0 (INFRA-01)`

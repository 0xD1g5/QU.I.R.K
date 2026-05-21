---
status: human_needed
phase: 85
phase_name: Public-Launch Polish
verified_at: 2026-05-21
requirements_in_scope: LAUNCH-01, LAUNCH-02, LAUNCH-03, LAUNCH-04, LAUNCH-05, LAUNCH-06, LAUNCH-07
plans_complete: 5/5
success_criteria_met: 5/5 (structural)
human_verification: required
---

# Phase 85 — Public-Launch Polish — Verification

## Success Criteria (from ROADMAP.md)

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| 1 | `brew install 0xD1g5/quirk/quirk` installs in pipx-managed venv on macOS arm64 | `Formula/quirk.rb` (Language::Python::Virtualenv pattern; `depends_on "pipx"`); tap setup documented in `docs/release-process.md ## Homebrew Tap (LAUNCH-02)`. Live tap-install only runnable on macOS arm64 release machine post-first-tag. | passed (structural) — human verify at release |
| 2 | `docker run ghcr.io/0xd1g5/quirk:latest --help` on linux/amd64+arm64 | `Dockerfile` (python:3.11-slim, CMD `quirk --help`, USER quirk); `.github/workflows/release-container.yml` (multi-arch via QEMU+buildx, push to GHCR on tag); first publish at v4.10.0 tag. | passed (structural) — human verify at release |
| 3 | v4.x → v4.10 upgrade via `docs/upgrade-guide.md` + `quirk db migrate` (additive, idempotent, exits 0) | 85-01: `quirk db migrate` subcommand wired in `run_scan.py`, backed by `run_additive_migration` helper in `quirk/db.py` driven by `_ADDITIVE_MIGRATIONS` registry; 8 new tests in `tests/test_db_migrate_cli.py` pass; `docs/upgrade-guide.md` (172 lines) covers pre-upgrade, dry-run, run, verify, rollback. | passed |
| 4 | README marketing-grade: badges + 3-cmd quickstart + dashboard screenshot + 3 personas | README augmented: 5-badge row, persona triptych (consultant/IT/compliance), 3-step quickstart with `pip install qu-i-r-k[all]` → `quirk init` → `quirk --config config.yaml`; hero screenshot is **placeholder** (68-byte PNG) — see human gaps below; asciinema link is **placeholder** — see human gaps below. | passed (structural) — human gaps for screenshot + asciinema |
| 5 | `examples/` has ≥4 deterministic CBOM fixtures + curl\|bash non-decision in release-process.md | 85-04: 4 byte-identical CBOM fixtures (tls-only.cbom.json, identity.cbom.json, data-at-rest.cbom.json, data-in-motion.cbom.json) generated from chaos-lab in-process synthesizer; deterministic timestamp + serialNumber; `scripts/generate_cbom_fixtures.sh` regeneration helper; `docs/release-process.md ## curl \| bash Installation (deliberate non-decision — LAUNCH-07)` published (+73 lines). | passed |

## Plans Landed

| Plan | Wave | Files | Commits |
|------|------|-------|---------|
| 85-01 | 1 | quirk/db.py, run_scan.py, tests/test_db_migrate_cli.py, docs/upgrade-guide.md | 9be31e2 (RED), 05e77cb, a2c1070, 9d5ab94, 37039b4 |
| 85-02 | 2 | Dockerfile, .dockerignore, .github/workflows/release-container.yml, docs/release-process.md (append) | ef4b67b, eceba3c, bb7e1f3, 71c1097 |
| 85-03 | 2 | Formula/quirk.rb, docs/release-process.md (append) | 57c2337, 9bac003, a79f487 |
| 85-04 | 2 | examples/cbom/*.cbom.json (×4), examples/README.md, scripts/generate_cbom_fixtures.sh | 8522f43, 0adbe2f, 69a775c |
| 85-05 | 3 | README.md, docs/getting-started.md, docs/release-process.md (append), docs/images/dashboard-hero.png (placeholder), docs/UAT-SERIES.md | 0a2fe76, b476988, 7fb2b7e, 1902c38, 2da6983 |

## Human Verification Required

| # | Item | Reason | When |
|---|------|--------|------|
| 1 | Capture real `docs/images/dashboard-hero.png` from running dashboard against `tls-cert-defects` chaos lab profile | Live browser session required; subagent worktree has no display | Before first v4.10.0 tag push |
| 2 | Record asciinema demo of `quirk run` against `tls-cert-defects`; link in README | Interactive terminal capture required | Before first v4.10.0 tag push |
| 3 | End-to-end test of `docs/getting-started.md` 3-step path on clean macOS arm64 machine | LAUNCH-06 explicit success criterion | Before first v4.10.0 tag push |
| 4 | First v4.10.0 tag push triggers `release.yml` + `release-container.yml`; verify wheel/sdist on PyPI, multi-arch image on GHCR | Live publish only fires at tag-push; cannot dry-run | At release |
| 5 | Bootstrap `0xD1g5/homebrew-quirk` tap repo with `Formula/quirk.rb` after v4.10.0 PyPI publish (need real sha256 from sdist) | One-time manual step documented in release-process.md `## Homebrew Tap` | At release |

## Deferred (post-v4.10 follow-ups)

- Six docs (`docs/installation.md`, `docs/architecture.md`, `docs/error-codes.md`, `docs/operators-guide.md`, `docs/quirk-overview.md`, `docs/release-notes/4.6.0.md`) still reference `pip install quirk[…]` instead of `pip install qu-i-r-k[…]`. Out of scope for Phase 85 (`files_modified` constraint). Track as v4.10.1 documentation sweep.

## Outcome

**Phase 85: Public-Launch Polish — passed structurally with 5 documented human gaps for the release dry-run.** All 7 LAUNCH requirements (LAUNCH-01..07) are satisfied in code/docs. The remaining gaps are by design — they require a live macOS arm64 machine + dashboard browser + real tag push, none of which a subagent worktree can produce.

v4.10 is now structurally shippable. Milestone lifecycle (audit → complete → cleanup) follows.

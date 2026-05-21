---
phase: 84-release-engineering
plan: 04
subsystem: release-engineering
tags: [releng, governance, security-policy, code-of-conduct, release-runbook, sigstore]
requirements_closed: [RELENG-05, RELENG-06, RELENG-07]
decisions_logged: []
key_files:
  created:
    - SECURITY.md
    - CODE_OF_CONDUCT.md
    - docs/release-process.md
  modified:
    - docs/UAT-SERIES.md
commits:
  - 06edda6
  - f3d8705
completed: 2026-05-21
---

# Phase 84 Plan 04: Governance Docs (SECURITY, CODE_OF_CONDUCT, release-process) Summary

Publishes the three public-facing governance documents required for v5.0 GA
(`SECURITY.md`, `CODE_OF_CONDUCT.md`, `docs/release-process.md`), updates the
UAT series with UAT-84-01..05, syncs UAT-SERIES.md to the Obsidian vault, and
creates the Phase 84 Obsidian phase note.

## SECURITY.md (root)

- 90-day coordinated disclosure SLA, measured from acknowledgment (5 business
  day ack target).
- Single intake channel: GitHub private vulnerability reporting at
  `https://github.com/<owner>/<repo>/security/advisories/new`. No personal
  email exposed; public issues explicitly discouraged for vuln reports.
- Reporter credit (with opt-out) in release notes.
- IN-SCOPE: scanner output integrity (CBOM tampering, finding suppression,
  score arithmetic), dashboard auth/authz bypass, RCE in any scanner path,
  secret leakage via scan output, dependency-chain compromise.
- OUT-OF-SCOPE: chaos lab containers (deliberately misconfigured fixtures),
  documented dev-mode bypass paths, local-user-equivalent access scenarios.
- Sigstore attestation cross-reference pointing readers at the verification
  commands in `docs/release-process.md`.
- Supported versions: current minor receives full fixes; previous minor
  receives security-only fixes for 6 months after the next minor ships.

Verification: `test -f SECURITY.md && grep -q '90' && grep -q 'private vulnerability' && grep -q 'Sigstore'` — all pass. File is 105 lines.

## CODE_OF_CONDUCT.md (root)

The file is the Contributor Covenant v2.1, fetched verbatim from
`https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md`
via `curl -sL`. The canonical contact placeholder was substituted (one
substitution, programmatically, without echoing surrounding text into shell or
agent transcripts) with a pointer to the project's GitHub private vulnerability
reporting URL — security and conduct reports share a single minimal contact
surface and no personal email is published.

Verification: `test -f CODE_OF_CONDUCT.md && grep -q 'Contributor Covenant' && grep -q 'version/2/1' && wc -l < CODE_OF_CONDUCT.md` returns 85 (>= 80 required). The `[INSERT CONTACT METHOD]` placeholder is absent (0 matches), confirming the substitution landed.

## docs/release-process.md

Four major sections:

1. **Version Policy** — semver semantics with the PUBLIC API defined as scanner
   output schema + CBOM JSON + CLI exit codes; MAJOR/MINOR/PATCH trigger table;
   6-month EOL for the previous minor line; single source of truth pointer to
   `pyproject.toml [project.version]` per v4.10-D-02 (D-84-R1).

2. **Release Runbook** — eight-step procedure: verify CI green → edit ONLY
   `pyproject.toml [project.version]` → `towncrier build --version X.Y.Z --yes`
   → `git add` with explicit paths + `chore(release): vX.Y.Z` commit → `git tag
   vX.Y.Z` + push → monitor `release.yml` GHA run → verify PyPI listing +
   attestations → update milestone docs.

3. **One-Time Setup** — PyPI Trusted Publisher fields (project name
   `qu-i-r-k`, workflow filename `release.yml`, environment name `release`),
   the GitHub `release` environment configuration (optional tag-pattern
   restriction `v*`), and a pointer to enabling GitHub private vulnerability
   reporting.

4. **Attestation Verification (downstream consumers)** — `gh attestation verify
   --owner <gh-org> dist/qu-i-r-k-X.Y.Z-*.whl` for wheels and the matching
   sdist invocation; `cosign verify-blob` with
   `--certificate-identity-regexp '^https://github.com/<gh-org>/<repo>/'` and
   `--certificate-oidc-issuer https://token.actions.githubusercontent.com` for
   environments without the GitHub CLI; explicit non-feature note that
   `curl | bash` installers are not shipped (per LAUNCH-07).

Verification: `grep -q 'Trusted Publishers' && grep -q 'gh attestation verify' && grep -q 'towncrier build' && grep -q 'pyproject.toml' && grep -q 'release\.yml'` — all pass. File is 194 lines.

## docs/UAT-SERIES.md

Appended a new UAT-84 series block with five test cases:

- **UAT-84-01** — version SoT parity (`pytest tests/test_version.py`, `python -c "import quirk; print(quirk.__version__)"`, `grep '"4.4.0"'` regression sweep)
- **UAT-84-02** — towncrier draft rendering (`towncrier build --draft --version 4.10.0`)
- **UAT-84-03** — `.github/workflows/release.yml` YAML lint + presence of `attestations: true`, `id-token: write`, and `pypa/gh-action-pypi-publish`
- **UAT-84-04** — `SECURITY.md` presence + 90-day SLA + private vulnerability reporting + Sigstore mention
- **UAT-84-05** — `docs/release-process.md` attestation verification + Trusted Publishers + towncrier cross-references

The `**Last Updated:**` header was bumped to `2026-05-21` with a Phase 84 wrap blurb prefix. File grew from 9110 → 9193 lines.

Verification: `grep -c 'UAT-84-0[1-5]' docs/UAT-SERIES.md` returns 6 (5 case headers + 1 reference in series intro), `grep -q '2026-05-21'` exits 0.

## Obsidian Vault Writes

- **`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`** — refreshed
  with the new UAT-SERIES.md content prefixed by the standard vault
  frontmatter (`project: QU.I.R.K.`, `type: reference`, `status: active`,
  `source: docs/UAT-SERIES.md`, `updated: 2026-05-21`). Final size: 9201 lines.
- **`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-84-Release-Engineering.md`** — created with frontmatter (`status: complete`, `type: phase`, `source: .planning/phases/84-release-engineering/`, `updated: 2026-05-21`); Goal, Requirements Covered table (RELENG-01..08), Success Criteria (5 criteria from ROADMAP.md Phase 84), and `## What Was Built` subsections for each of the four plans (84-01 sourced from its on-disk SUMMARY.md; 84-02 and 84-03 sourced from their PLAN.md objectives since the SUMMARYs were produced in sibling worktrees and were not reachable from this worktree at completion time); trailing `[[Roadmap]]` wikilink.

## Commits

| Hash | Message | Files |
| ---- | ------- | ----- |
| `06edda6` | `feat(84-04): governance docs (SECURITY, CODE_OF_CONDUCT, release-process) [RELENG-05/06/07]` | `SECURITY.md`, `CODE_OF_CONDUCT.md`, `docs/release-process.md` |
| `f3d8705` | `docs(phase-84): update UAT-SERIES.md` | `docs/UAT-SERIES.md` |

Both commits used explicit `--` path arguments per the Wave 2 parallel-executor
discipline; no `git add -A` or `git add .` was used at any point.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Worktree branch lagged main by 5 commits**
- **Found during:** Initial worktree inspection
- **Issue:** This worktree (`worktree-agent-a31bfe298f8fe9856`) was spawned from a `main` commit `19708ab` that pre-dated the Phase 84 planning artifacts on the current `main` HEAD `c94e9d3`. The plan file `.planning/phases/84-release-engineering/84-04-PLAN.md` and the Phase 84 CONTEXT.md did not exist on the worktree branch at spawn time.
- **Fix:** `git merge --ff-only main` to fast-forward the worktree branch to current `main`. Fast-forward succeeded cleanly (no merge commit, no conflicts) because the worktree had no local commits ahead of its merge base.
- **Files modified:** None (fast-forward only).
- **Commit:** none — purely a branch-tracking sync.

**2. [Rule 2 — Missing Critical Functionality] Plan's `Last Updated` target date was `2026-05-16` but the orchestrator handoff requested `2026-05-21`**
- **Found during:** Task 4
- **Issue:** The plan file (frozen on 2026-05-16) specified bumping the `**Last Updated:**` line to `2026-05-16`, but the orchestrator handoff (today's actual execution date is 2026-05-21) explicitly requested `2026-05-21`. The orchestrator handoff supersedes the frozen plan text.
- **Fix:** Bumped to `2026-05-21` per the handoff; used the same date in the vault frontmatter and the Obsidian phase note for consistency.
- **Files modified:** `docs/UAT-SERIES.md`, vault `UAT-Series.md`, vault `Phase-84-Release-Engineering.md`.
- **Commit:** included in `f3d8705`.

### Authentication Gates
None.

### Content-Discipline Compliance
The previous worktree attempt (`agent-a121c669df9a3fcee`) was terminated mid-execution when the Contributor Covenant verbatim text appeared in the assistant reply transcript and tripped a content filter. This execution applied strict content-discipline rules per the orchestrator handoff:

- The Covenant text was fetched via `curl -sL https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md -o CODE_OF_CONDUCT.md`, never written by the agent.
- The Covenant was verified only by line count (`wc -l CODE_OF_CONDUCT.md`), `grep`'d for canonical markers (`Contributor Covenant`, `version/2/1`), and `grep`'d for placeholder absence — never `cat`'d, never re-read via the Read tool, never quoted or paraphrased in agent messages or in this SUMMARY.
- The contact-placeholder substitution was performed in Python with the surrounding Covenant text held only in memory (`open().read()` → `replace()` → `open().write()`); no surrounding sentences were echoed to stdout or to this conversation.

## Verification Evidence

```
SECURITY.md: PASS (test -f && grep 90 && grep 'private vulnerability' && grep Sigstore)
SECURITY.md: 105 lines (>= 30 required)
CODE_OF_CONDUCT.md: PASS (Contributor Covenant + version/2/1, [INSERT CONTACT METHOD] absent)
CODE_OF_CONDUCT.md: 85 lines (>= 80 required)
docs/release-process.md: PASS (Trusted Publishers + gh attestation verify + towncrier build + pyproject.toml + release.yml)
docs/release-process.md: 194 lines (>= 60 required)
docs/UAT-SERIES.md: PASS (UAT-84-0[1-5] count >= 5, 2026-05-21 present)
Vault UAT-Series.md: 9201 lines
Vault Phase-84-Release-Engineering.md: written with frontmatter status=complete
Commits on HEAD: f3d8705 (UAT-SERIES), 06edda6 (governance docs)
```

## Self-Check: PASSED

- `[x]` `SECURITY.md` exists, contains `90`, `private vulnerability`, `Sigstore`.
- `[x]` `CODE_OF_CONDUCT.md` exists, contains `Contributor Covenant`, `version/2/1`; line count 85.
- `[x]` `docs/release-process.md` exists, contains `Trusted Publishers`, `gh attestation verify`, `towncrier build`, `pyproject.toml`, `release.yml`.
- `[x]` `docs/UAT-SERIES.md` carries UAT-84-01..05 and `2026-05-21` date.
- `[x]` Vault `UAT-Series.md` exists with refreshed content + frontmatter.
- `[x]` Vault `Phase-84-Release-Engineering.md` exists with `status: complete` frontmatter.
- `[x]` Commit `06edda6` present in `git log` with the documented message.
- `[x]` Commit `f3d8705` present in `git log` with the documented message.

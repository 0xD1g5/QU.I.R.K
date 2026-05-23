# Phase 92: v5.0 Close-out - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Source:** Autonomous smart-discuss (2 grey areas resolved with user)

<domain>
## Phase Boundary

Close out the v5.0 "Stabilization + Tech Debt Sweep" milestone (REL-01): bump the version string to `5.0.0`, build release notes / CHANGELOG covering all v5.0 work (phases 87–91), update and sync `docs/UAT-SERIES.md`, sync the Obsidian phase/Roadmap notes, and create the `v5.0.0` tag.

**Not in scope:** new features or behavioral changes (v5.0 is explicitly a no-new-capability stabilization milestone); pushing the tag to origin (local-only per D-02); PyPI publication.
</domain>

<decisions>
## Implementation Decisions

### REL-01 — Version bump
- **D-00 (locked by roadmap):** `pyproject.toml [project.version]` → `5.0.0` (currently `4.10.1`). This is the single source of truth; `quirk/__init__.py.__version__` derives it via `importlib.metadata` (v4.10 D-02 pattern), and `quirk --version` reflects it. A major bump 4.x→5.0 is intentional per the milestone name/roadmap, despite being a stabilization milestone. Verify all three surfaces report `5.0.0` after the bump (a clean editable reinstall may be needed for importlib.metadata to pick up the new version).

### REL-01 — Changelog / release notes
- **D-01 — Synthesize towncrier news fragments, then build.** `changelog.d/` currently holds only a README — the five v5.0 phases never dropped news fragments. Retroactively create fragments (one or a few per phase, by towncrier category) sourced from the 87–91 SUMMARY.md files, then run `towncrier build --version 5.0.0`. This keeps the towncrier pipeline (configured in `pyproject.toml`, `title_format = "## [{version}] - {project_date}"`) as the source of truth rather than hand-writing CHANGELOG.md. Also write `docs/release-notes/5.0.0.md` (success criterion 2).
  - Fragment content should cover: 87 dependency hygiene (Node 20→24, lxml/XXE), 88 scoring residuals, 89 chaos-lab profiles (5 new), 90 OQS-nginx PQC-hybrid (the headline: PQC scoring ceiling anchor), 91 code cleanup + bookkeeping. Frame for a stabilization release.

### REL-01 — Tag scope
- **D-02 — Local annotated `v5.0.0` tag only; do NOT push to origin.** Matches the established pattern for this repo's prior milestone tags (v4.10.1, v4.10.0 were local-only). Annotated tag with a short message.

### REL-01 — Docs + Obsidian
- **D-03 — UAT-SERIES.md + Obsidian sync** per the standing CLAUDE.md phase-completion pattern: update `docs/UAT-SERIES.md` to reflect v5.0 (version strings, the new oqs-nginx profile, the 5 phase-89 profiles), sync to vault `UAT-Series.md`, finalize the Phase-92 Obsidian note and re-sync the Roadmap note.

### Claude's Discretion
- Exact towncrier fragment count/categories per phase, the release-notes prose, whether the version bump needs a `pip install -e .` reinstall step to satisfy the `quirk --version` check, and the tag message wording.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` — REL-01.
- `.planning/ROADMAP.md` — Phase 92 goal + 4 success criteria; "Progress — v5.0 Phases" table (87–91 all complete).
- `pyproject.toml` — `[project] version` (line 7); `[tool.towncrier]` config (~line 115+, `title_format`, `directory = changelog.d`).
- `quirk/__init__.py` — `__version__` via importlib.metadata (do NOT hardcode; it derives from pyproject).
- `changelog.d/` — towncrier fragment directory (currently only README).
- `CHANGELOG.md` — towncrier build target.
- `docs/UAT-SERIES.md` — update + vault sync (CLAUDE.md mandatory step).
- The 87–91 `*-SUMMARY.md` files — source material for the changelog fragments + release notes.
- `./CLAUDE.md` — Mandatory Phase Completion Steps; PEP 8; minimal diffs.
- Prior close-out reference: `.planning/milestones/v4.10.1-ROADMAP.md` (how v4.10.1 was archived/tagged).
</canonical_refs>

<code_context>
## Existing Code Insights

- Version resolution is single-source (pyproject → importlib.metadata → `__version__`); v4.10 D-02. Bump one place.
- towncrier is configured but unused this milestone (no fragments). `towncrier build --version 5.0.0 --yes` is the documented invocation (commented in pyproject ~line 115).
- Prior milestone tags are local-only (v4.10.1, v4.10.0). The milestone *lifecycle* (audit → complete → cleanup) runs AFTER this phase via the autonomous workflow, which archives the ROADMAP/REQUIREMENTS to `.planning/milestones/`.
</code_context>

<specifics>
## Specific Ideas

- v5.0.0 release-notes headline = the OQS-nginx PQC-hybrid scoring ceiling (the one demoable capability anchor in an otherwise-internal stabilization milestone).
- After version bump, a clean `pip install -e .` may be required so `quirk --version` reports 5.0.0 via importlib.metadata.
</specifics>

<deferred>
## Deferred Ideas

- Pushing v5.0.0 to origin / PyPI publication (kept out by D-02 — local tag only).

### Reviewed Todos (not folded)
None for this phase.
</deferred>

---

*Phase: 92-v50-close-out*
*Context gathered: 2026-05-22 via autonomous smart-discuss*

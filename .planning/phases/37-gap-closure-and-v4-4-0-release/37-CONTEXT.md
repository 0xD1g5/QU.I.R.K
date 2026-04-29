# Phase 37: Gap Closure and v4.4.0 Release - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Close out the v4.4 milestone by verifying every milestone requirement is actually satisfied, backfilling Nyquist `VALIDATION.md` files to reflect ground truth, bumping the version string to `4.4.0` everywhere it appears, and producing the user-facing release docs (CHANGELOG entry + release notes).

**In scope:**
- INFRA-01: bump version `4.3.0 → 4.4.0` in `quirk/__init__.py` and `pyproject.toml`; verify `quirk --version`, CBOM metadata, report headers all return `4.4.0`.
- INFRA-02: declare `[motion]` extras with all direct dependencies (per scanner imports).
- INFRA-03: write a new `tests/test_infra03_nyquist_coverage.py` module covering 6 scanner entry points × 3 scenarios (happy, refused, plaintext-only) = 18 cases.
- VALIDATION.md backfill for phases 34, 35, 36 + creation for phase 37 (this phase).
- CHANGELOG.md entry for 4.4.0.
- `docs/release-notes/4.4.0.md` standalone narrative release notes.
- `tests/test_version.py` asserting `quirk.__version__ == "4.4.0"` and CLI string match.
- Mandatory phase close-out per CLAUDE.md: Obsidian phase note, `docs/UAT-SERIES.md` update, vault sync, commit.

**Out of scope (deferred or other phases):**
- Git tag `v4.4.0` — defer to milestone close.
- `/gsd-complete-milestone` invocation — separate user-driven step after this phase.
- Any new scanner, scoring, CBOM, or dashboard capability — closed in phases 32–36.
- Renaming or restructuring existing extras beyond INFRA-02 work.
- Any retroactive code change in phases 32–36 not driven by a discovered VALIDATION gap.

</domain>

<decisions>
## Implementation Decisions

### `[motion]` extras structure (INFRA-02)
- **D-01:** **Meta-extra topology.** `motion` is a meta-extra that pulls in flat sub-extras: `motion = ["quirk[email]", "quirk[broker]", "quirk[kafka]"]`. Sub-extras `[email]`, `[broker]`, `[kafka]` remain independently installable. `pip install quirk[motion]` is the single happy path.
- **D-02:** **Inventory by actual scanner imports.** Researcher greps `quirk/scanner/email_scanner.py` and `quirk/scanner/broker_scanner.py` for non-stdlib imports and pins those (likely: `kafka-python` already there, plus `pika` for RabbitMQ, `redis` for Redis). `sslyze` stays in core deps. Anything imported by a scanner that isn't in the right sub-extra is an INFRA-02 violation flagged in the plan.

### INFRA-03 Nyquist coverage (6 scanners × 3 scenarios)
- **D-03:** **Write all 18 cases fresh in a dedicated module.** New `tests/test_infra03_nyquist_coverage.py` contains 18 explicit test functions, one per `(entry_point, scenario)` pair. Each test imports the scanner entry point directly and exercises the scenario. Single auditable artifact for INFRA-03; existing scenario tests remain untouched.
- **D-04:** **Coverage matrix lives inline in each phase's `VALIDATION.md`.** Each v4.4 phase that owns a scanner (32 for email, 33 for broker) gets a "Nyquist scenarios" subsection in its `VALIDATION.md` listing its scanners' happy/refused/plaintext rows pointing at the test names from D-03. Phase 37 verifies the trail is complete; per-phase ownership stays intact.
- The 6 scanner entry points are: `scan_email_targets`, `scan_kafka_targets`, `scan_rabbitmq_targets`, `scan_redis_targets`, plus the Azure Service Bus and AWS SQS probe paths inside `quirk/scanner/broker_scanner.py`.

### VALIDATION.md backfill strategy
- **D-05:** **Re-run `gsd-plan-checker` per phase.** For phases 34, 35, 36, invoke the plan-checker against existing plans + current code/tests. Whatever the checker produces becomes the authoritative `VALIDATION.md`. If the checker still fails, fix the underlying gap before flipping any flag — no rubber-stamping.
- **D-06:** **Phase 36 `wave_0_complete` flip is gated on existing artifacts + clean run.** Phase 37 reads `36-VERIFICATION.md` (status: approved) and `36-UAT.md` (sign-off), runs the test suite on current `main`, then flips `wave_0_complete: true`. Do not re-run the manual UAT cases.
- Phase 35 has no `VALIDATION.md` at all — plan-checker run is mandatory; cannot be hand-edited.
- Phase 34 currently reads `nyquist_compliant: false`. Plan-checker may surface a real gap; treat as part of scope.

### Release artifacts in scope for Phase 37
- **D-07:** **CHANGELOG.md 4.4.0 entry** — append a `## 4.4.0 - 2026-04-XX` section summarizing email scanner (Phase 32), broker scanner (Phase 33), motion intelligence (Phase 34), CBOM motion integration (Phase 35), dashboard motion tab (Phase 36). Source narrative from each phase's `SUMMARY.md`.
- **D-08:** **`docs/release-notes/4.4.0.md`** — standalone narrative: what's new, what's changed, upgrade guidance (`pip install quirk[motion]`), known limitations. Linked from CHANGELOG.
- **D-09:** **`tests/test_version.py`** — asserts `quirk.__version__ == "4.4.0"` and runs the CLI subprocess to assert the same string. Locks INFRA-01 success criterion #1 against regression.

### Release artifacts deferred from Phase 37
- **D-10:** **No git tag in this phase.** `v4.4.0` tag is deferred to milestone close — phase 37 may not be the final commit on `main`.
- **D-11:** **No auto-trigger of `/gsd-complete-milestone`.** Phase 37 stops after VALIDATION sign-off + commit; milestone archival is a separate user-driven step.

### Claude's Discretion
- Plan partitioning (single plan vs. multi-wave) — planner decides, but each plan must be atomic and reversible.
- Exact wording of CHANGELOG entries and release notes — sourced from phase SUMMARY.md files; planner/executor frame for end-user audience.
- Order of operations within Wave 1 — extras structure (D-01) and version bump (INFRA-01) are independent; do whichever is cheapest first.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap and requirements
- `.planning/ROADMAP.md` §"Phase 37: Gap Closure and v4.4.0 Release" — goal, success criteria, requirements list.
- `.planning/REQUIREMENTS.md` — INFRA-01 (line 134), INFRA-02 (line 135), INFRA-03 (line 136); STRUCT-01/02/03 (per-phase structure requirements).
- `.planning/PROJECT.md` — project identity and current focus.
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note, UAT-SERIES update, vault sync, commit.

### Prior-phase artifacts that drive this phase
- `.planning/phases/32-email-scanner/32-VALIDATION.md` — already nyquist_compliant; needs Nyquist-scenarios matrix added per D-04.
- `.planning/phases/33-broker-scanner/33-VALIDATION.md` — already nyquist_compliant; needs Nyquist-scenarios matrix added per D-04.
- `.planning/phases/34-motion-intelligence/34-VALIDATION.md` — currently `nyquist_compliant: false`; re-run per D-05.
- `.planning/phases/35-cbom-integration/` — **no VALIDATION.md exists**; must be created per D-05.
- `.planning/phases/36-dashboard-motion-tab/36-VALIDATION.md` — currently `wave_0_complete: false`; flip per D-06.
- `.planning/phases/36-dashboard-motion-tab/36-VERIFICATION.md` and `36-UAT.md` — proof artifacts gating the wave_0 flip.
- `.planning/phases/22-v42-gap-closure/22-01-PLAN.md` — prior gap-closure pattern reference.

### Source files touched by this phase
- `quirk/__init__.py` — version string (currently `4.3.0`).
- `pyproject.toml` — version field + `[project.optional-dependencies]` extras (`motion`, `email`, `broker`, `kafka`).
- `quirk/scanner/email_scanner.py` — read-only; scan imports for INFRA-02 inventory.
- `quirk/scanner/broker_scanner.py` — read-only; scan imports for INFRA-02 inventory.
- `quirk/cbom/builder.py` — verify CBOM metadata version field reflects `4.4.0`.

### Output documents created/updated
- `CHANGELOG.md` (may be created if absent).
- `docs/release-notes/4.4.0.md` (created).
- `docs/UAT-SERIES.md` (updated per CLAUDE.md mandate).
- `tests/test_infra03_nyquist_coverage.py` (created — D-03).
- `tests/test_version.py` (created — D-09).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Plan-checker skill** (`gsd-plan-checker`) — existing tool that produces VALIDATION.md from a phase's plans + code state; the only honest way to backfill phases 34/35/36 (D-05).
- **Phase 22 gap-closure pattern** — single-plan, surgical-fix-only structure documented in `.planning/phases/22-v42-gap-closure/22-01-PLAN.md`. Phase 37 should mirror its tight scope discipline but is structurally larger (release artifacts + multi-phase backfill).
- **Existing test infrastructure** — `tests/test_email_scanner.py`, `tests/test_broker_scanner.py`, `tests/test_cbom_builder.py` etc. are already present; D-03's new module is additive, not a refactor.

### Established Patterns
- **CLAUDE.md mandatory close-out** — every phase ends with Obsidian phase note + UAT-SERIES update + vault sync + commit. Non-negotiable.
- **`[motion]` is currently empty** (`motion = []`) and **`[kafka]` exists separately** with `kafka-python>=2.0`. The current asymmetry is the artifact INFRA-02 is asking us to clean up.
- **VALIDATION.md frontmatter convention** — `phase`, `status`, `nyquist_compliant`, `wave_0_complete` (booleans). `wave_0_complete` is meant to flip *during execution*, not at write time.

### Integration Points
- `quirk --version` exits via `quirk/__init__.py` `__version__`. CBOM metadata version is sourced via `importlib.metadata` or direct import — researcher must confirm the exact path so `tests/test_version.py` asserts the right surface.
- `pyproject.toml` extras feed `pip install quirk[motion]`; broken extras don't fail at install but do fail at scanner import time. The new `tests/test_infra03_*` module exercises scanner entry points and will surface missing deps.

</code_context>

<specifics>
## Specific Ideas

- **Honest validation over rubber-stamping** — user explicitly chose "re-run plan-checker" over hand-edits for VALIDATION.md backfill. The audit trail matters more than the speed.
- **Per-phase VALIDATION.md ownership** — user explicitly chose inline coverage matrices over a centralized phase-37 rollup. Each phase owns its own audit story.
- **Stop short of milestone close** — phase 37 is feature-closure for v4.4, not milestone archival. `/gsd-complete-milestone` and the git tag come later, by user invocation.
- **18-test artifact for INFRA-03** — single dedicated module (`tests/test_infra03_nyquist_coverage.py`) is a deliberate audit artifact. Even if existing tests duplicate some scenarios, INFRA-03's value is the *single auditable surface*.

</specifics>

<deferred>
## Deferred Ideas

- **Git tag `v4.4.0`** — defer to milestone close (D-10).
- **`/gsd-complete-milestone` automation** — manual user step after phase 37 sign-off (D-11).
- **Documenting INFRA-03 coverage in a centralized rollup doc** — chose per-phase inline tables instead (D-04). If a future audit asks for a single-page view, the rollup can be generated mechanically from the inline tables.
- **Re-running UAT-36-01..05 manually in phase 37** — chose to trust existing `36-VERIFICATION.md` + `36-UAT.md` artifacts (D-06). If UAT environment drift becomes a concern in v4.5+, revisit.

</deferred>

---

*Phase: 37-gap-closure-and-v4-4-0-release*
*Context gathered: 2026-04-28*

# Phase 116: Windows Packaging Spike - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — grey areas proposed in batch tables, all accepted

<domain>
## Phase Boundary

A **spike** (investigation), not a build. Produce a written, evidence-backed
feasibility + sizing assessment for packaging the QUIRK **sensor** as a
PyInstaller frozen EXE hosted as a Windows Scheduled Task (or Service), validated
on the existing `windows-latest` CI runner, ending in an explicit **go/no-go**
recommendation and an effort estimate for the full v5.6 build.

**Delivers (WINPKG-01):**
- `docs/windows-packaging-spike.md` — assessment covering PyInstaller spec
  viability, hidden-import surface, Scheduled-Task-vs-Service trade-offs, CI
  validation results on `windows-latest`, and the estimated v5.6 effort.
- A `windows-latest` CI job that executes the spike validation and whose result
  (pass, or documented failure with root cause) is captured in the assessment.
- An unambiguous go / no-go / defer recommendation with rationale.

**Hard scope guard (criterion 4 — LOCKED):** NO production packaging artifact
(frozen EXE, installer, NSIS script) is committed or published. The phase
deliverable is the **assessment document + CI evidence only**.

**Locked milestone constraints:** Windows is spike-only this milestone; the full
frozen-binary build is a v5.6 fast-follow IF the spike returns "go". The spike is
sequenced after Phase 113 so it validates the per-sensor-auth wire contract
compatibility.

</domain>

<decisions>
## Implementation Decisions

### Spike CI execution (Area 1)
- **D-01:** The CI validation runs a **real `pyinstaller --onefile` build of the
  `quirk` console entrypoint** (`run_scan:_run_main_with_job_guard`, the entrypoint
  the sensor runs under) on `windows-latest`, and **captures hidden-import /
  collection failures** as evidence — richer than a `--collect-all quirk` dry-run
  alone. (Accepted Area 1 Q1.) The criterion's `--collect-all` is an acceptable
  fallback if the onefile build exceeds reasonable CI time.
- **D-02:** Add a **new dedicated, non-blocking** `windows-packaging-spike` job to
  `.github/workflows/python-ci.yml` (`continue-on-error: true`) so a spike failure
  is documented in CI + the assessment rather than gating the pipeline. (Accepted
  Area 1 Q2.) Mirror the existing `windows-sensor-smoke` job's setup (checkout,
  setup-python 3.11, `pip install -e .`).
- **D-03:** PyInstaller is installed **CI-only inline** (`pip install
  pyinstaller==<pinned>` in the spike job step) — **NOT** added to `[project]`
  dependencies or a `[packaging]` extra. (Accepted Area 1 Q3.) Zero new runtime/
  install-time deps for end users this milestone.

### Host-model recommendation (Area 2)
- **D-04:** The assessment recommends a **Windows Scheduled Task** as the primary
  v5.6 sensor host model (the sensor is a periodic scan→push, not an always-on
  daemon; avoids a pywin32 Windows Service wrapper), and **documents a Windows
  Service as the always-on alternative** with its trade-offs. (Accepted Area 2 Q1.)

### Go/no-go threshold + scope guard (Area 3)
- **D-05:** Recommend **"go"** if the spike build yields a runnable EXE (or fails
  only on documented, fixable hidden-imports) **AND** the estimated full-build
  effort fits one focused v5.6 phase; otherwise **"defer"/"no-go"** with explicit
  rationale. (Accepted Area 3 Q1.)
- **D-06:** **LOCKED scope guard:** the deliverable is the assessment doc + CI
  evidence only — no frozen EXE, installer, or NSIS script is committed or
  published (success criterion 4). (Accepted Area 3 Q2.)

### Claude's Discretion
- The exact pinned PyInstaller version and whether to add a minimal `.spec` file
  in the assessment as an appendix (illustrative only, not a shipped build script).
- The precise structure/headings of `docs/windows-packaging-spike.md` beyond the
  five required topics.
- How the CI job surfaces the build result into the doc (artifact upload, log
  excerpt, or a committed summary) — pick the lowest-friction evidence capture.
- Effort-estimate format (t-shirt size + rough day/phase breakdown).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CI + entrypoint
- `.github/workflows/python-ci.yml` — existing `windows-sensor-smoke` job
  (windows-latest, Python 3.11, `pip install -e .`) — the pattern to mirror for
  the new non-blocking `windows-packaging-spike` job.
- `pyproject.toml` `[project.scripts]` — `quirk = "run_scan:_run_main_with_job_guard"`
  is the entrypoint to freeze; `[tool.setuptools.package-data]` (cmvp_cache.json
  shipped in Phase 115 STAB-02 — relevant to PyInstaller data-file collection).
- `run_scan.py` — the entrypoint module; sensor subcommands dispatch through it.

### Sensor wire contract (spike must confirm compatibility)
- `quirk/dashboard/api/middleware/sensor_auth.py` + `quirk/cli/sensor_cmd.py` —
  Phase 113 per-sensor auth; the frozen sensor must still enroll + push under the
  per-sensor Bearer-token contract.
- `docs/architecture-distributed.md` — sensor/console split + wire contract.

### Requirements / outlook
- `.planning/REQUIREMENTS.md` §WINPKG — WINPKG-01.
- HORIZON.md / STATE.md v5.6 seeds — full build is the v5.6 fast-follow if go.

### Optional-extra / hidden-import surface
- `quirk/util/optional_extra.py` + the `[all]` extras in `pyproject.toml` — the
  optional-dependency surface PyInstaller hidden-import analysis must account for.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The `windows-sensor-smoke` CI job as a copy-from template (setup-python 3.11,
  editable install).
- The single `quirk` console entrypoint — one freeze target covers the sensor.

### Established Patterns
- Non-blocking Windows CI (`windows-sensor-smoke` stays non-blocking this
  milestone per locked decisions) — the spike job follows suit (`continue-on-error`).
- Optional-extra lazy-import pattern (`optional_extra.py`) — informs which modules
  PyInstaller will/won't need to collect.

### Integration Points
- New CI job in `.github/workflows/python-ci.yml`.
- New doc `docs/windows-packaging-spike.md`.
- (No source code changes expected — this is a spike.)

</code_context>

<specifics>
## Specific Ideas

- The assessment MUST cover all five criterion-1 topics: PyInstaller spec
  viability, hidden-import surface, Scheduled-Task-vs-Service trade-offs, CI
  validation results, and v5.6 effort estimate.
- CI evidence (build pass, or documented failure + root cause) must be reflected
  in the doc, not just left in CI logs.
- The doc ends with a single, unambiguous go / no-go / defer line + rationale.
- Per CLAUDE.md: include a docs/UAT-SERIES.md update (Series 116) + Obsidian sync.

</specifics>

<deferred>
## Deferred Ideas

- Full production PyInstaller build + Windows Scheduled Task/Service host +
  installer — v5.6 fast-follow, gated on this spike's go/no-go (D-05).
- Adding PyInstaller as a shipped `[packaging]` extra — only if v5.6 proceeds.
- Public-repo cutover + required `windows-sensor-smoke` status check — separate
  v5.6 launch decision (not this phase).

</deferred>

---

*Phase: 116-windows-packaging-spike*
*Context gathered: 2026-05-27 via smart discuss (autonomous)*

# Phase 41: CI Stability & Scanner Robustness - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Two intertwined deliverables:

1. **CI Stability (CI-01..03)** — pytest runs green, deterministically, in <60s on a developer machine. Zero `skip`/`xfail` markers for code reasons; live-infra and registered-optional-extra skips are acceptable.
2. **Scanner Robustness (ROBUST-01..04)** — every scanner degrades gracefully under (a) missing optional extras, (b) slow/partially-unreachable targets, (c) unexpected exceptions. Timeout/retry policy lives in a single canonical location.

Cross-cutting: the Phase 40 carry-over fix to `lab.sh` (`down --profile "*" --remove-orphans`) is folded into this phase — it's a robustness/cleanup fix that fits the theme.

</domain>

<decisions>
## Implementation Decisions

### Skip-Marker Triage Policy
- **D-01:** Adopt the **Pragmatic** policy. Stale skips (where the underlying module/feature now exists) are deleted; optional-extra skips are kept; live-infra skips are kept.
- **D-02:** Build a single `tests/skip_registry.py` (or equivalent in `conftest.py`) that registers every acceptable skip with `{file:line, category ∈ {optional_extra, live_infra}, reason}`.
- **D-03:** Add a CI gate (a meta-test) that fails when an unregistered `pytest.skip` / `importorskip` / `@skipif` is encountered. This is the structural mechanism that prevents skip-set drift.
- **D-04:** Initial deletion targets identified by scout (must be re-verified during planning):
  - `tests/conftest.py:111` — `quirk.dashboard not yet implemented` (dashboard exists)
  - `tests/test_cloud_connectors.py` — 6× `@skipif(not _HAS_GCP_MODULE)` (gcp_connector.py exists)
  - `tests/test_broker_db_schema.py:70` — column-already-present skip (covered by sibling test, redundant)
- **D-05:** `pytest.importorskip("quirk.scanner.broker_scanner")` patterns in the broker tests stay (broker_scanner is part of `[motion]`, intentionally optional).

### Timeout / Retry Single Source of Truth
- **D-06:** Canonical policy lives in `quirk/config.py` as a `[scan.timeouts]` TOML sub-table loaded into `ScanConfig`. Per-scanner overrides supported via `[scan.timeouts.tls]`, `[scan.timeouts.ssh]`, `[scan.timeouts.fingerprint]`, etc.
- **D-07:** The four current divergent fields (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds=5`, `ssh_timeout_seconds=5`) migrate INTO this sub-table. Existing field names get deprecation aliases (warn-on-read, removed in a future minor).
- **D-08:** **Read-only consumption** — every scanner reads its own slot (`cfg.scan.timeouts.<name>`). `run_scan.py` MUST NOT mutate `cfg.scan.*` around scanner phases. This dissolves BACK-45 (the try/finally guard becomes unnecessary because the unsafe pattern is removed).
- **D-09:** Retry/backoff defaults live in the same sub-table: `[scan.retry] retry_count`, `backoff_base_seconds`, `backoff_max_seconds`. ROBUST-04 audit doc (markdown table) lists every scanner's effective values + cites the canonical source.
- **D-10:** Documented overall scan upper-bound formula derived from the policy: `sum(per_scanner_timeout × max_targets_for_phase) + 10s safety_margin`. Documented in `docs/configuration.md`.

### Failure-Surface UX (`scan_errors[]` + missing-extras)
- **D-11:** `scan_errors[]` entries use the **minimal schema**: `{scanner, target, reason, category}` where `category ∈ {missing_extra, timeout, exception, config}`.
- **D-12:** Missing optional extras (ROBUST-01) emit BOTH a `scan_errors[]` entry with `category="missing_extra"` AND a stderr advisory (one line, `[advisory] scanner=<name> extra=<group> not installed — run \`pip install quirk[<group>]\` to enable`).
- **D-13:** CLI exit code: `0` for any combination of `missing_extra` / `timeout` / handled `exception` entries (scan completed). Non-zero ONLY for unhandled crashes that abort the scan entirely.
- **D-14:** ROBUST-03 (unexpected exception capture): every scanner entrypoint runs inside a `try/except BaseException` wrapper that produces a `scan_errors[]` entry with `category="exception"`, then re-raises only `KeyboardInterrupt` / `SystemExit`. All other exceptions captured + logged + scan continues.
- **D-15:** `scan_errors[]` is consumed by `quirk/intelligence/trends.py` (`scan_errors_new_count` / `scan_errors_resolved_count`); the new `category` field MUST be respected so delta reports don't conflate "regression crash" with "user didn't install [motion] this run."

### Slow-Test Policy & CI Scope
- **D-16:** Threshold: any individual test consistently >1s gets `@pytest.mark.slow`. Default `pytest` invocation excludes `slow` and must complete in <60s on a developer machine.
- **D-17:** Phase 41 scope is **local pytest only**. `.github/workflows/*` is NOT modified in this phase. ("CI" in the requirement text refers to the pytest invocation, which is what runs in any CI environment.) GitHub Actions tuning is a future phase if needed.
- **D-18:** Phase 40 carry-over fix is in-scope as a single small plan: `lab.sh` `down` arm changes from `compose down --remove-orphans` to `compose --profile "*" down --remove-orphans` so profile-tagged services are swept.

### Claude's Discretion
- Exact filename/location of the skip registry (`tests/skip_registry.py` vs entry in `conftest.py`) — planner picks per ergonomics.
- Exact mechanism of the unregistered-skip CI gate (pytest plugin vs collection hook vs sentinel meta-test) — planner picks the lowest-friction option.
- Per-scanner default timeout values inside the new sub-table — planner derives from current divergent values, defaulting to the more conservative number when they conflict, then documents.
- Whether the `try/except BaseException` wrapper lives in `run_scan.py` or as a decorator on each scanner — planner picks based on existing scan flow.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 41: CI Stability & Scanner Robustness" — goal, success criteria, dependencies
- `.planning/REQUIREMENTS.md` — CI-01, CI-02, CI-03, ROBUST-01, ROBUST-02, ROBUST-03, ROBUST-04
- `.planning/PROJECT.md` — Key Decisions table (BACK-45 entry on cfg.scan mutation, dissolved by D-08)

### Existing Code (Audit Targets)
- `quirk/config.py` — current `ScanConfig` dataclass and the four divergent `*_timeout_seconds` fields (D-06, D-07)
- `quirk/run_scan.py` — current cfg.scan mutation pattern around TLS/SSH phases (D-08 removes this)
- `quirk/scanner/` — 21 scanners; each must read its timeout slot read-only (D-08) and be wrapped for ROBUST-03 (D-14)
- `quirk/intelligence/trends.py:74-75, 215-216, 258-259` — existing `scan_errors_new_count` / `scan_errors_resolved_count` consumers (D-15)
- `tests/conftest.py:111`, `tests/test_cloud_connectors.py`, `tests/test_broker_db_schema.py:70` — initial deletion targets (D-04)
- `tests/test_broker_scanner_*.py` (3 files) — keep `importorskip` (D-05)

### Phase-40 Carry-over
- `quantum-chaos-enterprise-lab/lab.sh` lines 97-101 (down arm) — D-18 fix target
- Phase 40 SUMMARY references in `.planning/phases/40-chaos-lab-parity/`

### Documentation Updates
- `docs/configuration.md` — must document the new `[scan.timeouts]` and `[scan.retry]` sub-tables + overall upper-bound formula (D-10)
- `docs/UAT-SERIES.md` — phase-completion update per CLAUDE.md mandate
- `CLAUDE.md` Mandatory Phase Completion Steps — Obsidian phase note + UAT series sync

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ScanConfig` dataclass in `quirk/config.py` — already loads TOML; extending with a sub-table is structurally cheap
- `scan_errors_new_count` / `scan_errors_resolved_count` already wired in `quirk/intelligence/trends.py` — minimal-schema additions flow through automatically
- Phase 40's `_derive_all_profiles()` precedent in `lab.sh` shows the team's preference for runtime-derivation over hardcoded lists; the down-arm fix follows the same spirit
- 21 scanners share a common entrypoint shape — a single decorator or `run_scan.py` wrapper can apply ROBUST-03 protection across all of them

### Established Patterns
- TOML config drives most user-tunable behavior in QU.I.R.K. — adding a sub-table preserves discoverability for consultants
- Phase-completion structural rule: `pyproject.toml` diff + `session_start` parameter (carried forward from v4.3) — applies to any new scanner-adjacent code
- Live-infra skips are an established acceptable pattern (Phase 27, 28, 30, 31 UAT carry-overs); the skip registry formalizes this

### Integration Points
- `quirk/run_scan.py` orchestrates all scanner phases — primary integration site for D-08 (no-mutation), D-14 (exception wrapper), and `scan_errors[]` accumulation
- `quirk/intelligence/trends.py` consumes scan_errors counts — the new `category` field is the integration that prevents noisy delta reports
- Dashboard (Phase 43) will eventually surface `scan_errors[]` by category — Phase 41 produces the data shape; Phase 43 surfaces it

</code_context>

<specifics>
## Specific Ideas

- "ALLOWED_SKIPS" registry naming preference came from the option label — final filename is planner's call but the registry concept is locked.
- Documented overall-scan upper-bound formula must appear in `docs/configuration.md` so consultants can quote it to clients.
- Stderr advisory format: `[advisory] scanner=<name> extra=<group> not installed — run \`pip install quirk[<group>]\` to enable` (D-12 specifies this shape).

</specifics>

<deferred>
## Deferred Ideas

- **Dashboard "Scan Issues" widget** — group `scan_errors[]` by `category` in a dashboard panel. Belongs in Phase 43 (Dashboard Polish); the data shape (D-11) is provisioned in this phase.
- **GitHub Actions CI YAML tuning** — splitting slow tests into a separate matrix job, enforcing the <60s budget at workflow level. Out of scope for Phase 41 (D-17). Candidate for a future polish phase if/when CI runtime becomes a pain point.
- **Single-bundled wheel removing `[motion]` optionality** — would change the calculus on optional-extra skips. Not on the roadmap; flagged here in case the project ever heads that direction.
- **Deprecation removal of legacy `*_timeout_seconds` fields** — D-07 keeps deprecation aliases. Actual removal belongs in a future minor-version cleanup phase.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 41-ci-stability-scanner-robustness*
*Context gathered: 2026-04-29*

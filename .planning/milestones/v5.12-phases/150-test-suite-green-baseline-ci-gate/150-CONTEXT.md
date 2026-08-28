# Phase 150: Test Suite Green Baseline + CI Gate - Context

**Gathered:** 2026-08-12 (original) — **Updated:** 2026-08-12 (remediation addendum)
**Status:** Ready for planning (replan of Plan 150-03)

<domain>
## Phase Boundary

`pytest -q` produces a green baseline on a clean, `.[all]`-installed, `ubuntu-latest`/Python-3.11
environment, and a new CI job holds that baseline so a newly introduced failure is visible
immediately instead of joining a permanent red background. This phase does **not** re-triage or
re-disposition anything — Phase 149 already produced a mechanically-verified 116-row ledger and
confirmed a fresh `pytest -q -m ""` run is 0 failed in its own (macOS, broad-extras) sandbox. This
phase's job is to prove that same green state holds in CI's actual environment, wire the gate so
it stays held, prove the gate bites on a real new failure, document the standard, and (per D-05
below) fix one specific real bug flagged by Phase 149 as a genuine currently-shipping defect.

### Remediation addendum (2026-08-12)

Plan 150-03's live-fire push (D-07) surfaced a real gap: the local "0 failed" baseline (Phase
149's sandbox, and Plan 150-02's own local run) was validated with a broader extras surface than
CI's declared `.[all]`-only install actually provisions. The real GitHub Actions run
([31598809033](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31598809033)) came back 38 failed.
D-09 through D-16 below (captured via `/gsd-discuss-phase 150` after the blocker) close that gap.
**D-01 through D-08 above are unchanged and still govern** — this addendum clarifies HOW to make
the existing 31 extras-gated/environment-gapped tests actually honor D-01's boundary, not whether
that boundary is correct. See `150-03-SUMMARY.md` for the full 8-category failure breakdown this
addendum resolves.

</domain>

<decisions>
## Implementation Decisions

### CI environment parity

- **D-01:** The new CI job installs `.[all]` only — the documented, guard-tested production
  extras surface (`pyproject.toml` lines 117-128) — not the broader `identity`/`hw` extras
  surface Phase 149's reconciliation sandbox happened to have installed. impacket/pysnmp/
  googleapiclient-gated tests take their "optional extra not installed" skip path in this CI job;
  that is expected and still counts as green. Rationale: `.[all]` deliberately excludes
  `identity` (impacket→pyOpenSSL→cryptography downgrade chain, Phase 45/D-01) and `hw` (pysnmp,
  Phase 133/D-08, explicit operator opt-in posture) — installing them in the gate would
  reintroduce the exact dependency-chain risk those exclusions exist to prevent, and would test
  an environment no real `pip install quirk-scanner[all]` operator actually has.
  `tests/test_install_all_excludes_impacket.py` and `tests/test_install_all_excludes_pysnmp.py`
  already guard this boundary — do not add `identity`/`hw` to the CI job's install step.

### CI job design

- **D-02:** Add a new job to the existing `.github/workflows/python-ci.yml` (not a new dedicated
  workflow file). `python-ci.yml` today has only Windows jobs (sensor smoke, packaging spike,
  sensor build, sensor E2E); the new job is the first Linux/pytest job in that file. Runs on
  `ubuntu-latest`, Python 3.11 (matching the project's floor per `pyproject.toml` and
  `actions/setup-python` usage elsewhere in the repo).
- **D-03 (favorable side-effect, not a requirement):** Because the Phase 149 macOS
  fork()-under-full-suite-load SIGSEGV cluster (5 tests, `xfail(strict=False)`) is specific to
  macOS `fork()` semantics, those tests are expected to genuinely PASS on the `ubuntu-latest`
  runner rather than exercise their xfail path. This is not something to force or assert on —
  `strict=False` already tolerates either outcome — just an expected observation worth noting in
  the phase's VERIFICATION.md.
- **D-04:** The full-suite CI invocation overrides `pyproject.toml`'s default `addopts = "-m 'not
  slow'"` explicitly (e.g. `pytest -q -m ""`) so slow-marked tests are included, satisfying
  Success Criterion 2's "not a narrower `-m 'not slow'` subset." The **local default** in
  `pyproject.toml` stays `-m 'not slow'` — this phase does not change the default developer
  experience of a fast local `pytest -q`; only the CI invocation is widened to the true full
  suite.

### KDCOptions bug fix (scope pull-in)

- **D-05:** Fix the impacket `KDCOptions` class→enum incompatibility in
  `quirk/scanner/kerberos_scanner.py::_build_as_req` (impacket `>=0.13.0,<0.14`, the current pin)
  as part of this phase, not deferred to backlog. Phase 149's Plan 11 identified this as a real,
  currently-shipping Kerberos-scanner defect (not a flaky/environment test) uncovered while fixing
  the adjacent `MethodData`→`METHOD_DATA` import rename. Once fixed, remove the
  `@pytest.mark.xfail(strict=False)` markers from the 2 affected tests in
  `tests/test_identity_scanner_hardening.py` so they become real, permanently CI-enforced passes
  — leaving `xfail(strict=False)` in place after a genuine fix would let a future regression in
  this exact code path go uncaught, defeating the purpose of this phase's gate. Also remove the
  corresponding entries from `tests/skip_registry.py`'s `ALLOWED_SKIPS` and update
  `docs/test-triage-149.md`'s ledger rows to reflect the fix (do not leave the ledger claiming
  "quarantined" for tests that are no longer quarantined).
  **Note:** since D-01 excludes `identity` extras from the CI job's install, these 2 tests will
  still skip (not execute) in the new CI job specifically — the fix and marker removal matter for
  local/dev-sandbox runs with `identity` installed, and for correctness of the shipped scanner
  code itself, not for the CI gate's own pass/fail signal.

### Other Phase 149 follow-up items — explicitly deferred

- **D-06:** The remaining 4 items flagged in `149-11-SUMMARY.md`'s "Next Phase Readiness" section
  stay out of this phase's scope and go to the backlog: (1) the macOS fork()-SIGSEGV cluster
  investigation itself (root-caused already; a `multiprocessing` start-method change or
  CI-runner-level mitigation is future work, not blocking since D-03 means Linux CI sidesteps it
  entirely), (2) widening `test_safe_filter_audit.py`'s `_has_upstream_sanitize`, (3) widening
  `test_scan_error_gate.py`'s `_classify_rhs()` for `ast.IfExp`, (4) an `otics` synthesizer for
  `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` / a `googleapiclient` sandbox-parity note. None of
  these block the green baseline (all already correctly quarantined); pulling them in would widen
  Phase 150 beyond its roadmap-scoped SUITE-02/SUITE-03 boundary.

### Smoke-check mechanism (Success Criterion 3)

- **D-07:** Prove the CI gate bites via a live-fire test against the real GitHub Actions job, not
  a local-only simulation: add a deliberately failing test to a branch/PR, push it, capture
  evidence that the new CI job goes red (run URL + log excerpt), then revert the commit before
  the phase closes. This evidence (the failed-run link/log) goes into the phase's
  `VERIFICATION.md`. A local-only "add a broken test, confirm non-zero exit locally, remove it"
  would not catch a workflow-YAML wiring bug (e.g. wrong test path, wrong job trigger) — only a
  real CI run proves the gate is actually wired correctly.

### Documentation (Success Criterion 4)

- **D-08:** Create `CONTRIBUTING.md` at the repo root as the new home for the green-baseline
  standard: the exact command to run the full suite locally to match CI (`pytest -q -m ""`),
  what "green" means (0 failed; skips/xfails are expected and fine), and a pointer to
  `docs/test-triage-149.md` for why specific tests are quarantined. No `CONTRIBUTING.md` exists
  today. This also means `CLAUDE.md`'s per-phase documentation checklist table gains no new row
  for this — `CONTRIBUTING.md` is a new, standalone file, not one of the existing `docs/*.md` →
  `20_Dev-Work/QUIRK/Guides/*.md` Obsidian-synced pairs. Do not create an Obsidian vault sync
  for it unless the user asks; it is not one of the mapped `docs/` sources in CLAUDE.md's sync
  table.

### Claude's Discretion

- Exact CI job name/step structure within `python-ci.yml` (e.g. job key naming, whether pip
  caching is added) — executor judgment, follow the existing Windows jobs' style for consistency.
- Whether `CONTRIBUTING.md` also covers non-testing contribution basics (PR process, code style)
  beyond the testing standard — Success Criterion 4 only requires the testing/green-baseline
  content; anything broader is executor's call on how much value to add without scope-creeping.
- Exact wording/placement of the live-fire smoke-check test (D-07) and its revert commit message.

### Remediation: extras-gated skip guards (Categories B/C/D/F, 31 failures)

- **D-09:** Guard each of the 31 failing tests individually with a per-test `try: import X /
  except ImportError: pytest.skip("X not installed")` block at the top of the test function (or
  `setUp`, for class-based tests) — matching the existing idiom in `test_aws_connector.py:172`
  exactly. **Do not use module-level `pytest.importorskip()`** for any of the 6 affected files:
  verified `test_snmp_scanner_contract.py` has 22 tests total (only 1 fails) and
  `test_rest_fuzzer_probes.py` has 21 tests total (only 9 fail) — both files are dominated by
  tests that specifically exercise the "extra absent, graceful fallback" guard path and must keep
  running without the extra. A module-level skip would silently stop testing that fallback
  behavior. Apply the same per-test pattern uniformly even to the files where every test happens
  to fail (`test_bacnet_scanner.py`, `test_modbus_scanner.py`) — one consistent mechanism, no
  per-file judgment calls for the executor to make.
- **D-10:** Register all 31 new skips under a new `tests/skip_registry.py` category,
  `"ci_extras_gap"` — distinct from the existing `"optional_extra"` category (which covers
  pre-existing local-dev-sandbox skips like boto3/bs4/httpx). The new category name should make
  it possible to later grep/report specifically "tests touched to close the Phase 150 CI-parity
  gap" separately from unrelated pre-existing skips.
- **D-11:** Category F (`test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols`)
  gets the same D-09 treatment despite having a different shape from the other 30 — it's a
  positive assertion expecting a real `KERBEROS` finding, not a guard-path test — for consistency
  with D-05's existing `identity`-extras skip precedent in
  `test_identity_scanner_hardening.py`. Do not special-case it.

### Remediation: chaos-lab Docker tests in the gating job (Category E, 1 failure + proactive extension)

- **D-12:** `ubuntu-latest` runners have Docker preinstalled, so D-04's `-m ""` override
  genuinely spins up the `email` chaos-lab profile for
  `test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[email]` — and it fails because
  `labs/email/certs/dovecot.{key,crt}` are gitignored with **no generator anywhere in the repo**.
  Verified: `quantum-chaos-enterprise-lab/lab.sh`'s existing `ensure_lab_certs()` (line 76) only
  covers the top-level `quantum-chaos-enterprise-lab/certs/` mTLS pair (ca.key/client.key,
  Phase 120), not any `labs/*/certs/` profile-specific certs. This requires genuinely new
  cert-generation logic, not a call to something existing. Extend `ensure_lab_certs()` (or add a
  sibling function called from the same `up`/`reset` entry points) to also generate
  `labs/email/certs/dovecot.{key,crt}` via `openssl` if absent, per CLAUDE.md's Chaos Lab
  Maintenance rule that `lab.sh` must stay a faithful reflection of the lab's current state —
  this fixes both the CI gap and local `./lab.sh up --profile email` on a fresh clone.
- **D-13:** `labs/grpc-tls/` has the identical gap (`.gitignore` excludes `certs/*.key`, no
  generator anywhere) — it simply hasn't tripped a CI failure yet. Fix it in the same pass as
  D-12, using the same generation mechanism, since CLAUDE.md's Chaos Lab Maintenance rule applies
  lab-wide and the mechanism is already being built for `email`.
- **D-14:** Add a short note to `CONTRIBUTING.md` (alongside D-08's green-baseline standard)
  stating that `pytest -q -m ""` (the CI-equivalent full-suite command) will spin up Docker
  chaos-lab containers for slow-marked profile tests when Docker is available — so a contributor
  reproducing CI locally isn't surprised by containers starting.

### Remediation: public-repo gitignored fixture reads (Category A, 4 failures)

- **D-15:** All 4 failures (`test_phase57_invariants.py::test_audit_tasks_six_blockers_closed`,
  `test_audit_ledger_zero_open.py::test_audit_ledger_has_zero_bare_open_rows`,
  `test_audit_ledger_zero_open.py::test_deferred_and_wontfix_rows_have_rationale`,
  `test_extras_concurrency_expander.py::test_audit_rows_flipped_to_phase_71`) do a direct
  `.read_text()` on `.planning/audit-2026-05-08/AUDIT-TASKS.md` with no existence check — this
  path is gitignored on the public repo (Phase 120 PUBREPO-01) and will never exist in a public
  clone or CI checkout. Add an existence-check skip guard (`if not path.exists(): pytest.skip(...)`)
  to each, registered under a new `tests/skip_registry.py` category,
  `"gitignored_planning_dir"`. Verified this is the complete set — grepped all 8 files in `tests/`
  that reference `.planning/` and confirmed the other 3 (`test_coverage_bounds.py`,
  `test_dashboard_api.py`, `test_dashboard_trends.py`) only reference `.planning/` paths in doc
  comments, never at runtime, so no wider scope applies here.

### Remediation: unexplained failures (Categories G + H, 2 failures)

- **D-16:** `test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0`
  (Category H) is a **dead Phase-16-era RED scaffold** — it hardcodes
  `importlib.metadata.version("quirk") == "4.4.0"`, but the package was renamed to
  `quirk-scanner` at the v4.10 PyPI rename (current `pyproject.toml`:
  `name = "quirk-scanner"`, `version = "5.11.0"`) — the queried package name hasn't existed for
  15+ releases. It only ever passed locally because dev sandboxes carry editable-install metadata
  predating the rename; CI's fresh install exposes the true `PackageNotFoundError`. **Delete this
  test** — there is no live requirement pinning a hardcoded version string via
  `importlib.metadata`; do not attempt to fix-in-place (would immediately go stale again).
- **D-17:** `test_sensor_ingest.py::test_push_endpoint_exists` (Category G, `/api/sensor/push`
  404 on a genuine `.[all]`-only install) is **not root-caused and not to be guessed at** —
  verified during discussion that `create_app()` in `quirk/dashboard/api/app.py` registers
  `sensor.sensor_push_router` unconditionally (no try/except, no extras-gating anywhere in that
  path) and `zstandard` (imported by `sensor.py`) is a base dependency, not an extra — so this is
  **not** an obvious extras-exclusion artifact like the other categories. Hand this to the
  executor as a scoped investigation task: reproduce in a clean `.[all]`-only venv matching CI's
  exact install, and root-cause before deciding fix vs. quarantine. Do not register a
  speculative skip for this one — an unexplained 404 could be a real regression, and D-07/D-09's
  "don't paper over failures" precedent applies here too.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` §"Test Signal Integrity" — SUITE-02, SUITE-03 (this phase),
  SUITE-01 (Phase 149, already complete).
- `.planning/ROADMAP.md` lines 175-194 §"Phase 150: Test Suite Green Baseline + CI Gate" — goal,
  success criteria, depends-on Phase 149.

### Phase 149 outputs (this phase builds directly on these — do not re-derive)
- `.planning/milestones/v5.12-phases/149-test-suite-triage/149-CONTEXT.md` — Phase 149's own decisions (D-01
  through D-05), establishes the quarantine mechanism this phase must respect (D-05 above touches
  it for the KDCOptions fix only).
- `.planning/milestones/v5.12-phases/149-test-suite-triage/149-11-SUMMARY.md` — the final reconciliation: fresh
  `pytest -q -m ""` is 0 failed (3088 passed, 42 skipped, 81 xfailed) in Phase 149's sandbox; the
  5 flagged follow-up items (see D-05/D-06 above) and their disposition in this phase.
  `key-decisions` frontmatter documents the SIGSEGV-cluster consolidation and the two production
  bug fixes already applied (sslyze `__version__`, impacket `MethodData`).
- `docs/test-triage-149.md` — the 116-row (now effectively adjusting to reflect D-05's 2-row
  un-quarantine) disposition ledger. Read the `## Reconciliation` section (near the end) for the
  authoritative fresh-run numbers and the KDCOptions root-cause description this phase's D-05
  fix must resolve.

### Existing quarantine/skip machinery (Phase 41, extended Phase 149) — must stay working
- `tests/skip_registry.py` — `ALLOWED_SKIPS` list, `pre_existing_triage_149` category holds the
  Phase 149 entries. D-05 removes 2 of these entries when the KDCOptions fix lands.
- `tests/test_skip_registry.py::test_no_unregistered_skips` — the AST-walking meta-gate. Must
  stay green after any marker changes in this phase.

### Pytest / CI configuration this phase modifies
- `pyproject.toml` lines 151-159 — `[tool.pytest.ini_options]`, `addopts = "-m 'not slow'"` (D-04:
  stays as-is for local default; CI invocation overrides it explicitly).
- `pyproject.toml` lines 38-132 — `[project.optional-dependencies]`, especially the `all` group
  (117-128) and its documented exclusions (`identity` at 129-131 for impacket, `hw` at 60-66 for
  pysnmp, `api` at 75-78 for schemathesis). D-01's install step must match this exactly.
- `.github/workflows/python-ci.yml` — the file gaining the new full-suite job (D-02). Existing
  Windows jobs (`windows-sensor-smoke`, `windows-packaging-spike`, `windows-sensor-build`,
  `windows-sensor-e2e`) are the style/pattern reference for pinned-SHA action versions and
  `permissions: contents: read`.
- `.github/workflows/python-staleness.yml` — the only other existing CI pytest invocation
  (narrow, staleness-gate-only); not touched by this phase, but shows the existing pinned-action
  conventions to follow.

### Bug fix target (D-05)
- `quirk/scanner/kerberos_scanner.py::_build_as_req` — impacket `KDCOptions` class→enum
  incompatibility on the pinned `impacket>=0.13.0,<0.14`. See `docs/test-triage-149.md`'s ledger
  entries for the 2 affected `tests/test_identity_scanner_hardening.py` tests for the exact
  symptom/root-cause description already captured by Phase 149.

### Remediation addendum refs (D-09 through D-17)
- `.planning/phases/150-test-suite-green-baseline-ci-gate/150-03-SUMMARY.md` — the authoritative
  38-failure, 8-category breakdown with exact test names; this addendum's decisions map 1:1 onto
  its categories.
- `.planning/phases/150-test-suite-green-baseline-ci-gate/.continue-here.md` — blocking
  anti-pattern (local-baseline-as-CI-proxy) acknowledged at the start of this discussion; contains
  the same failure breakdown plus infrastructure-state notes (origin/main sync status, no
  smoke-test branch/PR exists).
- `tests/test_aws_connector.py:172` — the existing per-test `pytest.skip(...)` idiom D-09 must
  match exactly.
- `tests/test_cmvp_refresh.py:22-23` — the existing module-level `pytest.importorskip()` idiom
  D-09 explicitly rejects for the 6 affected files (verified those files are NOT homogeneous).
- `quantum-chaos-enterprise-lab/lab.sh` lines 76-101 (`ensure_lab_certs()`) — the function D-12
  extends; currently only covers the top-level mTLS cert pair, not per-profile certs.
- `labs/email/.gitignore`, `labs/grpc-tls/.gitignore` — confirm both profiles exclude
  `certs/*.key` with no generator; D-12/D-13's targets.
- `quantum-chaos-enterprise-lab/docker-compose.yml` lines 1041-1064 (`dovecot-email` service) —
  the bind-mount definition whose missing source files caused Category E's failure.
- `quirk/dashboard/api/app.py::create_app` — verified unconditional route registration (D-17);
  the investigation should start here to confirm the executor doesn't re-derive this.
- `tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` —
  the dead test D-16 deletes.
- `.planning/REQUIREMENTS.md` lines 45-49, 116-117 — SUITE-02/SUITE-03 rows are currently marked
  `[x]`/"Complete" despite the real CI baseline being red; this addendum's remediation plans
  should result in REQUIREMENTS.md being corrected to reflect actual status once genuinely green
  (not this discussion's job to fix directly, but the executor/planner should be aware the
  requirements table is currently stale relative to ground truth).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/python-ci.yml`'s existing Windows jobs establish the house style: pinned
  action SHAs with version comments (e.g. `actions/checkout@34e11487...  # v4.3.1`), a
  `permissions: contents: read` top-level block, `workflow_dispatch` alongside `pull_request`/
  `push: branches: [main]` triggers. The new Linux job should match this style.
- `tests/skip_registry.py` + `tests/test_skip_registry.py` — direct mechanism already proven in
  Phase 149; D-05's un-quarantine is a subtraction from this same registry, not new machinery.

### Established Patterns
- `pyproject.toml`'s per-extras-group exclusion comments (impacket at 129-131, pysnmp at 60-66,
  schemathesis/api at 75-78) each cite a specific phase/decision and a guard test
  (`test_install_all_excludes_*.py`). D-01 follows this same "documented exclusion + guard test"
  posture rather than reopening it.

### Integration Points
- The new CI job is additive to `python-ci.yml` — it must not change the existing Windows jobs'
  triggers, permissions, or behavior. `python-staleness.yml`'s narrow pytest invocation is a
  separate, pre-existing gate and stays untouched.

### Remediation addendum findings
- `test_snmp_scanner_contract.py` (22 tests, 1 fails) and `test_rest_fuzzer_probes.py` (21 tests,
  9 fail) are NOT homogeneous extras-only files — most of their tests specifically validate the
  "extra absent" fallback path itself and must keep running. This ruled out module-level
  `importorskip` as a uniform solution (D-09).
- `test_v41_gap_closure.py`'s stale package-name/version assertion (D-16) is an isolated
  occurrence — no other test in `tests/` shares the pattern (grepped for
  `importlib.metadata.version("quirk")`/`'quirk'` — single hit).
- `labs/*/` gitignore audit: only `email` and `grpc-tls` profiles have gitignored certs with no
  generator; all other profiles either don't require self-signed certs or already generate them
  (D-12/D-13 scope is complete at 2 profiles).

</code_context>

<specifics>
## Specific Ideas

No further specific implementation examples beyond the decisions above — this discussion covered
the full set of gray areas for this phase (CI environment, job design, smoke-check proof method,
follow-up-item scope, and docs location).

**Remediation addendum:** no further specifics beyond D-09 through D-17 — the 4 discussed areas
(skip-guard mechanism, chaos-lab certs, gitignored-fixture handling, unexplained failures) covered
all 8 failure categories from `150-03-SUMMARY.md`.

</specifics>

<deferred>
## Deferred Ideas

- macOS fork()-under-full-suite-load SIGSEGV cluster investigation (root cause already identified
  by Phase 149; a `multiprocessing` start-method change or CI-runner mitigation is future work) —
  backlog (D-06).
- Widening `test_safe_filter_audit.py`'s `_has_upstream_sanitize` — backlog (D-06).
- Widening `test_scan_error_gate.py`'s `_classify_rhs()` for `ast.IfExp` support — backlog (D-06).
- Adding an `otics` synthesizer to `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` and a
  `googleapiclient` sandbox-parity note — backlog (D-06).

### Reviewed Todos (not folded)
None — `todo.match-phase` was not run for this discussion; no todos surfaced organically.

</deferred>

---

*Phase: 150-Test Suite Green Baseline + CI Gate*
*Context gathered: 2026-08-12 (original); updated 2026-08-12 (remediation addendum, D-09..D-17)*

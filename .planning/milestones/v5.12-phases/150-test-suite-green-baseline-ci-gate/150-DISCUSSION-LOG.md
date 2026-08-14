# Phase 150: Test Suite Green Baseline + CI Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-12
**Phase:** 150-Test Suite Green Baseline + CI Gate
**Areas discussed:** CI environment parity, CI job design, Smoke-check method, Follow-up item scope, Docs location, KDCOptions scope

---

## CI environment parity — what does the CI job install?

| Option | Description | Selected |
|--------|-------------|----------|
| Install `.[all]` only | Matches the documented, guarded production install surface; impacket/pysnmp-gated tests skip cleanly, matching a real operator install | ✓ |
| Install `.[all]` plus identity+hw extras | Mirrors Phase 149's reconciliation sandbox exactly, exercising sslyze/impacket/KDCOptions code paths for real, but reintroduces the pyOpenSSL/cryptography downgrade chain `[all]` was built to avoid | |
| Matrix: both, as separate jobs | Production parity + dev/triage parity, at the cost of doubled CI runtime/complexity | |

**User's choice:** Install `.[all]` only (recommended option).
**Notes:** None of the excluded extras block the 0-failed baseline — they just change which
tests execute vs. skip. `.[all]`'s exclusions are already guard-tested
(`test_install_all_excludes_impacket.py`, `test_install_all_excludes_pysnmp.py`).

---

## CI job design — where does the new job live, and on what OS?

| Option | Description | Selected |
|--------|-------------|----------|
| New job in python-ci.yml, ubuntu-latest | Keeps one workflow file as the PR-breakage source of truth; ubuntu-latest is cheaper and sidesteps the macOS-only SIGSEGV cluster | ✓ |
| New dedicated workflow file | Isolates the full-suite gate from Windows packaging/E2E concerns, at the cost of a second workflow file to reason about | |

**User's choice:** New job in `python-ci.yml`, `ubuntu-latest` (recommended option).
**Notes:** Phase 149's 5-test macOS fork()-SIGSEGV cluster (`xfail(strict=False)`) is expected to
just pass on Linux CI — noted as a favorable side-effect (D-03), not a hard requirement to verify.

---

## Smoke-check method — how to prove Success Criterion 3 (a new failing test fails CI)?

| Option | Description | Selected |
|--------|-------------|----------|
| Live-fire: add, push, confirm red, then revert | Proves the actual GitHub Actions job is wired correctly, not just local pytest exit codes; evidence goes in VERIFICATION.md | ✓ |
| Local-only simulation | Faster, avoids a throwaway red commit, but wouldn't catch a workflow-YAML wiring bug | |

**User's choice:** Live-fire against real CI (recommended option).
**Notes:** A local-only exit-code check can't rule out an incorrectly wired job trigger, path, or
step ordering in the new YAML — only a real push proves the gate bites.

---

## Follow-up item scope — do any of Phase 149's 5 flagged follow-ups land in Phase 150?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay strictly in scope — defer all 5 | Phase 150 does only green-baseline + CI-gate + docs; all 5 items go to backlog | |
| Pull in the real bug fix (impacket KDCOptions) | Fix the genuine, currently-shipping Kerberos-scanner defect now while context is fresh; the other 4 items still go to backlog | ✓ |

**User's choice:** Pull in the KDCOptions fix only; the other 4 items (SIGSEGV-cluster
investigation, 2 test-helper widenings, otics/googleapiclient fixture gap) are deferred to backlog.
**Notes:** Follow-up question then clarified that once fixed, the 2 affected tests' `xfail`
markers should be removed (not left in place) so the fix becomes a real, permanently-enforced
CI pass — see the "KDCOptions scope" area below.

---

## Docs location — where does the green-baseline standard get documented?

| Option | Description | Selected |
|--------|-------------|----------|
| New CONTRIBUTING.md at repo root | Standard OSS convention, discoverable via GitHub's UI, natural home for the test-run command | ✓ |
| New section in docs/operators-guide.md | Keeps it under the existing Obsidian-synced docs/ tree, but mixes contributor/operator audiences | |

**User's choice:** New `CONTRIBUTING.md` at repo root (recommended option).
**Notes:** No `CONTRIBUTING.md` exists today. This file is NOT one of CLAUDE.md's mapped
`docs/*.md` → Obsidian-sync pairs — no vault sync required for it.

---

## KDCOptions scope — once the bug is fixed, do the xfail markers come off?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — fix the bug AND remove the xfail markers | Turns the fix into a real, permanently CI-enforced assertion; leaving xfail(strict=False) in place would let a future regression go uncaught | ✓ |
| Fix the bug, leave xfail markers in place | Smaller diff, matches Phase 149's minimal-footprint discipline, keeps a safety margin | |

**User's choice:** Fix the bug and remove the xfail markers (recommended option).
**Notes:** Also requires removing the 2 corresponding `ALLOWED_SKIPS` entries in
`tests/skip_registry.py` and updating `docs/test-triage-149.md`'s ledger rows so the ledger
doesn't claim "quarantined" for tests that are no longer quarantined.

---

## Claude's Discretion

- Exact CI job name/step structure within `python-ci.yml` (job key naming, whether pip caching is
  added) — follow the existing Windows jobs' style for consistency.
- Whether `CONTRIBUTING.md` covers non-testing contribution basics beyond the testing standard —
  Success Criterion 4 only requires the testing/green-baseline content.
- Exact wording/placement of the live-fire smoke-check test and its revert commit message.

## Deferred Ideas

- macOS fork()-under-full-suite-load SIGSEGV cluster investigation — backlog.
- Widening `test_safe_filter_audit.py`'s `_has_upstream_sanitize` — backlog.
- Widening `test_scan_error_gate.py`'s `_classify_rhs()` for `ast.IfExp` support — backlog.
- Adding an `otics` synthesizer to `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` and a
  `googleapiclient` sandbox-parity note — backlog.

---

# Remediation Addendum — 2026-08-12

> Triggered by Plan 150-03's live-fire push surfacing 38 real CI-only failures
> (run [31598809033](https://github.com/0xD1g5/QU.I.R.K/actions/runs/31598809033)).
> Decisions captured as D-09 through D-17 in `150-CONTEXT.md`.

**Date:** 2026-08-12
**Phase:** 150-Test Suite Green Baseline + CI Gate (remediation)
**Areas discussed:** Extras-gated skip-guard mechanism, Chaos-lab Docker tests in the gating job, Public-repo gitignored fixtures, Unexplained failures

---

## Extras-gated skip-guard mechanism (Categories B/C/D/F, 31 failures)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-test skip, uniform pattern | `pytest.skip(...)` per failing test, matching `test_aws_connector.py`'s existing idiom | ✓ |
| Module-level where homogeneous, per-test elsewhere | `pytest.importorskip()` for uniform files, per-test for mixed files | |
| Shared conftest fixture/marker | New `@pytest.mark.requires_extra(...)` resolved by a conftest hook | |

**User's choice:** Per-test skip, uniform pattern.
**Notes:** Verified `test_snmp_scanner_contract.py` (22 tests, 1 fails) and `test_rest_fuzzer_probes.py` (21 tests, 9 fail) are not homogeneous — module-level skip would wrongly disable currently-passing guard-path tests.

| Option | Description | Selected |
|--------|-------------|----------|
| try/import at top of test, skip on ImportError | Matches `test_aws_connector.py` exactly | ✓ |
| Shared `importlib.util.find_spec()` helper | New `tests/_extras.py` helper, avoids repeated boilerplate | |

**User's choice:** try/import per test.

| Option | Description | Selected |
|--------|-------------|----------|
| New category: `ci_extras_gap` | Distinct from pre-existing `optional_extra` registry entries | ✓ |
| Reuse existing `optional_extra` category | Same shape as pre-existing local-dev skips | |

**User's choice:** New category `ci_extras_gap`.

| Option | Description | Selected |
|--------|-------------|----------|
| Same per-test skip as the other 30 | Uniform handling for Category F despite different test shape | ✓ |
| Investigate separately | Flag Category F as its own item | |

**User's choice:** Same per-test skip (uniform handling), despite Category F being a positive-assertion test rather than a guard-path test.

---

## Chaos-lab Docker tests in the gating job (Category E, 1 failure + proactive extension)

| Option | Description | Selected |
|--------|-------------|----------|
| Regenerate certs in CI (lab.sh pre-step) | New cert-gen logic in `ensure_lab_certs()`, matches CLAUDE.md's Chaos Lab Maintenance rule | ✓ |
| Exclude Docker-backed chaos-lab tests from this gating job | Narrow the CI invocation, weakens D-04's "true full suite" goal | |
| Skip just the email profile specifically | Narrowest fix, patches only the known gap | |

**User's choice:** Regenerate certs in CI.
**Notes:** Verified no existing generator covers `labs/*/certs/` — only the top-level mTLS pair is handled today.

| Option | Description | Selected |
|--------|-------------|----------|
| Extend lab.sh's `ensure_lab_certs()` | Works for both CI and local `./lab.sh up --profile email` | ✓ |
| New pytest fixture/conftest step | Test-local only, doesn't help local lab usage | |
| GitHub Actions workflow step | CI-only, simplest but doesn't help local usage | |

**User's choice:** Extend `ensure_lab_certs()`.

| Option | Description | Selected |
|--------|-------------|----------|
| Fix `grpc-tls` too, same pass | Same root cause, same fix shape, found during discussion | ✓ |
| Email only — grpc-tls stays deferred | Keep strictly scoped to what CI proved broken | |

**User's choice:** Fix `grpc-tls` too, same pass.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add a note to CONTRIBUTING.md | Contributors reproducing CI locally should know Docker containers may start | ✓ |
| No, out of scope | Leave CONTRIBUTING.md as-is | |

**User's choice:** Add the note.

---

## Public-repo gitignored fixtures (Category A, 4 failures)

| Option | Description | Selected |
|--------|-------------|----------|
| Skip when file absent (existence guard) | Keeps the invariant check alive for environments where `.planning/` exists | ✓ |
| Delete the tests | Argue the one-time audit-closure checks have served their purpose | |
| Public-safe stand-in fixture | Commit a sanitized non-gitignored excerpt | |

**User's choice:** Skip when file absent.
**Notes:** Confirmed these are the only 4 tests that read `.planning/` at runtime; 3 other files reference `.planning/` paths only in doc comments.

| Option | Description | Selected |
|--------|-------------|----------|
| `gitignored_planning_dir` | New, self-explanatory registry category | ✓ |
| Reuse `optional_extra` | Treat as a variant of the same underlying condition | |

**User's choice:** New category `gitignored_planning_dir`.

---

## Unexplained failures (Categories G + H, 2 failures)

| Option | Description | Selected |
|--------|-------------|----------|
| Delete the test | `test_v41_gap_closure.py`'s hardcoded `importlib.metadata.version("quirk") == "4.4.0"` is a dead Phase-16 scaffold; package renamed to `quirk-scanner` at v4.10 | ✓ |
| Fix in place — update name + version | Keep the hardcoded-check pattern, just make it current | |
| Rewrite to check dynamically | Compare against `pyproject.toml`'s own version field | |

**User's choice:** Delete the test.
**Notes:** Only occurrence of this pattern in the whole suite (grepped for `importlib.metadata.version("quirk")`).

| Option | Description | Selected |
|--------|-------------|----------|
| Hand off as a scoped investigation task | `test_sensor_ingest.py::test_push_endpoint_exists` 404 not explained by extras-gating; needs a real clean-venv repro | ✓ |
| Keep investigating in this session | Continue static analysis before locking a plan | |

**User's choice:** Hand off as investigation task.
**Notes:** Ruled out during discussion: `create_app()` registers the route unconditionally; `zstandard` is a base dependency, not an extra. Not to be guessed at or given a speculative skip.

---

## Claude's Discretion (remediation addendum)

- Exact wording of the new `ci_extras_gap` / `gitignored_planning_dir` skip messages.
- Whether the `ensure_lab_certs()` extension for `email`/`grpc-tls` is a new function or inline branches within the existing one.

## Deferred Ideas (remediation addendum)

None — all 4 discussed areas map directly onto the 8 failure categories from `150-03-SUMMARY.md`; no scope creep surfaced during this round.

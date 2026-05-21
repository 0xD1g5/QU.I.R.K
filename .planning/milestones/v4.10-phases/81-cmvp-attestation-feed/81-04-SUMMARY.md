---
phase: 81-cmvp-attestation-feed
plan: 04
type: execute-summary
subsystem: ci/cmvp
tags: [cmvp, ci-gates, ast-invariant, staleness, uat, obsidian, phase-closure]
requires:
  - 81-01 (cmvp_cache.json + error codes)
  - 81-02 (quirk/compliance/cmvp.py + CLI)
  - 81-03 (Algorithm Inventory section + CMVP Coverage column)
provides:
  - tests/test_cmvp_freshness.py (90-day staleness CI gate)
  - tests/test_cmvp_no_certified_true.py (PERMANENT v4.10-D-01 / CMVP-07 AST gate)
  - tests/test_cmvp_refresh.py (refresh CLI mock-httpx tests)
  - tests/test_cmvp_coverage_query.py (coverage lookup + normalization tests)
  - tests/test_cmvp_report_column.py (HTML report column rendering tests)
  - python-staleness.yml extension running tests/test_cmvp_freshness.py
  - UAT-81-01..05 in docs/UAT-SERIES.md + vault sync
  - Phase-81-CMVP-Attestation-Feed.md vault note
affects:
  - .github/workflows/python-staleness.yml
  - docs/UAT-SERIES.md
tech_stack_added: []
patterns_followed:
  - tests/test_qramm_staleness.py:41-81 staleness gate clone
  - tests/test_smime_ast_gate.py:28-46 AST walker + self-test pattern
  - tests/test_jwt_scanner.py:50-67 httpx-mock pattern (patch quirk.compliance.cmvp.httpx)
  - tests/test_report_injection_hardening.py:30-153 write_reports harness clone
  - CLAUDE.md mandatory phase completion steps (Obsidian note + UAT sync)
key_files_created:
  - tests/test_cmvp_freshness.py
  - tests/test_cmvp_no_certified_true.py
  - tests/test_cmvp_refresh.py
  - tests/test_cmvp_coverage_query.py
  - tests/test_cmvp_report_column.py
  - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-81-CMVP-Attestation-Feed.md
key_files_modified:
  - .github/workflows/python-staleness.yml
  - docs/UAT-SERIES.md
  - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md
key_decisions:
  - PERMANENT INVARIANT marker enforced via meta-test (`test_invariant_test_self_protection`) — the AST gate file itself asserts its header contains `v4.10-D-01`, `CMVP-07`, and `PERMANENT INVARIANT` strings, so a future PR that strips the rationale is caught by the gate's own self-test.
  - EdDSA case-insensitivity test (`test_normalize_eddsa_case_insensitive`) asserts only that EdDSA and EDDSA agree (both map to the same family OR both to None) — preserves the RESEARCH MEDIUM-confidence latitude in `_FAMILY_MAP` without locking the production module into a specific resolution.
  - bs4 dep gated via `pytest.importorskip("bs4")` at module scope in test_cmvp_refresh.py — refresh CLI tests skip gracefully in minimal CI environments while the dep is declared in pyproject.toml (Plan 81-01).
metrics:
  duration_minutes: 22
  completed: 2026-05-16
  tests_added: 38
  commits: 2
---

# Phase 81 Plan 04: CMVP CI Gates + Tests + UAT-SERIES.md + Phase Closure

**One-liner:** Locked in Phase 81's permanent invariants (v4.10-D-01 / CMVP-07 AST gate, 90-day staleness CI gate, refresh CLI + coverage + report-column unit tests) across 5 test files (38 tests), extended `.github/workflows/python-staleness.yml`, appended UAT-81-01..05, and finalized the Obsidian phase note — closing Phase 81 with all 7 CMVP-* requirements met.

## Files Added

| Path | Tests | Purpose |
|------|------:|---------|
| `tests/test_cmvp_freshness.py` | 5 | 90-day staleness CI gate (CMVP-02). Clones `test_qramm_staleness.py:41-81`; honors `QUIRK_CI_STALENESS_OVERRIDE_DATE`; fail message cites `source_url` per CONTEXT Area 4. Boundary: strict greater-than 90 days = STALE. |
| `tests/test_cmvp_no_certified_true.py` | 9 | PERMANENT INVARIANT (v4.10-D-01 / CMVP-07). AST walker over `quirk/compliance/` + `quirk/cbom/` with three forbidden patterns (dict literal / kwarg call / subscript-or-attribute assignment). Positive + negative + combined + meta self-tests. Header marker: `PERMANENT INVARIANT — DO NOT REMOVE (v4.10-D-01 / CMVP-07)`. |
| `tests/test_cmvp_refresh.py` | 6 | Refresh CLI tests (CMVP-03). Mocks `quirk.compliance.cmvp.httpx` with frozen NIST CSRC HTML fixtures anchored on `table#searchResultsTable`, `#cert-number-link-N`, `table#fips-algo-table`. Happy path + network/parse exceptions + CLI error-code stderr + `--dry-run` no-write diff dict. Gated by `pytest.importorskip("bs4")`. |
| `tests/test_cmvp_coverage_query.py` | 12 | Coverage lookup tests (CMVP-05). AES-256-GCM hits cache; AES family alias idempotent; ChaCha20-Poly1305 / unknown / empty → `[]`; 140-3 ordering; recent `module_version` first; EdDSA/EDDSA case-insensitive normalization; sntrup761 hybrid KEM → None per RESEARCH MEDIUM-confidence; garbage-input never raises. |
| `tests/test_cmvp_report_column.py` | 6 | HTML report rendering smoke (CMVP-06). Synthetic AES + ChaCha20 + XSS endpoints through stubbed `write_reports`; asserts `<h2>Algorithm Inventory` + `CMVP Coverage` header + `OpenSSL FIPS Provider` in AES row + `Not in CMVP catalog` literal for ChaCha20 + XSS payload sanitized + zero `certified: true` in rendered HTML. |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-81-CMVP-Attestation-Feed.md` | — | Obsidian phase note with frontmatter (status: complete, type: phase), Goal, Requirements Covered, Success Criteria, What Was Built (4 plan subsections), Permanent Invariants, `[[Roadmap]]` link. |

## Files Modified

| Path | Change |
|------|--------|
| `.github/workflows/python-staleness.yml` | Added `tests/test_cmvp_freshness.py` to the staleness pytest invocation (line 33) alongside QRAMM, compliance, and error-code freshness gates. No schedule change — same Monday 09:00 UTC cron + PR + push triggers. YAML parses clean. |
| `docs/UAT-SERIES.md` | Prepended Phase 81 wrap clause to `**Last Updated:** 2026-05-16` line (replacing the Phase 80 wrap clause). Appended UAT-81-01..05 cases at the document tail (CMVP status FRESH verdict, refresh `--dry-run` no-write, AES report column, offline CBOM coverage, permanent AST invariant gate). |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | Synced from `docs/UAT-SERIES.md` via printf+cat+cp; fresh frontmatter (`updated: 2026-05-16`). |

## Test Counts

| File | Tests | All Passing |
|------|------:|------------:|
| `test_cmvp_freshness.py` | 5 | yes |
| `test_cmvp_no_certified_true.py` | 9 | yes |
| `test_cmvp_refresh.py` | 6 | yes |
| `test_cmvp_coverage_query.py` | 12 | yes |
| `test_cmvp_report_column.py` | 6 | yes |
| **Total** | **38** | **38 / 38** |

## Verification Results

```
$ .venv/bin/python -m pytest tests/test_cmvp_freshness.py \
    tests/test_cmvp_no_certified_true.py tests/test_cmvp_refresh.py \
    tests/test_cmvp_coverage_query.py tests/test_cmvp_report_column.py -q
......................................                                   [100%]
38 passed in 3.23s

$ python -m compileall -q quirk/ tests/    # clean

$ python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/python-staleness.yml').read_text()); print('workflow YAML parses OK')"
workflow YAML parses OK

$ grep -c 'test_cmvp_freshness.py' .github/workflows/python-staleness.yml
1

$ grep -c 'UAT-81-' docs/UAT-SERIES.md
7

$ test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-81-CMVP-Attestation-Feed.md" && echo OK
OK
```

## Commits

| SHA | Subject | Files |
|------|---------|-------|
| `a3984f9` | `feat(81-04): cmvp ci gates + refresh + coverage + report-column tests` | 6 (5 test files + python-staleness.yml) |
| `754de76` | `docs(phase-81): update UAT-SERIES.md` | 1 (docs/UAT-SERIES.md) |

Vault files (`UAT-Series.md`, `Phase-81-CMVP-Attestation-Feed.md`) live outside the repo per CLAUDE.md — not committed.

## Deviations from Plan

### [Rule 3 — Blocking issue] Environment missing `bs4` / `pypdf` in default Python 3.14

- **Found during:** Task 1 verification (`pytest tests/test_cmvp_refresh.py` collected 0 items + skipped 1; `pytest tests/test_cmvp_report_column.py` failed with `AttributeError: module 'quirk.reports' has no attribute 'writer'` due to `pypdf` import failure in `html_renderer.py`).
- **Issue:** The host's Python 3.14 environment lacks `bs4` and `pypdf` even though `beautifulsoup4>=4.13.0` is declared in `pyproject.toml` (Plan 81-01). The project's `.venv/bin/python` already has both. The pre-existing `tests/test_report_injection_hardening.py` exhibits the same failure under the bare interpreter — this is an environment-bootstrap problem, not a Phase 81 regression.
- **Fix:** Ran all verification through `.venv/bin/python`. Installed `beautifulsoup4` into the venv to clear the importorskip guard. The `pytest.importorskip("bs4")` at module scope in `test_cmvp_refresh.py` provides graceful CI degradation when the dep is genuinely absent — no change required to the test logic.
- **Files modified:** none (test code already guards correctly).
- **Outcome:** 38 / 38 tests pass under `.venv/bin/python -m pytest`; refresh suite would skip cleanly in any environment without bs4.

## Self-Check: PASSED

- `tests/test_cmvp_freshness.py` — FOUND (5 tests, all green)
- `tests/test_cmvp_no_certified_true.py` — FOUND (9 tests, all green; PERMANENT INVARIANT header present)
- `tests/test_cmvp_refresh.py` — FOUND (6 tests, all green)
- `tests/test_cmvp_coverage_query.py` — FOUND (12 tests, all green)
- `tests/test_cmvp_report_column.py` — FOUND (6 tests, all green)
- `.github/workflows/python-staleness.yml` — `test_cmvp_freshness.py` grepped; YAML parses OK
- `docs/UAT-SERIES.md` — 7 occurrences of `UAT-81-` (5 new cases + table-of-contents references); `2026-05-16` present
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — synced; frontmatter `updated: 2026-05-16`; `source: docs/UAT-SERIES.md`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-81-CMVP-Attestation-Feed.md` — exists with `status: complete`, `type: phase`, `v4.10-D-01`, `CMVP-07`, `[[Roadmap]]`
- Commit `a3984f9` — present in `git log`
- Commit `754de76` — present in `git log`

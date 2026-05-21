---
status: passed
phase: 84
phase_name: Release Engineering
verified_at: 2026-05-21
requirements_in_scope: RELENG-01, RELENG-02, RELENG-03, RELENG-04, RELENG-05, RELENG-06, RELENG-07, RELENG-08
plans_complete: 4/4
success_criteria_met: 5/5
human_verification: none_required
---

# Phase 84 — Release Engineering — Verification

## Success Criteria (from ROADMAP.md)

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| 1 | PyPI name verified, decision logged, test upload feasible | `pyproject.toml` shows `name = "qu-i-r-k"`; decision v4.10-D-02 logged in `.continue-here.md` handoff and recorded here below; `quirk` was squatted on PyPI by an unrelated 0.1.x project, alternate `qu-i-r-k` selected (84-01-SUMMARY.md) | passed |
| 2 | `v*` tag triggers `release.yml` with Trusted Publishers + Sigstore | `.github/workflows/release.yml` (85 lines) — tag pattern `v*.*.*`, `pypa/gh-action-pypi-publish@release/v1`, `attestations: true`, `id-token: write`, `environment: release`, URL `https://pypi.org/p/qu-i-r-k`; YAML parses; zero token/password references (84-03-SUMMARY.md) | passed |
| 3 | `SECURITY.md` at root with 90-day SLA + GitHub PVR + Sigstore identity | `SECURITY.md` (105 lines) — supported-versions table, 90-day disclosure SLA, GitHub private vulnerability reporting URL, in-scope/out-of-scope statement, Sigstore signing identity reference (84-04-SUMMARY.md) | passed |
| 4 | `towncrier build` + `docs/release-process.md` release runbook | `pyproject.toml [tool.towncrier]` package="quirk" with five section types + `dev` extras pin `towncrier>=24.7.0`; `changelog.d/` with `.gitkeep`, `README.md`, example `v4.10.feature.md`; `CHANGELOG.md` marker inserted; agent ran `towncrier build --draft --version 4.10.0` clean (84-02-SUMMARY.md); `docs/release-process.md` (194 lines) covers semver policy, release runbook, attestation verification, Trusted Publishers setup pointer (84-04-SUMMARY.md) | passed |
| 5 | Single version source of truth | `pyproject.toml [project.version] = "4.10.0"`; `quirk/__init__.py::__version__` resolves via `importlib.metadata.version("qu-i-r-k")` with `tomllib` fallback; `tests/test_version.py` extended to 7 surfaces per decision v4.10-D-02 (84-01-SUMMARY.md) | passed |

## Decisions Locked

- **v4.10-D-02 (Phase 84):** PyPI distribution name `qu-i-r-k` (squatter present on `quirk`). Version SoT: `pyproject.toml [project.version]`. Reverses RELENG-08's original `__init__.py`-as-SoT wording.

## Smoke Tests Run (orchestrator merge gate, 2026-05-21)

```
python3 -c "import tomllib; ..." → name: qu-i-r-k, version: 4.10.0, towncrier package: quirk
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))" → ok
file presence → SECURITY.md, CODE_OF_CONDUCT.md, docs/release-process.md,
                 changelog.d/README.md, .github/workflows/release.yml,
                 .planning/phases/84-release-engineering/84-0[1-4]-SUMMARY.md all present
```

Three-way auto-merge of `pyproject.toml` succeeded without conflict (84-01's name/version rename and 84-02's `[tool.towncrier]` + `dev` extras touched disjoint sections).

## Human Verification Required

None — all five success criteria verifiable via filesystem + syntax checks above. The Trusted Publisher itself must be configured on the PyPI side after the first tag push, but that is **deferred-by-design** per `docs/release-process.md` (first-time setup pointer) and is not a Phase 84 deliverable.

## Outcome

**Phase 84: Release Engineering — passed.** All 8 RELENG requirements (RELENG-01..08) are satisfied. Proceeding to Phase 85 (Public-Launch Polish).

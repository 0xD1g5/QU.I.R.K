# Phase 41: CI Stability & Scanner Robustness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 41-ci-stability-scanner-robustness
**Areas discussed:** Skip-marker triage policy, Timeout/retry single source, Failure-surface UX, Slow-test policy & CI scope

---

## Skip-Marker Triage Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Strictest — only live-infra skips | Stale skips deleted; optional-extra skips converted to real tests OR deleted; only Docker/Vault/cloud-creds skips survive | |
| Pragmatic — stale gone, extras kept | Delete stale skips; keep optional-extra skips (e.g., importorskip(broker_scanner)); document allowed via single ALLOWED_SKIPS registry | ✓ |
| Audit-only — categorize then decide per-skip | First plan task is an inventory; per-skip decisions during execution | |

**User's choice:** Pragmatic (after asking for a recommendation; agreed with rationale).
**Notes:** User initially asked "what is recommended here — I am having a hard time distinguishing between the options," then accepted Option 2 with rationale that `importorskip` for an optional extra is not a "code reason" skip and is closer in nature to a live-infra skip. ALLOWED_SKIPS registry + CI gate = structural mechanism preventing drift.

---

## Timeout / Retry Single Source

### Q1 — Policy home

| Option | Description | Selected |
|--------|-------------|----------|
| Extend ScanConfig in config.py | Add [scan.timeouts] sub-table; per-scanner overrides; migrate the 4 existing fields with deprecation aliases | ✓ |
| New quirk/scanner/policy.py module | Code-level constants imported by every scanner | |
| Hybrid — constants in code, exposed via ScanConfig | policy.py defines constants; ScanConfig.timeouts proxies them | |

**User's choice:** Extend ScanConfig (Recommended).
**Notes:** Aligns with existing TOML-driven configuration pattern; one source of truth for users and code.

### Q2 — Consumption pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only — each scanner reads its slot | No mutation of cfg.scan in run_scan.py; eliminates BACK-45 | ✓ |
| Keep mutation pattern, add try/finally (BACK-45) | Smaller diff; preserves the smell | |
| Defer consumption refactor to later phase | Phase 41 only delivers sub-table + audit doc | |

**User's choice:** Read-only.
**Notes:** Dissolves BACK-45 by structurally removing the unsafe mutation pattern rather than guarding it.

---

## Failure-Surface UX (`scan_errors[]` schema + missing-extras advisory)

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal schema + structured advisory | scan_errors[] = {scanner, target, reason, category}; missing extras → entry + stderr advisory; exit code 0 for missing_extra | ✓ |
| Full forensic schema, advisory in stderr only | Adds exception_type, traceback_excerpt, phase, duration_ms; missing extras stderr-only | |
| Two-tier — minimal default, --verbose-errors adds forensic | Default minimal; CLI flag adds forensic fields | |

**User's choice:** Minimal schema + structured advisory (Recommended).
**Notes:** `category` field is the unlock for `quirk/intelligence/trends.py` to distinguish "regression crash" from "missing extra this run" in delta reports. Avoids traceback noise leaking into client-facing JSON.

---

## Slow-Test Policy & CI Scope

| Option | Description | Selected |
|--------|-------------|----------|
| 1s threshold, local-only, lab.sh fix in-scope | >1s = @pytest.mark.slow; <60s default budget; no GHA changes; Phase 40 lab.sh down-sweep fix folded in | ✓ |
| 5s threshold, also touches GitHub Actions | Higher threshold; modifies .github/workflows/* | |
| 1s threshold, local-only, lab.sh fix punted | Same as Recommended but lab.sh stays in backlog | |

**User's choice:** 1s threshold, local-only, lab.sh fix in-scope (Recommended).
**Notes:** Keeps phase scope tight (no CI YAML), but includes the small lab.sh `down --profile "*"` cleanup as a single-task plan since it fits the robustness theme.

---

## Claude's Discretion

- Exact filename/location of the skip registry (`tests/skip_registry.py` vs entry in `conftest.py`).
- Exact mechanism of unregistered-skip CI gate (pytest plugin vs collection hook vs sentinel meta-test).
- Per-scanner default timeout values when reconciling current divergent fields (default to more conservative).
- Whether the `try/except BaseException` ROBUST-03 wrapper lives in `run_scan.py` or as a per-scanner decorator.

## Deferred Ideas

- Dashboard "Scan Issues" widget grouped by `category` — belongs in Phase 43 (Dashboard Polish).
- GitHub Actions CI YAML tuning — out of scope for Phase 41; future phase if needed.
- Single-bundled wheel removing `[motion]` optionality — would change skip calculus; not on roadmap.
- Removal of deprecated `*_timeout_seconds` aliases — future minor-version cleanup.

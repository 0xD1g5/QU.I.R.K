# source_scanner loses partial results and leaks paths; error handling is loose

**Filed:** 2026-10-30 (Phase 235 post-GO code review, group (d): WR-01, with WR-02, IN-03, IN-04 which live in the same file)
**Priority:** P2. Latent in 5.28.0 (every semgrep run exits 7 while the ruleset 404s), live the moment a working ruleset returns.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` WR-01, WR-02, IN-03, IN-04
**Where it lives:** **[package]** `quirk/scanner/source_scanner.py`, `run_scan.py:337-343` (`_wrapped_phase`).

## Items

- **WR-01** `source_scanner.py:110-127, 162-171`: `scan_source_targets` re-raises `SourceScanError` mid-loop, so
  `_wrapped_phase` returns `[]` and earlier repos' findings (and their `invalid_input` rows) are lost; within one
  repo a single `level:"error"` entry beside valid results discards all of them. Fix: collect per repo, record
  per-repo failures as ERROR rows, raise only when every repo failed; keep `data["results"]` when errors are
  per-target and rc is 0 or 1.
- **WR-02** `:27-34, 111-127`; `run_scan.py:337-343`: the docstrings promise messages carry no repo path, but `first`
  is raw semgrep `errors[0].message` (200 chars), and `scan_error=str(exc)` is persisted raw (no `safe_str`). Fix:
  redact `repo_path` and absolute paths; add a test whose fixture message contains the path.
- **IN-03** `:117-120`: substring "configuration" classifies any message as `SourceRulesetUnavailable`; key on
  semgrep's error `code`/`type` instead.
- **IN-04** `:130-135, 168-170`: `"results": null` or non-dict entries raise `TypeError`/`AttributeError`, swallowed
  by the generic `except Exception` (only `logger.v`), so the repo reads clean. Validate and raise `SourceScanError`;
  narrow or remove the generic except.

CR-02 (missing binary recorded as ran) touches the same file; do both in one pass.

## Feasibility & Effort

- **Feasibility: LIKELY.** WR-01/WR-02 reproduced by reading code and the existing fixtures, not by a live run.
  Item shapes are local to one module.
- **Effort: M** overall (WR-01 restructures the loop and its result contract; the rest are S).
- **Unknowns:** how coverage/report should present "some repos failed, some produced findings"; there is no
  precedent row type for a partial phase.
- **Spike needed?** No. Fixtures for mixed results can be built from `tests/fixtures/semgrep_exit7_p_cryptography.json`.

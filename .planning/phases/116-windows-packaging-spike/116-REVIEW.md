---
phase: 116-windows-packaging-spike
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - run_scan.py
  - .github/workflows/python-ci.yml
  - tests/test_windows_ci_hardgate.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 116: Code Review Report

**Reviewed:** 2026-05-27
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files reviewed. The scope is intentionally minimal: a 2-line `run_scan.py`
delta, a new non-blocking CI job, and a rewritten hard-gate test. No critical
defects found. The `freeze_support()` placement is correct and the
`continue-on-error: true` spike job cannot gate the pipeline. Three warnings
concern: a missing explicit `shell:` declaration, redundant step-level
`continue-on-error`, and a fragile block-end heuristic in the hard-gate test.
One info item covers a missing upload-artifact hygiene flag.

## Warnings

### WR-01: "Build onefile EXE" step relies on implicit PowerShell default — no explicit `shell:` declared

**File:** `.github/workflows/python-ci.yml:45-60`
**Issue:** The multi-line `pyinstaller` command uses PowerShell backtick (`` ` ``) line
continuations. This syntax is valid only in PowerShell (`pwsh`). The step does not
declare `shell: pwsh`, relying on the implicit `windows-latest` default. The adjacent
"Report build outcome" step (line 63) does declare `shell: pwsh` explicitly. The
inconsistency creates a silent dependency on GitHub Actions default-shell assignment
and makes the backtick syntax non-obvious to maintainers unfamiliar with the
runner default.

**Fix:** Add `shell: pwsh` to the "Build onefile EXE" step:
```yaml
      - name: Build onefile EXE
        shell: pwsh
        run: |
          pyinstaller --onefile --name quirk `
            ...
```

---

### WR-02: Redundant `continue-on-error: true` at step level when already set at job level

**File:** `.github/workflows/python-ci.yml:61`
**Issue:** The "Build onefile EXE" step sets `continue-on-error: true` at line 61.
The `windows-packaging-spike` job already sets `continue-on-error: true` at line 32
(job level). A job-level `continue-on-error` makes individual step failures
non-blocking for the overall workflow, so the step-level flag is redundant. This
creates a misleading signal: readers may infer the step-level flag is the load-bearing
mechanism that keeps the job non-blocking, not realising the job-level flag already
handles it. If the job-level flag is ever removed as a "cleanup", the step-level flag
would not substitute for it (job-level and step-level flags have different scopes).

**Fix:** Remove `continue-on-error: true` from the step (line 61). The job-level
flag at line 32 is the canonical non-blocking mechanism for this spike job. Add a
comment on the job-level flag to make the intent explicit:
```yaml
  windows-packaging-spike:
    name: Windows Packaging Spike
    runs-on: windows-latest
    continue-on-error: true  # spike: informational only — must not gate the pipeline
```

---

### WR-03: Block-end heuristic in `test_no_continue_on_error_literal_in_smoke_job` is fragile

**File:** `tests/test_windows_ci_hardgate.py:110-114`
**Issue:** The end-of-smoke-block detection (lines 110-114) terminates on the first
line that satisfies all of:
1. `line.startswith("  ")` — exactly 2-space indent, and
2. `not line.startswith("   ")` — not 3+ spaces, and
3. `line.strip().endswith(":")` — stripped line ends with colon.

Condition 3 is the fragile one. A job key with a YAML inline mapping
(e.g., `  future-job: {uses: ./.github/workflows/reuse.yml}`) or any line at
2-space indent not ending with `:` would be skipped, causing `end` to remain
`len(lines)` — folding the entire `windows-packaging-spike` block into the smoke
block. The `packaging-spike` block contains `continue-on-error: true` (line 32),
so the `assert "continue-on-error: true" not in smoke_block` check would then
falsely fire, breaking CI for an unrelated reason.

In the current YAML this does not trigger because `  windows-packaging-spike:`
ends with `:`. But the heuristic is brittle enough to warrant hardening.

**Fix:** Drop condition 3 from the end-detection loop. Any 2-space-indented,
non-3-space-indented non-blank line that is not a continuation of the smoke block
is a sufficient terminator:
```python
    for j in range(start + 1, len(lines)):
        line = lines[j]
        # Next 2-space-indented key signals start of a sibling job block.
        if (
            line.startswith("  ")
            and not line.startswith("   ")
            and line.strip()           # skip blank lines
            and not line.strip().startswith("#")  # skip comments
        ):
            end = j
            break
```
Alternatively, rely exclusively on the YAML-parsed assertions
(`test_job_has_no_continue_on_error`, `test_no_step_has_continue_on_error`) which
are already authoritative and do not need the text-scan backup for correctness.

## Info

### IN-01: `upload-artifact` step missing `if-no-files-found: ignore`

**File:** `.github/workflows/python-ci.yml:73-81`
**Issue:** The `actions/upload-artifact@v4` step uses `if: always()` to ensure
evidence is captured even on build failure. However, it does not set
`if-no-files-found:`, which defaults to `warn`. If the build fails early (e.g.,
`pyinstaller` is not on PATH, or the checkout fails), none of the listed artifact
paths (`pyinstaller-build.log`, `build/quirk/warn-quirk.txt`, `dist/quirk.exe`)
will exist. The step will emit a yellow-warning annotation in the Actions log,
which is noise for a spike job expected to be non-blocking.

**Fix:** Add `if-no-files-found: ignore` to suppress the warning when no files
exist (consistent with the spike's "informational only" intent):
```yaml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pyinstaller-spike-evidence
          if-no-files-found: ignore
          path: |
            pyinstaller-build.log
            build/quirk/warn-quirk.txt
            dist/quirk.exe
          retention-days: 30
```

---

## Verified Correct (no findings)

**`run_scan.py` — `import multiprocessing` (line 3) and `freeze_support()` (line 2256):**
- The `multiprocessing` import is used at line 2256; it is not unused.
- `multiprocessing.freeze_support()` is the first statement in the
  `if __name__ == "__main__":` block, placed before `_run_main_with_job_guard()`.
  This is the correct placement — PyInstaller requires it to be the first call in
  `__main__` before any subprocess or argument-parsing logic runs.
- `freeze_support()` is documented (Python stdlib) as a no-op on non-Windows
  platforms and on non-frozen (normal interpreter) runs. It does not alter CLI
  behavior.

**`python-ci.yml` — Pipeline gate integrity:**
- `windows-packaging-spike` has no `needs:` relationship to or from any gating job.
  It cannot block the pipeline even if `continue-on-error: true` were removed.
- The `windows-sensor-smoke` job (the hard gate) has no `continue-on-error` at job
  or step level. The SENSOR-06 guard is intact.
- No secrets are exposed. No `${{ github.event.* }}` user-controlled inputs are
  interpolated into `run:` scripts.
- The `--add-data` `;` separator is correct for Windows (PyInstaller uses `;` on
  Windows, `:` on POSIX).

**`test_windows_ci_hardgate.py` — Block extraction correctness (current YAML):**
- The smoke-job start heuristic correctly matches `  windows-sensor-smoke:` at
  exactly 2-space indent.
- The end heuristic correctly terminates at `  windows-packaging-spike:` (which
  ends with `:`), excluding the spike block from the smoke block text.
- The YAML-parsed assertions (`test_job_has_no_continue_on_error`,
  `test_no_step_has_continue_on_error`) are the authoritative SENSOR-06 guards and
  correctly scope to `JOB_NAME = "windows-sensor-smoke"` only.

---

_Reviewed: 2026-05-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

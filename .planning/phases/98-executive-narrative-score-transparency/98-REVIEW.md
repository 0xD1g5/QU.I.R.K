---
phase: 98-executive-narrative-score-transparency
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - quirk/reports/content_model.py
  - quirk/reports/executive.py
  - quirk/reports/html_renderer.py
  - quirk/reports/templates/report.html.j2
  - quirk/reports/writer.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 98: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 98 executive-narrative / score-transparency seam: the shared `ExecContent`
model (`content_model.py`), the CLI markdown renderer (`executive.py`), the HTML/PDF renderer
(`html_renderer.py` + `report.html.j2`), and the orchestration seam (`writer.py`).

The congruence guard is correctly placed before any file I/O (`build_exec_content` is called in
`write_reports` at line 165, before the first executive/HTML write at lines 209/224), and the
band-vs-rating contract is internally consistent because scoring's `_rating()` thresholds
(85/70/55/35) match the HTML renderer's `_score_band()` thresholds exactly and both key off the
same rounded total. HTML sanitization of scanner-derived cells is applied at the documented
chokepoint.

However there is one BLOCKER (a crash in the congruence/raw_sum path on a malformed subscore
value that bypasses the documented "no error when empty" guarantee), plus several data-contract
and injection-hardening defects where the markdown and HTML surfaces are NOT held to the same
sanitization standard the code comments claim.

## Critical Issues

### CR-01: `raw_sum` computation crashes on non-numeric subscore values, defeating the "no error" guarantee

**File:** `quirk/reports/content_model.py:457`
**Issue:** The docstring/field comment (lines 73, 456) promises `raw_sum` is "0 when subscores is
empty — no error (Pitfall 3)". But the implementation only guards the *empty* case, not the
*malformed-value* case:

```python
raw_sum: int = int(sum(subscores.values())) if subscores else 0
```

`build_exec_content` receives `subscores` from `score_raw.get("subscores")` and does
`dict(... or {})` (line 454) with no value-type validation. If any subscore value is non-numeric
(e.g., a sentinel like `"—"`, `None`, or a string injected by a calibration-override path),
`sum(subscores.values())` raises `TypeError` *inside* `build_exec_content`. Because this builder
is the very first thing `write_reports` calls (writer.py:165), the exception propagates and aborts
the **entire** report run — no findings JSON, no technical markdown, nothing — even though those
earlier artifacts (writer.py lines 144-150) were already written and the failure is purely in
executive content. This is broader-than-intended data loss for a malformed/partial score dict, and
contradicts the stated resilience contract.

**Fix:** Coerce defensively and never let a bad value abort the run:
```python
def _coerce_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0

raw_sum: int = sum(_coerce_int(v) for v in subscores.values()) if subscores else 0
```
Apply the same coercion in the markdown (`executive.py:221`) and template (`report.html.j2:230`)
rollup sums so all three surfaces agree under degraded input.

## Warnings

### WR-01: Markdown narrative drivers bypass `md_cell`, breaking the HARDEN-01 chokepoint contract

**File:** `quirk/reports/executive.py:187`
**Issue:** Every other scanner-derived markdown cell in this file is wrapped in `md_cell(...)`
(lines 192, 201, 234, 277, 312, 316, etc.). The new narrative-drivers line is not:

```python
lines.append("Key factors: " + "; ".join(exec_content.narrative_drivers) + ".")
```

`narrative_drivers` is normalized in `content_model.py:466-469` from `score_raw["drivers"]`. Today
those `reason` strings are static literals from `scoring.py` (e.g., "Database plaintext
connections"), so there is no live injection. But the HTML template explicitly treats this same
data as untrusted ("narrative_drivers come from score_raw[\"drivers\"] — sanitize scanner-derived
text", report.html.j2:203 applies `| sanitize`). The two surfaces now disagree on whether this
data is trusted. If a future driver ever embeds finding/host text, the markdown surface is
unprotected while HTML is hardened. The chokepoint must be symmetric.

**Fix:** Wrap each driver: `"; ".join(md_cell(d) for d in exec_content.narrative_drivers)`.

### WR-02: `narrative_drivers` normalization can emit a raw `dict` repr into the report

**File:** `quirk/reports/content_model.py:466-469`
**Issue:**
```python
narrative_drivers: List[str] = [
    d.get("reason") or d.get("label") or str(d) if isinstance(d, dict) else str(d)
    for d in (score_raw.get("drivers") or [])
]
```
Operator precedence: the conditional binds as
`(d.get("reason") or d.get("label") or str(d)) if isinstance(d, dict) else str(d)`. For a dict
driver missing both `reason` and `label` (or with both falsy/empty-string), the fallback is
`str(d)` — i.e. the literal Python dict repr `{'points': -3, ...}` is rendered into the executive
narrative. Scoring currently always emits `reason`, so this is latent, but the fallback produces
user-facing garbage rather than a safe omission.

**Fix:** Skip empties instead of dumping the repr:
```python
narrative_drivers = []
for d in (score_raw.get("drivers") or []):
    if isinstance(d, dict):
        clause = d.get("reason") or d.get("label")
        if clause:
            narrative_drivers.append(str(clause))
    elif d:
        narrative_drivers.append(str(d))
```

### WR-03: Rollup sum diverges between surfaces if subscores carry extra keys

**File:** `quirk/reports/templates/report.html.j2:230` vs `quirk/reports/executive.py:221`
**Issue:** HTML computes the rollup numerator as `{{ subscores.values() | sum }}` (sum of *all*
keys present), while the markdown computes `sum(subscores.get(k, 0) for k, _ in _SUBSCORE_LABELS)`
(sum of only the six known keys). Scoring today emits exactly the six keys (scoring.py:303-310) so
they match, but the contract is fragile: any future seventh subscore (the project has repeatedly
walked SCORE_WEIGHTS upward) would silently make the HTML "How this score was computed" block
disagree with the CLI markdown — the exact cross-surface parity Phase 98 is meant to guarantee.

**Fix:** Make both surfaces sum the same key set. Either iterate the six labeled keys in the
template too, or have both consume the single pre-computed `ExecContent.raw_sum` field (which today
is computed but unused by either renderer — see IN-01).

### WR-04: `_score_band` / band displayed in HTML is recomputed instead of sourced from the guarded model

**File:** `quirk/reports/html_renderer.py:172-173`
**Issue:** `render_html_report` recomputes the band locally:
```python
total_score = score.get("total", 0)
band = _score_band(total_score)
```
rather than using `exec_content.score_band` (which is what the congruence guard in
`content_model._check_congruence` actually validated against). They agree *today* only because
`_rating()` and `_score_band()` are hand-kept identical (85/70/55/35). This is a duplicated-source-
of-truth hazard: if one threshold table is edited without the other, the HTML could display a band
that the guard never checked, re-opening the incongruence Phase 98 exists to close. The whole point
of D-03 is single-source content.

**Fix:** When `exec_content` is provided, prefer `band = exec_content.score_band` and
`total_score = exec_content.score_total`, falling back to the local recompute only on the
backward-compat path.

### WR-05: Congruence guard not applied to the backward-compat (`exec_content is None`) paths

**File:** `quirk/reports/html_renderer.py:210-218`, `quirk/reports/executive.py:189-193`
**Issue:** Both renderers retain a legacy branch that runs when `exec_content is None`. On that
path no congruence check ever fires — an EXCELLENT/GOOD/MODERATE band can be rendered alongside
CRITICAL findings, which is precisely the inconsistency `ReportCongruenceError` was added to
prevent. `write_reports` always passes `exec_content` today, but `build_exec_markdown` and
`render_html_report` are public functions (`build_exec_markdown` is also imported elsewhere and
exercised directly by tests), so the unguarded path is reachable by callers and tests.

**Fix:** Either route the compat path through `build_exec_content` as well, or document at the
function signature that callers without `exec_content` are responsible for the congruence check.
Prefer the former to keep the guard truly fail-closed.

## Info

### IN-01: `ExecContent.raw_sum` is computed but never consumed

**File:** `quirk/reports/content_model.py:457`, `:492`
**Issue:** `raw_sum` is populated on the model but neither `executive.py` nor `report.html.j2` read
it — both recompute their own rollup numerator (see WR-03). Dead data on the shared model invites
exactly the kind of drift WR-03 describes.
**Fix:** Have both renderers consume `exec_content.raw_sum`, or drop the field.

### IN-02: Misleading conditional `if nist_level is not None or True`

**File:** `quirk/reports/html_renderer.py:111`
**Issue:** `fips_status = _fips_status(nist_level) if nist_level is not None or True else "non-approved"`
— `... or True` makes the condition unconditionally true, so the `else "non-approved"` branch is
dead code. This is confusing and looks like a leftover from an edited condition. (Pre-existing,
not Phase-98 new, but inside a reviewed file.)
**Fix:** Simplify to `fips_status = _fips_status(nist_level)` and delete the dead branch.

### IN-03: Template comment mislabels `narrative_drivers` provenance relative to markdown handling

**File:** `quirk/reports/templates/report.html.j2:196,203`
**Issue:** The template comments correctly call `narrative_drivers` "scanner-derived text" and
apply `| sanitize`, but the markdown renderer treats the same field as trusted (WR-01). The
divergent treatment plus the comment make the intended trust boundary ambiguous. Align the comments
and the handling once WR-01 is fixed.
**Fix:** After making markdown apply `md_cell`, ensure both comments state the same trust posture.

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 49-compliance-mapping
type: patterns
status: active
source: /gsd-plan-phase 49 (gsd-pattern-mapper)
updated: 2026-05-05
---

# Phase 49: Compliance Mapping — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 11 (5 new, 6 modified)
**Analogs found:** 11 / 11

## Path Correction (vs. RESEARCH.md / CONTEXT.md)

CONTEXT.md and RESEARCH.md reference `quirk/cli/run_scan.py:176-221`. The actual entry point lives at the repo root: `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/run_scan.py`. The `init` and `serve` pre-intercept blocks live at `run_scan.py:176-221` (verified). All planner action items targeting "run_scan.py" should use the root-level path.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/compliance/__init__.py` | data-module / config | static-data | `quirk/engine/risk_engine.py` (module-level constants `_OPENSSL_EOL`, `NIST_IR_8547_DEPRECATION`) | role-match |
| `tests/test_compliance_schema.py` | test (invariant gate) | static-data validation | `tests/test_pqc_terminology_gate.py` | exact |
| `tests/test_compliance_freshness.py` | test (invariant gate) | static-data validation | `tests/test_pqc_terminology_gate.py` | exact |
| `tests/test_compliance_title_join.py` | test (cross-source invariant) | data-join | `tests/test_pqc_terminology_gate.py` | exact |
| `tests/test_compliance_report_section.py` | test (smoke / render) | request-response | `tests/test_pqc_terminology_gate.py` (file-resolution pattern) | role-match |
| `tests/test_compliance_cli.py` | test (CLI smoke) | request-response | `tests/test_pqc_terminology_gate.py` | role-match |
| `quirk/engine/risk_engine.py` (modify) | engine helper | transform | `_build_finding` (self) | exact (extension) |
| `run_scan.py` (modify) | CLI entry | request-response | `run_scan.py` lines 176-221 (`init` / `serve` intercepts) | exact (extension) |
| `quirk/reports/templates/report.html.j2` (modify) | view template | render | `report.html.j2` lines 223-242 ("All Findings" table) | exact (extension) |
| `docs/report-interpretation.md` (modify) | doc | doc-sync | existing docs (per CLAUDE.md) | role-match |
| `docs/UAT-SERIES.md` (modify) | doc | doc-sync | existing series structure | role-match |

## Pattern Assignments

### `quirk/compliance/__init__.py` (NEW data module)

**Analog:** `quirk/engine/risk_engine.py` lines 1-29 (module-level data constants + canonical-anchor pattern)

**Module-level data + canonical anchor pattern** (`risk_engine.py:1-29`):
```python
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# (version_prefix, severity, eol_label)
_OPENSSL_EOL: List[Tuple[str, str, str]] = [
    ("0.", "CRITICAL", "OpenSSL 0.x"),
    ("1.0.", "CRITICAL", "OpenSSL 1.0.x (EOL Dec 2019)"),
    ...
]

# Phase 48 D-06: canonical NIST IR 8547 deprecation phrase. The single
# authoritative anchor for the v4.6 quantum-vulnerable recommendation suffix
# and for Phase 49 (Compliance Mapping). Per-finding drift is structurally
# impossible because every quantum-vulnerable finding receives this exact
# constant via _build_finding(quantum_vulnerable=True).
NIST_IR_8547_DEPRECATION = (
    "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and "
    "disallowed after 2035."
)
```

**Apply to Phase 49:**
- `from __future__ import annotations` header (matches project style).
- `from datetime import date` for `last_verified` parsing.
- Typed module-level constants: `STALENESS_THRESHOLD_DAYS: int = 365`, `COMPLIANCE_MAP: Dict[str, List[Dict[str, Any]]] = {...}`, `UNMAPPED_TITLES: FrozenSet[str] = frozenset({...})`.
- Each `UNMAPPED_TITLES` entry **must** carry a preceding `# ` comment — same self-documenting convention used in `_OPENSSL_EOL`.
- Module docstring carries the load-bearing maintenance note pointing forward to `docs/operators-guide.md` (Phase 50 TODO marker).

---

### `quirk/engine/risk_engine.py` — extend `_build_finding` (MODIFY)

**Analog:** `quirk/engine/risk_engine.py:32-67` (the helper itself; Phase 48 chokepoint)

**Existing helper** (lines 32-67):
```python
def _build_finding(
    *,
    severity: str,
    host: str,
    port: int,
    title: str,
    description: str,
    recommendation: str,
    quantum_vulnerable: bool = False,
) -> Dict[str, Any]:
    """Single chokepoint for finding construction (Phase 48 D-02)."""
    if not description or not description.strip():
        raise ValueError("_build_finding requires a non-empty description")
    if not recommendation or not recommendation.strip():
        raise ValueError("_build_finding requires a non-empty recommendation")
    rec = recommendation.strip()
    if quantum_vulnerable:
        rec = f"{rec} {NIST_IR_8547_DEPRECATION}"
    return {
        "severity": severity,
        "host": host,
        "port": port,
        "title": title,
        "description": description.strip(),
        "recommendation": rec,
    }
```

**Phase 49 patch (D-02 + Pitfall 1 normalization):**
```python
# Add at top of file alongside existing constants:
import re
from quirk.compliance import COMPLIANCE_MAP

_PAREN_SUFFIX_RE = re.compile(r"\s*\([^)]+\)\s*$")


def _normalize_for_compliance(title: str) -> str:
    """Strip trailing parenthesized data from f-string titles so the
    7 container-finding titles map to canonical COMPLIANCE_MAP keys.
    See RESEARCH.md Pitfall 1."""
    return _PAREN_SUFFIX_RE.sub("", title).strip()


# Inside _build_finding, replace the return dict:
    return {
        "severity": severity,
        "host": host,
        "port": port,
        "title": title,
        "description": description.strip(),
        "recommendation": rec,
        # Phase 49 D-02: eager compliance attachment (single chokepoint)
        "compliance": COMPLIANCE_MAP.get(_normalize_for_compliance(title), []),
    }
```

**Discipline:** Diff is one new import, one new module-level helper + regex, and one new dict key. Per CLAUDE.md "Keep diffs minimal."

---

### `tests/test_compliance_schema.py` / `test_compliance_freshness.py` / `test_compliance_title_join.py` (NEW gates)

**Analog:** `tests/test_pqc_terminology_gate.py` (entire file — Phase 48 D-07/D-08 gate)

**Module docstring + scope-locked constants** (lines 1-20):
```python
"""Phase 48 CI gate: forbid stale PQC terminology in two locked source files.

D-07: scope is exactly quirk/engine/risk_engine.py + quirk/dashboard/api/routes/scan.py.
D-08: case-insensitive substring match on 'kyber', 'dilithium',
      'when standards are adopted'. No exemptions.
"""
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_GATED_FILES = [
    "quirk/engine/risk_engine.py",
    "quirk/dashboard/api/routes/scan.py",
]

_FORBIDDEN = ("kyber", "dilithium", "when standards are adopted")
```

**File-resolution test pattern** (lines 28-33):
```python
def test_gated_files_resolve():
    """Catch accidental file rename — both gated paths must exist."""
    for rel in _GATED_FILES:
        assert os.path.isfile(os.path.join(_REPO_ROOT, rel)), (
            f"Gated file missing: {rel}. Update _GATED_FILES if file was renamed."
        )
```

**Invariant test with offender accumulation + actionable message** (lines 36-47):
```python
def test_no_stale_pqc_terminology_in_gated_files():
    """D-07/D-08: forbidden substrings must not appear in the two gated source files."""
    offenders = []
    for rel in _GATED_FILES:
        text = _read(rel)
        for needle in _FORBIDDEN:
            if needle in text:
                offenders.append((rel, needle))
    assert not offenders, (
        f"Stale PQC terminology found: {offenders}. "
        f"Use FIPS designations only (FIPS 203/204/205); see Phase 48 D-04/D-08."
    )
```

**Apply to all three Phase 49 gates:**
1. **Module-docstring header** that names the decision ID (e.g., "Phase 49 D-04 gate 1: schema completeness").
2. **`offenders = []`** accumulation pattern — collect every violator before asserting; never short-circuit on first failure.
3. **Single trailing `assert not offenders, f"..."`** with a *recipe* in the message (what to fix + where the rule lives), not just "found N violations".
4. **Always a paired file-resolution test** for any path the gate references (`test_module_imports` for `from quirk.compliance import COMPLIANCE_MAP`) so a rename produces a clean error, not a confusing import failure.
5. Schema gate uses `_REQUIRED = {"framework", "control", "version", "last_verified", "source_url"}` set-difference pattern (mirrors `_FORBIDDEN` tuple).

---

### `run_scan.py` — add `compliance` subcommand (MODIFY)

**Analog:** `run_scan.py:176-221` (existing `init` + `serve` pre-intercept blocks)

**Existing intercept pattern** (lines 176-221):
```python
def main():
    # --- init subcommand: intercept before scan argparse ---
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "init":
        init_parser = argparse.ArgumentParser(
            prog="quirk init",
            description="Generate a starter config.yaml",
        )
        init_parser.add_argument(
            "--output",
            default="config.yaml",
            help="Output path for generated config.yaml (default: ./config.yaml)",
        )
        init_args = init_parser.parse_args(_sys.argv[2:])
        from quirk.cli.init_cmd import run_init
        run_init(init_args.output)
        return

    # --- serve subcommand: intercept before scan argparse to avoid conflicts ---
    if len(_sys.argv) > 1 and _sys.argv[1] == "serve":
        serve_parser = argparse.ArgumentParser(
            prog="quirk serve",
            description="Start the QU.I.R.K. web dashboard",
        )
        serve_parser.add_argument("--port", type=int, default=8512, ...)
        ...
        serve_args = serve_parser.parse_args(_sys.argv[2:])
        ...
        return

    parser = argparse.ArgumentParser(description="QU.I.R.K. -- ...")
```

**Apply to Phase 49 (D-05):** Add a third intercept block immediately after the `serve` block (before the main `parser` is constructed at line 223). Critical conventions:
- Use `_sys.argv[1] == "compliance"` guard — same shape as `init` / `serve`.
- Local `argparse.ArgumentParser(prog="quirk compliance", ...)` inside the block — do **not** add subparsers to the main scan parser (Pitfall 4).
- Use `add_subparsers(dest="action", required=True)` for the second-level dispatch (`status` initially; future `validate`, `export`).
- Lazy import: `from quirk.compliance import status_report` *inside* the block, mirroring `from quirk.cli.init_cmd import run_init` (line 190) — keeps cold-start cost off the scan path.
- `return` at end of block — matches lines 192, 221.
- Bare `quirk` and `quirk --any-flag` continue falling through to the existing scan parser unchanged. **Zero edits to lines 223+ of `run_scan.py`.**

**Recommended subparser shape (per RESEARCH.md Pattern 3):**
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "compliance":
    comp_parser = argparse.ArgumentParser(
        prog="quirk compliance",
        description="Inspect QUIRK's compliance mapping data",
    )
    comp_sub = comp_parser.add_subparsers(dest="action", required=True)
    status_parser = comp_sub.add_parser("status", help="Show framework metadata")
    status_parser.add_argument("--format", choices=["text", "json"], default="text")
    args = comp_parser.parse_args(_sys.argv[2:])
    if args.action == "status":
        from quirk.compliance import status_report
        status_report(format=args.format)
    return
```

---

### `quirk/reports/templates/report.html.j2` — Compliance Summary block (MODIFY)

**Analog:** `report.html.j2` lines 223-242 ("All Findings" table inside Technical Appendix)

**Existing finding table pattern** (lines 223-242):
```jinja
<h2>All Findings</h2>
{% if findings %}
<table>
  <thead><tr><th>Severity</th><th>Title</th><th>Host</th><th>Port</th><th>Description</th><th>Recommendation</th></tr></thead>
  <tbody>
  {% for f in findings if f.get('category') != 'coverage_gap' %}
  <tr>
    <td><span class="sev-cell sev-{{ f.get('severity','INFO')|upper }}">{{ f.get('severity','INFO')|upper }}</span></td>
    <td>{{ f.get('title','') }}</td>
    <td>{{ f.get('host','') }}</td>
    <td>{{ f.get('port','') }}</td>
    <td>{{ f.get('description','')[:200] }}{% if f.get('description','')|length > 200 %}…{% endif %}</td>
    <td>{{ f.get('recommendation','')[:200] }}{% if f.get('recommendation','')|length > 200 %}…{% endif %}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p style="color:var(--text-muted)">No findings recorded for this scan.</p>
{% endif %}
```

**Apply to Phase 49 D-03 — match these exact conventions:**
- `<h2>` for the "Compliance Summary" section heading; `<h3>` for per-framework subsection headings (matches existing `<h2>All Findings</h2>` / `<h2>Endpoint Inventory</h2>` hierarchy at lines 223, 244).
- Plain `<table><thead><tbody>` markup — **no** flex/grid/`position:sticky`/`color-mix()` (Pitfall 2 — Playwright PDF fidelity).
- `{% for f in findings if f.get('category') != 'coverage_gap' %}` filter — coverage_gap findings already excluded from severity counts (`html_renderer.py:73`) and All-Findings (`.j2:228`); keep that exclusion in Compliance Summary too.
- `<span class="sev-cell sev-{{ f.get('severity','INFO')|upper }}">` for the severity cell — reuses existing CSS classes; no new CSS required.
- `f.get('compliance', [])` — defensive `.get()` with default `[]` mirrors the rest of the template's defensive accessors (`.get('title','')`, `.get('severity','INFO')`).
- "Findings without compliance mapping" subsection sits at the end of the Compliance Summary section — uses the same `<p style="color:var(--text-muted)">` muted-note style already used at lines 161, 212, 241.
- **Insertion point:** immediately after line 242 (end of "All Findings" table, before "Endpoint Inventory" at line 244). This places Compliance Summary inside the Technical Appendix, after the raw findings table — matches D-03's "audit evidence" intent (the assessor reads findings first, then sees the control mapping below).
- **No code change required in `quirk/reports/html_renderer.py`** — the `findings` variable is already passed to `template.render()` at `html_renderer.py:93`; the template reads `f.compliance` directly off the existing dict.

---

### PDF rendering path (`quirk/reports/html_renderer.py:105` `render_pdf_report`)

**Analog:** `quirk/reports/html_renderer.py:105-128` (the PDF function itself)

**Confirmed:** `render_pdf_report` invokes Playwright on the *already-rendered HTML file* (`page.goto(f"file://{os.path.abspath(html_path)}")` at line 118). **No changes needed to this function** — the PDF inherits the new Compliance Summary block automatically. This validates RESEARCH.md COMPLY-05 architectural claim.

**Smoke test (`tests/test_compliance_report_section.py`) responsibility:** render a fixture `findings` list (with at least one mapped + one unmapped) through `render_html_report` to a `tmp_path` HTML file, then assert the file contains the literal strings `"Compliance Summary"`, `"PCI-DSS 4.0.1"`, `"HIPAA 45 CFR"`, `"FIPS 140-3"`, and `"Findings without compliance mapping"`. Substring matching mirrors `tests/test_pqc_terminology_gate.py`'s pattern.

---

### `tests/test_compliance_cli.py` (NEW CLI smoke)

**Analog:** No exact analog (no existing CLI test in `tests/`). Closest pattern:
- File-resolution + invariant shape from `tests/test_pqc_terminology_gate.py`
- Subprocess invocation pattern: planner should use `subprocess.run([sys.executable, "run_scan.py", "compliance", "status"], capture_output=True, text=True)` and assert exit code 0 + stdout contains `"PCI-DSS"`, `"HIPAA"`, `"FIPS"`.

**Recommendation to planner:** keep this test minimal (one happy-path invocation + one `--format json` invocation). Heavier CLI coverage lives in UAT-49-04 (manual smoke per RESEARCH.md §Validation Architecture).

---

### `docs/report-interpretation.md` + `docs/UAT-SERIES.md` (MODIFY)

**Analog:** Existing docs in `docs/` directory + recent UAT-SERIES patterns from Phase 48 (`UAT-48-01..04`).

**Apply to Phase 49:**
- Add a "Compliance Summary" subsection in `docs/report-interpretation.md` describing how to read the new section, what each column means, and the meaning of the "Findings without compliance mapping" subsection (audit-trail of coverage gaps).
- Add `UAT-49-01..05` cases to `docs/UAT-SERIES.md` covering: schema gate, title-join gate, staleness gate, CLI smoke, report-render smoke. Bump `**Last Updated:**` date to 2026-05-05.
- Sync to Obsidian per CLAUDE.md "Mandatory Phase Completion Steps" §3 — write to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` via filesystem (not `obsidian content=`).

## Shared Patterns

### Pattern: Module-Level Canonical Anchor + Decision ID Anchoring
**Source:** `quirk/engine/risk_engine.py:21-29` (the `NIST_IR_8547_DEPRECATION` constant block, which carries inline references to "Phase 48 D-06" and "Phase 49 (Compliance Mapping)")
**Apply to:** `quirk/compliance/__init__.py` module docstring + each significant constant. Every load-bearing decision should carry the decision ID (e.g., "Phase 49 D-04") in a comment or docstring so future readers can grep back to CONTEXT.md.

```python
# Phase 48 D-06: canonical NIST IR 8547 deprecation phrase. The single
# authoritative anchor for the v4.6 quantum-vulnerable recommendation suffix
# and for Phase 49 (Compliance Mapping). Per-finding drift is structurally
# impossible because every quantum-vulnerable finding receives this exact
# constant via _build_finding(quantum_vulnerable=True).
NIST_IR_8547_DEPRECATION = (...)
```

### Pattern: Pytest-as-CI-Gate (Phase 48 precedent → Phase 49 reuse)
**Source:** `tests/test_pqc_terminology_gate.py` (entire file)
**Apply to:** All three new compliance gate test files. Conventions: file-resolution test paired with invariant test; offender-accumulation pattern; assertion message contains a fix recipe.

### Pattern: Pre-Intercept Subcommand Dispatch
**Source:** `run_scan.py:176-221` (`init` + `serve` blocks)
**Apply to:** New `compliance` block. Convention: lazy import inside the block; `_sys.argv[1] == "<subcommand>"` guard; `return` at block end; **never** modify the main scan parser's `add_subparsers`.

### Pattern: Defensive Template Accessors
**Source:** `report.html.j2:179-182` (`f.get('severity','INFO')`, `f.get('title','')`)
**Apply to:** New Compliance Summary template block. Use `f.get('compliance', [])` and `c.framework` / `c.control` / `c.source_url` / `c.last_verified` only after `for c in f.get('compliance', [])` iteration guard.

### Pattern: Coverage-Gap Exclusion Filter
**Source:** `report.html.j2:177, 228`, `html_renderer.py:73-74`
**Apply to:** Compliance Summary iteration — `{% for f in findings if f.get('category') != 'coverage_gap' %}` so coverage-gap advisories don't show up in compliance reporting.

### Pattern: Mandatory Phase Completion (CLAUDE.md)
**Apply to:** Every plan in Phase 49. Each plan must include explicit tasks for:
1. Obsidian phase note write (`/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md` via filesystem, not CLI `content=`).
2. `docs/UAT-SERIES.md` update.
3. UAT sync to Obsidian (filesystem write to vault).
4. Commit `docs/UAT-SERIES.md` via `gsd-tools.cjs commit`.
5. `_QUIRK-Hub.md` link refresh.

## No Analog Found

| File | Role | Reason | Planner action |
|------|------|--------|----------------|
| `tests/test_compliance_cli.py` | CLI subprocess smoke | No existing test invokes the `quirk` CLI via subprocess in `tests/`. | Use `subprocess.run([sys.executable, "run_scan.py", "compliance", "status"], ...)`; minimal coverage; defer heavier CLI testing to manual UAT-49-04. |
| `tests/fixtures/chaos_lab_findings.py` (`collect_emitted_titles()` helper) | Test fixture aggregator | RESEARCH.md Open Question 2 — no existing aggregator confirmed in repo. | Wave 0 task: verify whether one exists (grep `tests/fixtures/`); if not, planner adds one. Without it the title-join gate cannot run. |

## Metadata

**Analog search scope:**
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/engine/risk_engine.py`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/run_scan.py`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/html_renderer.py`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/templates/report.html.j2`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_pqc_terminology_gate.py`

**Files scanned (read):** 5
**Pattern extraction date:** 2026-05-05

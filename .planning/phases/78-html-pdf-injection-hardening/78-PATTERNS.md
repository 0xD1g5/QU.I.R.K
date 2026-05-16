# Phase 78: HTML/PDF Injection Hardening — Pattern Map

**Mapped:** 2026-05-16
**Files surfaced:** 8 (1 new module, 4 modified sources, 1 new test, 1 modified test set, 1 dep manifest)

## File Classification

| File | Role | Data Flow | Closest Analog | Match |
|------|------|-----------|----------------|-------|
| `quirk/util/sanitize.py` (NEW) | utility | transform | `quirk/util/safe_exc.py` | exact |
| `quirk/reports/html_renderer.py` (MOD) | renderer | transform | self (existing) | self |
| `quirk/reports/executive.py` (MOD) | renderer | transform | `quirk/reports/technical.py` | exact |
| `quirk/reports/writer.py` (MOD — Playwright lock) | renderer | request-response | `quirk/reports/html_renderer.py:112-146` | exact (Playwright lives here today, not writer.py) |
| `tests/test_safe_filter_audit.py` (NEW) | test | AST scan | `tests/test_scan_error_gate.py` | exact |
| `tests/test_html_pdf_injection_regression.py` (NEW) | test | render assert | `tests/test_report_sanitization.py` | exact |
| `pyproject.toml` (MOD) | config | n/a | self `[project] dependencies` block | self |

> **Drift flag:** Phase scope says "Lock Playwright PDF context in `quirk/reports/writer.py`", but the actual Playwright launch site is `quirk/reports/html_renderer.py:render_pdf_report` (lines 112-146). `writer.py` only *invokes* `render_pdf_report` at line 194. Planner must reconcile — recommend hardening the launch site in `html_renderer.py` and treating the writer.py reference in CONTEXT.md as a scope-name (not literal file).

---

## Pattern Assignments

### 1. `quirk/util/sanitize.py` (NEW — utility, transform)

**Closest analog:** `quirk/util/safe_exc.py` (entire file, 53 lines)

**Why this analog:** Both are single-function credential/injection-neutralizing string transforms with `from __future__ import annotations`, module-level `Final` constants, and a single public callable. Deliberately no cross-imports from other `quirk.util` modules (D-02/D-03 independence rule cited in `safe_exc.py:7-9`).

**Copy verbatim:**
- Module docstring shape (`safe_exc.py:1-13`) — purpose statement → decision enforcement → public surface.
- `from __future__ import annotations` (line 14).
- Module-level `Final` constant block (lines 21-33) — adapt as `_NH3_TAGS: Final[set[str]] = set()` and `_NH3_ATTRS: Final[dict[str, set[str]]] = {}`.
- Single public function signature pattern (line 36): `def sanitize_scanner_text(s: str) -> str:`.

**Adapt — body shape (mirror `safe_exc.py:36-53`):**
```python
import nh3
def sanitize_scanner_text(s: str) -> str:
    """Strip ALL HTML — text-only output for scanner-emitted strings."""
    if s is None:
        return ""
    try:
        text = str(s)
    except Exception:
        return ""
    return nh3.clean(text, tags=_NH3_TAGS, attributes=_NH3_ATTRS)
```

**Do differently:** No regex pattern table (this is a strip-everything sanitizer, not a pattern-matcher). Import `nh3` at top (not lazily) — it is a project hard dep after Phase 78.

---

### 2. Jinja `| sanitize` filter registration

**Closest analog:** `quirk/reports/html_renderer.py:62-65` (Environment construction).

**Current state:** The Environment is built with `autoescape=select_autoescape(["html", "j2"])` and **no custom filters** are registered. The template (`report.html.j2`) does **not** currently use `| safe` anywhere (grep verified — only `[:120]` slicing). So the filter registration is a defensive prophylactic for future template authors plus an audit-gate anchor.

**Adapt** at `html_renderer.py:62-65`:
```python
from quirk.util.sanitize import sanitize_scanner_text
env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "j2"]),
)
env.filters["sanitize"] = sanitize_scanner_text
```

**Do differently:** The existing import block at `html_renderer.py:7-9` already imports from `quirk.util.safe_exc` — add the sanitize import on a new line in the same block.

---

### 3. `md_cell()` extension to `quirk/reports/executive.py`

**Closest analog:** `quirk/reports/technical.py:4` (import) and `:44, :63, :83, :99` (call sites).

**Copy verbatim:**
- Import at `technical.py:4`: `from quirk.reports._md_escape import md_cell` → add identical line to `executive.py`.
- Call-site wrapping pattern at `technical.py:44`: `f"| {md_cell(e.host)} | {e.port} | {md_cell(...)} |"` — every adversary-controllable cell is `md_cell()`-wrapped; integer cells (`e.port`) are not.

**Apply at:** `executive.py:109+` (`build_exec_markdown`) — audit every `f"... | {x} | ..."` and wrap string cells.

**Do differently:** Nothing — the pattern is mature and proven.

---

### 4. Post-markdown `nh3.clean()` in `html_renderer.py`

**Closest analog:** `html_renderer.py:89-109` (the `template.render(...)` → `f.write(html)` flow).

**Insert** between line 106 (`html = template.render(...)`) and line 107 (`os.makedirs(...)`):
```python
import nh3
html = nh3.clean(html, tags={"html","head","body","title","meta","style",
    "h1","h2","h3","h4","p","div","span","table","thead","tbody","tr","th","td",
    "ul","ol","li","strong","em","br","hr","a"}, attributes={"a":{"href"},"*":{"class","id","style"}})
```

**Do differently:** Tag/attr allowlist must be wider than `sanitize_scanner_text` (template structure must survive) but narrower than "everything" (no `<script>`, `<iframe>`, `<object>`, event handlers). Pin allowlist in a module constant near `_TEMPLATES_DIR`.

---

### 5. Playwright PDF context lock

**Closest analog:** `quirk/reports/html_renderer.py:122-134` (current `render_pdf_report` body).

**Current code** (lines 124-133):
```python
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file://{os.path.abspath(html_path)}")
    page.pdf(
        path=pdf_path,
        format="A4",
        margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
        print_background=True,
    )
```

**Replace with:**
```python
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        java_script_enabled=False,
        offline=True,
        bypass_csp=False,
    )
    page = context.new_page()
    page.goto(f"file://{os.path.abspath(html_path)}")
    page.pdf(
        path=pdf_path,
        format="A4",
        margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
        print_background=True,
        display_header_footer=False,
    )
```

**PDF metadata (Title / Author):** Playwright's `page.pdf()` API does **not** expose Title/Author directly — these are baked into the rendered HTML via `<title>` (already present at template line 6: `<title>QU.I.R.K. — {{ org_name }} Quantum Readiness Report</title>`) and a `<meta name="author">` tag that must be added to `report.html.j2`'s `<head>`. Override the `<title>` to the literal `"QU.I.R.K. Cryptographic Readiness Report"` for the PDF metadata path, or use Chromium DevTools `Page.printToPDF` with `documentTitle` (advanced — defer to planner).

**Cleanup at finally block** (`html_renderer.py:141-146`): existing pattern is correct; add `context.close()` before `browser.close()`.

---

### 6. AST CI gate `tests/test_safe_filter_audit.py` (NEW)

**Closest analog:** `tests/test_scan_error_gate.py` (entire file — Phase 59 LEAK-03 AST gate).

**Copy verbatim — 5-line skeleton:**
```python
"""Phase 78 / HARDEN-XX: AST CI gate that fails when a Jinja `| safe` filter
is used in templates without a paired `| sanitize` upstream, or when
quirk/reports/*.py emits raw HTML via Markup() / mark_safe() without
funneling through sanitize_scanner_text().

Mechanism: walk every .j2 in quirk/reports/templates/ AND every .py in
quirk/reports/. For .j2 files, regex-scan for `| safe` not preceded by
`| sanitize`. For .py files, AST-walk for ast.Call to Markup/mark_safe.

SAFE shapes:
  - Jinja: `{{ x | sanitize | safe }}` (filter chain ends in safe AFTER sanitize)
  - Python: ast.Call to Markup/mark_safe whose only arg is ast.Call to
    sanitize_scanner_text
"""
from __future__ import annotations
import ast
import pathlib
import re
import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET_DIRS = [PROJECT_ROOT / "quirk" / "reports"]
TEMPLATE_DIRS = [PROJECT_ROOT / "quirk" / "reports" / "templates"]
```

**Copy verbatim — predicate pattern** from `test_scan_error_gate.py:39-49`:
```python
def _is_sanitize_call(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "sanitize_scanner_text":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "sanitize_scanner_text":
        return True
    return False
```

**Copy verbatim — file-walk discovery loop** from `test_scan_error_gate.py:26-32` (PROJECT_ROOT + SCANNER_DIRS list).

**Do differently:**
- Add a Jinja-template regex pass (not in scan_error_gate): `re.compile(r"\|\s*safe\b")` matched against each `.j2` file; for each hit, assert `| sanitize` appears earlier on the same line.
- Parametrize over discovered files (mirror `test_credential_leakage.py:87`'s `@pytest.mark.parametrize("relpath", ...)` import-presence gate as a secondary check that `quirk/reports/__init__.py` exports `sanitize_scanner_text` re-exposure or that each report module imports it).

---

### 7. Regression test `tests/test_html_pdf_injection_regression.py` (NEW)

**Closest analog:** `tests/test_report_sanitization.py` (Phase 61 REPORT-SAN-02, hostile-corpus rendering test).

**Copy verbatim:**
- Module docstring shape (`test_report_sanitization.py:1-11`).
- Hostile-input construction pattern (lines 27-54): `CryptoEndpoint(host="bad.host.com|injected-col", ...)` and `finding` dict with `\n`, `\r\n`, `|`, control chars.
- `_cfg()` SimpleNamespace pattern (lines 23-24).
- `@pytest.fixture` rendering pattern (lines 57-60).

**Adapt — XSS corpus:**
```python
def _xss_endpoint():
    return CryptoEndpoint(
        host="evil.example.com",
        port=443,
        cert_subject="CN=<script>alert(1)</script>",
        cert_issuer="CN=<img src=x onerror=alert(1)>",
        # ... rest mirror _adversarial_endpoint at test_report_sanitization.py:27
    )
```

**Assertions** (replace the GFM-table-shape asserts):
- `"<script>" not in rendered_html` — must be escaped/stripped.
- `"&lt;script&gt;" in rendered_html OR rendered_html.count("script") == 0` — proves escape OR strip.
- For PDF: render via `render_pdf_report` (mock Playwright like `test_pdf_render_hardening.py:15-56`), then `pdftotext` the output and assert literal `<script>` substring absence. Defer PDF assert to integration tier if `pdftotext` unavailable.

---

### 8. `pyproject.toml` dependency addition

**Closest analog:** `pyproject.toml:11-31` (existing `[project] dependencies` block).

**Insertion site:** After line 30 (`"signxml>=4.4.0",`) add:
```toml
    "nh3>=0.2.17",
```

**Removal:** `grep -n "bleach" pyproject.toml` returns nothing — no removal needed. Add `bleach` to a "MUST NOT APPEAR" CI check if Phase 78 wants belt-and-suspenders.

**Do differently:** Keep `nh3` in core `dependencies` (not `[project.optional-dependencies]`) — every install path needs sanitization, including CLI-only users who emit Markdown that later flows through downstream HTML renderers.

---

## Shared Patterns

### Module independence rule
**Source:** `quirk/util/safe_exc.py:7-9` (docstring comment).
**Apply to:** `quirk/util/sanitize.py` — no cross-imports from other `quirk.util` modules so the helper is importable in isolation. Only `import nh3` + stdlib.

### AST predicate composition
**Source:** `tests/test_scan_error_gate.py:39-80` (`_is_safe_str_call`, `_is_literal_or_none`, `_is_attr_read`, `_name_assigned_via_safe_str`, `_is_fstring_with_safe_str`).
**Apply to:** `tests/test_safe_filter_audit.py` — rename `safe_str` → `sanitize_scanner_text`; keep the SAFE-shape taxonomy. The `JoinedStr`/f-string handler is directly applicable since `f"{x}"` in Python report code is the analog of `{{ x }}` in Jinja.

### Import-presence gate
**Source:** `tests/test_credential_leakage.py:87-91`.
**Apply to:** `test_safe_filter_audit.py` as the secondary check (after AST gate) — parametrize over `quirk/reports/*.py` and assert `from quirk.util.sanitize import sanitize_scanner_text` appears in every file that calls `template.render` or emits HTML.

---

## No Analog Found

| File | Reason |
|------|--------|
| (none) | All Phase 78 surfaces map cleanly to existing analogs. |

## Metadata

**Analog search scope:** `quirk/util/`, `quirk/reports/`, `tests/`, `pyproject.toml`, `quirk/reports/templates/`
**Files scanned:** ~40
**Key cross-references:** Phase 59 (safe_str AST gate at `test_scan_error_gate.py`), Phase 61 (md_cell at `_md_escape.py` + `test_report_sanitization.py`), Phase 73 INTEL-01 (`test_pdf_render_hardening.py` Playwright mock pattern).

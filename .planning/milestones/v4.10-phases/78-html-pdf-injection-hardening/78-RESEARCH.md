# Phase 78: HTML/PDF Injection Hardening — Research

**Researched:** 2026-05-16
**Domain:** Output sanitization for HTML/PDF/Markdown consultant deliverables
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **nh3 allowlist:** Strict text-only — `nh3.clean(s, tags=set(), attributes={})`. All HTML stripped to plain text.
- **Chokepoint:** Single `quirk/util/sanitize.py` exposing `sanitize_scanner_text(s: str) -> str`. Module docstring carries invariant contract.
- **URL handling:** URLs stripped entirely from free-text fields. Trusted template literals (target host:port) are the only URL render path.
- **Scanner-controlled surface:** Certificate CN/SAN, host names, error messages, finding titles + descriptions + recommendations, service banners.
- **Layering:** `nh3.clean()` runs at template render boundary via Jinja `| sanitize` filter, **paired with every `| safe`**. `autoescape=True` already on (verified — see code_context). Raw data stays in DB so other format consumers can re-apply policy.
- **Markdown table escape:** Extend `md_cell()` to `executive.py` and every scanner-string-in-table site. Unit test asserts `|`, `\n`, `\r`, backtick neutralization.
- **Markdown→HTML cleanup:** Run `nh3.clean()` AFTER markdown→HTML conversion (NOTE: see Risk R-1 — no markdown→HTML conversion currently exists in this codebase).
- **Playwright context:** `browser.new_context(java_script_enabled=False, offline=True, bypass_csp=False)`.
- **PDF metadata:** Title = `"QU.I.R.K. Cryptographic Readiness Report"`; Author = `"QU.I.R.K. Scanner"` (constants — never scan content).
- **Retroactive sweep:** All Finding/IdentityFinding description writers route through chokepoint.
- **AST CI gate:** Modeled on Phase 59 `safe_str` gate (`tests/test_scan_error_gate.py`). Detects `| safe` filter usages in Jinja templates lacking a paired `sanitize` filter upstream.
- **Regression test fixture:** Certificate CN = `<script>alert(1)</script>` — assert rendered output contains `&lt;script&gt;` (HTML + PDF).

### Claude's Discretion
- Concrete shape of `sanitize_scanner_text()` body.
- Touch-point enumeration & order of changes.
- AST gate implementation details (stdlib `ast` + `jinja2.Environment.parse`).
- Module-docstring contract wording.
- Naming of new CI test file (`tests/test_safe_filter_audit.py` per CONTEXT.md).

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARDEN-01 | All markdown table cells emitted in `quirk/reports/executive.py` and any remaining unguarded paths use `md_cell()` for parity with `technical.py`. | Section "Markdown emission sites (executive.py)". `md_cell()` already implemented in `quirk/reports/_md_escape.py`; `technical.py` is the reference consumer. |
| HARDEN-02 | All Jinja2 templates run with `autoescape=True`; every `\| safe` filter usage is documented AND wraps a value already sanitized through `nh3.clean()` (policy defined once in `quirk/util/sanitize.py`). | Section "Jinja env audit" — `autoescape=select_autoescape(["html","j2"])` already active in `html_renderer.py:62-65`. Zero `\| safe` usages in template today (verified by grep). Filter registration sketch below. |
| HARDEN-03 | Scanner-emitted free-text (CN/SAN, host, error msg, finding desc) sanitized before HTML/PDF render. | Section "Scanner-string emission sites" enumerates every render-boundary site. nh3 API confirmed; `sanitize_scanner_text` body in "Chokepoint" section. |
| HARDEN-04 | Playwright PDF disables JS AND uses no-network context; PDF metadata (Title/Author) from constants. | Section "Playwright PDF hardening" — `java_script_enabled`, `offline`, `bypass_csp` parameters confirmed on `browser.new_context()`. PDF title/author flow via HTML `<title>` + `<meta name="author">` (page.pdf() does NOT expose direct metadata params — Risk R-2). |
| HARDEN-05 | CI AST gate enforces no new `\| safe` without paired `nh3.clean()`. | Section "AST CI gate" — Phase 59 `tests/test_scan_error_gate.py` is the verbatim model. Jinja templates parse via `jinja2.Environment.parse()`. |
| HARDEN-06 | `nh3>=0.2.17` added as core dependency (replace `bleach` if present). | Section "pyproject.toml state" — `bleach` NOT present (verified by grep); `nh3` NOT present. Pure addition, no replacement step. nh3 current version is 0.3.5 (2026-04-25); pin `>=0.2.17` per CONTEXT. |

</phase_requirements>

## Summary

This phase wires a single sanitization chokepoint (`quirk/util/sanitize.py::sanitize_scanner_text`) into every report-rendering surface so adversary-controlled scanner output (certificate CN/SAN, hostnames, error messages, finding descriptions) cannot inject script tags, HTML, or markdown control characters into consultant-facing HTML, PDF, or `.md` deliverables.

**Three critical findings differ from CONTEXT.md assumptions and must inform planning:**

1. **No markdown→HTML conversion exists in this codebase.** `html_renderer.py` renders the HTML report **directly from a Jinja template** populated from Python dict/object data (findings list, endpoint list, score dict). The markdown files (`executive-summary-*.md`, `technical-findings-*.md`) are written as standalone `.md` artifacts; the HTML report is **not** derived from them. CONTEXT.md's "Markdown→HTML cleanup" decision (run `nh3.clean()` AFTER markdown→HTML) therefore has no current target — but the decision IS still valid as a forward guard for any future markdown→HTML path (e.g., if scorecard/roadmap markdown ever feeds the HTML report). Plan should record this as a deferred sink and add a CI assertion that no markdown→HTML library appears in deps without paired nh3 wiring. **R-1.**

2. **Playwright `page.pdf()` has no `title`/`author` parameters.** PDF metadata is sourced from the HTML document's `<title>` element and `<meta name="author">` tag. HARDEN-04 metadata enforcement is therefore a **template-side change**, not a Python-side `page.pdf()` kwargs change. **R-2.**

3. **Zero `| safe` filter usages currently exist in `report.html.j2`.** The CI gate is a forward guard (prevents new violations from landing) rather than a fixer of existing violations. This makes HARDEN-05 a pure additive gate — no remediation of existing template required.

**Primary recommendation:** Implement chokepoint first → register `sanitize` Jinja filter → extend `md_cell()` coverage to `executive.py` + endpoint-row template cells → harden Playwright context + template `<head>` metadata → land AST CI gate last (it gates future drift).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Strict text-only HTML sanitization (nh3 wrapper) | `quirk/util/` (helper) | — | Pure stateless helper; mirrors `quirk/util/safe_exc.py` / `quirk/util/weak_crypto.py` siting. |
| Jinja `\| sanitize` filter registration | `quirk/reports/html_renderer.py` (Jinja env owner) | — | Environment is constructed in `render_html_report()`; filter must be added to `env.filters` before `get_template()`. |
| Markdown table cell escaping (`md_cell`) | `quirk/reports/_md_escape.py` (existing) | `executive.py`, `technical.py`, `writer.py::_scorecard_markdown`, `writer.py::_roadmap_markdown` (callers) | Existing module, expanded caller set. |
| Playwright context hardening + PDF metadata | `quirk/reports/html_renderer.py::render_pdf_report` (context) + `templates/report.html.j2` (`<title>`/`<meta>`) | — | Browser-context flags are Python-side; PDF Title/Author come from HTML head. |
| AST CI gate | `tests/test_safe_filter_audit.py` (new) | — | Mirrors `tests/test_scan_error_gate.py` siting (Phase 59 model). |
| Dependency declaration | `pyproject.toml::[project] dependencies` | — | nh3 is core (used by every report render path), not optional. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nh3 | `>=0.2.17` (current: 0.3.5, 2026-04-25) | HTML allowlist sanitizer (Rust/Ammonia binding) | `[VERIFIED: pypi.org/project/nh3]` ~20× faster than bleach; bleach deprecated 2023 ([CITED: daniel.feldroy.com/posts/2023-06-converting-from-bleach-to-nh3]); messense/nh3 actively maintained. |
| jinja2 | `>=3.1.0` (already in deps) | Templating engine | Already used; `autoescape=True` already configured. |
| playwright | `>=1.58.0` (already in `[dashboard]` extra) | Headless Chromium PDF render | Already used; supports JS-disable + offline context. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ast` (stdlib) | — | AST walking for CI gate | Phase 59 model uses stdlib `ast` only — no external dep. |
| `pathlib` (stdlib) | — | File traversal in CI gate | Phase 59 model pattern. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nh3 | bleach | Deprecated 2023; slower; security maintenance lapsing. **Rejected by CONTEXT.md.** |
| nh3 strict allowlist | Permit `<b>`, `<i>`, `<code>` | Scanner output is identifier data, not prose — no legitimate inline markup. Strict empty allowlist is correct. |
| AST gate via libcst | stdlib `ast` | libcst preserves comments/formatting we don't need for a validation walk. Phase 59 precedent is stdlib `ast`. |

**Installation:**
```bash
# Add to pyproject.toml [project] dependencies — no install command per se
# Editable installs pick it up after `pip install -e .`
```

**Version verification:** `[VERIFIED: pypi.org/project/nh3]` current release is 0.3.5 (2026-04-25). CONTEXT.md pins `>=0.2.17` (which precedes feature-removal risk). Pin is conservative and compatible.

## nh3 API — The Exact Body of `sanitize_scanner_text`

`[VERIFIED: nh3.readthedocs.io/en/latest/, github.com/messense/nh3/blob/main/docs/index.rst]`

**Signature:**
```python
nh3.clean(
    html,
    tags=None,
    clean_content_tags=None,
    attributes=None,
    attribute_filter=None,
    strip_comments=True,
    link_rel='noopener noreferrer',
    generic_attribute_prefixes=None,
    tag_attribute_values=None,
    set_tag_attribute_values=None,
    url_schemes=None,
    allowed_classes=None,
    filter_style_properties=None,
)
```

**Strict-text-only invocation:** `nh3.clean(s, tags=set(), attributes={})` strips every tag while preserving text content. Confirmed by official docs + community examples.

**URL stripping:** There is no native `nh3` option to strip bare URL text (e.g., `https://evil.example/` appearing as plain text). `url_schemes=set()` only restricts attribute schemes on `<a href>`/`<img src>` — and since we strip all tags, those attribute hooks never run. **URL stripping for free-text fields must be implemented in `sanitize_scanner_text` itself**, not delegated to nh3. `[ASSUMED]` Use a conservative regex (`r"\bhttps?://\S+"` plus `r"\b(?:javascript|data|vbscript|file):\S+"`).

**Concrete `sanitize_scanner_text` body (recommended for planner):**

```python
"""Single source of truth for scanner-controlled string sanitization.

Strict text-only allowlist. URLs stripped. Used by every Jinja `| sanitize`
filter call and every report-side scanner-string write. Never bypass.

Phase 78 / HARDEN-02..HARDEN-03 (closes audit).
"""
from __future__ import annotations

import re
from typing import Final

import nh3

# Hostile schemes + plain URL text — stripped before nh3 (nh3 has no plain-text
# URL stripper; it only restricts attribute schemes on tags we are removing).
_URL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:https?|javascript|data|vbscript|file|ftp)://\S+",
    re.IGNORECASE,
)


def sanitize_scanner_text(value) -> str:
    """Return a sanitized plain-text rendering of scanner-controlled input.

    Pipeline:
      1. None → ""; coerce to str.
      2. Strip URL-like substrings (any scheme).
      3. nh3.clean() with empty tag + attribute allowlists.

    The output is suitable for direct interpolation into HTML (via Jinja
    autoescape) or markdown (paired with md_cell for table-cell contexts).
    """
    if value is None:
        return ""
    text = str(value)
    text = _URL_RE.sub("", text)
    return nh3.clean(text, tags=set(), attributes={})
```

**Performance note:** `[ASSUMED]` nh3 is Rust-backed; per-cell call cost is microseconds. With ~10⁴ template substitutions per large report, no measurable latency impact expected. If hot-path profiling later shows otherwise, add an LRU cache keyed by input — but do not premature-optimize.

## Scanner-String Emission Sites (Concrete Touch List)

These are every render-boundary location where a scanner-controlled string reaches a consultant-facing artifact. Planner should produce one task per cluster.

### Cluster A — Markdown table cells (HARDEN-01)

| File:Line | Current emission | Action |
|-----------|------------------|--------|
| `quirk/reports/technical.py:44` | `md_cell(e.host)`, `md_cell(_service_detail(e))` | Already wrapped. Verify only. |
| `quirk/reports/technical.py:63` | `md_cell(e.host)`, `md_cell(sv)`, `md_cell(sample)`, `md_cell(notes)` | Already wrapped. Verify only. |
| `quirk/reports/technical.py:83` | `md_cell(e.host)`, `md_cell(blocker)`, `md_cell(getattr(e,'scan_error',''))` | Already wrapped. Verify only. |
| `quirk/reports/technical.py:99` | `md_cell(host)`, `md_cell(title)`, `md_cell(desc)`, `md_cell(rec)` | Already wrapped. Verify only. |
| `quirk/reports/executive.py:169` | `f"- {d['reason']} (**-{d['points']}**)"` | Wrap `d['reason']` in `md_cell` (driver reason is internally generated but may interpolate finding titles in future — defense in depth). |
| `quirk/reports/executive.py:188` | `f"  - {category}: {count}"` | Wrap `category` (scan_error category — adversary-influenced via TLS error strings). |
| `quirk/reports/executive.py:206` | `f"- {b}"` (interp bullet) | Bullets are internally formatted strings; low-risk but wrap for parity. |
| `quirk/reports/executive.py:222` | `f"- **{item['title']}** — {item['why']}"` | Roadmap items can echo finding/host context — wrap both. |
| `quirk/reports/executive.py:224` | `f"  - Owner: {item['owner_placeholder']} \| Timeframe: {item['timeframe']}"` | Wrap both. |
| `quirk/reports/executive.py:235` | `f"- **{r.get('path')}** — {r.get('recommendation')}"` | **Primary HARDEN-01 target.** `recommendation` is scanner-derived. |
| `quirk/reports/executive.py:238` | `f"  - Target: {r.get('host')}:{r.get('port')} \| Severity: {r.get('severity')}"` | `host` is scanner-derived. Wrap. |
| `quirk/reports/writer.py:74-75` | `f"- {d}"` (driver strings) in `_scorecard_markdown` | Wrap. |
| `quirk/reports/writer.py:81` | `f"- **{a.get('title')}** — {a.get('why')}"` in `_scorecard_markdown` | Wrap. |
| `quirk/reports/writer.py:97` | `f"- **{r.get('title')}** — {r.get('why')}{dep_txt}"` in `_roadmap_markdown` | Wrap `title`, `why`, and dep components. |

**Note:** `md_cell()` is currently designed for GFM **table cells** (pipe/newline/CRLF escape). For bullet lists (`- item`) and bold-prefix bullets, an additional escape may be warranted for backtick/asterisk in the future, but CONTEXT.md explicitly defers backtick handling. Plan should re-use `md_cell()` as-is and document the deferred backtick guard.

### Cluster B — Jinja template scanner-string sites (HARDEN-02 / HARDEN-03)

`quirk/reports/templates/report.html.j2` — currently relies on `autoescape=True` only. With the new chokepoint registered as a `sanitize` filter, every scanner-controlled variable should pipe through it. Sites:

| Line | Variable | Origin |
|------|----------|--------|
| 130 | `{{ org_name }}` | Config-derived but operator-supplied → run through `sanitize` |
| 140 | `{{ org_name }}` | same |
| 141 | `{{ report_owner }}` | Config-derived → `sanitize` |
| 142 | `{{ data_classification }}` | Config-derived → `sanitize` |
| 168 | `{{ d }}` (driver string) | Internally generated but may contain finding host/title → `sanitize` |
| 180 | `{{ f.get('title','') }}` | **Scanner-controlled** → `sanitize` |
| 181 | `{{ f.get('host','') }}{% if f.get('port') %}:{{ f.get('port') }}{% endif %}` | **Scanner-controlled** → `sanitize` on host |
| 182 | `{{ f.get('description','')[:120] }}` | **Scanner-controlled** → `sanitize` |
| 196 | `{{ item.get('title','') }}` | Roadmap echo → `sanitize` |
| 197 | `{{ item.get('why','') }}` | Roadmap echo → `sanitize` |
| 217 | `{{ f.get('host','') }}`, `{{ f.get('recommendation','') }}` | **Scanner-controlled** → `sanitize` both |
| 231-235 | findings table row (title, host, port, description, recommendation) | **Scanner-controlled** → `sanitize` all string cells |
| 267-270 | compliance row (title, control, source_url) | **Mostly scanner-controlled** (title), config-trusted (control/version). `source_url` is config-derived → `sanitize` defensively |
| 294 | `{{ f.get('title','') }} ({{ f.get('host','') }})` (unmapped findings) | **Scanner-controlled** → `sanitize` |
| 308-313 | endpoint inventory row (`ep.host`, `ep.port`, `ep.protocol`, `ep.tls_version`, `ep.cipher_suite`, `ep.cert_pubkey_alg`) | **Scanner-controlled** (these are exactly the CN/SAN/version strings that motivate the phase) → `sanitize` host + protocol + tls_version + cipher_suite + cert_pubkey_alg |

**Pattern to apply:** `{{ value | sanitize }}` (with autoescape still on — sanitize is defense in depth, autoescape is baseline).

**`| safe` placement:** Per CONTEXT.md, `| safe` only goes on values that have already been sanitized. The recommended idiom is `{{ value | sanitize | safe }}` — but this is **only required when the surrounding context needs the value rendered as HTML** (e.g., embedded `<span>` formatting). Since every site above renders plain text, `{{ value | sanitize }}` alone is correct (autoescape continues to escape any remaining `<`/`>`/`&`). The AST gate enforces this: **`| safe` without an upstream `sanitize` in the same expression = violation.**

### Cluster C — Finding dict construction (data-layer)

Finding dicts are built in `quirk/engine/findings_evaluator.py` (and dashboard-side `IdentityFinding`/`DarFinding` in `quirk/dashboard/api/schemas.py`). CONTEXT.md specifies "raw scanner data stays in the DB so future report formats can re-apply policy" — i.e., **do NOT sanitize at write time**. Sanitization is a render-boundary concern. Plan should explicitly document this invariant and add a test that the DB-stored value is the raw original. **No changes to evaluator/scanner code for HARDEN-03.**

## Jinja Filter Registration Pattern

Current env construction (`quirk/reports/html_renderer.py:62-65`):

```python
env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "j2"]),
)
```

**Recommended change (single line added):**

```python
from quirk.util.sanitize import sanitize_scanner_text

env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "j2"]),
)
env.filters["sanitize"] = sanitize_scanner_text
```

`[VERIFIED: jinja.palletsprojects.com — env.filters dict]` Filters registered on `env.filters` (a dict) are available in all templates loaded from that env. This is the canonical pattern.

**Why not a global default sanitize on every variable?** CONTEXT.md decided: `autoescape=True` covers the common case (HTML metachars); nh3 on every variable is perf waste. The `| sanitize` filter is explicit at each scanner-controlled site so the AST gate has stable anchor points to enforce against.

## AST CI Gate — Concrete Sketch

**File:** `tests/test_safe_filter_audit.py` (new)
**Model:** `tests/test_scan_error_gate.py` (Phase 59, verbatim structure)

Two AST surfaces are walked:

### Surface 1 — Python files (catches misuse of `Markup`, `MarkupSafe`, manual `str.replace`-based bypasses)

```python
# Walk quirk/**/*.py for ast.Call(func.id='Markup' or func.attr='Markup').
# Any such call is a VIOLATION unless its argument is a Call to
# sanitize_scanner_text or nh3.clean. Self-test + negative test mirror Phase 59.
```

### Surface 2 — Jinja templates (catches `| safe` without paired `| sanitize`)

`jinja2.Environment.parse()` returns an AST node tree. The relevant node types:
- `jinja2.nodes.Filter` — represents a `| name(...)` filter call.
- `Filter.name` is the filter identifier (e.g., `"safe"`).
- `Filter.node` is the upstream expression (could be another `Filter`, a `Name`, a `Call`, etc.).

**Algorithm sketch:**

```python
from __future__ import annotations

import pathlib
import jinja2
import pytest
from jinja2 import nodes

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE_DIRS = [PROJECT_ROOT / "quirk" / "reports" / "templates"]


def _has_upstream_sanitize(filter_node: nodes.Filter) -> bool:
    """Walk Filter.node chain upward, returning True if any link is | sanitize."""
    cur = filter_node.node
    while isinstance(cur, nodes.Filter):
        if cur.name == "sanitize":
            return True
        cur = cur.node
    return False


def test_safe_filter_paired_with_sanitize() -> None:
    env = jinja2.Environment()
    violations: list[tuple[str, int]] = []
    for tdir in TEMPLATE_DIRS:
        for tpl in sorted(tdir.rglob("*.j2")):
            source = tpl.read_text(encoding="utf-8")
            try:
                tree = env.parse(source)
            except jinja2.TemplateSyntaxError:
                continue
            for node in tree.find_all(nodes.Filter):
                if node.name == "safe" and not _has_upstream_sanitize(node):
                    violations.append(
                        (str(tpl.relative_to(PROJECT_ROOT)), node.lineno)
                    )
    if violations:
        formatted = "\n".join(f"  {f}:{ln}" for f, ln in violations)
        pytest.fail(f"| safe usages without upstream | sanitize:\n{formatted}")


def test_gate_catches_synthetic_bypass() -> None:
    env = jinja2.Environment()
    bad = "{{ scanner_string | safe }}"  # no sanitize upstream
    tree = env.parse(bad)
    found = [
        n for n in tree.find_all(nodes.Filter)
        if n.name == "safe" and not _has_upstream_sanitize(n)
    ]
    assert len(found) == 1


def test_gate_does_not_flag_safe_patterns() -> None:
    env = jinja2.Environment()
    good = "{{ scanner_string | sanitize | safe }}"
    tree = env.parse(good)
    bad_safe = [
        n for n in tree.find_all(nodes.Filter)
        if n.name == "safe" and not _has_upstream_sanitize(n)
    ]
    assert bad_safe == []
```

`[VERIFIED: jinja.palletsprojects.com/en/stable/api/#jinja2.Environment.parse]` `Environment.parse()` returns a `nodes.Template`; `tree.find_all(NodeType)` is the canonical walker. `[ASSUMED — needs quick smoke in implementation]` `nodes.Filter.lineno` is populated for `| filter` expressions (Jinja attaches line numbers consistently to nodes; behaviour mirrors `nodes.Output.lineno`).

**Self-test discipline:** Per Phase 59 precedent (`test_gate_catches_synthetic_bypass` + `test_gate_does_not_flag_safe_patterns`), include both positive and negative gate self-tests so CI fails if the detector silently stops detecting.

**Optional Python-side gate (defense in depth):**

```python
def test_no_markup_without_sanitize() -> None:
    """Catch jinja2.Markup(scanner_string) bypasses in Python code."""
    # Walk quirk/**/*.py; flag ast.Call to Markup whose arg is not a Call to
    # sanitize_scanner_text. Pattern mirrors test_scan_error_gate.py::_classify_rhs.
```

## Playwright PDF Hardening — Exact Incantation

Current `quirk/reports/html_renderer.py:124-133`:

```python
browser = p.chromium.launch()
page = browser.new_page()
page.goto(f"file://{os.path.abspath(html_path)}")
page.pdf(path=pdf_path, format="A4", margin={...}, print_background=True)
```

**Hardened version:**

```python
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
)
context.close()
browser.close()
```

**Confirmed parameters** `[VERIFIED: playwright.dev/python/docs/api/class-browser#browser-new-context]`:
- `java_script_enabled: bool = True` → set `False`.
- `offline: bool = False` → set `True`.
- `bypass_csp: bool = False` → set `False` explicitly (already default; CONTEXT.md mandates explicit deny).

### PDF Metadata (Title / Author)

`[VERIFIED: playwright.dev/python/docs/api/class-page#page-pdf]` `page.pdf()` parameter list: `display_header_footer, footer_template, format, header_template, height, landscape, margin, outline, page_ranges, path, prefer_css_page_size, print_background, scale, tagged, width`. **No `title` or `author` parameters exist.**

**Therefore PDF Title/Author flow via the HTML document head:**

```html
<head>
  <meta charset="UTF-8">
  <title>QU.I.R.K. Cryptographic Readiness Report</title>
  <meta name="author" content="QU.I.R.K. Scanner">
  ...
</head>
```

**Current template** at `report.html.j2:6` has:
```html
<title>QU.I.R.K. — {{ org_name }} Quantum Readiness Report</title>
```

This interpolates scanner/operator-controlled `org_name` into the PDF metadata — direct HARDEN-04 violation. Replace with the constant title; add `<meta name="author">` constant.

**Caveat:** `[ASSUMED]` Chromium PDF generation reads `<title>` for the PDF `Title` metadata field. Behaviour confirmed widely in practice; not explicitly documented in Playwright API ref. Plan should include a verification task: open the generated `.pdf` and inspect metadata (`pdfinfo` or `exiftool report.pdf`).

## Markdown Library — Codebase State

**Finding:** No markdown→HTML library is imported anywhere in `quirk/reports/`. Verified by:
```bash
grep -rn "import markdown\|from markdown\|markdown_it\|mistune" quirk/reports/
# (no results)
```

`html_renderer.py` populates a Jinja template directly from Python data structures. The `.md` artifacts (executive, technical, scorecard, roadmap) are written as standalone files; they are not converted to HTML in the QUIRK pipeline.

**Implications:**
- CONTEXT.md's "Markdown→HTML cleanup: Run `nh3.clean()` AFTER markdown→HTML conversion in `html_renderer.py`" has **no current target**. There is nothing to wire.
- The decision remains valid as a **forward guard**: if a future phase adds a markdown→HTML conversion (e.g., to render the executive summary into a polished HTML email), the chokepoint must run post-conversion.
- **Recommended forward guard:** add an importable assertion in `tests/test_safe_filter_audit.py` that flags the appearance of `markdown`, `markdown-it-py`, or `mistune` in `pyproject.toml` dependencies without a corresponding test that proves output passes through `sanitize_scanner_text` post-conversion. This is a low-cost trip wire.

## pyproject.toml State

`[VERIFIED: grep quirk/Volumes/...QUIRK/pyproject.toml]`:
- `bleach` is **NOT present** anywhere in the project. HARDEN-06 "replaces bleach if present" is a no-op replace step — pure additive.
- `nh3` is **NOT present** anywhere. Pure addition.
- `jinja2>=3.1.0` already in `[project] dependencies` (line 18).
- `playwright>=1.58.0` is in `[project.optional-dependencies] dashboard` (line 38). PDF rendering already degrades gracefully when missing (`render_pdf_report` returns `False` on ImportError).

**Recommended diff:**

```toml
[project]
dependencies = [
    ...
    "jinja2>=3.1.0",
    "nh3>=0.2.17",       # Phase 78 / HARDEN-06: HTML allowlist sanitizer
    ...
]
```

nh3 is a core dep (used on every report render, not just dashboard). Do not put it in an extra.

## Jinja Env Audit (HARDEN-02 baseline)

`[VERIFIED: quirk/reports/html_renderer.py:62-65]` `autoescape=select_autoescape(["html", "j2"])` is already active for both `.html` and `.j2` template files. HARDEN-02 baseline is therefore already met for autoescape; the phase work is:

1. **Audit `| safe` usages in templates.** `[VERIFIED: grep "| safe" report.html.j2]` → **zero current usages.** AST gate is a forward guard.
2. **Register `sanitize` filter** (one-line addition above).
3. **Apply `| sanitize` at every Cluster B site.**

## Regression Test Design

**Existing fixture pattern:** `tests/test_reports_writer.py` already provides `_make_cfg(tmp_path)` and `_findings_fixture()` helpers that build a `SimpleNamespace` cfg and a list of finding dicts, then call `write_reports(cfg, endpoints, findings)` and assert on the generated artifacts on disk. This is the right host for the new regression test.

**Required new test (success criterion #1 from ROADMAP):**

```python
# tests/test_report_injection_hardening.py
"""Phase 78 / HARDEN-03 regression: scanner-controlled HTML payloads
in certificate CN must be rendered as escaped plain text in HTML + PDF."""

def test_script_payload_in_cert_cn_is_escaped(tmp_path):
    cfg = _make_cfg(tmp_path)
    endpoints = [
        SimpleNamespace(
            host="evil.example",
            port=443,
            protocol="TLS",
            tls_version="TLSv1.3",
            cipher_suite="<script>alert(1)</script>",
            cert_pubkey_alg="RSA-2048",
            scan_error=None,
        )
    ]
    findings = [{
        "severity": "HIGH",
        "host": "<script>alert(1)</script>",
        "port": 443,
        "title": "<img src=x onerror=alert(1)>",
        "description": "<script>alert('xss')</script> Vulnerable RSA cert.",
        "recommendation": "Migrate.",
    }]
    write_reports(cfg, endpoints, findings)
    html = next(tmp_path.glob("report-*.html")).read_text()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    # PDF: shell out to pdftotext or use pypdf to extract text, assert no raw <script>.
```

Also add unit tests for:
- `sanitize_scanner_text(None) == ""`
- `sanitize_scanner_text("<script>x</script>") == "x"` (tag stripped, content kept)
- `sanitize_scanner_text("click https://evil.example/path now") == "click  now"` (URL stripped)
- `sanitize_scanner_text("javascript:alert(1)") == "alert(1)"` (URL stripped, content kept)
- `md_cell` already has implicit tests via `test_reports_writer.py`; add explicit unit tests for `|`, `\n`, `\r`, `\x00..\x1f` escape.

## Risk Register

| ID | Risk | Mitigation |
|----|------|------------|
| **R-1** | CONTEXT.md mandates "Markdown→HTML cleanup" but no such conversion exists. Planner may waste a task slot wiring a non-existent integration. | Plan should explicitly mark this decision as "deferred sink" with a forward-guard test (CI assertion that prohibits adding a markdown→HTML lib without paired sanitize wiring). No production wiring this phase. |
| **R-2** | `page.pdf()` has no `title`/`author` params. HARDEN-04 metadata flow is template-side (`<title>` + `<meta name="author">`), not Python-side. | Confirmed via Playwright API ref. Plan must include a verification task using `pdfinfo` / `exiftool` to inspect the generated PDF's Title/Author fields and assert they equal the constants. |
| **R-3** | `nh3` strips bare-text URLs only because we pre-strip them via regex. nh3 does NOT inherently strip URL text. | `sanitize_scanner_text` does the URL strip explicitly via `_URL_RE.sub("", text)` before calling `nh3.clean`. Documented in the chokepoint docstring. |
| **R-4** | `md_cell` is designed for GFM table cells, but `executive.py` emits bullet lists (`- item`). Pipe escape is irrelevant; backtick is unhandled by design (CONTEXT.md defers). Reusing `md_cell` outside table contexts is mildly wrong-shaped. | Use `md_cell` for table cells; for bullet contexts, apply newline/CRLF/control-char strip only (consider a thin `md_text` wrapper later). For Phase 78, use `md_cell` everywhere and document the looseness as accepted technical debt. |
| **R-5** | `nodes.Filter.lineno` may be `0` for some Jinja parse paths. Self-test confirms by parsing a known bad fragment and asserting `lineno > 0`. | Self-test discipline (Phase 59 model) catches this immediately. |
| **R-6** | Existing `tests/test_reports_writer.py` may already pass adversarial payloads accidentally (no current escape). Phase 78 may surface regressions in those tests if they assert raw `<` characters. | Run the existing reports suite before changes to baseline; update assertions to expect escaped output. |
| **R-7** | Operator-supplied `cfg.assessment.name` / `report_owner` / `data_classification` reach the HTML head `<title>` and various body sites. These are technically not scanner-controlled, but the chokepoint is the safer policy. | CONTEXT.md scanner-string definition is narrow; plan should explicitly extend sanitization to these config-derived strings (defense in depth, single-policy boundary). The PDF `<title>` change replaces `{{ org_name }}` with a constant — independently addresses the operator-controlled-metadata vector. |
| **R-8** | Removal of `org_name` from `<title>` changes the visible browser tab title for the HTML report. UX regression risk for consultants who recognize reports by tab title. | The constant title still says "QU.I.R.K. Cryptographic Readiness Report" — clear and on-brand. Generated_at + org_name remain visible in the header bar (`report.html.j2:130`). Acceptable. |
| **R-9** | The dashboard at `quirk/dashboard/` renders findings into FastAPI responses via Pydantic schemas (`IdentityFinding`, `DarFinding`, etc.). CONTEXT.md does not list dashboard-side sites as in scope for Phase 78. | Confirm with user via planner. If dashboard scope is in: extend chokepoint coverage to API responses (FastAPI auto-serializes JSON; the browser-side dashboard is responsible for safe rendering). If out: document explicitly as a deferred sink. **Recommendation: out of scope for Phase 78 (FastAPI returns JSON, browser-side React handles escaping).** |

## File Touch List

| File | Action | Rationale |
|------|--------|-----------|
| `quirk/util/sanitize.py` | **CREATE** | New chokepoint module — `sanitize_scanner_text()` + module-docstring invariant contract. |
| `pyproject.toml` | **EDIT** | Add `nh3>=0.2.17` to `[project] dependencies`. |
| `quirk/reports/html_renderer.py` | **EDIT** | (a) Import `sanitize_scanner_text`; (b) register as `env.filters["sanitize"]`; (c) harden `render_pdf_report` to use `browser.new_context(java_script_enabled=False, offline=True, bypass_csp=False)` and route page via that context. |
| `quirk/reports/templates/report.html.j2` | **EDIT** | (a) Replace dynamic `<title>` with constant `"QU.I.R.K. Cryptographic Readiness Report"`; (b) add `<meta name="author" content="QU.I.R.K. Scanner">`; (c) apply `\| sanitize` at every Cluster B site enumerated above. |
| `quirk/reports/executive.py` | **EDIT** | Wrap scanner-controlled bullet/heading interpolations in `md_cell()` — Cluster A. |
| `quirk/reports/writer.py` | **EDIT** | Wrap scanner-controlled cells in `_scorecard_markdown()` and `_roadmap_markdown()` — Cluster A. |
| `quirk/reports/_md_escape.py` | **NO CHANGE** | Existing `md_cell()` is sufficient. Add module-level invariant comment if helpful. |
| `quirk/reports/technical.py` | **NO CHANGE** | Already fully wrapped via `md_cell()`. Add regression test that confirms it stays wrapped. |
| `tests/test_safe_filter_audit.py` | **CREATE** | AST CI gate (Jinja Filter walker) + Python-side Markup walker + self-tests. Phase 59 model. |
| `tests/test_report_injection_hardening.py` | **CREATE** | End-to-end regression: `<script>alert(1)</script>` in finding + cert fields → escaped output in HTML and PDF. |
| `tests/test_sanitize_scanner_text.py` | **CREATE** | Unit tests for chokepoint: None handling, tag strip, URL strip (all schemes), content preservation, surrogate / control-char handling. |
| `docs/report-interpretation.md` | **OPTIONAL EDIT** | Add a short paragraph on injection hardening for the consulting audience: "All scanner-observed strings pass through an allowlist sanitizer before rendering." |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (per `pyproject.toml [tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (lines 89-96) |
| Quick run command | `pytest tests/test_sanitize_scanner_text.py tests/test_safe_filter_audit.py -x` |
| Full suite command | `pytest -m 'not slow'` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| HARDEN-01 | Every markdown scanner-cell wrapped in `md_cell` | unit + AST grep | `pytest tests/test_safe_filter_audit.py -x` (Python-side walker for unwrapped `f.get('host')` in markdown files) + manual diff review | ❌ Wave 0 |
| HARDEN-02 | Jinja `\| safe` paired with `\| sanitize` | unit (AST) | `pytest tests/test_safe_filter_audit.py::test_safe_filter_paired_with_sanitize -x` | ❌ Wave 0 |
| HARDEN-03 | `<script>` in CN renders as `&lt;script&gt;` | integration | `pytest tests/test_report_injection_hardening.py -x` | ❌ Wave 0 |
| HARDEN-04 | Playwright JS disabled + PDF Title/Author constants | integration | `pytest tests/test_report_injection_hardening.py::test_pdf_metadata_constants -x` (uses `pypdf` or `pdfinfo`) | ❌ Wave 0 |
| HARDEN-05 | Self-tests confirm gate catches synthetic bypasses | unit | `pytest tests/test_safe_filter_audit.py::test_gate_catches_synthetic_bypass tests/test_safe_filter_audit.py::test_gate_does_not_flag_safe_patterns -x` | ❌ Wave 0 |
| HARDEN-06 | `nh3` importable; `bleach` not present | unit | `pytest tests/test_sanitize_scanner_text.py::test_nh3_available -x` + grep assertion | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_sanitize_scanner_text.py tests/test_safe_filter_audit.py tests/test_report_injection_hardening.py -x`
- **Per wave merge:** `pytest -m 'not slow'`
- **Phase gate:** Full suite green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_sanitize_scanner_text.py` — covers HARDEN-03, HARDEN-06
- [ ] `tests/test_safe_filter_audit.py` — covers HARDEN-02, HARDEN-05
- [ ] `tests/test_report_injection_hardening.py` — covers HARDEN-01, HARDEN-03, HARDEN-04
- [ ] (Optional) `pypdf>=4.0` as a dev/test dep if PDF metadata inspection is in-process; otherwise shell out to `pdfinfo` from poppler.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | **yes** | nh3 strict allowlist on render-boundary output |
| V6 Cryptography | no (out-of-scope — phase concerns presentation hardening) | — |
| V14 Configuration | yes | `bypass_csp=False`, `java_script_enabled=False`, `offline=True` in PDF renderer |

### Known Threat Patterns for Python + Jinja + Playwright

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `<script>` in scanner-observed field reaches HTML report | Tampering / Spoofing | nh3 strict allowlist + Jinja autoescape (defense in depth) |
| `javascript:` URL in cert CN interpolated as `<a href>` | Tampering | URL pre-strip + nh3 (no `<a>` tag allowed) |
| Pipe injection in markdown table cell (`\|` adds adversary-controlled column) | Tampering | `md_cell()` escapes `\|` to `\\|` |
| CRLF injection in markdown row (`\r\n` adds adversary-controlled row) | Tampering | `md_cell()` collapses to single space |
| Adversary-controlled PDF metadata (Title/Author) | Spoofing | Constants in HTML head, never scan content |
| JS execution during PDF render (e.g., `<script>fetch()</script>` exfiltrating local files via `file://`) | Information Disclosure | `java_script_enabled=False` + `offline=True` |
| CSP bypass enabling unintended resource loads | Tampering | `bypass_csp=False` (explicit) |
| HTML comment injection (e.g., conditional comments) | Tampering | nh3 `strip_comments=True` (default) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | URL stripping for free-text fields must be implemented in `sanitize_scanner_text` itself (nh3 has no plain-text URL stripper). | "nh3 API" | Low — verified nh3 docs; URL behaviour confined to attribute schemes which our empty tag allowlist never reaches. |
| A2 | nh3 per-call cost is microseconds; no need for caching. | "Chokepoint" | Low — easy to add LRU later if profiling shows otherwise. |
| A3 | `jinja2.nodes.Filter.lineno` is reliably populated. | "AST CI gate" | Low — self-test exercises this immediately; if `0`, fall back to template path-only reporting. |
| A4 | Chromium PDF generation reads HTML `<title>` for the PDF `Title` metadata field. | "PDF Metadata" | Medium — widely accepted behaviour but not explicitly documented in Playwright API. Mitigation: verification task using `pdfinfo` / `exiftool`. |
| A5 | Dashboard `IdentityFinding`/`DarFinding` API responses are out of scope (browser-side React handles escaping). | "R-9" | Medium — if a future export path takes the API JSON straight into a PDF, the assumption breaks. Recommend confirming with user during plan-checker. |

## Open Questions

1. **Dashboard scope — in or out?**
   - What we know: Dashboard renders findings via FastAPI + React. CONTEXT.md scope says "scanner-controlled strings reach HTML, PDF, or markdown report" — silent on JSON-API consumers.
   - What's unclear: Whether dashboard PDF/HTML export paths (if any) need the same chokepoint.
   - Recommendation: Plan-checker should ask user. **Default: out of scope for Phase 78.**

2. **`md_cell` for bullet contexts — accept reuse, or split?**
   - What we know: `md_cell` is GFM-table-shaped (pipe/newline focus). Executive bullet emissions are not table cells.
   - What's unclear: Whether the reuse is acceptable technical debt or merits a `md_text` sibling helper.
   - Recommendation: Reuse `md_cell` for Phase 78 (per CONTEXT.md); document as debt; revisit if v4.10 phases add bullet-specific escape needs.

3. **PDF metadata verification — in-process or shell-out?**
   - What we know: Need to assert PDF Title=`"QU.I.R.K. Cryptographic Readiness Report"`, Author=`"QU.I.R.K. Scanner"`.
   - What's unclear: Whether to add `pypdf` as a dev dep or shell out to `pdfinfo`.
   - Recommendation: Prefer `pypdf` (in-process, deterministic, no system dep). Cost: one dev-only line in pyproject.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `bleach` | `nh3` (Rust/Ammonia binding) | 2023 — bleach deprecation announcement, daniel.feldroy migration write-up | ~20× faster, actively maintained, same allowlist semantics |
| Hand-rolled HTML escape (`html.escape`) for templates | Jinja2 `autoescape=True` | Long-standing | Eliminates per-variable manual escape mistakes; Phase 78 adds nh3 as defense in depth on scanner-controlled fields |
| Permissive Jinja env (autoescape off + manual `\|e`) | `select_autoescape(["html","j2"])` | Already in this codebase | Baseline already met — Phase 78 adds explicit `\| sanitize` for scanner-controlled vars |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: nh3.readthedocs.io] — nh3.clean() signature, parameters, strict-empty pattern, current version 0.3.5 (2026-04-25)
- [VERIFIED: playwright.dev/python/docs/api/class-browser#browser-new-context] — `java_script_enabled`, `offline`, `bypass_csp` confirmed
- [VERIFIED: playwright.dev/python/docs/api/class-page#page-pdf] — `page.pdf()` parameter list (no title/author params)
- [VERIFIED: jinja.palletsprojects.com] — `Environment.parse()`, `nodes.Filter`, `env.filters` dict
- [VERIFIED: codebase] — `tests/test_scan_error_gate.py` (Phase 59 AST gate model)
- [VERIFIED: codebase] — `quirk/reports/html_renderer.py:62-65` (autoescape already on)
- [VERIFIED: codebase grep] — `bleach` NOT present, `nh3` NOT present, no markdown→HTML library

### Secondary (MEDIUM confidence)
- [CITED: daniel.feldroy.com/posts/2023-06-converting-from-bleach-to-nh3] — bleach→nh3 migration rationale
- [CITED: adamj.eu/tech/2023/12/13/django-sanitize-incoming-html-nh3] — practical nh3 usage examples
- [CITED: github.com/marksweb/django-nh3] — community integration patterns

### Tertiary (LOW confidence)
- [ASSUMED] Chromium PDF Title field maps to HTML `<title>` — mitigated by verification task using pypdf/pdfinfo
- [ASSUMED] `nodes.Filter.lineno` is reliably populated — mitigated by gate self-test

## Metadata

**Confidence breakdown:**
- nh3 API + chokepoint shape: **HIGH** — official docs + multiple community references
- Scanner-string emission site enumeration: **HIGH** — direct codebase grep, line-numbered
- Jinja filter registration: **HIGH** — canonical Jinja API
- AST gate sketch: **HIGH (Python)** + **MEDIUM (Jinja Filter.lineno)** — Phase 59 model is verbatim; Jinja node line-attr behaviour validated by self-test
- Playwright context: **HIGH** — official API ref
- PDF metadata flow: **MEDIUM** — Playwright provides no direct kwarg; HTML head is the de facto channel
- Markdown→HTML library state: **HIGH (current)** + flagged as forward-guard concern

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (30 days — nh3 is stable, Playwright API is stable)

# Phase 78: HTML/PDF Injection Hardening - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Every scanner-controlled string that reaches an HTML, PDF, or markdown report passes
through a documented sanitization chokepoint — no raw scanner output can inject script
tags, HTML entities, or markdown control characters into consultant deliverables.

Wave A — gates downstream scanner template additions in Phases 79–81.

</domain>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 78 success criteria (HARDEN-01 … HARDEN-06)
- `.planning/REQUIREMENTS.md` — full HARDEN-01…06 requirement text
- `.planning/research/SUMMARY.md` — v4.10 research synthesis (nh3 vs bleach rationale)
- `quirk/reports/_md_escape.py` — existing `md_cell()` implementation (pipe/newline/control-char escape)
- `quirk/reports/technical.py` — current `md_cell()` consumer (template for executive.py rollout)
- `quirk/reports/executive.py` — unguarded markdown emission site (HARDEN-01 target)
- `quirk/reports/templates/report.html.j2` — Jinja2 template; needs `autoescape=True` audit
- `quirk/reports/html_renderer.py` — markdown→HTML conversion path; post-clean injection site
- `quirk/reports/writer.py` — Playwright PDF entry point; HARDEN-04 metadata + no-JS/no-network site
- Phase 59 — `safe_str` AST gate (model for HARDEN-05 `| safe` CI grep gate)

</canonical_refs>

<decisions>
## Implementation Decisions

### Area 1 — nh3 Sanitization Policy
- **Allowlist breadth:** Strict text-only. nh3 invoked with `tags=set()`, `attributes={}` — all HTML stripped to plain text. Scanner output is identifier data (CNs, hosts, error messages), never user-authored prose.
- **Policy location:** Single chokepoint at `quirk/util/sanitize.py` exposed as `sanitize_scanner_text(s: str) -> str` (HARDEN-02 mandates "allowlist policy defined once").
- **URL handling:** Strip URLs entirely from free-text fields. URLs only render through known-safe template variables (target host:port) — prevents `javascript:` / `data:` URI injection.
- **Chokepoint surface (what counts as scanner-controlled):** Certificate CN/SAN, host names, error messages, finding titles + descriptions + recommendations, service banners. Template literals and numeric scores are trusted.

### Area 2 — Sanitization Layering Strategy
- **When `nh3.clean()` runs:** At template render boundary via a Jinja `| sanitize` filter, paired with `| safe` on each documented site. Raw scanner data stays in the DB so future report formats can re-apply policy.
- **Markdown injection prevention:** Extend `md_cell()` to every scanner-string-in-table site across all markdown emitters (including `executive.py` per HARDEN-01). Unit test asserts `|`, `\n`, `\r`, backtick all escape.
- **HTML escape baseline:** `autoescape=True` on the Jinja env + `| sanitize` only where `| safe` is intentionally used. nh3 on every variable would be perf waste when autoescape covers the common case.
- **Markdown→HTML cleanup:** Run `nh3.clean()` AFTER markdown→HTML conversion in `html_renderer.py`. Markdown allows raw HTML by spec, so post-clean is the only reliable sink.

### Area 3 — PDF Metadata & Error-Message Surface
- **PDF `<title>` constant:** `"QU.I.R.K. Cryptographic Readiness Report"` (matches existing CLI branding and `quirk init` voice).
- **PDF Author constant:** `"QU.I.R.K. Scanner"` (tool attribution, never operator/tenant name).
- **Playwright context:** `browser.new_context(java_script_enabled=False, offline=True, bypass_csp=False)` — explicit deny on JS, network, and CSP bypass.
- **Retroactive sweep:** Yes. Sweep all `IdentityFinding`/`Finding` description writers and confirm they flow through the new chokepoint. Add a regression test for `<script>alert(1)</script>` in a certificate CN rendering as `&lt;script&gt;alert(1)&lt;/script&gt;` in both HTML and PDF outputs (success criterion #1).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/reports/_md_escape.py::md_cell()` — pipe/newline/CRLF/control-char escape; battle-tested in technical.py
- `quirk/reports/technical.py` rows 44, 63, 83, 99 — reference pattern for md_cell wrapping all scanner-controlled cells
- Jinja2 env already present in `html_renderer.py` (audit needed for `autoescape` flag)
- Phase 59 `safe_str` AST gate — model for HARDEN-05 `| safe` CI gate

### Established Patterns
- Centralized helpers under `quirk/util/` (e.g., `weak_crypto.py`) — `sanitize.py` joins this pattern
- AST-based CI gates already proven in Phase 59 (credential leakage) and `tests/test_audit_ledger_zero_open.py`
- Module headers carrying invariant docstrings (Phase 80 ADCS-09 style) — applies here for the chokepoint contract

### Integration Points
- `quirk/reports/executive.py` — primary new caller for md_cell
- `quirk/reports/templates/report.html.j2` — autoescape audit + sanitize filter registration
- `quirk/reports/html_renderer.py` — Jinja env registration site for `sanitize` filter; markdown→HTML post-clean
- `quirk/reports/writer.py` — Playwright launch site; metadata constants live here
- `pyproject.toml::[project] dependencies` — add `nh3>=0.2.17`; remove `bleach` if present
- New CI gate file: `tests/test_safe_filter_audit.py` (mirrors `tests/test_safe_str_*` pattern from Phase 59)

</code_context>

<specifics>
## Specific Ideas

- The chokepoint contract belongs in the module docstring of `quirk/util/sanitize.py`:
  "Single source of truth for scanner-controlled string sanitization. Strict text-only
  allowlist. URLs stripped. Used by every Jinja `| sanitize` filter call. Never bypass."
- Regression test fixture: a synthetic ScanSession with a certificate whose CN is
  `CN=<script>alert(1)</script>` — assert rendered output contains `&lt;script&gt;` not
  `<script>` in both HTML and PDF outputs (success criterion #1 verbatim).
- The `| safe` AST gate looks for `Filter(name="safe")` nodes in Jinja templates and
  requires a paired `sanitize` filter upstream in the same expression chain.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

# Stack Research

**Domain:** Report composition/templating/branding additions on top of an existing
`ReportContent` → three-renderer (CLI-rich / HTML+Playwright-PDF / DOCX) reporting pipeline
**Researched:** 2026-09-11
**Confidence:** HIGH (all recommendations verified directly against installed versions and
live source in this repo; no unverified training-data claims below)

## Scope note (read this first)

This research is scoped to what the v5.23 milestone actually commits to: **999.105 Tier 1**
(template/branding overrides) plus opportunistic **Tier 2** (named section-composition
profiles) if the 999.101 NOW/NEXT/LATER re-frame touches the same code anyway. **Tier 3 (a
full per-section templating engine across all three surfaces, including DOCX templating) is
explicitly NOT in scope for this milestone** — `999.105-customizable-reporting-engine/IDEA.md`
marks it `UNKNOWN / L (milestone-sized)` and requires its own spike before scoping. This file
therefore recommends **zero new runtime dependencies** for the committed scope, and documents
`docxtpl` only as a Tier-3 "if you ever get there" alternative with an explicit security
caveat — not a Tier-1/2 recommendation.

## Recommended Stack

### Core Technologies (already in the stack — verified, zero new dependency needed)

| Technology | Version (installed) | Purpose | Why Recommended |
|------------|---------------------|---------|-----------------|
| Jinja2 | 3.1.6 (pyproject pins `>=3.1.0`) | HTML report templating | Already the HTML renderer's engine — `quirk/reports/html_renderer.py:9` imports `Environment, FileSystemLoader, select_autoescape`; `_TEMPLATES_DIR` at line 135 points `FileSystemLoader` at `quirk/reports/templates/`. Tier 1's "custom HTML template dir" requirement is a **loader change, not a new dependency**: swap/extend `FileSystemLoader(_TEMPLATES_DIR)` (line 1005) for a `ChoiceLoader([FileSystemLoader(operator_dir), FileSystemLoader(_TEMPLATES_DIR)])` so an operator-supplied directory is tried first and the stock template is the fallback. `select_autoescape(["html", "j2"])` (line 1006) already autoescapes interpolated values — keep this ON for any operator-supplied template too (see Pitfalls). |
| python-docx | 1.2.0 available / pyproject pins `>=1.1.0` (optional `[docx]` extra) | DOCX report rendering | `docx_renderer.py` is imperative (no templating layer) but python-docx's own `Document.styles` object is sufficient for Tier 1 branding: a `styles["Heading 1"].font.color.rgb` / `.name` override, or loading an operator-supplied `.docx` as the base `Document(template_path)` instead of `Document()`, gives color/font/logo branding without a new templating dependency. This is the same "template as a Word file, populate via python-docx API" pattern many consulting tools use before reaching for `docxtpl`. |
| Playwright | 1.60.0 available / pyproject pins `>=1.58.0` (optional) | Headless-Chromium HTML→PDF export | No change needed. PDF branding/theming is entirely inherited from whatever the HTML template renders — Tier 1's branding tokens flow through the same `report.html.j2` → PDF path with zero renderer-specific work. |
| rich | >=13.0.0 | CLI report rendering | No templating concept exists here and none is needed for Tier 1 — CLI output is markdown/table text; "branding" for this surface is limited to the `report_owner`/text tokens already threaded through `_scorecard_markdown()` / `build_tech_markdown()` (`writer.py`). Do not introduce a templating library for the CLI surface. |

### Supporting Libraries — NEW additions needed for Tier 1/2 (schema/config only, no packages)

| Addition | Type | Purpose | When to Use |
|----------|------|---------|-------------|
| `report.template_dir` (new `str \| None` config field) | Config schema | Points `FileSystemLoader`/`ChoiceLoader` at an operator directory of override `.html.j2` files (and optionally a base `.docx` for python-docx branding) | Tier 1. Mirrors the existing `assessment.logo_path` precedent (`quirk/config.py:24`) — same "optional path to local file, `None` default" shape. |
| `report.branding` (new sub-table: `primary_color`, `footer_text`, `cover_subtitle`, etc.) | Config schema | Token-level branding values threaded into the Jinja2 context (HTML/PDF) and into `docx_renderer.py`'s style/paragraph calls (DOCX), and interpolated as plain text into the CLI markdown builders | Tier 1. No new dependency — these are just new fields on the existing `ExecContent`/Jinja context dict and new keyword args on `render_docx_report`/`_scorecard_markdown`. |
| `report.section_profile` (new `str`, e.g. `"executive" \| "technical" \| "full"`) enum config field | Config schema | Selects/orders which `ExecContent` sections each renderer emits | Tier 2 only (opportunistic, gated on 999.101 touching this code). Requires refactoring each renderer's hardcoded section order into a small ordered-list-of-section-keys the renderer iterates — no library, a structural change to `writer.py`/`html_renderer.py`/`docx_renderer.py`/`technical.py`. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `jsonschema` (already a dependency, `cyclonedx-python-lib[json-validation]`) | N/A for this feature | Not needed for report config validation — QUIRK already validates config via its own dataclass/YAML loader (`quirk/config.py`), so new `report.*` fields follow that existing pattern, not a new schema library. |
| Existing parity test suite (`tests/test_key_reuse_render_parity.py`, `test_report_render_parity.py`, `test_cross_surface_parity.py`) | Regression guard | These assert **field presence** across CLI/HTML/DOCX. Any Tier 2 section-profile work must either (a) scope these tests per-profile (e.g. only run full-presence assertions against `section_profile: full`) or (b) add a parallel presence assertion for partial profiles. This is a real design decision flagged in the IDEA.md and is not solved by any library choice. |

## Installation

No new runtime dependency installation is required for Tier 1 or the opportunistic Tier 2 fold-in. All work is:

```bash
# Nothing new to install — Jinja2, python-docx, Playwright, rich already present.
# Confirm current pins if touching pyproject.toml:
pip show jinja2 python-docx playwright rich
```

If a future Tier 3 phase is spiked and approved (explicitly out of this milestone):

```bash
# Tier 3 ONLY — do not add for this milestone
pip install "docxtpl>=0.20,<0.21"   # pulls python-docx + jinja2 as transitive deps
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Extend existing Jinja2 `Environment`/`FileSystemLoader` with an operator template-dir override | New dedicated templating framework (Mako, Chameleon, Django templates standalone) | Never for this project — would mean maintaining two templating engines side by side for zero functional gain; Jinja2 already does everything Tier 1/2 needs and is a hard dependency already. |
| python-docx `Document(template_path)` + `styles` API for DOCX branding (Tier 1) | `docxtpl` (Jinja2-in-docx templating) | Only if/when a genuine Tier 3 "full engine" phase is scoped and spiked, per the IDEA.md's own gating (`UNKNOWN / L`, spike required). `docxtpl` adds real value only once operators need free-form section/loop templating *inside* the Word document itself — Tier 1's fixed-structure + branding tokens don't need it. |
| Config-driven `section_profile` enum + ordered section list (Tier 2) | A general-purpose plugin/rule engine for section selection | Overkill for 3-5 named profiles (executive/technical/full); a plugin engine is unjustified complexity for a closed, small enumeration operators pick from a dropdown/config value. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `docxtpl` (or any Jinja2-in-DOCX templating) for Tier 1 or Tier 2 | Out of scope per IDEA.md's own gating; also a security-sensitive addition — rendering **operator-supplied** Jinja2 templates in-process is a well-documented SSTI/RCE risk class even the library's own docs flag ("reserve Jinja2 templates for trusted sources only"; sandbox escapes have a public CVE history, e.g. the `\|attr` filter SSTI bypass). Adding this dependency without a threat model would reopen exactly the kind of "new security surface, deferred by decision" pattern this project already applied to Tier 4 config-file editing (999.104). | Defer to a dedicated Tier 3 phase with its own threat model, matching how Tier 4 config editing was deferred. |
| A raw, un-autoescaped Jinja2 `Environment` for operator-supplied HTML templates | `select_autoescape` is already correctly enabled at `html_renderer.py:1006` for the STOCK template; if the loader is widened to also accept an operator-authored template directory, autoescape must stay on for the SAME environment instance — a second, separately-constructed `Environment` without autoescape for "the custom path" would silently reopen XSS in the client-facing HTML/PDF deliverable. | Reuse the single `Environment(..., autoescape=select_autoescape(["html","j2"]))` object with a `ChoiceLoader`, never a second unescaped `Environment`. |
| Treating `report.template_dir` like `assessment.logo_path` for path-traversal purposes without re-deriving the guard | `logo_path` is explicitly called out in this project's own review history as a path-traversal-sensitive surface (`_load_logo_b64` already has a size guard at `html_renderer.py:142-165`, but no path-containment check is visible in the excerpt reviewed). A new `report.template_dir` is a DIRECTORY an operator points Jinja2's loader at — if that path is ever accepted from an untrusted/remote source (e.g. a future dashboard-driven config-upload flow, not just local CLI config.yaml), path traversal and arbitrary-template-read/inclusion become live risks the CLI-only threat model may not have considered. | Scope `report.template_dir` (like `logo_path`) to **local CLI config.yaml only**, never a server-writable/dashboard-uploadable field, until a real path-containment review happens — same reasoning that kept Tier 4 config-file editing out of 999.104. |
| Adding a JSON-schema validation library for the new `report.*` config keys | QUIRK already validates its config surface through hand-written dataclasses in `quirk/config.py`, not a schema library; introducing one for a handful of new fields is inconsistent with the rest of the codebase and unnecessary weight. | Add `report.template_dir`, `report.branding.*`, `report.section_profile` as typed dataclass fields following the exact pattern of `assessment.logo_path`/`assessment.report_owner`. |

## Stack Patterns by Variant

**If Tier 1 only (this milestone's committed floor):**
- Add `report.template_dir` + `report.branding` config fields (dataclass, mirrors `logo_path`).
- Widen the existing HTML Jinja2 `Environment`'s loader to a `ChoiceLoader([operator_dir, stock_dir])`, autoescape unchanged.
- Thread `branding` tokens into `render_docx_report`'s existing style-setting calls and into the CLI markdown builders' string interpolation.
- Zero new dependencies, zero new security review needed beyond the path-scoping note above.

**If Tier 2 is opportunistically folded in (gated on 999.101 touching migration_planner/roadmap code anyway):**
- Add `report.section_profile` enum field.
- Refactor `write_reports()` and each renderer to iterate an ordered list of section keys drawn from `ExecContent` rather than emitting sections inline in fixed order.
- Explicitly re-scope (not skip) the three cross-surface parity tests to apply their presence assertions per-profile.
- Still zero new dependencies.

**If a future milestone scopes Tier 3 (explicitly NOT this milestone):**
- Spike `docxtpl` against a real client-style Word template first, behind an operator-trust boundary (local file only, never uploaded/remote).
- Treat any operator-supplied Jinja2 template execution as requiring `jinja2.sandbox.SandboxedEnvironment` at minimum, documented as defense-in-depth only (per current CVE history on the sandbox's `|attr` filter), not a complete mitigation — the safer default remains "local files only, no remote/multi-tenant path."

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| jinja2 3.1.6 | python-docx 1.2.0, playwright 1.60.0 | No interaction; independent renderers already coexist in this codebase today. |
| docxtpl 0.20.x (Tier 3 only, not installed) | python-docx (bundled as a transitive dep), jinja2 (bundled as a transitive dep) | `docxtpl` vendors/depends on both existing dependencies directly — no version conflict expected if ever adopted, per its PyPI metadata. |

## Sources

- Direct source read: `quirk/reports/html_renderer.py` (Jinja2 `Environment`/`FileSystemLoader`/`select_autoescape` at lines 9, 133-135, 1004-1006; logo loader `_load_logo_b64` at 142-165) — HIGH confidence, verified in this repo.
- Direct source read: `quirk/reports/docx_renderer.py` (imperative python-docx renderer, module docstring D-09..D-12) — HIGH confidence.
- Direct source read: `quirk/reports/writer.py` (single `write_reports()` orchestration entrypoint, `categorize_waves()` at line 293, `build_phased_roadmap` import at line 20) — HIGH confidence.
- Direct source read: `quirk/config.py:22-24` (`report_owner`, `logo_path` precedent for new config fields) — HIGH confidence.
- `pip index versions` / `pip show` against the active environment (jinja2 3.1.6, python-docx 1.2.0 available, playwright 1.60.0 available) — HIGH confidence, verified 2026-09-11.
- `.planning/backlog/999.105-customizable-reporting-engine/IDEA.md` — feasibility tiering (Tier 1 CONFIRMED S-M, Tier 2 LIKELY M, Tier 3 UNKNOWN L) — HIGH confidence, project source of truth for scope.
- [docxtpl PyPI](https://pypi.org/project/docxtpl/) — version 0.20.2, dependency on python-docx + Jinja2 — MEDIUM confidence (WebSearch, cross-checked against docxtpl's own readthedocs description of its two dependencies).
- [Secure Templating with Jinja2: SSTI and Sandbox Environment](https://techtonics.medium.com/secure-templating-with-jinja2-understanding-ssti-and-jinja2-sandbox-environment-b956edd60456) — sandbox escape risk framing — MEDIUM confidence (WebSearch, community source, consistent with Jinja2's own documented sandbox caveats).
- [CVE-2025-27516 / Jinja2 sandbox `|attr` filter SSTI](https://security.snyk.io/vuln/SNYK-PYTHON-JINJA2-9292516) — concrete evidence that Jinja2 sandbox escapes are a real, recurring CVE class, not theoretical — MEDIUM confidence (WebSearch, vulnerability database).

---
*Stack research for: QU.I.R.K. v5.23 Deliverable Experience — customizable reporting engine (999.105 Tier 1/2)*
*Researched: 2026-09-11*

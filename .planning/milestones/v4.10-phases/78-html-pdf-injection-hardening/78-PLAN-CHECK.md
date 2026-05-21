# Phase 78 — Plan Check

**Checked:** 2026-05-16
**Plans verified:** 78-01 … 78-05
**Methodology:** Goal-backward verification against ROADMAP Phase 78 success criteria + HARDEN-01..06 + CONTEXT/RESEARCH deltas.

---

## Dimension 1 — Coverage

**Verdict: PASS**

Every HARDEN requirement and every ROADMAP success criterion maps to at least one plan task.

| Req / Criterion | Covering Plan(s) | Task(s) | Evidence |
|---|---|---|---|
| HARDEN-01 (md_cell parity in executive.py + unguarded paths) | 78-03 | T1, T2, T3 | Plan 03 wraps Cluster A sites in `executive.py` (lines 169/188/206/222/224/235/238) + `writer.py::_scorecard_markdown` + `_roadmap_markdown` + adds `test_md_cell_escape.py`. |
| HARDEN-02 (autoescape + `\| safe` paired with nh3) | 78-02 (full); 78-05 (gate) | 78-02 T1+T2; 78-05 T1 | Plan 02 registers `sanitize` filter; Plan 05 lands AST CI gate enforcing pairing. |
| HARDEN-03 (free-text sanitized) | 78-01 (chokepoint); 78-02 (HTML); 78-03 (markdown); 78-05 (regression) | All | Chokepoint → Jinja `\| sanitize` at every Cluster B site → md_cell at every Cluster A site → end-to-end XSS regression in HTML+PDF. |
| HARDEN-04 (Playwright JS-off + no-network + metadata constants) | 78-02 (template); 78-04 (Python) | 78-02 T2; 78-04 T2+T3 | Template constant `<title>` + `<meta name="author">` (Plan 02). Playwright `new_context(java_script_enabled=False, offline=True, bypass_csp=False)` + pypdf verification (Plan 04). |
| HARDEN-05 (AST CI gate) | 78-05 | T1 | `test_safe_filter_audit.py` with positive + negative self-tests + Jinja walker. |
| HARDEN-06 (nh3>=0.2.17 core dep, no bleach) | 78-01 | T1 + T3 (`test_no_bleach_in_deps`) | Direct pyproject edit + unit test belt-and-suspenders + 78-05 redundant CI assertion. |
| ROADMAP #1 (script-in-CN escaped in HTML+PDF) | 78-05 | T2 | `test_script_payload_in_cert_cn_is_escaped_in_html` + `_in_pdf`. |
| ROADMAP #2 (autoescape on, paired `\| safe`) | 78-02 + 78-05 | T1, T2, T1 | Filter registration + AST gate. |
| ROADMAP #3 (CI `\| safe` AST gate) | 78-05 | T1 | Six tests including self-tests. |
| ROADMAP #4 (Playwright no-JS + no-net + constant metadata) | 78-04 | T2 + T3 | Context lock + pypdf metadata assertion + JS-disabled invariant smoke. |
| ROADMAP #5 (nh3>=0.2.17 in pyproject) | 78-01 | T1 | Direct edit + `tomllib` parse verify. |

Every HARDEN ID appears in at least one plan's `requirements` frontmatter (cross-checked).

---

## Dimension 2 — Context Compliance (D-NN supremacy over CONTEXT.md where they conflict)

**Verdict: PASS**

The three RESEARCH deltas are honored explicitly in plan bodies — they are not silently dropped.

| Delta | What it overrides | Honored in plan(s) | Evidence |
|---|---|---|---|
| **D-78-R1** (markdown→HTML is a non-existent target — forward guard only) | CONTEXT Area 2 "Run nh3.clean() AFTER markdown→HTML conversion in html_renderer.py" | 78-05 T1 | Plan 05 T1 `test_no_markdown_to_html_lib_in_deps` walks pyproject and fails CI if any markdown→HTML lib lands without paired sanitize wiring. No active markdown→HTML cleanup code is written (correct — there is no target). Plan 05 objective explicitly cites D-78-R1. |
| **D-78-R2** (PDF metadata is template-side `<title>` + `<meta name="author">`, NOT Playwright kwargs) | CONTEXT Area 3 implies Python-side metadata setting | 78-02 T2 (template constants); 78-04 T2 + T3 (truths: "page.pdf() is called WITHOUT any title/author kwargs") | Plan 02 replaces dynamic `<title>` with constant + adds author meta. Plan 04 explicitly forbids title/author kwargs on `page.pdf()` and verifies via pypdf. Both plans cite D-78-R2 by name. |
| **D-78-R3** (Playwright launch is `html_renderer.py::render_pdf_report`, NOT `writer.py`) | CONTEXT Area 3 implies writer.py and PATTERNS §5 calls it out as a drift flag | 78-04 (entire plan) | Plan 04 `files_modified` is `quirk/reports/html_renderer.py` — not `writer.py`. Objective explicitly cites D-78-R3. PATTERNS-flagged drift is correctly resolved. |

No plan task contradicts a locked decision. No deferred-idea scope creep (CONTEXT deferred list is empty).

---

## Dimension 3 — Atomicity

**Verdict: PASS**

Each plan produces one logically-coherent commit (Plan 05 produces two — production tests, then docs/UAT — by design and labeled as such).

| Plan | Commit subject | Atomic? |
|---|---|---|
| 78-01 | `feat(78): add nh3 chokepoint sanitize_scanner_text + unit tests (HARDEN-06)` | Yes — chokepoint + dep + unit tests are one unit. |
| 78-02 | `feat(78): register sanitize Jinja filter + constant PDF title/author + sanitize-pipe Cluster B sites (HARDEN-02, HARDEN-04 template portion)` | Yes — single Jinja/template wiring unit. |
| 78-03 | `feat(78): wrap Cluster A markdown cells in md_cell across executive.py + writer.py + escape unit tests (HARDEN-01, HARDEN-03 markdown portion)` | Yes — Cluster A rollout + escape tests. |
| 78-04 | `feat(78): lock Playwright PDF context (JS-off + offline + no CSP bypass) + pypdf metadata verification (HARDEN-04 Python portion)` | Yes — Python-side Playwright hardening + pypdf test. |
| 78-05 | (a) `test(78): add AST CI gate + end-to-end XSS regression + markdown→HTML forward guard`; (b) `docs(phase-78): update UAT-SERIES.md` | Two atomic commits by design (CLAUDE.md mandates separate UAT commit). |

No plan smuggles unrelated changes. Plan 04 includes a `pyproject.toml` edit (pypdf dev-dep) bundled with the Playwright hardening — acceptable because pypdf only exists to verify the metadata Plan 04 itself locks down. Plan 03 includes `tests/test_md_cell_escape.py` — naturally co-located with the md_cell rollout.

---

## Dimension 4 — Wave Correctness

**Verdict: PASS**

Read each `files_modified` and `depends_on` independently:

| Plan | Wave | depends_on | files_modified |
|---|---|---|---|
| 78-01 | 1 | [] | `pyproject.toml`, `quirk/util/sanitize.py`, `tests/test_sanitize_scanner_text.py` |
| 78-02 | 2 | [78-01] | `quirk/reports/html_renderer.py`, `quirk/reports/templates/report.html.j2` |
| 78-03 | 2 | [78-01] | `quirk/reports/executive.py`, `quirk/reports/writer.py`, `tests/test_md_cell_escape.py` |
| 78-04 | 3 | [78-02] | `quirk/reports/html_renderer.py`, `tests/test_pdf_metadata_constants.py`, `pyproject.toml` |
| 78-05 | 4 | [78-02, 78-03, 78-04] | `tests/test_safe_filter_audit.py`, `tests/test_report_injection_hardening.py`, `docs/UAT-SERIES.md` |

- **Plan 02 vs Plan 03 (both wave 2):** Disjoint file sets — `html_renderer.py` + `report.html.j2` vs `executive.py` + `writer.py` + `test_md_cell_escape.py`. Safe to parallelize. ✓
- **Plan 04 after Plan 02:** Both modify `html_renderer.py` — Plan 04's `depends_on: [78-02]` enforces serialization. ✓
- **Plan 04 vs Plan 01 (`pyproject.toml`):** Plan 04 is wave 3, Plan 01 is wave 1, transitively serialized via 78-02 → 78-01. ✓
- **No cycles, no forward references, no missing references.** ✓
- Plan 05 correctly depends on all three predecessors because the regression test exercises HTML (Plan 02), markdown (Plan 03), and PDF (Plan 04) paths.

---

## Dimension 5 — Executability

**Verdict: PASS** (with one minor WARN)

Every task carries concrete files, action steps, automated verify commands, and done criteria. Line numbers are cited from RESEARCH where applicable (executive.py 169/188/206/222/224/235/238; report.html.j2 130/140/141/142/168/180/181/182/196/197/217/231-235/267-270/294/308-313). Verify commands are runnable as written.

**WARN (non-blocking):** Plan 03 Task 1 asks the executor to "Read `_md_escape.py` first to determine the actual contract, encode tests against reality." This delegates a small design call (backtick: escape vs passthrough) to the executor. This is acceptable because (a) CONTEXT.md explicitly defers backtick policy, (b) the plan instructs the executor to document the discrepancy in SUMMARY, and (c) R-4 in RESEARCH names this as accepted technical debt. No blocker.

**WARN (non-blocking):** Plan 03 Task 3 step 3 says "if `dep_txt` is constructed from scanner-derived strings, wrap those components individually." This is a soft branch — the executor must inspect `writer.py:97` to make the call. Acceptable but tightens executability slightly; recommend the planner pre-inspects on revision if a tightening pass is otherwise needed.

---

## Dimension 6 — CLAUDE.md Compliance

**Verdict: PASS**

Plan 05 explicitly contains the four mandatory phase-completion steps from `CLAUDE.md`:

1. **Obsidian phase note (Task 6):** Writes directly to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-78-HTML-PDF-Injection-Hardening.md` via the Write tool (NOT via `obsidian CLI content=`, correctly avoiding the shell-expansion limit). Frontmatter shape matches the project template. ✓
2. **UAT-SERIES.md update (Task 4):** Updates last-updated date and adds HARDEN-01..06 cases. ✓
3. **Sync UAT-SERIES.md to vault (Task 5):** Uses `printf + cat + cp` pattern from CLAUDE.md verbatim. ✓
4. **Commit UAT-SERIES.md (Task 5):** Uses `gsd-tools.cjs commit "docs(phase-78): update UAT-SERIES.md"` matching the CLAUDE.md template. ✓

Plan 05 also references `@CLAUDE.md` in its `<context>` block. PEP-8 / `python -m compileall` invocations are present in every code-touching plan's verify step per CLAUDE.md "Code Standards."

---

## Dimension 7 — Test Discipline

**Verdict: PASS**

Every plan touching code adds or modifies at least one test:

| Plan | Code touched? | Test added/modified | Notes |
|---|---|---|---|
| 78-01 | Yes (`sanitize.py`) | `tests/test_sanitize_scanner_text.py` (NEW) — 12+ cases | None/coerce/tag-strip/six URL schemes/idempotency/nh3-available/no-bleach. |
| 78-02 | Yes (renderer + template) | Re-runs `tests/test_reports_writer.py` + `tests/test_report_sanitization.py` (regression sweep); no new test file — but Plan 05 lands the dedicated XSS regression. | Acceptable: Plan 02 verifies template parses + existing suite stays green; the user-observable assertion (script-in-CN → escaped) lives in Plan 05's regression test that exercises this exact code path. |
| 78-03 | Yes (executive.py + writer.py) | `tests/test_md_cell_escape.py` (NEW) | pipe/newline/CRLF/control-char/None/int/backtick. |
| 78-04 | Yes (renderer Playwright path) | `tests/test_pdf_metadata_constants.py` (NEW) | pypdf-based Title/Author + JS-disabled invariant smoke. |
| 78-05 | No production code, only tests | `tests/test_safe_filter_audit.py` + `tests/test_report_injection_hardening.py` (both NEW) | AST gate + end-to-end XSS regression closes ROADMAP success criterion #1. |

**ROADMAP success criterion #1** (script-in-CN escaped in HTML+PDF) is materialized in Plan 05 Task 2 (`test_script_payload_in_cert_cn_is_escaped_in_html` + `_in_pdf`). ✓

---

## Overall Verdict: **PASS** — Executor may proceed.

### Summary

All seven dimensions pass. Two non-blocking warnings flagged in Dimension 5 (Plan 03 contains two soft branches that delegate small inspection decisions to the executor). These do not require revision — they are bounded by the executor's instruction to record findings in SUMMARY and they sit within CONTEXT.md's accepted-debt envelope (R-4, backtick deferral).

### Strengths worth noting

- The three RESEARCH deltas (D-78-R1/R2/R3) are surfaced verbatim in plan objectives and `must_haves.truths` — not lost in the translation from RESEARCH to PLAN. This is the planner-context-precedence pattern from MEMORY working correctly.
- Plan 05 builds the regression test that closes the literal ROADMAP success criterion #1 (`<script>alert(1)</script>` in CN → `&lt;script&gt;...&lt;/script&gt;` in BOTH HTML and PDF), not just one render target.
- Forward guards (markdown→HTML lib gate, `Markup()` walker, `bleach`-not-in-deps assertion) are correctly scoped as CI-only and explained as future-drift prevention.
- Wave 2 parallelization (Plans 02 + 03) is genuinely safe — disjoint file sets verified by direct reading.
- pypdf is correctly placed in an optional extra (not core dep) — runtime PDF render does not need to read PDFs back.

### Optional (NOT required) polish suggestions

These are not revision requests; they are notes the planner may incorporate on a future pass without blocking execution:

- **Plan 03 Task 3:** Pre-inspect `writer.py:97` and pin whether `dep_txt` is scanner-derived (removes the soft branch). One-line tightening.
- **Plan 02 Task 2:** The grep-based verify `[ "$(grep -c '| sanitize' ...)" -ge 18 ]` counts substrings, not Jinja filter calls; a Jinja `tree.find_all(nodes.Filter)` count would be stricter. Acceptable as-is because Plan 05's AST gate covers the strict check; this is a belt-and-suspenders smoke.
- **Plan 04 Task 2 step 4:** The `if 'context' in locals()` guard is reasonable but a `try/finally` with `context: Optional[BrowserContext] = None` initialization upfront is cleaner. Style only.

### Files referenced (absolute paths)

- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/78-html-pdf-injection-hardening/78-CONTEXT.md`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/78-html-pdf-injection-hardening/78-RESEARCH.md`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/78-html-pdf-injection-hardening/78-PATTERNS.md`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/78-html-pdf-injection-hardening/78-01-PLAN.md` … `78-05-PLAN.md`
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/ROADMAP.md` (Phase 78 §1509-1526)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/REQUIREMENTS.md` (HARDEN-01..06 §20-25)

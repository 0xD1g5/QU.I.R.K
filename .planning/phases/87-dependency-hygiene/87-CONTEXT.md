# Phase 87: Dependency Hygiene - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Deadline-driven CI + dependency cleanup, sequenced first in v5.0. Two independent, parallel-safe plans:

1. **Node bump (DEP-01):** raise the GitHub Actions Node runtime from 20 to 24 (deprecation default-switch 2026-06-16, hard removal 2026-09-16).
2. **lxml/XXE migration (DEP-02):** remove `defusedxml` and route all XML parsing through a single hardened `lxml` chokepoint (`quirk/util/xml_safe.py`).

In scope: the two changes above + a forward-locking XXE regression test. Out of scope: any other dependency upgrades, scanner behavior changes, or new XML features.

</domain>

<decisions>
## Implementation Decisions

### Node Runtime Bump (DEP-01)
- **D-01:** Minimal scope — change `node-version: '20'` → `'24'` in `.github/workflows/dashboard-quality.yml` only. Keep `actions/setup-node@v4` (it already supports Node 24). Do NOT bump the action major to v6 or audit third-party actions' bundled Node in this phase — smallest diff that clears the deadline, lowest churn risk.
- **D-02:** Verification = a **real GitHub Actions run** on a branch. "Done" for Plan 1 means the `dashboard-quality` workflow actually executes on Node 24 and goes green — local validation alone is insufficient (success criterion #1 is "CI green on Node 24"). Push a branch to trigger the workflow.

### XML Parser Hardening (DEP-02)
- **D-03:** `defusedxml` is removed from `pyproject.toml:30` (nothing replaces it; `lxml>=6.0` already a core dep at line 28). Both consumers re-route through the new chokepoint: `quirk/discovery/nmap_parser.py:6` (currently `defusedxml.ElementTree`) and `quirk/scanner/saml_scanner.py:17` (defusedxml fallback branch — delete it; lxml is already the primary path there).
- **D-04:** `quirk/util/xml_safe.py` exposes a **factory function** `make_safe_parser()` returning a *fresh* hardened `lxml.etree.XMLParser` per call — NOT a shared module-level constant. Rationale: lxml parser objects are not thread-safe, and the SSH/SAML scanners run threaded; a shared parser would be a latent concurrency bug. Hardening flags: `resolve_entities=False`, `no_network=True`, `load_dtd=False`, `dtd_validation=False`, `huge_tree=False`.
- **D-05:** Module also exposes a thin **`parse_safely(source)` convenience helper** alongside the factory, so call sites have one obvious, hard-to-misuse entry point (callers can't forget to pass the parser).
- **D-06:** `nmap_parser.py` migrates via **lxml.etree compatibility** — use `lxml.etree` with the factory parser and keep the existing ElementTree-style navigation (`findall`/`get`/etc., which lxml supports near-identically). Smallest behavioral change; re-test against the existing nmap XML fixtures. No full rewrite to lxml-native xpath idioms.

### XXE Regression Protection (DEP-02)
- **D-07:** Add a billion-laughs / XXE pytest that asserts the malicious payload **raises rather than expands or fetches**, wired as a **permanent forward-locking CI invariant** (consistent with the project's existing AST/staleness-gate culture, e.g. `tests/test_audit_ledger_zero_open.py`). A future re-introduction of an unsafe parser must fail CI.

### Audit Traceability (DEP-02)
- **D-08:** `nmap_parser.py:5` documents the parser as the mitigation for **audit finding WR-06** (XXE/billion-laughs on nmap output), and the repo enforces a zero-open-ledger gate. Treat this as a **controlled mitigation swap**: update the WR-06 comment to cite the new `xml_safe` chokepoint, and add an explicit acceptance check that WR-06 stays mitigated and `tests/test_audit_ledger_zero_open.py` stays green.

### Execution Shape
- **D-09:** Plan 1 (Node) and Plan 2 (lxml) are **parallel-safe** — disjoint files (workflow YAML vs Python) — with **independent atomic commits**, so a CI failure in one never blocks the other (matches the roadmap rationale for the two-plan split).

### Claude's Discretion
- Exact test file name/location for the XXE invariant (follow existing `tests/` naming conventions).
- Whether `parse_safely` wraps `fromstring` + `parse` or just one (planner's call based on actual call-site needs).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research (this milestone)
- `.planning/research/SUMMARY.md` — v5.0 synthesis; Phase 87 dependency-hygiene findings (Node date correction, single-file Node pin, defusedxml→lxml exact targets)
- `.planning/research/STACK.md` — lxml XXE API surface, Node 24 action versions, "what NOT to add" table
- `.planning/research/ARCHITECTURE.md` — defusedxml scope (exactly 2 files), Node single-file pin, integration points
- `.planning/research/PITFALLS.md` — lxml XXE footguns (load_dtd/huge_tree traps), shared-parser thread-safety, Node deadline reality

### Code targets
- `.github/workflows/dashboard-quality.yml` §lines 20,22 — `setup-node@v4`, `node-version: '20'` (the only Node pin)
- `quirk/discovery/nmap_parser.py` §lines 5-6 — defusedxml import + WR-06 mitigation comment
- `quirk/scanner/saml_scanner.py` §lines 17-23 — defusedxml fallback branch (lxml is primary)
- `pyproject.toml` §lines 28,30 — `lxml>=6.0` (keep), `defusedxml>=0.7.1` (remove)

### Audit / invariant context
- `tests/test_audit_ledger_zero_open.py` — zero-open-ledger CI gate; WR-06 must stay mitigated
- `CLAUDE.md` §"Code Standards" — PEP 8, minimal diffs, run `python -m compileall` + tests after changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/util/` already holds shared utilities (`optional_extra`, `targets`) — `quirk/util/xml_safe.py` is the consistent home for the new chokepoint.
- `saml_scanner.py` already uses the correct lxml hardened-parser pattern on its primary path (Phase 52 DEBT-04) — the factory can mirror/replace it.

### Established Patterns
- Forward-locking CI invariants (AST gates, staleness gates, `test_audit_ledger_zero_open.py`) are the project's idiom for preventing regression — the XXE test follows this pattern (D-07).
- Single-source-of-truth chokepoints (e.g., `_build_finding`, `safe_str`) — `xml_safe` is the XML-parsing analog.

### Integration Points
- `nmap_parser.py` and `saml_scanner.py` are the only two import sites; both switch to `xml_safe` (D-03/D-06).
- `dashboard-quality.yml` is the only CI consumer of the Node runtime (D-01).

</code_context>

<specifics>
## Specific Ideas

- Hardened parser flags are explicit and audit-reviewer-legible (the 5-flag set), even where lxml ≥6 defaults already match — so a reviewer can see XXE protection at the call site.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Broader dependency audits, setup-node major bump, and third-party action Node audits were explicitly scoped OUT per D-01.)

</deferred>

---

*Phase: 87-Dependency Hygiene*
*Context gathered: 2026-05-22*

# Phase 87: Dependency Hygiene - Research

**Researched:** 2026-05-22
**Domain:** GitHub Actions CI runtime upgrade + Python XML parser hardening
**Confidence:** HIGH — all findings verified against live codebase and official milestone research

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Node Runtime Bump (DEP-01)**
- **D-01:** Minimal scope — change `node-version: '20'` → `'24'` in `.github/workflows/dashboard-quality.yml` only. Keep `actions/setup-node@v4` (it already supports Node 24). Do NOT bump the action major to v6 or audit third-party actions' bundled Node in this phase.
- **D-02:** Verification = a **real GitHub Actions run** on a branch. "Done" for Plan 1 means the `dashboard-quality` workflow actually executes on Node 24 and goes green — local validation alone is insufficient. Push a branch to trigger the workflow.

**XML Parser Hardening (DEP-02)**
- **D-03:** `defusedxml` is removed from `pyproject.toml:30` (nothing replaces it; `lxml>=6.0` already a core dep at line 28). Both consumers re-route through the new chokepoint: `quirk/discovery/nmap_parser.py:6` (currently `defusedxml.ElementTree`) and `quirk/scanner/saml_scanner.py:17` (defusedxml fallback branch — delete it; lxml is already the primary path there).
- **D-04:** `quirk/util/xml_safe.py` exposes a **factory function** `make_safe_parser()` returning a *fresh* hardened `lxml.etree.XMLParser` per call — NOT a shared module-level constant. Rationale: lxml parser objects are not thread-safe, and the SSH/SAML scanners run threaded; a shared parser would be a latent concurrency bug. Hardening flags: `resolve_entities=False`, `no_network=True`, `load_dtd=False`, `dtd_validation=False`, `huge_tree=False`.
- **D-05:** Module also exposes a thin **`parse_safely(source)` convenience helper** alongside the factory, so call sites have one obvious, hard-to-misuse entry point (callers can't forget to pass the parser).
- **D-06:** `nmap_parser.py` migrates via **lxml.etree compatibility** — use `lxml.etree` with the factory parser and keep the existing ElementTree-style navigation (`findall`/`get`/etc., which lxml supports near-identically). Smallest behavioral change; re-test against the existing nmap XML fixtures. No full rewrite to lxml-native xpath idioms.

**XXE Regression Protection (DEP-02)**
- **D-07:** Add a billion-laughs / XXE pytest that asserts the malicious payload **raises rather than expands or fetches**, wired as a **permanent forward-locking CI invariant** (consistent with the project's existing AST/staleness-gate culture). A future re-introduction of an unsafe parser must fail CI.

**Audit Traceability (DEP-02)**
- **D-08:** `nmap_parser.py:5` documents the parser as the mitigation for **audit finding WR-06** (XXE/billion-laughs on nmap output). Update the WR-06 comment to cite the new `xml_safe` chokepoint, and the repo enforces a zero-open-ledger gate. WR-06 must stay mitigated and `tests/test_audit_ledger_zero_open.py` stays green.

**Execution Shape**
- **D-09:** Plan 1 (Node) and Plan 2 (lxml) are **parallel-safe** — disjoint files (workflow YAML vs Python) — with **independent atomic commits**, so a CI failure in one never blocks the other.

### Claude's Discretion
- Exact test file name/location for the XXE invariant (follow existing `tests/` naming conventions).
- Whether `parse_safely` wraps `fromstring` + `parse` or just one (planner's call based on actual call-site needs).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Broader dependency audits, setup-node major bump, and third-party action Node audits were explicitly scoped OUT per D-01.)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEP-01 | `.github/workflows/dashboard-quality.yml` bumps `node-version` from `20` to `24`; dashboard-quality CI job passes green on a real run. | Single-line change confirmed at line 22; `actions/setup-node@v4` already supports Node 24; deadline June 16, 2026. |
| DEP-02 | `defusedxml` removed from `pyproject.toml`. A shared `quirk/util/xml_safe.py` exposes a hardened lxml parser; `nmap_parser.py` and `saml_scanner.py` both use it (saml_scanner's defusedxml fallback removed). A billion-laughs / XXE pytest asserts the payload raises. | Two import sites confirmed; `lxml>=6.0` is already a core dep; factory pattern required for thread safety; three blocking tests need replacement/update. |
</phase_requirements>

---

## Summary

Phase 87 closes two deadline-adjacent dependency risks in two parallel plans. Plan 1 is a single-line CI change; Plan 2 is a narrow Python refactor affecting exactly four files plus tests.

**Plan 1 (Node):** The only Node version pin in the repo is `node-version: '20'` in `.github/workflows/dashboard-quality.yml` line 22. One edit. The `release-container.yml` and `release.yml` workflows have no Node step. Verification requires an actual GHA run because local execution cannot confirm runner Node behavior. Deadline: June 16, 2026 (GitHub default-switch from Node 20 to 24).

**Plan 2 (lxml/XXE):** Two import sites in `quirk/` currently reference `defusedxml`. The new `quirk/util/xml_safe.py` becomes the single hardened entry point exposing `make_safe_parser()` (factory, returns a fresh parser per call — thread-safe) and `parse_safely()` (convenience). `nmap_parser.py` migrates from `defusedxml.ElementTree` to `lxml.etree` via the factory; `saml_scanner.py` drops its defusedxml fallback branch (lxml is already its primary path). Three existing test functions that assert defusedxml is present must be replaced with lxml-native equivalents. The WR-06 comment in nmap_parser.py updates to cite the new chokepoint.

**Primary recommendation:** Implement both plans as independent atomic commits on a feature branch. Merge Plan 1 first so the Node deadline is cleared immediately; Plan 2 follows in the same branch. One GHA push suffices to validate both.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Node runtime for dashboard CI | CI/CD layer (GitHub Actions) | — | Node 24 runs dashboard quality checks (npm build + lint + a11y); no application-tier change |
| XML parser hardening | Python library layer (`quirk/util/`) | Scanner consumers | Chokepoint pattern — scanners delegate to shared utility, not direct library calls |
| XXE/billion-laughs regression gate | Test suite (pytest CI) | — | Forward-locking CI invariant; scanner code is the implementation, test is the enforcement |
| Audit WR-06 mitigation traceability | Source comment + audit ledger | Test assertion | Comment in nmap_parser.py + `test_audit_ledger_zero_open.py` CI gate |

---

## Standard Stack

### Core (no changes — existing deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `lxml` | `>=6.0` (latest 6.1.1, 2026-05-18) | XML parsing with hardened XMLParser | Already mandatory core dep; replaces defusedxml as the XXE control layer [VERIFIED: codebase + official docs] |
| `actions/setup-node` | `@v4` | Install specified Node version in GHA | v4 already in use; supports `node-version: '24'` without upgrade [VERIFIED: .github/workflows/dashboard-quality.yml] |

### Removed

| Package | Removed from | Why |
|---------|-------------|-----|
| `defusedxml>=0.7.1` | `pyproject.toml` core deps | Last release 2021 (0.7.1); `lxml>=6.0` with explicit flags provides stronger, auditable XXE control [VERIFIED: codebase] |

### What NOT to add or change

| Avoid | Why |
|-------|-----|
| `actions/setup-node@v6` | Not required to clear the June 16 deadline; `@v4` with `node-version: '24'` is sufficient |
| `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` workaround | Runner env workaround, not a project fix; change `node-version` instead |
| Module-level `_SAFE_XML_PARSER` constant (shared instance) | lxml XMLParser is not thread-safe; factory function per D-04 |
| `defusedxml.lxml` submodule | Thin wrapper around the same lxml flags; eliminated with the migration |

---

## Package Legitimacy Audit

No new packages are installed in this phase. `defusedxml` is removed; `lxml` is already a verified core dependency.

| Package | Change | Disposition |
|---------|--------|-------------|
| `defusedxml>=0.7.1` | REMOVED from core deps | Removal approved — superseded by lxml hardening |
| `lxml>=6.0` | Existing core dep, no version change | Approved — already in `pyproject.toml` |

**Packages removed due to slopcheck [SLOP] verdict:** none
**New packages flagged:** none (zero new installs)

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │   GitHub Actions             │
                    │   dashboard-quality.yml      │
                    │   node-version: '24'  (NEW)  │──► npm ci / build / lint / a11y
                    └─────────────────────────────┘

              XML parsing data flow (after Phase 87):

nmap_parser.py           saml_scanner.py
      │                        │
      └──────────┬─────────────┘
                 ▼
      quirk/util/xml_safe.py          (NEW chokepoint)
        make_safe_parser()  ──────► lxml.etree.XMLParser(
        parse_safely()               resolve_entities=False,
                                     no_network=True,
                                     load_dtd=False,
                                     dtd_validation=False,
                                     huge_tree=False,
                                   )
                 │
                 ▼
        lxml.etree tree / element
        (API-compatible with stdlib ElementTree at findall/get/text level)
```

### Recommended Project Structure

```
quirk/
├── util/
│   ├── xml_safe.py      ← NEW: make_safe_parser(), parse_safely()
│   ├── optional_extra.py
│   ├── targets.py
│   └── ...
├── discovery/
│   └── nmap_parser.py   ← MODIFIED: defusedxml → lxml via xml_safe
└── scanner/
    └── saml_scanner.py  ← MODIFIED: remove defusedxml fallback branch (lines 16-23)

tests/
└── test_nmap_hardening.py  ← MODIFIED: replace defusedxml-specific assertions
                               with lxml-native assertions + billion-laughs test
```

### Pattern 1: Factory Function (thread-safe parser creation)

**What:** `make_safe_parser()` returns a fresh `lxml.etree.XMLParser` per call. Each call site gets its own parser instance.

**When to use:** Whenever a scanner (possibly running in a thread via `_wrapped_phase`) needs to parse XML.

**Why NOT a module-level constant:** lxml XMLParser objects carry internal state; reuse across threads causes data races. The factory pattern guarantees thread safety without a lock.

**Example:**
```python
# quirk/util/xml_safe.py
# Source: D-04 (CONTEXT.md) + lxml thread-safety documentation

from lxml import etree


def make_safe_parser() -> etree.XMLParser:
    """Return a fresh hardened lxml XMLParser.

    Callers MUST use this factory (not a shared constant) because lxml
    XMLParser objects are not thread-safe.  All five flags are explicit so
    audit reviewers can verify XXE protection at a glance.
    """
    return etree.XMLParser(
        resolve_entities=False,   # block XXE entity expansion (primary control)
        no_network=True,          # block SSRF via external DTD/entity URIs
        load_dtd=False,           # prevent DTD loading (filesystem + network vectors)
        dtd_validation=False,     # prevent DTD-triggered fetches during validation
        huge_tree=False,          # keep memory/depth limits active
    )


def parse_safely(source):
    """Convenience wrapper: parse XML from a path or file-like object safely.

    Returns an lxml._ElementTree.  Callers that need fromstring() should call
    make_safe_parser() directly and pass the result to etree.fromstring().
    """
    return etree.parse(source, parser=make_safe_parser())
```

### Pattern 2: nmap_parser.py Migration

**What:** Replace `defusedxml.ElementTree` with `lxml.etree` using the factory.

**Compatibility note:** `lxml.etree._ElementTree` supports all the navigation patterns used in `nmap_parser.py` (`findall`, `getroot`, `.get`, `.find`) — no caller changes required. [VERIFIED: codebase inspection of nmap_parser.py; no type annotations reference ET.Element directly]

**Example:**
```python
# quirk/discovery/nmap_parser.py  (AFTER migration)
# Source: D-06 (CONTEXT.md) + D-08 audit traceability requirement

from lxml import etree as _lxml_etree
from quirk.util.xml_safe import make_safe_parser

# WR-06 mitigation: XML parsed via quirk/util/xml_safe.py hardened lxml parser
# (resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
# huge_tree=False).  Replaces defusedxml per Phase 87 DEP-02.
# DO NOT replace make_safe_parser() with a shared parser constant — see D-04.


def parse_nmap_xml(xml_path: str) -> list:
    tree = _lxml_etree.parse(xml_path, parser=make_safe_parser())
    root = tree.getroot()
    # ... rest of function unchanged
```

### Pattern 3: saml_scanner.py Cleanup

**What:** Remove lines 16-23 (the defusedxml fallback branch). Keep only the `try: import lxml.etree as ET` primary path and replace with an import from `xml_safe`.

**Rationale:** `lxml>=6.0` is a mandatory core dep; its absence means a broken install, not a scenario that warrants a downgrade to an unsafe stdlib parser. Per D-03, raising `ImportError` on missing lxml is the correct behavior.

**Key detail:** The existing `_safe_ET_fromstring` in saml_scanner.py creates a new XMLParser per call via `ET.XMLParser(...)` — this is the correct thread-safe pattern and is exactly what D-04 mandates for the shared factory. After migration, `_safe_ET_fromstring` can delegate to `make_safe_parser()`.

### Anti-Patterns to Avoid

- **Shared XMLParser constant:** `_SAFE_PARSER = etree.XMLParser(...)` at module scope — lxml parsers are not thread-safe; use the factory.
- **Omitting `load_dtd=False`:** Even with `resolve_entities=False`, loading a DTD enables internal entity expansion (billion-laughs). Both flags must be present. [VERIFIED: lxml parsing docs + PITFALLS.md]
- **Omitting `huge_tree=False`:** Removes lxml's depth/size limits. The nmap output is bounded but the defence-in-depth matters for the SAML metadata path.
- **`iterparse()` without explicit parser:** `lxml.etree.iterparse(f)` does not inherit XMLParser options. Any future streaming parse must pass `make_safe_parser()` explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML entity expansion blocking | Custom pre-parse string filter | `lxml.etree.XMLParser` with the 5-flag set | String filters miss binary-encoded entities, namespace tricks, and parameter entities; lxml's parser-level controls are the correct interception point |
| Thread-safe parser sharing | `threading.local()` pool | Factory function per call | Simpler, no pool management, no leak risk; lxml is fast enough that per-call instantiation has no measurable overhead at QUIRK's parse volume |

---

## Runtime State Inventory

> Not applicable — this is a greenfield addition (new chokepoint file) plus mechanical rewrites of two existing files. No rename/migration, no stored data involved.

**Nothing found in any category** — verified by phase scope review. No Mem0/n8n/SQLite state is affected. No OS-registered tasks. No SOPS keys. No build artifacts that persist the defusedxml dep post-removal (pip re-install will drop it).

---

## Common Pitfalls

### Pitfall 1: Three existing tests assert defusedxml is present — they will fail after migration

**What goes wrong:** Running `pytest` after Plan 2 changes without updating tests produces three failures:
1. `tests/test_nmap_hardening.py::test_nmap_parser_uses_defusedxml` — asserts `nmap_parser.ET.__name__.startswith("defusedxml")`
2. `tests/test_nmap_hardening.py::test_nmap_parser_blocks_xxe` — imports `defusedxml.common.EntitiesForbidden` (no longer installed)
3. `tests/test_packaging.py::test_defusedxml_in_core_deps` — asserts `"defusedxml"` in `pyproject.toml` core deps section

**Why it happens:** These tests were forward-locking gates for the Phase 71 WR-06 mitigation (defusedxml adoption). After migration, the mitigation mechanism changes but the protection must continue.

**How to avoid:** Update all three in the same plan as the source changes:
- `test_nmap_parser_uses_defusedxml` → replace with a test that `make_safe_parser()` is a callable and `parse_nmap_xml` succeeds on a valid fixture
- `test_nmap_parser_blocks_xxe` → rewrite as the D-07 billion-laughs invariant (see Validation Architecture below) using `lxml.etree.XMLSyntaxError` instead of `defusedxml.common.EntitiesForbidden`
- `test_defusedxml_in_core_deps` → replace with a test asserting `"defusedxml"` is NOT in core deps and `"lxml"` IS

**Warning signs:** Any CI run in the plan that touches pyproject.toml before updating these tests.

### Pitfall 2: test_identity_infra.py asserts defusedxml in [identity] group

**What goes wrong:** `tests/test_identity_infra.py:240` asserts `'"defusedxml>=0.7.1"'` is present in the `[identity]` extras group. If the Phase 87 removal only touches core deps and not this test, CI breaks after the change.

**Why it happens:** Phase 71 D-07 required defusedxml in the `[identity]` group as a belt-and-suspenders measure. After Phase 87, defusedxml is entirely removed.

**How to avoid:** Inspect `pyproject.toml` to confirm whether defusedxml appears in both core deps AND `[identity]`. [VERIFIED: pyproject.toml inspection — defusedxml is at line 30 in core deps only; `[identity]` group does NOT separately list defusedxml]. However, `test_identity_infra.py:240` still references it — this test must be updated to remove the defusedxml assertion.

**Warning signs:** `tests/test_identity_infra.py` failure in CI after pyproject.toml edit.

### Pitfall 3: lxml parser thread-safety — shared constant forbidden

**What goes wrong:** If the planner implements `xml_safe.py` with a module-level `_SAFE_PARSER = etree.XMLParser(...)` constant (matching the pattern shown in STACK.md and PITFALLS.md), SAML scanner threaded execution risks data corruption. The SAML and SSH scanners run in threads via `_wrapped_phase()`.

**Why it happens:** STACK.md's code examples show a `_SAFE_PARSER` module-level constant for illustration. D-04 explicitly mandates a factory function instead.

**How to avoid:** The `xml_safe.py` module MUST expose `make_safe_parser()` returning a fresh parser per call. The CONTEXT.md D-04 decision explicitly overrides any code example from STACK.md or PITFALLS.md that shows a shared constant. [CITED: 87-CONTEXT.md D-04]

**Warning signs:** Any `xml_safe.py` that has a `_SAFE_PARSER = ...` module-level assignment.

### Pitfall 4: WR-06 audit entry must stay `[x] closed` after migration

**What goes wrong:** If the plan updates the source comment but fails to verify `tests/test_audit_ledger_zero_open.py` still passes, the audit ledger could be left in an inconsistent state.

**Why it happens:** The WR-06 entry in `AUDIT-TASKS.md` currently cites defusedxml as the mitigation mechanism. The comment in nmap_parser.py references `defusedxml per audit WR-06`. After migration, the comment must be updated to cite `xml_safe` chokepoint, but the audit ledger entry in AUDIT-TASKS.md references the test names. Those tests still exist (renamed/rewritten) so the ledger stays valid.

**How to avoid:** After updating `nmap_parser.py`'s comment, verify `python -m pytest tests/test_audit_ledger_zero_open.py -v` passes. The ledger entry says `[x] closed` and the mitigation mechanism change does not re-open it — only adding a new unfixed finding would. No change to `AUDIT-TASKS.md` is needed.

### Pitfall 5: `parse_safely()` call-site coverage — both `ET.parse()` (nmap) and `ET.fromstring()` (saml) are used

**What goes wrong:** If `parse_safely()` only wraps `etree.parse()` (file path source), `saml_scanner.py`'s `_safe_ET_fromstring(xml_bytes)` call site cannot use it and must call `make_safe_parser()` directly.

**Why it happens:** nmap_parser uses `ET.parse(xml_path)` (file path); saml_scanner uses `ET.fromstring(xml_bytes, parser=...)` (byte string). These are different lxml entry points.

**How to avoid:** D-05 says `parse_safely` is a "convenience helper" — the planner must decide at implementation time whether it wraps `parse` only (nmap consumer), `fromstring` only (saml consumer), or both. Given the two actual call sites, the cleanest design is: `parse_safely(source)` wraps `etree.parse()` for nmap; saml_scanner continues calling `make_safe_parser()` directly inside its `_safe_ET_fromstring`. This is Claude's discretion per CONTEXT.md.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### Existing saml_scanner.py safe parser pattern (lines 5-12) — this is the model

```python
# Source: quirk/scanner/saml_scanner.py:5-12 [VERIFIED: live codebase]
try:
    import lxml.etree as ET
    def _safe_ET_fromstring(xml_bytes):
        # Phase 52 DEBT-04: raw lxml.etree parser with security flags.
        # resolve_entities=False blocks XXE; no_network=True blocks SSRF.
        return ET.fromstring(
            xml_bytes,
            parser=ET.XMLParser(resolve_entities=False, no_network=True),
        )
    LXML_AVAILABLE = True
```

Note: This pattern creates a new XMLParser per call already — it is thread-safe. The Phase 87 factory formalization makes this pattern explicit and canonical.

### lxml XMLParser 5-flag hardening (authoritative flag set per D-04)

```python
# Source: CONTEXT.md D-04 + lxml.de/parsing.html [CITED: lxml official docs]
etree.XMLParser(
    resolve_entities=False,   # PRIMARY: blocks XXE entity expansion
    no_network=True,          # blocks SSRF via DTD/entity URIs
    load_dtd=False,           # prevents DTD loading (default False — explicit for audit)
    dtd_validation=False,     # prevents DTD-triggered fetches (default False — explicit)
    huge_tree=False,          # keeps memory/depth limits active (default False — explicit)
)
```

### Billion-laughs test target payload

```python
# Canonical billion-laughs XML payload for the D-07 forward-locking test
# Source: defusedxml project README (well-known test vector) [ASSUMED — standard security test]
BILLION_LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<root>&lol4;</root>"""
```

Expected behaviour with hardened parser: `lxml.etree.XMLSyntaxError` (entity expansion blocked). Note: with the 5-flag set (`resolve_entities=False`, `load_dtd=False`), lxml refuses to process the DTD entity declarations entirely — the exception is raised before any expansion begins.

### XXE external entity payload

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>
```

Expected behaviour: `lxml.etree.XMLSyntaxError` — external entity reference blocked by `resolve_entities=False` and `no_network=True`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `defusedxml.ElementTree` for XXE-safe XML | `lxml.etree.XMLParser` with explicit security flags | Phase 87 (this phase) | Stronger — lxml's XMLParser flags block network access and DTD loading in addition to entity expansion; defusedxml patched only entity expansion at the stdlib level |
| Per-call inline `XMLParser(...)` construction | `make_safe_parser()` factory in shared `quirk/util/xml_safe.py` | Phase 87 | Single chokepoint ensures flag consistency; audit reviewers find all XML security decisions in one file |
| defusedxml as explicit XXE signal in import | lxml flags as XXE signal in `xml_safe.py` | Phase 87 | More legible for audit reviewers — the 5 flags are visible at the control point |

**Deprecated/outdated:**
- `defusedxml.ElementTree`: superseded — the lxml XMLParser approach provides a superset of defusedxml's entity-expansion protection while adding network blocking and DTD controls. The defusedxml project has had no substantive release since 2021.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Billion-laughs payload raises `lxml.etree.XMLSyntaxError` (not hangs) with the 5-flag set | Code Examples | If lxml silently ignores the entity (unlikely given the flags), the test would falsely pass — low risk given lxml 6.x behaviour |
| A2 | `test_identity_infra.py:240` asserts defusedxml in `[identity]` extras group | Common Pitfalls | If the assertion targets core deps instead of identity, the fix target differs — plan must inspect the actual assertion |

---

## Open Questions

1. **`parse_safely()` signature — wraps `parse` or `fromstring` or both?**
   - What we know: nmap_parser uses `ET.parse(path)`; saml_scanner uses `ET.fromstring(bytes, parser=...)`
   - What's unclear: D-05 leaves this to Claude's discretion
   - Recommendation: `parse_safely(source)` wraps `etree.parse()` only (matches nmap_parser usage); saml_scanner uses `make_safe_parser()` directly inside `_safe_ET_fromstring()`. This keeps each call site explicit about its data shape.

2. **Should the updated WR-06 nmap_parser.py comment include the new test name?**
   - What we know: D-08 says update the comment to cite the `xml_safe` chokepoint
   - What's unclear: Whether to also cite the new test file name (following the Phase 71 pattern)
   - Recommendation: Yes — follow the Phase 71 pattern; cite the new test function name(s) in the comment for audit-trail continuity.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `lxml` | `quirk/util/xml_safe.py` | Yes (core dep) | `>=6.0` (6.1.1 latest) | None needed |
| `pytest` | Test suite | Yes | Confirmed by existing test runs | — |
| GitHub Actions runner | DEP-01 verification | Yes (push to branch) | ubuntu-latest | None — real GHA run required per D-02 |
| Node 24 (in GHA) | `dashboard-quality.yml` CI job | Yes (setup-node@v4 installs it) | 24.x | — |

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

> nyquist_validation is enabled (config.json has no explicit `false`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_nmap_hardening.py tests/test_packaging.py tests/test_audit_ledger_zero_open.py -v -x` |
| Full suite command | `python -m pytest tests/ -v` |
| Pre-change baseline | `tests/test_nmap_hardening.py` — 23 passed (confirmed 2026-05-22) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEP-01 | Node 24 in `dashboard-quality.yml` | smoke (GHA only) | Real GitHub Actions run on branch — not automatable locally | N/A — GHA-only validation per D-02 |
| DEP-01 | No `node-version: '20'` reference remains in any workflow file | unit | `grep -r "node-version: '20'" .github/workflows/` returns empty | N/A — grep check |
| DEP-02 | `xml_safe.make_safe_parser()` returns a fresh parser with correct flags | unit | `python -m pytest tests/test_xml_safe.py -v` | ❌ Wave 0 |
| DEP-02 | `parse_nmap_xml` succeeds on valid nmap XML fixture (regression) | unit | `python -m pytest tests/test_nmap_hardening.py -v` | ✅ (exists; test_nmap_parser_uses_defusedxml must be rewritten) |
| DEP-02 | Billion-laughs payload raises (not hangs) — D-07 forward-locking invariant | unit | `python -m pytest tests/test_nmap_hardening.py::test_nmap_parser_blocks_xxe_lxml -v` | ❌ Wave 0 (rename + rewrite of existing test) |
| DEP-02 | External entity (XXE) payload raises — D-07 forward-locking invariant | unit | `python -m pytest tests/test_xml_safe.py::test_parse_safely_blocks_xxe -v` | ❌ Wave 0 |
| DEP-02 | `defusedxml` absent from `pyproject.toml` core deps | unit | `python -m pytest tests/test_packaging.py::test_defusedxml_not_in_core_deps -v` | ❌ Wave 0 (replaces test_defusedxml_in_core_deps) |
| DEP-02 | `lxml` present in `pyproject.toml` core deps | unit | `python -m pytest tests/test_packaging.py::test_lxml_in_core_deps -v` | ✅ (likely already exists) |
| DEP-02 | `defusedxml` absent from all `quirk/` imports | unit (grep gate) | `python -m pytest tests/test_xml_safe.py::test_no_defusedxml_import_in_quirk -v` | ❌ Wave 0 |
| DEP-02 | WR-06 audit ledger stays `[x] closed` | integration | `python -m pytest tests/test_audit_ledger_zero_open.py -v` | ✅ |
| DEP-02 | `saml_scanner.py` defusedxml fallback removed — no `import defusedxml` in saml_scanner | unit | included in no-defusedxml-import gate | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_nmap_hardening.py tests/test_xml_safe.py tests/test_packaging.py tests/test_audit_ledger_zero_open.py -x`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_xml_safe.py` — covers: `make_safe_parser()` returns fresh instance per call, `parse_safely()` works on valid file, billion-laughs raises, XXE raises, no-network blocks external URI
- [ ] Rewrite `tests/test_nmap_hardening.py::test_nmap_parser_uses_defusedxml` → `test_nmap_parser_uses_xml_safe` (asserts `make_safe_parser` used, not defusedxml)
- [ ] Rewrite `tests/test_nmap_hardening.py::test_nmap_parser_blocks_xxe` → lxml-native (`lxml.etree.XMLSyntaxError` not `defusedxml.common.EntitiesForbidden`)
- [ ] Replace `tests/test_packaging.py::test_defusedxml_in_core_deps` with `test_defusedxml_not_in_core_deps`
- [ ] Update `tests/test_identity_infra.py:240` assertion — remove or invert the defusedxml identity-group check (verify exact assertion target before editing)
- [ ] Grep-gate test: assert `grep -r "defusedxml" quirk/` returns zero hits after migration

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | lxml XMLParser with 5 security flags; factory pattern prevents flag-bypass |
| V6 Cryptography | no | — |
| V14 Configuration | yes | CI node-version pin; no default/ambient insecure config |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XXE (external entity injection) via nmap XML output | Tampering / Information disclosure | `resolve_entities=False` + `no_network=True` in XMLParser |
| Billion-laughs DoS via internal entity recursion | Denial of service | `load_dtd=False` prevents internal entity declaration processing |
| SSRF via DTD external URI | Spoofing / Information disclosure | `no_network=True` blocks network access; `load_dtd=False` prevents DTD URI fetch |
| Parser-instance reuse across threads | Tampering | Factory function (not shared constant) per D-04 |
| Future developer weakening the parser (load_dtd=True) | Tampering | D-07 forward-locking test; CI grep gate for `load_dtd=True` |

---

## Sources

### Primary (HIGH confidence)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/discovery/nmap_parser.py` — confirmed `defusedxml.ElementTree` import at line 6; confirmed ElementTree navigation API (`findall`, `getroot`, `.get`) [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/scanner/saml_scanner.py:1-25` — confirmed lxml primary path + defusedxml fallback at lines 16-23; existing per-call XMLParser pattern confirmed [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/pyproject.toml:28,30` — `lxml>=6.0` at line 28, `defusedxml>=0.7.1` at line 30 (core deps); defusedxml NOT in `[identity]` group [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.github/workflows/dashboard-quality.yml:22` — `node-version: '20'` confirmed; `actions/setup-node@v4` confirmed; only Node pin in any workflow [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_nmap_hardening.py` — three defusedxml-dependent tests identified by name [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_packaging.py` — `test_defusedxml_in_core_deps` confirmed [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_identity_infra.py:240` — `'"defusedxml>=0.7.1"'` assertion confirmed [VERIFIED: codebase]
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/util/` — directory listing confirms `xml_safe.py` does not yet exist; `optional_extra.py`, `targets.py`, etc. establish the naming convention [VERIFIED: codebase]
- `.planning/research/STACK.md` — lxml XXE API surface, 5-flag set, Node deadline, actions/setup-node version analysis [VERIFIED: milestone research]
- `.planning/research/ARCHITECTURE.md` — two-file defusedxml scope, nmap/saml migration actions, single-line Node change [VERIFIED: milestone research]
- `.planning/research/PITFALLS.md` — lxml thread-safety, load_dtd footgun, three defusedxml-blocking test names, Node deadline September 16 hard-fail [VERIFIED: milestone research]
- `87-CONTEXT.md` — 9 locked decisions (D-01..D-09) including factory-not-constant mandate (D-04) [VERIFIED: CONTEXT.md]

### Secondary (MEDIUM confidence)
- lxml.de/parsing.html — XMLParser keyword argument semantics, all 5 flags confirmed [CITED: lxml official docs]
- GitHub Changelog 2025-09-19 — June 16, 2026 default-switch, September 16, 2026 hard removal [CITED: github.blog/changelog]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages; all changes are within lxml 6.x (existing dep) and single-line CI YAML
- Architecture: HIGH — live codebase inspection confirms exact file paths, line numbers, and API shapes
- Pitfalls: HIGH — three blocking test replacements identified by name from codebase inspection; thread-safety rationale documented in D-04

**Research date:** 2026-05-22
**Valid until:** 2026-06-16 (Node deadline) — research is stable; action required before this date

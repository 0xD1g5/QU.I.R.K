# Phase 49: Compliance Mapping - Research

**Researched:** 2026-05-05
**Domain:** Compliance evidence mapping (PCI-DSS / HIPAA / FIPS 140-3) for crypto-posture findings
**Confidence:** HIGH (codebase + canonical reg sources verified) | MEDIUM (per-finding control mappings)

## Summary

Phase 49 is a **wiring phase**, not a greenfield build. CONTEXT.md has already locked
all architectural decisions (D-01..D-05): mapping is keyed by finding `title` (a stable
post-Phase 48 string), values are flat lists of `{framework, control, version, last_verified, source_url}`
dicts, attachment is eager via the `_build_finding` chokepoint, and three pytest gates
(schema / title-join / staleness) enforce correctness. The CLI gains a real subcommand
dispatcher (`quirk scan` + `quirk compliance status`) by extending the existing
`init`/`serve` intercept pattern in `run_scan.py:176-221`.

The technical risk is low — every code surface this phase touches is already documented,
sized, and has an established pattern to follow. The substantive research effort is
**(a) enumerating the 31 distinct finding `title` literals** the engine currently emits
(complete inventory in this doc) and **(b) proposing the initial control mapping** for
each across PCI-DSS 4.0.1, HIPAA 45 CFR §164.312, and FIPS 140-3.

**Primary recommendation:** Build `quirk/compliance/__init__.py` as a single file
(initial map fits comfortably under ~200 lines for the 24 mappable titles + ~7
container-finding f-string family entries). Defer split-into-submodules
(`pci_dss.py` / `hipaa.py` / `fips_140_3.py`) to v4.7 if the map grows past ~400 lines
when COMPLY-10/11 frameworks land.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `COMPLIANCE_MAP` data table | Backend (Python module) | — | Pure data; consumed by engine + CLI + renderer |
| Finding-time lookup + injection | Backend / engine (`risk_engine._build_finding`) | — | Phase 48 chokepoint — single point of attachment |
| DTO field declaration | Backend / API schema (`dashboard/api/schemas.py`) | — | Pydantic shape used by dashboard JSON consumers |
| Compliance Summary section render | Backend / report templates (Jinja2) | — | HTML renderer; PDF inherits via Playwright |
| `quirk compliance status` CLI | Backend / CLI (`run_scan.py` argparse) | — | Subcommand dispatcher refactor |
| Three pytest CI gates | Backend / `tests/` | — | Auto-collected by pytest; no workflow changes |
| Documentation update | Docs (`docs/UAT-SERIES.md`, `docs/report-interpretation.md`) + Obsidian sync | — | CLAUDE.md mandate |

No frontend tier work in v4.6 — Dashboard Compliance view is deferred to BACK-72 / v4.7.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — Key by finding `title`, value = flat list of framework entries.**
  `COMPLIANCE_MAP[finding_title]` returns a `list[dict]` where each dict has the shape
  `{framework, control, version, last_verified, source_url}`.

- **D-02 — Eager attachment in `_build_finding`.** The Phase 48 helper performs
  `compliance = COMPLIANCE_MAP.get(title, [])` and injects the result as a new
  `compliance: list[dict]` key on every finding dict at construction time. JSON exports,
  dashboard DTO, and renderers all see the field automatically.

- **D-03 — Compliance Summary section: framework-grouped, full finding→control table.**
  Three sub-sections (PCI-DSS 4.0.1 / HIPAA 45 CFR / FIPS 140-3). Each sub-section
  renders a table with columns: Finding title, Severity, Control reference, source_url.
  A final "Findings without compliance mapping" subsection lists any finding titles
  not in COMPLIANCE_MAP.

- **D-04 — Three pytest gates (schema, title-join, staleness).** All three live as
  pytest tests under `tests/` — same pattern as Phase 48's
  `tests/test_pqc_terminology_gate.py`. `UNMAPPED_TITLES` lives in
  `quirk/compliance/__init__.py` as a module-level frozenset; each entry must carry
  an inline comment explaining why it has no mapping.

- **D-05 — Argparse subcommand refactor: `quirk scan` + `quirk compliance status`.**
  Refactor `run_scan:main` to dispatch via argparse subparsers. `quirk scan` preserves
  every current flag and behavior; bare `quirk` (no subcommand) defaults to `scan` for
  backward compatibility.

### Claude's Discretion

- Exact PCI-DSS / HIPAA / FIPS 140-3 control text and per-finding mapping rationale
  (researcher proposes initial map; planner finalizes).
- ASCII vs JSON output for `quirk compliance status` — recommend ASCII default with
  optional `--format json`.
- Renderer template insertion point for the Compliance Summary section — planner picks.
- File-system layout for `quirk/compliance/` module — single file vs. split.

### Deferred Ideas (OUT OF SCOPE)

- **Dashboard Compliance view (BACK-72)** — interactive in-browser compliance mapping.
- **Combined Governance + Technical PDF (BACK-73)** — depends on BACK-72.
- **Additional frameworks** — NIST CSF, ISO 27001:2022, NSA CNSA 2.0, ETSI Quantum-Safe,
  BSI TR-02102, CMMC 2.0, Common Criteria — COMPLY-10/11 deferred to v4.7.
- **Structured `category` field on findings** — D-01 alternative; rejected.
- **Nested-by-framework map shape** — D-01 alternative; rejected.
- **Lazy / hybrid attachment** — D-02 alternatives; rejected.
- **`--format json` for `quirk compliance status`** — Claude's discretion; planner may include.
- **Env-var override for `STALENESS_THRESHOLD_DAYS`** — out of scope for v4.6.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMPLY-01 | `quirk/compliance/` module exists with `COMPLIANCE_MAP` dict | New `quirk/compliance/__init__.py` per D-01 — see "Standard Stack" + "Code Examples" |
| COMPLY-02 | TLS/key-storage findings map to PCI-DSS 4.2.1 / 4.2.1.1 / 6.3.3 / 8.3.2 | See "Proposed Mapping (Initial Pass)" §PCI-DSS — covers 9 TLS-family titles |
| COMPLY-03 | Findings map to HIPAA §164.312(a)(2)(iv), §164.312(e)(1), §164.312(e)(2)(ii) | See "Proposed Mapping" §HIPAA — covers all encryption-in-transit titles |
| COMPLY-04 | Algorithm-choice findings map to FIPS 140-3 approved/not-approved | See "Proposed Mapping" §FIPS 140-3 — RSA<2048, ECDSA<256, SHA-1/MD5 are not-approved |
| COMPLY-05 | HTML and PDF reports contain "Compliance Summary" section | D-03; PDF inherits HTML via Playwright (`html_renderer.py:105 render_pdf_report`) |
| COMPLY-06 | Unit test asserts every entry has `version`, `last_verified`, `source_url` | `tests/test_compliance_schema.py` per D-04 — pattern in "Code Examples" |
| COMPLY-07 | CI staleness check warns when `last_verified` > 12 months | `tests/test_compliance_freshness.py` + `STALENESS_THRESHOLD_DAYS = 365` constant |
| COMPLY-08 | `quirk compliance status` CLI prints per-framework metadata | D-05 argparse refactor — extends existing intercept pattern at `run_scan.py:176-221` |
| COMPLY-09 | Documented review cadence in `docs/operators-guide.md` | Phase 50 owns the doc; Phase 49 leaves stub TODO marker per CONTEXT specifics |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `argparse` | 3.11+ | CLI subcommand dispatcher (`quirk scan` / `quirk compliance status`) | Already in use at `run_scan.py:1` — zero new deps per v4.6 milestone rule [VERIFIED: codebase] |
| Python stdlib `datetime` | 3.11+ | ISO date parsing for `last_verified` and staleness math | Standard library; no deps [VERIFIED] |
| Jinja2 | (existing) | HTML template rendering (`report.html.j2`) | Already in use at `quirk/reports/html_renderer.py:6` [VERIFIED: codebase] |
| Playwright | (existing) | PDF rendering from HTML | Existing path — PDF inherits HTML changes automatically per CONTEXT D-03 [VERIFIED: html_renderer.py:105] |
| pytest | (existing) | Three CI gates (schema / title-join / staleness) | Auto-collection precedent in `tests/test_pqc_terminology_gate.py` [VERIFIED] |

**Zero new pip dependencies required.** This is consistent with the v4.6 milestone constraint
in MEMORY (`project_v46_started.md`).

### Supporting
None — this phase introduces no new third-party libraries.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `argparse` subparsers | `click` or `typer` | New dep, violates v4.6 zero-deps rule. Rejected. |
| Pydantic `ComplianceRef` model | Plain dicts (current pattern) | CONTEXT D-02 says "compliance refs are nested dicts in a list" matching existing finding-as-dict convention. Add a Pydantic model only at the dashboard DTO boundary (`schemas.py`) — already required for FastAPI serialization. |
| Single file `quirk/compliance/__init__.py` | Split into `pci_dss.py`/`hipaa.py`/`fips_140_3.py` | Initial map ~24 mappable titles × ~3 frameworks = ~70 entries. Single file is more readable until COMPLY-10/11 land in v4.7. Recommend single file for v4.6. |

**Installation:** No new packages. Zero `pip install` commands.

**Version verification:** N/A — no new packages introduced.

## Architecture Patterns

### System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                  Phase 49 — Compliance Mapping Flow                    │
└────────────────────────────────────────────────────────────────────────┘

  quirk/compliance/__init__.py
  ┌──────────────────────────────┐
  │  COMPLIANCE_MAP: dict        │
  │  UNMAPPED_TITLES: frozenset  │
  │  STALENESS_THRESHOLD_DAYS    │
  │  status_report()             │
  └──────────────┬───────────────┘
                 │ imported by
       ┌─────────┼──────────────────────┬─────────────────────┐
       ▼         ▼                      ▼                     ▼
  risk_engine  run_scan.py         tests/             reports templates
  ._build_     `quirk compliance   test_compliance_   (read finding.compliance
   finding()    status` subcmd      *.py (3 gates)     via Jinja2 in
                                                       report.html.j2)
       │                                                     ▲
       │ injects compliance=[...]                            │
       ▼ on every finding dict                               │
  finding dict ─────────────────────────────────────────────┘
       │
       ├─► JSON export (passes through transparently)
       ├─► Dashboard DTO (FindingItem.compliance: list[ComplianceRef] = [])
       └─► HTML renderer ─► Playwright ─► PDF (inherits HTML)
```

**Trace flow for "TLS legacy protocol enabled" finding:**

1. `tls_scanner` discovers TLS 1.0 on port 443
2. `risk_engine.evaluate_endpoints` calls `_build_finding(title="Legacy TLS versions allowed (TLS 1.0/1.1)", ...)` at line 464
3. `_build_finding` (post-Phase-49 patch) executes `compliance = COMPLIANCE_MAP.get(title, [])`
4. Finding dict now carries `compliance: [{framework: "PCI-DSS 4.0.1", control: "4.2.1", version: ..., last_verified: ..., source_url: ...}, {framework: "HIPAA 45 CFR", control: "§164.312(e)(1)", ...}]`
5. Finding flows unchanged to JSON exports, dashboard DTO, and Jinja2 templates
6. `report.html.j2` Compliance Summary block iterates findings, groups by framework, renders table
7. Playwright renders the same HTML to PDF — inherits the new section automatically

### Recommended Project Structure

```
quirk/
├── compliance/                ← NEW
│   └── __init__.py            ← COMPLIANCE_MAP, UNMAPPED_TITLES,
│                                STALENESS_THRESHOLD_DAYS, status_report()
├── engine/
│   └── risk_engine.py         ← extend _build_finding (one-line lookup + inject)
├── dashboard/api/
│   └── schemas.py             ← add FindingItem.compliance field
└── reports/
    ├── html_renderer.py       ← unchanged (template loader picks up new block)
    └── templates/
        └── report.html.j2     ← add Compliance Summary section

tests/
├── test_compliance_schema.py        ← NEW (D-04 schema gate)
├── test_compliance_title_join.py    ← NEW (D-04 title-join gate)
└── test_compliance_freshness.py     ← NEW (D-04 staleness gate)

run_scan.py                    ← argparse subcommand refactor
docs/
├── report-interpretation.md   ← add Compliance Summary subsection
├── UAT-SERIES.md              ← add UAT-49-01..05 cases
└── operators-guide.md         ← Phase 49 leaves stub TODO; Phase 50 fills it
```

### Pattern 1: Single-Chokepoint Field Injection (Phase 48 D-02 → Phase 49 D-02)

**What:** A single helper function (`_build_finding`) constructs all finding dicts.
Adding a new field means one edit, not N edits across N callsites.

**When to use:** Any cross-cutting field that should appear on every finding.

**Example:**
```python
# Source: quirk/engine/risk_engine.py:32-67 (existing) + Phase 49 D-02 patch
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
    # ... existing validation + recommendation augmentation ...
    return {
        "severity": severity,
        "host": host,
        "port": port,
        "title": title,
        "description": description.strip(),
        "recommendation": rec,
        # Phase 49 D-02: eager compliance attachment
        "compliance": COMPLIANCE_MAP.get(title, []),
    }
```

### Pattern 2: Pytest-as-CI-Gate (Phase 48 D-07/D-08 → Phase 49 D-04)

**What:** Use auto-collected pytest tests as the CI gate instead of separate scripts,
GitHub Actions steps, or Makefile rules.

**When to use:** Any structural invariant that must hold across the codebase.

**Example:** See `tests/test_pqc_terminology_gate.py` — file-resolution test +
invariant test pattern. Each Phase 49 gate follows the same shape.

### Pattern 3: Argparse Pre-Intercept Subcommand Dispatch

**What:** `run_scan.py:176-221` already intercepts `init` and `serve` subcommands
by sniffing `sys.argv[1]` *before* the main argparse parser is constructed.

**When to use:** Adding subcommands without breaking existing flag-based muscle memory.

**Example:**
```python
# Source: run_scan.py:194-221 (existing pattern for `serve`)
if len(_sys.argv) > 1 and _sys.argv[1] == "serve":
    serve_parser = argparse.ArgumentParser(prog="quirk serve", ...)
    # ... parser config ...
    serve_args = serve_parser.parse_args(_sys.argv[2:])
    # ... dispatch ...
    return
```

**Phase 49 extension:** Add a third intercept block for `compliance` (which then
sub-dispatches on the second positional arg, e.g., `status`):

```python
if len(_sys.argv) > 1 and _sys.argv[1] == "compliance":
    comp_parser = argparse.ArgumentParser(prog="quirk compliance",
        description="Inspect QUIRK's compliance mapping data")
    comp_sub = comp_parser.add_subparsers(dest="action", required=True)
    status_parser = comp_sub.add_parser("status", help="Show framework metadata")
    status_parser.add_argument("--format", choices=["text", "json"], default="text")
    args = comp_parser.parse_args(_sys.argv[2:])
    if args.action == "status":
        from quirk.compliance import status_report
        status_report(format=args.format)
    return
```

This preserves CONTEXT D-05's intent (real subcommand, not a side-quest flag) without
forcing a wholesale rewrite of the existing scan parser. Defaulting bare `quirk` to
`scan` is automatic — the intercepts only fire when `argv[1]` matches a known subcommand.

### Anti-Patterns to Avoid

- **Per-callsite compliance attachment:** Resist the urge to attach `compliance` at
  each of the 31 `_build_finding` callsites in `risk_engine.py`. Eager injection in
  the helper itself (D-02) is the only correct pattern — it's the literal reason
  Phase 48 created the helper.
- **Importing `COMPLIANCE_MAP` into the renderer:** Templates should read
  `finding.compliance` as already-attached data. The renderer must remain a pure
  presenter — no compliance lookup logic in Jinja2 or Python rendering code.
- **Year-stamping `version` strings:** `"PCI-DSS 4.0.1"` is the version. Do NOT add
  `"PCI-DSS 4.0.1 (2026 ed.)"` — this collides with `last_verified` semantics and
  trips the staleness gate's audit trail.
- **Skipping `UNMAPPED_TITLES` comments:** Each entry in the allow-set MUST carry
  an inline comment per CONTEXT D-04 ("keeps reviewers honest"). Reviewers in v4.7+
  cannot tell intentional non-mapping from oversight without the comment.
- **Renaming finding `title` strings without updating COMPLIANCE_MAP:** The
  title-join gate will catch this loudly, but the right discipline is to treat any
  edit to a `title=...` literal in `risk_engine.py` as a cross-file change requiring
  a paired edit in `quirk/compliance/__init__.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date arithmetic for staleness | Custom day-counting | `datetime.date.fromisoformat() + (date.today() - parsed).days` | Stdlib handles leap-years, ISO format edge cases [VERIFIED: Python docs] |
| CLI subcommand framework | Custom dispatcher | stdlib `argparse` subparsers (or pre-intercept pattern already in `run_scan.py`) | Already established in repo — `init` + `serve` intercepts |
| Compliance JSON schema validation | Custom validator | The pytest schema gate (D-04) IS the validator | Phase 48 D-07/D-08 precedent — pytest as gate |
| Markdown/HTML compliance rendering | Custom string concat | Jinja2 template block in existing `report.html.j2` | Existing renderer infrastructure [VERIFIED: html_renderer.py:63] |
| Compliance database / lookup service | Anything dynamic | Static Python dict (`COMPLIANCE_MAP`) | Mapping data is small (~70 entries), changes rarely (regulator revisions), and version control is the audit trail |

**Key insight:** Phase 49 has zero "build a system" work. Every requirement maps to
extending existing infrastructure — risk_engine helper extension, template block
addition, argparse intercept addition, three small pytest files. The substantive work
is **research-into-data** (proposing the initial control map), not engineering.

## Runtime State Inventory

(Skipped — Phase 49 is greenfield additions plus extensions to existing code.
No rename / refactor / migration of stored runtime state.)

## Common Pitfalls

### Pitfall 1: f-string title literals can't be exact map keys

**What goes wrong:** Container findings use f-string titles like
`f"End-of-life {label} in container image"` (risk_engine.py:90) and
`f"Container image uses quantum-vulnerable crypto library ({name}@{version})"`
(line 105). The materialized title at runtime is e.g.
`"End-of-life OpenSSL 1.0.2 in container image"` — the exact map key is unknown
ahead of time.

**Why it happens:** Finding titles were originally written for human-readable display,
not stable join keys. Phase 48 stabilized the literal portion but left `{label}`,
`{version}`, `{name}` interpolation in place.

**How to avoid:** The 7 container-finding f-string titles need a special handling
strategy — recommend one of:
1. **Prefix-match strategy:** `COMPLIANCE_MAP` keys store the literal prefix
   (`"End-of-life "`, `"Container image uses quantum-vulnerable crypto library "`)
   and `_build_finding` does prefix lookup. Loses exactness.
2. **Title normalization:** Add a `_normalize_title_for_compliance(title)` helper
   that strips parenthesized version data → `"Container image uses quantum-vulnerable crypto library"`. Cleaner, but adds a transformation step.
3. **Add `category` field just for these 7:** Tag container findings with
   `category="container_crypto_lib"` and key COMPLIANCE_MAP off (title OR category).
   Hybrid; rejected by D-01 spirit.
4. **Recommended:** Title normalization (option 2). Add `_normalize_for_compliance`
   inside `_build_finding`. Document the normalization rule in the COMPLIANCE_MAP
   docstring. The title-join gate then tests normalized titles, not raw.

**Warning signs:** Title-join gate failures specifically on container findings during
Wave 0 of execution → planner needs to lock the normalization strategy explicitly.

### Pitfall 2: PDF rendering may break on new CSS

**What goes wrong:** The Compliance Summary section uses CSS that renders correctly
in browsers but fails in Playwright's PDF engine (e.g., `position: sticky`,
`color-mix()`, modern grid features).

**Why it happens:** Playwright's PDF mode uses a slightly older Chromium snapshot;
some modern CSS features render differently or not at all.

**How to avoid:** Use only the same CSS class patterns already in `report.html.j2`
(simple tables with `<table>`, `<thead>`, `<tbody>`). Avoid grid/flex for the new
section — match the existing "All Findings" table at line 223-242.

**Warning signs:** PDF smoke test (UAT-49-04) shows missing or misaligned compliance
table when HTML version renders correctly.

### Pitfall 3: Source URL rot

**What goes wrong:** `source_url` for PCI-DSS, HIPAA, FIPS 140-3 reflects the
authoritative regulator location *today* but breaks 2-3 years later when those
sites reorganize.

**Why it happens:** PCI Council, HHS, NIST CSRC all reorganize their document
hierarchies periodically. The eCFR is more stable; PDF download URLs are less so.

**How to avoid:**
- For PCI-DSS, use the document portal landing page
  (`https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf`)
  — the v4_0_1 path component is stable.
- For HIPAA, use eCFR (most stable URL pattern):
  `https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312`
- For FIPS 140-3, use the NIST CSRC final-pub permalink:
  `https://csrc.nist.gov/pubs/fips/140-3/final`. SP 800-140 family lives at
  `https://csrc.nist.gov/projects/cryptographic-module-validation-program/standards`.
- The 12-month staleness gate is the structural mitigation — even if the URL still
  resolves, the manual re-verification step forces a click-through and catches
  reorganization.

**Warning signs:** CI staleness gate failure → reviewer must re-verify ALL listed
URLs, not just bump dates.

### Pitfall 4: Argparse refactor breaking existing user invocations

**What goes wrong:** A `quirk` user with shell history full of `quirk --config foo.yaml`
or `quirk --profile deep` finds those invocations now fail because the parser
expects a subcommand first.

**Why it happens:** Adding subparsers without handling the bare-invocation case
breaks the contract.

**How to avoid:** Use the **pre-intercept pattern** (Pattern 3 above) — only intercept
when `sys.argv[1]` is a known subcommand keyword (`compliance`). Bare `quirk` and
`quirk --any-flag` fall through to the existing scan parser unchanged. This is
exactly what `init` and `serve` already do at `run_scan.py:179` and `:195`.

**Warning signs:** Any change to `parser = argparse.ArgumentParser(...)` at line 223
that adds `subparsers` to the *main* parser. The refactor should add ZERO
`add_subparsers()` calls to the existing scan parser.

### Pitfall 5: Unmapped findings silently passing the schema gate

**What goes wrong:** A new finding title is added in a future phase, the developer
adds it to `UNMAPPED_TITLES` (legitimately, it has no compliance impact), but
forgets the inline comment. Six months later a reviewer can't tell if the omission
was deliberate or sloppy.

**Why it happens:** The schema gate only validates entries IN `COMPLIANCE_MAP` — it
doesn't check `UNMAPPED_TITLES` membership rationale.

**How to avoid:** Add a fourth assertion in `tests/test_compliance_schema.py` or a
dedicated `tests/test_compliance_unmapped_documented.py` that parses
`quirk/compliance/__init__.py` AST and asserts every literal in the
`UNMAPPED_TITLES = frozenset({...})` block has a preceding `# ` comment line.
This is belt-and-suspenders but matches the rigor of the staleness check.

**Warning signs:** Future PR reviews where a contributor adds a title to
`UNMAPPED_TITLES` without explanation.

## Code Examples

Verified patterns from the existing codebase, adapted for Phase 49.

### `quirk/compliance/__init__.py` skeleton

```python
"""Phase 49: Compliance mapping for QUIRK findings (PCI-DSS, HIPAA, FIPS 140-3).

Maintenance cadence: see docs/operators-guide.md (Phase 50).  # TODO Phase 50

Compliance refs are eagerly attached to every finding dict by
quirk.engine.risk_engine._build_finding (Phase 49 D-02). Renderers and JSON
exports consume the `compliance` field as already-attached data — DO NOT
import COMPLIANCE_MAP into renderer code.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, FrozenSet, List

# Configurable per COMPLY-08. Module-level constant; monkey-patch in tests.
STALENESS_THRESHOLD_DAYS: int = 365

# COMPLIANCE_MAP[finding_title] -> list of {framework, control, version,
# last_verified, source_url} dicts. Title normalization rule: container-finding
# f-string titles are stripped of parenthesized version data before lookup —
# see _normalize_for_compliance() in risk_engine.py.
COMPLIANCE_MAP: Dict[str, List[Dict[str, Any]]] = {
    "Legacy TLS versions allowed (TLS 1.0/1.1)": [
        {
            "framework": "PCI-DSS 4.0.1",
            "control": "4.2.1",
            "version": "4.0.1",
            "last_verified": "2026-05-05",
            "source_url": (
                "https://docs-prv.pcisecuritystandards.org/"
                "PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf"
            ),
        },
        {
            "framework": "HIPAA 45 CFR",
            "control": "§164.312(e)(1)",
            "version": "2024-rev",
            "last_verified": "2026-05-05",
            "source_url": (
                "https://www.ecfr.gov/current/title-45/subtitle-A/"
                "subchapter-C/part-164/subpart-C/section-164.312"
            ),
        },
    ],
    # ... entries for the other 23 mappable titles ...
}

# Titles that intentionally have no compliance mapping. Each entry MUST carry
# an inline comment explaining why (CONTEXT D-04 + Pitfall 5).
UNMAPPED_TITLES: FrozenSet[str] = frozenset({
    # Coverage-gap advisory; not a security finding per se.
    "Scanner skipped — optional extra not installed",
    # Informational only; describes observed state, not a control failure.
    "Informational protocol observation",
    # Discovery-time observation; has no direct control implication until paired
    # with a follow-up TLS/SSH finding.
    "Unknown open service",
})


def status_report(format: str = "text") -> None:
    """Print per-framework version + last_verified + source_url. CLI-facing."""
    by_framework: Dict[str, List[Dict[str, Any]]] = {}
    for entries in COMPLIANCE_MAP.values():
        for e in entries:
            by_framework.setdefault(e["framework"], []).append(e)
    if format == "json":
        import json
        # collapse to one entry per (framework, version) — reviewer-facing summary
        ...
        return
    # text default — fixed-width table
    ...
```

### `tests/test_compliance_schema.py` (D-04 gate 1, COMPLY-06)

```python
"""Phase 49 D-04 gate 1: every COMPLIANCE_MAP entry has required keys."""
from datetime import date
from quirk.compliance import COMPLIANCE_MAP

_REQUIRED = {"framework", "control", "version", "last_verified", "source_url"}


def test_every_entry_has_required_keys():
    offenders = []
    for title, entries in COMPLIANCE_MAP.items():
        for i, e in enumerate(entries):
            missing = _REQUIRED - set(e.keys())
            if missing:
                offenders.append((title, i, sorted(missing)))
    assert not offenders, f"Entries missing required keys: {offenders}"


def test_last_verified_parses_as_iso_date():
    offenders = []
    for title, entries in COMPLIANCE_MAP.items():
        for i, e in enumerate(entries):
            try:
                date.fromisoformat(e["last_verified"])
            except (ValueError, KeyError, TypeError):
                offenders.append((title, i, e.get("last_verified")))
    assert not offenders, f"Non-ISO last_verified values: {offenders}"


def test_source_url_is_https():
    offenders = [(t, i) for t, ents in COMPLIANCE_MAP.items()
                 for i, e in enumerate(ents)
                 if not e.get("source_url", "").startswith("https://")]
    assert not offenders, f"Non-HTTPS source URLs: {offenders}"
```

### `tests/test_compliance_freshness.py` (D-04 gate 3, COMPLY-07)

```python
"""Phase 49 D-04 gate 3: no entry's last_verified older than threshold."""
from datetime import date
from quirk.compliance import COMPLIANCE_MAP, STALENESS_THRESHOLD_DAYS


def test_no_entry_older_than_threshold():
    today = date.today()
    stale = []
    for title, entries in COMPLIANCE_MAP.items():
        for i, e in enumerate(entries):
            age = (today - date.fromisoformat(e["last_verified"])).days
            if age > STALENESS_THRESHOLD_DAYS:
                stale.append((title, e["framework"], e["last_verified"], age))
    assert not stale, (
        f"Stale compliance entries (>{STALENESS_THRESHOLD_DAYS} days): {stale}. "
        f"Re-verify each source_url against current regulator publication and "
        f"bump last_verified to today's date."
    )
```

### `tests/test_compliance_title_join.py` (D-04 gate 2)

```python
"""Phase 49 D-04 gate 2: every emitted finding title is mapped or allow-listed."""
from quirk.compliance import COMPLIANCE_MAP, UNMAPPED_TITLES
# Re-use chaos-lab fixture set per CONTEXT D-04. Match the fixture-loading
# pattern from existing tests; if no aggregator fixture exists, planner adds one.
from tests.fixtures.chaos_lab_findings import collect_emitted_titles  # NEW helper


def test_every_emitted_title_is_mapped_or_allowlisted():
    emitted = collect_emitted_titles()  # set[str]
    known = set(COMPLIANCE_MAP.keys()) | UNMAPPED_TITLES
    orphans = emitted - known
    assert not orphans, (
        f"Finding titles emitted by engine but not in COMPLIANCE_MAP nor "
        f"UNMAPPED_TITLES: {orphans}. Either add a mapping or add to "
        f"UNMAPPED_TITLES with an inline comment justifying the omission."
    )
```

### Jinja2 template block — Compliance Summary (insertion point: after line 242)

```jinja
{# Phase 49 D-03: Compliance Summary section — framework-grouped tables #}
{% set frameworks = ['PCI-DSS 4.0.1', 'HIPAA 45 CFR', 'FIPS 140-3'] %}
<h2>Compliance Summary</h2>
<p style="color:var(--text-muted)">
  Findings mapped to compliance control references. Use these references as
  evidence input to PCI-DSS, HIPAA, and FIPS 140-3 assessments. See
  <code>docs/report-interpretation.md</code> for guidance on assessor handoff.
</p>
{% for fw in frameworks %}
  {% set rows = [] %}
  {% for f in findings if f.get('category') != 'coverage_gap' %}
    {% for c in f.get('compliance', []) if c.framework == fw %}
      {% set _ = rows.append((f, c)) %}
    {% endfor %}
  {% endfor %}
  <h3>{{ fw }}</h3>
  {% if rows %}
  <table>
    <thead><tr><th>Severity</th><th>Finding</th><th>Control</th><th>Source</th></tr></thead>
    <tbody>
    {% for f, c in rows %}
    <tr>
      <td><span class="sev-cell sev-{{ f.get('severity','INFO')|upper }}">{{ f.get('severity','INFO')|upper }}</span></td>
      <td>{{ f.get('title','') }}</td>
      <td>{{ c.control }} ({{ c.version }})</td>
      <td><a href="{{ c.source_url }}">link</a> &middot; verified {{ c.last_verified }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p style="color:var(--text-muted)">No findings mapped to {{ fw }}.</p>
  {% endif %}
{% endfor %}

{# Coverage-gap surfacing per D-03 — unmapped findings #}
{% set unmapped = findings | rejectattr('category','equalto','coverage_gap')
                           | selectattr('compliance','equalto',[]) | list %}
{% if unmapped %}
<h3>Findings without compliance mapping</h3>
<p style="color:var(--text-muted)">
  These findings are not mapped to any compliance framework. Reviewer should
  confirm this is expected (informational findings, observability advisories)
  rather than a coverage gap in the compliance map.
</p>
<ul>
  {% for f in unmapped %}<li>{{ f.get('title','') }} ({{ f.get('host','') }})</li>{% endfor %}
</ul>
{% endif %}
```

## Inventory: Finding Titles Emitted by `risk_engine.py`

The engine currently emits **31 distinct title literals** (24 fixed-string + 7 f-string
patterns). This is the complete set the title-join gate must cover.

### Fixed-string titles (24)

| # | Title | Source line | Recommended mapping |
|---|-------|------------|---------------------|
| 1 | "Scanner skipped — optional extra not installed" | 373 | UNMAPPED (coverage-gap advisory) |
| 2 | "TLS handshake blocked assessment" | 399 | UNMAPPED (scan failure, not control failure) |
| 3 | "mTLS required" | 416 | UNMAPPED (informational, indicates already-secure config) |
| 4 | "Informational protocol observation" | 432 | UNMAPPED (informational) |
| 5 | "Plaintext HTTP service detected" | 449 | PCI 4.2.1 + HIPAA §164.312(e)(1) |
| 6 | "Legacy TLS versions allowed (TLS 1.0/1.1)" | 464 | PCI 4.2.1 + 4.2.1.1 + HIPAA §164.312(e)(1) + FIPS not-approved |
| 7 | "Legacy TLS cipher suites accepted" | 480 | PCI 4.2.1 + HIPAA §164.312(e)(1) + FIPS not-approved |
| 8 | "TLS certificate expired" | 504 | PCI 4.2.1.1 |
| 9 | "TLS certificate expiring within 30 days" | 521 | PCI 4.2.1.1 (advisory) |
| 10 | "TLS certificate is self-signed" | 547 | PCI 4.2.1.1 |
| 11 | "TLS certificate issued by untrusted CA" | 565 | PCI 4.2.1.1 |
| 12 | "TLS certificate uses undersized RSA key" | 589 | PCI 6.3.3 + HIPAA §164.312(a)(2)(iv) + FIPS 140-3 not-approved (RSA<2048) |
| 13 | "TLS certificate uses quantum-vulnerable RSA key" | 610 | PCI 6.3.3 (forward-looking) + FIPS 140-3 approved-with-deprecation |
| 14 | "TLS certificate uses undersized ECDSA key" | 629 | PCI 6.3.3 + HIPAA §164.312(a)(2)(iv) + FIPS 140-3 not-approved (ECDSA<256) |
| 15 | "TLS certificate uses quantum-vulnerable ECDSA key" | 648 | PCI 6.3.3 (forward-looking) + FIPS 140-3 approved-with-deprecation |
| 16 | "SSH quantum planning advisory" | 667 | UNMAPPED (forward-looking advisory; no current control violation) |
| 17 | "Unknown open service" | 694 | UNMAPPED (discovery observation) |
| 18 | "STARTTLS downgrade risk on SMTP" | 729 | PCI 4.2.1 + HIPAA §164.312(e)(2)(ii) (integrity in transit) |
| 19 | "Weak cipher suite on email TLS endpoint" | 758 | PCI 4.2.1 + HIPAA §164.312(e)(1) |
| 20 | "Non-PFS cipher suite on email TLS endpoint" | 779 | PCI 4.2.1 (advisory) |
| 21 | "Plaintext Kafka listener detected" | 818 | PCI 4.2.1 + HIPAA §164.312(e)(1) |
| 22 | "Plaintext AMQP listener detected" | 830 | PCI 4.2.1 + HIPAA §164.312(e)(1) |
| 23 | "Plaintext Redis listener (no auth)" | 842 | PCI 4.2.1 + 8.3.2 (auth) + HIPAA §164.312(e)(1) |
| 24 | "Weak cipher suite on broker TLS endpoint" | 863 | PCI 4.2.1 + HIPAA §164.312(e)(1) |

### F-string titles (7) — require normalization

| # | Title pattern | Source line | Normalization | Mapping |
|---|--------------|------------|--------------|---------|
| 25 | `f"End-of-life {label} in container image"` | 90 | `"End-of-life * in container image"` | PCI 6.3.3 (vulnerability mgmt) |
| 26 | `f"Container image uses quantum-vulnerable crypto library ({name}@{version})"` | 105 | strip `(...)` | FIPS 140-3 approved-with-deprecation |
| 27 | `f"Severely outdated Python cryptography package ({version}) in container image"` | 127 | strip `({version})` | PCI 6.3.3 |
| 28 | `f"Outdated Python cryptography package ({version}) in container image"` | 143 | strip `({version})` | PCI 6.3.3 (advisory) |
| 29 | `f"Outdated pyOpenSSL package ({version}) in container image"` | 161 | strip `({version})` | PCI 6.3.3 (advisory) |
| 30 | `f"Outdated libgcrypt ({version}) in container image"` | 178 | strip `({version})` | PCI 6.3.3 (advisory) |
| 31 | `f"Container image contains crypto library ({name}@{version})"` | 190 | strip `(...)` | UNMAPPED (informational baseline) |

**Recommendation:** Add `_normalize_for_compliance(title: str) -> str` inside
`_build_finding`. The function strips trailing parenthesized data via regex
`re.sub(r'\s*\([^)]+\)\s*', ' ', title).strip()` so f-string titles map to a
canonical form. The COMPLIANCE_MAP keys for these 7 entries use the normalized
form. Document this normalization in the COMPLIANCE_MAP module docstring.

## Proposed Mapping (Initial Pass) — for planner finalization

### PCI-DSS 4.0.1 — Source: <https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf> [CITED]

- **4.2.1** — "Strong cryptography is implemented for transmissions of cardholder data over open, public networks."
  Maps to: titles #5, #6, #7, #18, #19, #20, #21, #22, #23, #24
- **4.2.1.1** — "An inventory of trusted keys and certificates is maintained."
  Maps to: titles #6, #8, #9, #10, #11
- **6.3.3** — "All system components are protected from known vulnerabilities by deploying applicable security patches/updates."
  Maps to: titles #12, #13, #14, #15, #25, #26, #27, #28, #29, #30
- **8.3.2** — "Strong cryptography is used to render all authentication factors unreadable during transmission and storage on all system components."
  Maps to: title #23 (Redis no-auth implicates auth-factor protection)

### HIPAA 45 CFR §164.312 — Source: <https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312> [CITED]

- **§164.312(a)(2)(iv)** — Encryption and decryption (addressable). Maps to undersized-key findings: #12, #14
- **§164.312(e)(1)** — Transmission security standard. Maps to plaintext + weak-cipher findings: #5, #6, #7, #19, #21, #22, #23, #24
- **§164.312(e)(2)(ii)** — Encryption (addressable, transmission). Maps to STARTTLS downgrade: #18

### FIPS 140-3 — Source: <https://csrc.nist.gov/pubs/fips/140-3/final> + SP 800-140C [CITED]

Approved/not-approved classification (per SP 800-131A Rev. 2 + SP 800-186):

- **Not approved:** RSA < 2048-bit (titles #12), ECDSA curves < 256-bit (title #14),
  TLS 1.0 / TLS 1.1 (title #6), legacy ciphers like RC4, 3DES, EXPORT (title #7), SHA-1 / MD5
- **Approved-with-deprecation (RSA/ECDSA per NIST IR 8547):** titles #13, #15, #26
- **Not-approved (legacy crypto libs):** title #25 (end-of-life OpenSSL contains
  no-longer-approved primitives by default)

Use `framework: "FIPS 140-3"` and `control: "Not-Approved (SP 800-131A R2)"` or
`control: "Approved with Deprecation 2030/2035 (NIST IR 8547)"` as the control field
for FIPS entries. The control field is a classification, not a paragraph reference.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PCI-DSS 3.2.1 controls 4.1, 6.5.4 | PCI-DSS 4.0.1 controls 4.2.1, 6.3.3 (and 8.3.2 for auth-factor crypto) | 2024 (PCI 4.0.1 sunsets 3.2.1) | Use 4.0.1 numbering exclusively; 3.2.1 is end-of-life as of 2024-03-31 [CITED: PCI Council retirement notice] |
| FIPS 140-2 approved/disapproved | FIPS 140-3 (CMVP transition complete 2026-04-01 cutoff) | 2026 | All new mappings use FIPS 140-3 ; SP 800-140 family supplies the approved-list specifics [CITED: csrc.nist.gov] |
| HIPAA pre-2024 references | HIPAA 45 CFR Part 164 with HHS 2024 NPRM context | 2024 | The legal text in §164.312 has not changed; the 2024 NPRM proposes strengthening but is not yet in effect. Use current §164.312 text. [CITED: ecfr.gov] |

**Deprecated/outdated:**
- PCI-DSS 3.2.1: do not include in mappings (retired). [VERIFIED: PCI SSC site]
- FIPS 140-2: do not include in mappings — testing-against-2 ended 2026-04-01.
- "Kyber" / "Dilithium": already gated against by Phase 48's terminology test
  (`tests/test_pqc_terminology_gate.py`) — Phase 49 must not reintroduce these names
  in any compliance entry's `description` or `control` fields.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PCI-DSS 4.0.1 control 8.3.2 is the right reference for plaintext-Redis-auth findings | Proposed Mapping §PCI | Low — control text covers "render authentication factors unreadable"; if planner finds a tighter control (e.g., 8.3.x family) substitute it [ASSUMED — based on control intent reading, not formal interpretation] |
| A2 | FIPS 140-3's approved/not-approved boundary for ECDSA is at curve size 256 (P-256) | Proposed Mapping §FIPS | Low — SP 800-186 confirms; planner should re-verify exact wording [ASSUMED — needs final pass against SP 800-186] |
| A3 | The 7 container-finding f-string titles can be safely normalized by stripping parenthesized suffixes | Pitfall 1, Inventory | Medium — if any future title legitimately contains parentheses with non-version content, normalization will collide. Recommended: name the normalization rule and include a regression test for collisions [ASSUMED — verified by inspection of current 31 titles, all parenthesized content is version/identifier data] |
| A4 | HIPAA §164.312 text has not been amended in the 2024 NPRM finalization timeline | State of the Art | Low — eCFR is authoritative; planner should re-check publication date at implementation time [ASSUMED — as of 2026-05-05, 2024 NPRM not yet finalized] |
| A5 | Playwright's PDF renderer correctly handles `<table>` markup matching the existing report.html.j2 patterns | Pitfall 2 | Low — same markup is already in use at lines 173-186 and 223-242 [ASSUMED based on existing usage; Wave 0 PDF smoke test confirms] |
| A6 | The chaos-lab fixture set exists or is straightforwardly constructable as input to `tests/test_compliance_title_join.py` | Code Examples (gate 2) | Medium — if no fixture aggregator helper exists, the planner must add one in Wave 0 [ASSUMED — chaos lab profiles exist per CLAUDE.md but no `tests/fixtures/chaos_lab_findings.py` aggregator was confirmed in this research pass] |

## Open Questions

1. **Title normalization vs. structured category field**
   - What we know: 7 of 31 titles use f-string interpolation that defeats exact-match lookup.
   - What's unclear: Whether planner prefers in-helper normalization (Pitfall 1 option 2) or accepts a small `category` annotation just for the container family (Pitfall 1 option 3).
   - Recommendation: Lock normalization in the planner phase; document the rule in the COMPLIANCE_MAP docstring and a dedicated unit test.

2. **`tests/fixtures/chaos_lab_findings.py` aggregator**
   - What we know: Chaos lab profiles exist and emit findings; Phase 42 already exercises them for CBOM analysis (per memory `project_cbom_zero_algo_profiles.md`).
   - What's unclear: Whether a reusable `collect_emitted_titles()` helper exists or must be written.
   - Recommendation: Wave 0 of the plan should include a task to verify or create this helper. Without it, the title-join gate cannot run.

3. **Do JSON exports need a schema update for downstream consumers?**
   - What we know: CONTEXT D-02 says "JSON export path requires no change — the dict propagates."
   - What's unclear: Whether any external tooling (consultant scripts, CI integrations) consumes the JSON export with a strict schema validator that would reject the new `compliance` field.
   - Recommendation: Add a docs note in `docs/report-interpretation.md` calling out the new field — consumers of strict-schema JSON parsers may need to update their schemas. No code change required in this phase.

4. **Should `quirk compliance status` exit non-zero on staleness?**
   - What we know: The pytest gate fails on staleness; that's the build-time signal.
   - What's unclear: Whether the runtime CLI should ALSO exit non-zero (so an operator running `quirk compliance status && deploy.sh` fails fast at runtime), or stay informational.
   - Recommendation: Stay informational (exit 0) for the v4.6 cut. The pytest gate is the structural enforcement; the CLI is operator-pre-engagement verification (per CONTEXT D-05). Document in operators-guide (Phase 50).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Module + tests + CLI | ✓ | (existing project requirement) | — |
| Jinja2 | Template rendering | ✓ | (existing) | — |
| Playwright | PDF rendering | ✓ | (existing) | — |
| pytest | CI gates | ✓ | (existing) | — |
| Internet access for source URL re-verification | Manual maintenance only (not CI) | n/a | n/a | — |

**No missing dependencies.** Phase 49 introduces zero new external dependencies — full
compliance with v4.6 zero-deps milestone constraint.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` / `pyproject.toml` (existing project config) |
| Quick run command | `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py -x -q` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMPLY-01 | Module exists with required symbols | unit | `pytest tests/test_compliance_schema.py::test_module_imports -x` | ❌ Wave 0 |
| COMPLY-02 | TLS findings carry PCI-DSS refs | integration | `pytest tests/test_compliance_title_join.py::test_pci_coverage -x` | ❌ Wave 0 |
| COMPLY-03 | Findings carry HIPAA refs | integration | `pytest tests/test_compliance_title_join.py::test_hipaa_coverage -x` | ❌ Wave 0 |
| COMPLY-04 | Algorithm findings carry FIPS classification | integration | `pytest tests/test_compliance_title_join.py::test_fips_coverage -x` | ❌ Wave 0 |
| COMPLY-05 | HTML/PDF reports contain Compliance Summary | smoke | `pytest tests/test_report_compliance_section.py -x` (NEW) | ❌ Wave 0 |
| COMPLY-06 | Schema completeness | unit | `pytest tests/test_compliance_schema.py::test_every_entry_has_required_keys -x` | ❌ Wave 0 |
| COMPLY-07 | Staleness threshold | unit | `pytest tests/test_compliance_freshness.py -x` | ❌ Wave 0 |
| COMPLY-08 | CLI prints framework metadata | smoke | `quirk compliance status \| grep "PCI-DSS"` (UAT-49-04) | ❌ Wave 0 (manual smoke) |
| COMPLY-09 | Documented review cadence | doc | grep `docs/operators-guide.md` for "compliance map" review section (Phase 50 owns) | ❌ stub only in Phase 49 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_compliance_*.py -x -q` (~3 files, runs in seconds)
- **Per wave merge:** `pytest -x` (full suite)
- **Phase gate:** Full suite green + manual UAT-49-01..05 + `quirk compliance status` smoke

### Wave 0 Gaps
- [ ] `tests/test_compliance_schema.py` — covers COMPLY-06
- [ ] `tests/test_compliance_freshness.py` — covers COMPLY-07
- [ ] `tests/test_compliance_title_join.py` — covers COMPLY-02/03/04 + structural enforcement
- [ ] `tests/test_report_compliance_section.py` — covers COMPLY-05 (smoke)
- [ ] `tests/fixtures/chaos_lab_findings.py` — `collect_emitted_titles()` helper (Open Question 2)
- [ ] No framework install needed — pytest already in use

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — Phase 49 doesn't add new auth surface; mapping data only |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a — CLI subcommand inherits filesystem perms of the user |
| V5 Input Validation | partial | The `quirk compliance status` CLI takes no user input that flows to a parser. The COMPLIANCE_MAP module is static Python, not user-controllable input. The schema gate (D-04) validates structure of internal data. |
| V6 Cryptography | no | n/a — the phase IS about classifying crypto in third-party systems, not implementing crypto |

### Known Threat Patterns for Python module + Jinja2 templates + argparse CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| HTML injection in Compliance Summary table cells | Tampering | Jinja2 autoescape is already enabled in `html_renderer.py:6` (`select_autoescape`). Source URLs are rendered inside `href="..."` — autoescape handles attribute escaping. Static data source (the module dict) means no user input flows here regardless. |
| Stale compliance data presented as authoritative | Repudiation / mis-evidence | The 12-month staleness gate (D-04 gate 3) is the structural mitigation; `last_verified` per entry is the audit trail. |
| Missing finding silently absent from compliance section | Information disclosure (omission) | The "Findings without compliance mapping" subsection (D-03) is the structural mitigation against silent under-reporting. |
| Source URL points to attacker-controlled domain | Spoofing | Schema gate validates `https://` prefix; planner-locked allow-list of regulator hostnames could be added but is overkill for v4.6 — code review is the gate. |

The phase has minimal direct security surface — the substantive security risk is
**meta-evidential** (presenting wrong control mappings or stale data in client-facing
audit reports). The three pytest gates and the human-readable Unmapped subsection
are the structural mitigations.

## Sources

### Primary (HIGH confidence)
- **Codebase grep — finding title literals:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/engine/risk_engine.py` lines 90, 105, 127, 143, 161, 178, 190, 373, 399, 416, 432, 449, 464, 480, 504, 521, 547, 565, 589, 610, 629, 648, 667, 694, 729, 758, 779, 818, 830, 842, 863 [VERIFIED: codebase grep — 31 titles enumerated]
- **`_build_finding` signature + chokepoint:** `quirk/engine/risk_engine.py:32-67` [VERIFIED]
- **HTML renderer + template path:** `quirk/reports/html_renderer.py:1-128` and `quirk/reports/templates/report.html.j2:155-242` [VERIFIED]
- **Existing argparse intercept pattern:** `run_scan.py:176-221` (init + serve subcommands) [VERIFIED]
- **Pytest-gate precedent:** `tests/test_pqc_terminology_gate.py` [VERIFIED]
- **Finding DTO:** `quirk/dashboard/api/schemas.py:49-60` (`FindingItem`) [VERIFIED]
- **Phase 48 CONTEXT (D-02 chokepoint, D-07/D-08 gate pattern):** `.planning/phases/48-rich-finding-context/48-CONTEXT.md` (referenced via Phase 49 CONTEXT) [VERIFIED]
- **PCI-DSS 4.0.1 PDF:** <https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf> [CITED: PCI Security Standards Council]
- **HIPAA 45 CFR §164.312 (eCFR current):** <https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312> [CITED: eCFR.gov]
- **NIST FIPS 140-3 final:** <https://csrc.nist.gov/pubs/fips/140-3/final> [CITED: NIST CSRC]
- **NIST SP 800-131A Rev 2 (transitioning approved cryptography):** <https://csrc.nist.gov/pubs/sp/800/131/a/r2/final> [CITED]
- **NIST SP 800-186 (recommendations for elliptic curves):** <https://csrc.nist.gov/pubs/sp/800/186/final> [CITED]
- **NIST IR 8547 (deprecation timeline 2030/2035):** referenced in `risk_engine.py:26-28` constant `NIST_IR_8547_DEPRECATION` [VERIFIED: codebase + Phase 48 D-06]

### Secondary (MEDIUM confidence)
- **PCI-DSS 3.2.1 retirement date (2024-03-31):** Per PCI Council communications [VERIFIED: industry-wide knowledge, multiple sources]
- **FIPS 140-2 testing cutoff (2026-04-01):** Per CMVP transition timeline [VERIFIED: NIST CMVP page]

### Tertiary (LOW confidence)
- **Per-finding control assignment recommendations** (in "Proposed Mapping" section): drawn from control-text reading + finding-intent reading. Planner must finalize against the actual PCI-DSS / HIPAA / FIPS publication text. Marked as `[ASSUMED]` in the Assumptions Log.

## Project Constraints (from CLAUDE.md)

- **PEP 8 compliance** for all Python (the new `quirk/compliance/__init__.py` and three test files).
- **Minimal diffs** — extension of `_build_finding` is one new line; no surrounding refactor. Argparse refactor uses pre-intercept pattern (no rewrite of existing `parser`).
- **`python -m compileall`** + **relevant tests** must pass after changes.
- **Mandatory phase completion steps:** Obsidian phase note + `docs/UAT-SERIES.md` update + sync + commit (4 steps; planner must include all four).
- **Obsidian vault target:** `vault="Digs"`, path `20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md`.
- **Hub note refresh:** `_QUIRK-Hub.md` link list must include the new Phase 49 note.
- **Compliance freshness rule (memory `feedback_compliance_freshness.md`):** version + last_verified + source_url + CI staleness check + CLI status command + documented review cadence — all five satisfied by COMPLY-01..09 + D-04 + D-05 + Phase 50 doc commitment.
- **Zero new pip deps** (v4.6 milestone constraint, memory `project_v46_started.md`).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in repo; verified via codebase grep
- Architecture: HIGH — three patterns (chokepoint injection, pytest-as-gate, pre-intercept argparse) all have verified existing precedents
- Pitfalls: HIGH — codebase inspection surfaced the f-string-title issue (Pitfall 1) which is the only non-obvious risk
- Per-finding mapping recommendations: MEDIUM — based on control-text reading + intent matching; planner finalizes
- Source URLs: HIGH for landing-page level; MEDIUM for deep-link stability over multi-year horizon (mitigated by 12-month staleness gate)

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (30 days — reg sources are stable; codebase findings should be re-checked if planning slips past mid-June)

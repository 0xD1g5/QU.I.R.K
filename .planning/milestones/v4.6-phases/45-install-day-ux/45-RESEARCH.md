# Phase 45: Install-Day UX — Research

**Researched:** 2026-05-03
**Domain:** Python packaging extras + optional-import probe + report rendering
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `pip install quirk[all]` resolves to `cloud + db + motion + redis + dashboard`. `[identity]` is intentionally excluded — impacket pulls a pyOpenSSL transitive that downgrades cryptography and breaks TLS scanner. Hard constraint; regression test required.
- **D-02:** Dashboard included in `[all]` despite Playwright browser binaries; size cost must be documented in user-facing install docs.
- **D-03:** Severity is **INFO** (not LOW). Coverage signal, not target finding.
- **D-04:** New finding category/kind: `coverage_gap`. Field name proposed in §2 below.
- **D-05:** One INFO finding per skipped-but-enabled scanner (not aggregated).
- **D-06:** Advisory findings persisted to SQLite via the same path as other findings.
- **D-07:** Zero impact on readiness/intelligence score (excluded from severity weighting and confidence subscore).
- **D-08:** Centralized pre-scan probe; runs after config load, before scanner dispatch. Config-disabled scanners stay silent.
- **D-09:** Advisory message MUST contain literal `pip install quirk[<extra>]`.
- **D-10:** New module `quirk/util/optional_extra.py` houses the registry + `is_extra_available(name)` + `probe_missing_extras(config)`.
- **D-11:** **No migration of existing scanners.** Their `*_AVAILABLE` flags and `*Scanner = None` patch points stay intact.

### Claude's Discretion
- Exact field name for the new finding category (researcher proposes — see §2).
- Exact wording of per-scanner install-hint strings (D-09 literal mandatory; prose at planner discretion — see §5).
- Whether the "Coverage Gaps" report section is a new template block or filtered render (researcher decides — see §3).
- Where in the scan lifecycle the probe is invoked (pinpointed in §4).

### Deferred Ideas (OUT OF SCOPE)
- Unifying scanner optional-import patterns onto the new helper.
- Confidence-subscore penalty for coverage gaps.
- Aggregated single-finding mode for advisories.
- `quirk doctor` / dependency-status CLI command.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSTALL-01 | `pip install quirk` + TLS-only scan with no ImportError | Existing `*_AVAILABLE` idiom (§9) already prevents TLS-path crash; new probe must NOT regress this by pre-importing missing modules. |
| INSTALL-02 | `missing_extra` advisory finding when scanner skipped | Phase 41 already wires `_emit_missing_extra_advisory` for email/broker (run_scan.py:122-142). §4 extends it to a centralized registry-driven probe; §3 adds report rendering. |
| INSTALL-03 | `pip install quirk[all]` installs all extras | §6 — self-referential extras spec, omitting `identity`. |
| INSTALL-04 | Install-time guidance names exact extra | §5 — hint string corpus per registry entry. |
</phase_requirements>

## Summary

Phase 45 generalizes the Phase 41 advisory mechanism (`_emit_missing_extra_advisory` in `run_scan.py:122` and the `scan_error_category="missing_extra"` column added in Phase 41 D-11) into a centralized registry living at `quirk/util/optional_extra.py`. Three changes flow from that: (1) a new `[all]` meta-extra in `pyproject.toml` referencing `quirk[cloud]`, `quirk[db]`, `quirk[motion]`, `quirk[redis]`, `quirk[dashboard]` — explicitly NOT `[identity]`; (2) a single probe call site inserted in `run_scan.main()` after `init_db(cfg.output.db_path)` (line 311) and before any scanner phase begins, so advisory rows are created up-front and naturally flow into the existing `error_endpoints` → `endpoints` merge at line 912; (3) `quirk/engine/risk_engine.py:evaluate_endpoints` gains a fast-path that converts ADVISORY-protocol endpoints into properly-shaped findings dicts with a new `category` key set to `"coverage_gap"`, plus a one-line template addition in `report.html.j2` to render a Coverage Gaps section before "All Findings". Order of work: pyproject extra → registry module → probe call site → risk_engine category mapping → template block → regression tests → docs.

**Primary recommendation:** Reuse Phase 41 wiring as the persistence path; add `category` to the findings dict shape (no DB schema change needed); use a Jinja2 filter on the existing `findings` list for the Coverage Gaps section.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Optional extra probe + registry | Library helper (`quirk/util/`) | — | Pure data + pure import check; no I/O dependencies. |
| Probe invocation | CLI orchestrator (`run_scan.main`) | — | The orchestrator is the only place that has `cfg` AND `error_endpoints` together at the right lifecycle moment (post-config, pre-scan). |
| Advisory persistence | DB persistence (existing path) | — | Already established in Phase 41; ADVISORY rows ride `crypto_endpoints` like any other CryptoEndpoint. |
| Advisory → finding mapping | Risk engine (`evaluate_endpoints`) | — | This function already converts CryptoEndpoint rows into finding dicts; adding a category branch keeps the flow uniform. |
| Coverage Gaps render | Report template (`report.html.j2`) | HTML renderer (`html_renderer.py`) | Filtering by `category=="coverage_gap"` is a one-line Jinja change; renderer doesn't need new args. |
| `[all]` meta-extra | `pyproject.toml` | — | Pure packaging metadata. |

## Standard Stack

No new runtime dependencies. Phase 45 is wholly internal — restructures existing extras and adds a Python helper module.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| importlib (stdlib) | 3.11+ | `importlib.util.find_spec(name)` for non-import availability check | Avoids actually importing the module (so a half-installed dep cannot raise ImportError). [VERIFIED: Python stdlib] |
| setuptools | ≥68 (already pinned in `[build-system]`) | Resolves self-referential extras at build/wheel time | Already in build-system; no change. |

**Version verification:**
- `importlib.util.find_spec` is the canonical "is this importable without importing it" check; behavior unchanged since Python 3.4. [CITED: docs.python.org/3/library/importlib.html#importlib.util.find_spec]
- pip ≥ 21.3 supports self-referential extras (`quirk[motion] = ["quirk[email]", "quirk[broker]"]` is already in use at `pyproject.toml:48`, so pip's support is already implicitly required). [CITED: pip 21.3 release notes — recursive extras resolution]

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────┐
   user CLI ──▶ │ run_scan.main()          │
                │  1. parse args            │
                │  2. load_config           │
                │  3. init_db               │
                │  4. ▶ probe_missing_     │ ◀── NEW (Phase 45)
                │      extras(cfg)          │     │
                │       │                   │     ▼
                │       └──▶ error_endpoints ──┐  ┌────────────────────────┐
                │  5. discovery / fingerprint  │  │ optional_extra.py      │
                │  6. scanner phases ──────────┤  │   REGISTRY:            │
                │       (existing *_AVAILABLE  │  │     extra → (mods,     │
                │        guards still fire,    │  │     scanner_label,     │
                │        D-11)                 │  │     install_hint,      │
                │  7. endpoints = (… +         │  │     enabled_attr)      │
                │     error_endpoints)         │  │   is_extra_available() │
                │  8. evaluate_endpoints ──────┤  │   probe_missing_extras │
                │       │                      │  └────────────────────────┘
                │       └──▶ findings list      │
                │             (advisory rows    │
                │             ▶ category=       │
                │             "coverage_gap")   │
                │  9. db_persist                │
                │ 10. render_html_report ───────┼──▶ report.html.j2
                │                               │      ▼
                └───────────────────────────────┘    [Coverage Gaps section]
                                                     [All Findings table]
```

### Pattern 1: Centralized Registry of (extra, modules, label, hint)

**What:** Single source of truth in `quirk/util/optional_extra.py` mapping each extra to importable modules + display label + install hint string + the `cfg.connectors.enable_*` attribute the probe must consult.

**When to use:** Once. The probe walks the registry; the registry is the only place strings live.

**Example (proposed):**
```python
# quirk/util/optional_extra.py
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Tuple

@dataclass(frozen=True)
class OptionalExtra:
    extra: str            # "identity", "db", "vault", "motion", "redis", "cloud", "dashboard"
    modules: Tuple[str, ...]   # importable module names that the extra installs
    scanner_label: str    # e.g., "kerberos_scanner" (matches Phase 41 advisory host=label)
    install_hint: str     # MUST contain literal "pip install quirk[<extra>]" (D-09)
    enabled_attrs: Tuple[str, ...]  # cfg.connectors attrs that turn this on

REGISTRY: Tuple[OptionalExtra, ...] = (
    OptionalExtra("identity", ("impacket",), "kerberos_scanner",
                  "Kerberos scanning skipped — install quirk[identity] to enable",
                  ("enable_kerberos",)),
    OptionalExtra("db", ("psycopg2", "pymysql"), "db_connector",
                  "Database TLS scanning skipped — install quirk[db] to enable",
                  ("enable_db",)),
    OptionalExtra("cloud", ("googleapiclient", "kubernetes", "hvac"), "cloud_connectors",
                  "Cloud KMS / Vault / K8s scanning skipped — install quirk[cloud] to enable",
                  ("enable_gcp", "enable_k8s", "enable_vault")),
    OptionalExtra("motion", ("sslyze", "kafka"), "motion_scanners",
                  "Email and broker TLS scanning skipped — install quirk[motion] to enable",
                  ("enable_email", "enable_broker")),
    OptionalExtra("redis", ("redis",), "redis_scanner",
                  "Redis TLS scanning skipped — install quirk[redis] to enable",
                  ("enable_broker",)),  # broker covers redis too in current config
    OptionalExtra("dashboard", ("fastapi", "uvicorn", "playwright"), "dashboard",
                  "Dashboard / PDF export unavailable — install quirk[dashboard] to enable",
                  ()),  # dashboard is a `quirk serve` concern, not a scan-time enable
)

def is_extra_available(extra: str) -> bool:
    entry = next((e for e in REGISTRY if e.extra == extra), None)
    if not entry:
        return False
    return all(find_spec(m) is not None for m in entry.modules)

def probe_missing_extras(cfg, error_endpoints) -> None:
    """For each registry entry whose modules are unimportable AND whose
    enabled_attrs flag is True, append a CryptoEndpoint advisory row."""
    for entry in REGISTRY:
        # Config-disabled scanners stay silent (D-08).
        if entry.enabled_attrs and not any(
            getattr(cfg.connectors, a, False) for a in entry.enabled_attrs
        ):
            continue
        if is_extra_available(entry.extra):
            continue
        # One INFO row per missing extra (D-05).
        from quirk.models import CryptoEndpoint
        error_endpoints.append(CryptoEndpoint(
            host=entry.scanner_label,
            port=0,
            protocol="ADVISORY",
            scan_error=entry.install_hint,
            scan_error_category="missing_extra",
        ))
```

**Why this shape:** Mirrors Phase 41's existing `_emit_missing_extra_advisory` row exactly (run_scan.py:136-142), so persistence + the Phase 41 trends.py exclusion (`scan_error_category != "missing_extra"`, see `quirk/intelligence/trends.py:262`) keeps working with zero changes.

### Anti-Patterns to Avoid

- **Don't `import` the optional modules in the registry.** Use `find_spec` only. An `import` triggers ImportError on partial installs (e.g., a broken `cryptography` shadow from a leftover impacket). [CITED: Python `importlib.util` docs]
- **Don't aggregate multiple missing extras into one advisory.** D-05 mandates one-per-scanner so reports stay greppable.
- **Don't add a `[project.optional-dependencies]` `all` that lists all packages flat.** Use self-referential extras (`quirk[cloud]`, etc.) so the SOT stays in the per-extra lists. [CITED: PEP 735 / setuptools docs]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Module availability detection | Custom try/except wrapper | `importlib.util.find_spec` | Doesn't trigger import side effects or partial-install ImportError. |
| Self-referential extras | Manually maintain a flat `all` list of ~25 packages | `all = ["quirk[cloud]", "quirk[db]", ...]` | Single source of truth; per-extra changes don't drift. |
| Advisory finding persistence | New table, new ORM model | Existing `CryptoEndpoint` row with `protocol="ADVISORY"`, `scan_error_category="missing_extra"` | Already wired by Phase 41 (D-11/D-12); risk_engine and trends.py both already understand it. |
| Coverage Gaps section | New PDF/HTML template file | One Jinja `{% set coverage_gaps = findings | selectattr('category', 'equalto', 'coverage_gap') | list %}` block in `report.html.j2` | Filter on existing list — no renderer signature change. |

## Runtime State Inventory

> Phase 45 is a packaging + wiring change. No data migrations are needed.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by reading `quirk/db.py` and `quirk/models.py`. The new advisory rows ride the existing `crypto_endpoints` table; the `scan_error_category="missing_extra"` column already exists from Phase 41 (`quirk/db.py:148-168`). | Code edit only. |
| Live service config | None. Config flags (`enable_*`) consumed read-only. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | None. | None. |
| Build artifacts | `quirk.egg-info/` will be re-emitted after `pip install -e .` rerun (because `pyproject.toml` extras change). | Reinstall `pip install -e '.[all]'` after merge. |

## Common Pitfalls

### Pitfall 1: `find_spec` returns truthy for namespace packages
**What goes wrong:** A namespace-only stub (e.g., a `kafka/` empty dir) returns a spec but `import kafka` still fails.
**Why it happens:** PEP 420 namespace packages are spec'd but unimportable until something fills them.
**How to avoid:** For each registry entry, check at least one **submodule** (e.g., `kafka.client` not just `kafka`) — or use `find_spec(name)` AND `getattr(spec, 'origin', None) is not None`.
**Warning signs:** A clean venv shows the extra "available" but scans still ImportError.

### Pitfall 2: pyOpenSSL transitive resurrection via `[identity]`
**What goes wrong:** Someone "helpfully" adds `[identity]` to `[all]`; impacket pulls pyOpenSSL≥24 which forces `cryptography<43`, downgrading from our `cryptography>=44.0` pin and breaking sslyze.
**Why it happens:** impacket 0.13 still requires pyOpenSSL; pyOpenSSL release cadence trails cryptography. [VERIFIED: pyOpenSSL changelog v24.x requires cryptography<44]
**How to avoid:** §7 regression test asserts impacket is absent in `quirk[all]` resolution. CI gate.
**Warning signs:** TLS scanner suddenly produces zero findings after a version bump.

### Pitfall 3: Probe runs before `error_endpoints` exists
**What goes wrong:** Probe is invoked before line 379 of `run_scan.py` (where `error_endpoints` is initialized) and TypeError fires.
**How to avoid:** §4 specifies invocation point AFTER `error_endpoints` initialization. The probe takes the list as a parameter.

### Pitfall 4: Test patches break when registry list changes
**What goes wrong:** Adding/removing an extra changes the registry tuple; tests patching the registry by index break.
**How to avoid:** Tests patch by `extra` name (`is_extra_available("identity")`) or replace the whole REGISTRY in the patch context, never by index.

## Code Examples

### Existing advisory pattern (Phase 41 — to be generalized, not replaced)
```python
# quirk/run_scan.py:122-142  — existing, kept as the persistence pattern
def _emit_missing_extra_advisory(scanner_name: str, extra_group: str, error_endpoints) -> None:
    print(
        f"[advisory] scanner={scanner_name} extra={extra_group} not installed"
        f" -- run `pip install quirk[{extra_group}]` to enable",
        file=sys.stderr,
    )
    error_endpoints.append(CryptoEndpoint(
        host=scanner_name,
        port=0,
        protocol="ADVISORY",
        scan_error=f"optional extra [{extra_group}] not installed",
        scan_error_category="missing_extra",
    ))
```

### Existing optional-import idiom (Phase 41 D-11 — kept verbatim)
```python
# quirk/scanner/broker_scanner.py:31-56  — DO NOT MIGRATE (D-11)
try:
    from sslyze import (
        ...
    )
    SSLYZE_AVAILABLE = True
except ImportError:
    SslyzeScanner = None  # type: ignore[assignment]
    SSLYZE_AVAILABLE = False
```

### Risk engine: convert ADVISORY rows to coverage_gap findings
```python
# Proposed addition to quirk/engine/risk_engine.py:254 (inside evaluate_endpoints loop)
proto = getattr(e, "protocol", "UNKNOWN")
if proto == "ADVISORY" and getattr(e, "scan_error_category", "") == "missing_extra":
    findings.append({
        "severity": "INFO",
        "category": "coverage_gap",            # NEW field — D-04
        "host": getattr(e, "host", ""),
        "port": 0,
        "title": "Scanner skipped — optional extra not installed",
        "recommendation": getattr(e, "scan_error", ""),  # carries the install hint string
    })
    continue   # do not fall through to the generic "Informational protocol observation" branch
```

### Coverage Gaps section in template
```jinja
{# Proposed insertion in quirk/reports/templates/report.html.j2 just before line 209 #}
{% set coverage_gaps = findings | selectattr('category', 'equalto', 'coverage_gap') | list %}
{% if coverage_gaps %}
<h2>Coverage Gaps</h2>
<p style="color:var(--text-muted)">Scanners that were enabled in config but skipped because their optional extra is not installed. These advisories do not affect the readiness score.</p>
<table>
  <thead><tr><th>Scanner</th><th>Recommendation</th></tr></thead>
  <tbody>
  {% for f in coverage_gaps %}
  <tr><td>{{ f.get('host','') }}</td><td>{{ f.get('recommendation','') }}</td></tr>
  {% endfor %}
  </tbody>
</table>
{% endif %}

{# All Findings table loop should now exclude coverage_gap so they don't appear twice #}
{% for f in findings if f.get('category') != 'coverage_gap' %}
  ...
{% endfor %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-scanner inline `_emit_missing_extra_advisory` calls in `run_scan.py:782, 827` | Centralized registry-driven probe at lifecycle start | Phase 45 | Single source of truth for hint strings; no per-scanner maintenance cost. Existing inline calls remain because D-11 forbids removing them. |
| Flat `all = [...]` package list | Self-referential `all = ["quirk[cloud]", ...]` | pip 21.3+ (already implicitly required by current `motion = ["quirk[email]", ...]`) | Per-extra changes propagate automatically. |

**Deprecated/outdated:** None.

---

## 2. FindingItem Schema — Field Name Recommendation

**Critical correction:** The CONTEXT.md statement "FindingItem model in `quirk/models.py`" is inaccurate. There is no `FindingItem` ORM model in `quirk/models.py`. The file defines only one ORM class — `CryptoEndpoint` (`quirk/models.py:9`). Findings are NOT a SQLAlchemy table; they are **dicts produced on-the-fly by `quirk/engine/risk_engine.py:evaluate_endpoints` from CryptoEndpoint rows** (`risk_engine.py:246-252`), then passed in-memory to the renderer.

The Pydantic `FindingItem` (`quirk/dashboard/api/schemas.py:44-55`) is the dashboard API DTO, not the persistence schema:
```python
# quirk/dashboard/api/schemas.py:44-54
class FindingItem(BaseModel):
    id: Optional[int] = None
    host: str
    port: int
    severity: str        # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None   # quantum-safety label
    source: Optional[str] = None        # scanner type
```

### Recommended field name: **`category`**

**Why `category`:**
1. `quirk/models.py:36` already uses `scan_error_category` for the same conceptual axis ("what kind of thing is this?") — a sibling `category` on the finding dict mirrors that vocabulary.
2. The risk engine's existing helper is named `_error_category` (`quirk/engine/risk_engine.py:116`). Identical noun = same concept.
3. Phase 41's column literal `category="missing_extra"` (referenced in `trends.py:256`) already establishes "category" as the project's chosen word for this axis.
4. Pydantic dashboard `FindingItem` does NOT use `kind` or `finding_type` for any field — `category` introduces no naming clash.

**Insertion guidance:**
- Risk engine: add `"category": "coverage_gap"` to the dict produced for ADVISORY rows (see §"Code Examples" above).
- Dashboard `FindingItem` (Pydantic): add `category: Optional[str] = None` — additive, default None, preserves backward compatibility.
- TypeScript mirror (`src/dashboard/src/types/api.ts` per the schemas.py docstring): add `category?: string`.
- ORM (`quirk/models.py`): no change required. The category lives on the in-memory finding dict; persistence to SQLite is via the already-existing `crypto_endpoints.scan_error_category` column populated by the advisory CryptoEndpoint row.

**Other names rejected:**
- `kind` — not used in the project's existing vocabulary.
- `finding_type` — too verbose; redundant with the dict already being a finding.
- `class` — Python keyword.

## 3. Coverage Gaps Render Path — Decision

**Recommendation: filtered render of existing INFO findings list, with one new section header inserted before "All Findings".**

**Justification:**
- `quirk/reports/html_renderer.py:78-95` calls `template.render(... findings=findings or [], ...)` — the renderer signature is fixed and doesn't take separate lists. Adding a parameter ripples to `run_scan.py` and `quirk/dashboard/api/routes/scan.py` callers (run_scan.py:929 area is the only producer, but the dashboard renders too).
- `report.html.j2:214-222` already iterates `findings` once. Adding a `selectattr('category','equalto','coverage_gap')` filter is one Jinja line.
- The "All Findings" table at line 214 must be amended with `if f.get('category') != 'coverage_gap'` so coverage gaps don't double-render.

**Anchor in template:**
- Insert new `<h2>Coverage Gaps</h2>` block at line 209 (immediately before `<h2>All Findings</h2>`).
- Modify `{% for f in findings %}` at line 214 → `{% for f in findings if f.get('category') != 'coverage_gap' %}`.
- Modify `{% for sev in ['CRITICAL','HIGH','MEDIUM','LOW','INFO'] %}` severity counts at line 155 to also exclude coverage_gap (since D-07 says "no impact on score" — count display should also not inflate the INFO count). Use a pre-filtered list inside the renderer (`html_renderer.py:69-72`) by computing `sev_counts` only over `[f for f in findings if f.get('category') != 'coverage_gap']`.

**Why NOT a new template block file:** Would require renderer signature change and an additional Jinja file in `quirk/reports/templates/` package data — more surface area for the same outcome.

## 4. Probe Call Site — Precise Insertion Point

**File:** `run_scan.py`
**Insertion line:** Between line 379 (where `error_endpoints` is initialized) and line 382 (start of TLS-discovery work). Concretely, **immediately after line 379**.

**Lifecycle ordering rationale:**
1. **Must be after `init_db(cfg.output.db_path)` at line 311** — so the DB exists when the advisory CryptoEndpoint rows are eventually persisted at the end of the scan.
2. **Must be after `error_endpoints: List[CryptoEndpoint] = []` at line 379** — so the probe has a list to append into.
3. **Must be before any scanner phase begins (line 384 onwards: `_fp_task` definition; line 408+ inventory build)** — so all advisories exist in `error_endpoints` before the merge at line 912.
4. **Should be after config materialization** (line 282 + lines 300-311) — so `cfg.connectors.enable_*` flags reflect user input.

**Surrounding code (run_scan.py:374-384):**
```python
374    inventory_endpoints: List[CryptoEndpoint] = []
375    # Phase 41 / D-12 + D-14: scanner-phase failure surface — both missing-extra
376    # advisory rows (category='missing_extra') and BaseException-captured rows
377    # (category='exception') flow through this list and merge into the main
378    # endpoints list before risk_engine / db_persist / write_reports.
379    error_endpoints: List[CryptoEndpoint] = []
        # ─── INSERT HERE ───────────────────────────────────────────
        # Phase 45 / D-08: probe optional extras up-front. Each enabled-but-
        # unavailable extra produces one CryptoEndpoint advisory row that
        # flows into endpoints (line 912) and becomes a coverage_gap
        # finding (risk_engine).
        from quirk.util.optional_extra import probe_missing_extras
        probe_missing_extras(cfg, error_endpoints)
        # ───────────────────────────────────────────────────────────
380    tls_targets: List[Tuple[str, int]] = []
381    ssh_targets: List[Tuple[str, int]] = []
382    classified_details: Dict[Tuple[str, int], str] = {}
```

**Why not earlier (e.g., right after line 311):** `error_endpoints` does not exist yet. Initializing it earlier would require moving line 379 up, which is a needless drift.

**Why not later:** After scanner phases begin, the existing per-scanner advisories (run_scan.py:782, 827) already emit. Running the centralized probe later would risk double-emitting if D-11's existing inline calls fire for the same extra. By probing before any scanner phase, the registry has first-and-only say for the registry-covered extras; the existing inline `_emit_missing_extra_advisory` calls for `email_scanner` / `broker_scanner` (run_scan.py:782, 827) need to be **left alone per D-11** but they will still fire — risking duplicate advisories. **Mitigation:** in the registry's `motion` entry, leave detection to the existing inline calls and EITHER (a) skip the `motion` entry in the central probe entirely, OR (b) deduplicate by (host, scan_error_category) before persistence. **Recommendation: option (a)** — let the existing Phase 41 inline calls keep emitting for `email_scanner` / `broker_scanner` and have the centralized registry only cover `identity`, `db`, `cloud`, `dashboard` (the genuinely new coverage). Note this carefully in the planner brief; this is the trickiest interaction in the phase.

## 5. Install-Hint String Corpus

Each hint string is **persisted as the `scan_error` column on the advisory CryptoEndpoint row** and **becomes the `recommendation` field on the resulting finding dict** (the user-visible string in the report). Each MUST contain the literal `pip install quirk[<extra>]` (D-09).

| extra | modules | scanner_label (`host` field) | install_hint |
|-------|---------|------------------------------|--------------|
| `identity` | `impacket` | `kerberos_scanner` | `Kerberos scanning skipped — run \`pip install quirk[identity]\` to enable` |
| `db` | `psycopg2`, `pymysql` | `db_connector` | `Database TLS scanning (PostgreSQL/MySQL) skipped — run \`pip install quirk[db]\` to enable` |
| `cloud` | `googleapiclient`, `kubernetes`, `hvac` | `cloud_connectors` | `GCP / Kubernetes / HashiCorp Vault scanning skipped — run \`pip install quirk[cloud]\` to enable` |
| `motion` | `sslyze`, `kafka` | `motion_scanners` | (HANDLED BY EXISTING PHASE 41 INLINE CALLS — see §4 caveat; if registry covers it, use:) `Email and broker TLS scanning skipped — run \`pip install quirk[motion]\` to enable` |
| `redis` | `redis` | `redis_scanner` | `Redis TLS scanning skipped — run \`pip install quirk[redis]\` to enable` |
| `dashboard` | `fastapi`, `uvicorn`, `playwright` | `dashboard` | `Web dashboard / PDF export unavailable — run \`pip install quirk[dashboard]\` to enable` |

**Note:** Backticks around `pip install quirk[<extra>]` matter — they survive HTML escaping in the Jinja template and cue the user that this is a literal command. The Phase 41 existing string uses backticks already (`run_scan.py:133`) — preserve the convention.

**Identity caveat (INSTALL-04 + D-01):** Even though `[identity]` is excluded from `[all]` (D-01), the hint must still tell the user to run `pip install quirk[identity]` if they specifically need Kerberos. The exclusion from `[all]` is about default convenience, not deprecation.

## 6. `[all]` Meta-Extra Recipe

**Proposed pyproject.toml addition:**
```toml
[project.optional-dependencies]
# ... existing extras unchanged ...
all = [
    "quirk[cloud]",
    "quirk[db]",
    "quirk[motion]",
    "quirk[redis]",
    "quirk[dashboard]",
]
# NOTE: quirk[identity] is INTENTIONALLY EXCLUDED — impacket transitively
# pulls pyOpenSSL which downgrades cryptography and breaks the TLS scanner.
# See Phase 45 / D-01. CI test test_install_all_excludes_impacket guards this.
```

**Self-referential extras spec:** PEP 508 allows the project's own name (with extras) inside `[project.optional-dependencies]` lists. The mechanism is documented in setuptools' user guide on declaring optional dependencies and in PEP 735's evolution discussion. The project already exercises this at `pyproject.toml:48` (`motion = ["quirk[email]", "quirk[broker]", "quirk[kafka]"]`), confirming the toolchain handles it. [CITED: setuptools userguide — "Declaring optional dependencies"; PEP 735]

**Install-tool compatibility:**
- pip ≥ 21.3 — full self-referential extras support. [CITED: pip 21.3 changelog]
- uv (any current release) — full support. [CITED: uv docs — pyproject.toml extras]
- Older pip (< 21.3) — would error on the existing `motion` extra already; project already implicitly requires pip 21.3+.

**Action item:** Add a note to `docs/installation.md` "System Requirements" (line 7+) that pip ≥ 21.3 is required.

## 7. Regression Test Design — `[all]` Excludes impacket

**Three options evaluated:**

| Option | Mechanism | Pros | Cons | CI cost |
|--------|-----------|------|------|---------|
| **(a) Parse `pip install --dry-run --report -` JSON** | `pip install --dry-run --report - quirk[all]` produces JSON resolution report; assert `impacket` not in `install` array | Pure Python parsing; no network beyond resolution; deterministic | Requires pip ≥ 22.2 for `--report -` to stdout; slow (~10s per CI run) | Low — one subprocess call |
| **(b) Post-install `import impacket` should fail** | In a clean venv, `pip install -e '.[all]'` then `python -c "import impacket"` should `exit 1` | Most realistic — tests resolved environment | Slow (~30s); requires fresh venv per CI; flaky on PyPI mirrors | Medium-high |
| **(c) Inspect resolved metadata via `pip install --dry-run` + grep** | `pip install --dry-run -e '.[all]' 2>&1 \| grep -v impacket` | Simple shell test | No structured output pre-pip-22.2; brittle string matching | Low |

**Recommendation: (a) — `pip install --dry-run --report` JSON parsing.**

**Reference test:**
```python
# tests/test_install_all_excludes_impacket.py
import json
import subprocess
import sys
from pathlib import Path

def test_install_all_excludes_impacket(tmp_path: Path):
    """Phase 45 D-01: pip install quirk[all] MUST NOT pull impacket.
    Hard constraint — impacket→pyOpenSSL→cryptography downgrade breaks TLS scanner."""
    repo_root = Path(__file__).parent.parent
    report_file = tmp_path / "report.json"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install",
         "--dry-run", "--ignore-installed", "--quiet",
         "--report", str(report_file),
         "-e", f"{repo_root}[all]"],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"
    report = json.loads(report_file.read_text())
    installed = {item["metadata"]["name"].lower() for item in report.get("install", [])}
    assert "impacket" not in installed, (
        "REGRESSION: quirk[all] now resolves impacket. "
        "This pulls pyOpenSSL which downgrades cryptography and breaks the TLS scanner. "
        "See Phase 45 / D-01."
    )
```

**CI considerations:**
- Mark with `@pytest.mark.slow` so the default test run skips it; CI runs `pytest -m slow` separately.
- Requires network access to PyPI for resolution; CI must have egress.
- Pin `pip>=22.2` in CI image (the `--report -` flag landed in pip 22.2). [CITED: pip 22.2 changelog]
- Alternative if CI is offline: option (c) using `pip install --dry-run` text output and a grep, as a fallback.

## 8. pyOpenSSL Conflict Trace

**Chain:**
```
quirk[identity]
  └─ impacket >= 0.13.0, < 0.14
        └─ pyOpenSSL  (transitive)
              └─ cryptography (constraint may force downgrade)
                    ▲
                    │  CONFLICT
                    │
quirk core deps
  └─ cryptography >= 44.0   (pyproject.toml:13)
        ▲
        │  pulled by
        │
sslyze 6.2.0  (used by tls_scanner.py, email_scanner.py, broker_scanner.py)
  └─ cryptography  (current resolved: 44.0.1, verified via `pip show`)
```

**Constraints (verified):**
- `pyproject.toml:13` pins `cryptography>=44.0` (HIGH confidence — read directly).
- `pip show cryptography` returns 44.0.1 in the current QUIRK venv (VERIFIED).
- `pip show sslyze` returns 6.2.0 with `Requires: cryptography, nassl, pydantic, tls-parser` (VERIFIED).
- impacket 0.13.x bundles pyOpenSSL as a runtime dep. pyOpenSSL 24.x supports `cryptography>=41,<45`; pyOpenSSL 23.x caps at `cryptography<43`. [CITED: pyOpenSSL changelog — historical caps] **MEDIUM confidence — exact pin depends on which pyOpenSSL version impacket's deps resolve to in user's env; behavior is empirically observed to break TLS scanner per the user's lived experience driving D-01.**

**Conclusion:** The conflict is real and the user has chosen exclusion as the structural fix. Phase 45 codifies the fix; verification belongs to the §7 regression test rather than to research.

## 9. Existing `*_AVAILABLE` Inventory — Do-Not-Migrate Surface (D-11)

| Module | Flag | Patch points | Test references |
|--------|------|--------------|-----------------|
| `quirk/scanner/tls_scanner.py:30` | `SSLYZE_AVAILABLE` | (no `*Scanner = None` — uses different shape) | (verify before edit) |
| `quirk/scanner/email_scanner.py:44` | `SSLYZE_AVAILABLE` | `SslyzeScanner = None` (line 50) | `tests/test_infra03_nyquist_coverage.py:82` patches `quirk.scanner.email_scanner.SSLYZE_AVAILABLE` |
| `quirk/scanner/broker_scanner.py:40` | `SSLYZE_AVAILABLE` | `SslyzeScanner = None` (line 42) | `tests/test_infra03_nyquist_coverage.py:139, 188, 238` patch `quirk.scanner.broker_scanner.SSLYZE_AVAILABLE` |
| `quirk/scanner/broker_scanner.py:61` | `KAFKA_AVAILABLE` | (kafka import) | (verify) |
| `quirk/scanner/broker_scanner.py:71` | `REDIS_AVAILABLE` | (redis import) | (verify) |
| `quirk/scanner/aws_connector.py:20` | `BOTO3_AVAILABLE` | (boto3 in core deps; flag exists for safety) | (verify) |
| `quirk/scanner/azure_connector.py:23` | `AZURE_AVAILABLE` | (azure in core deps) | (verify) |
| `quirk/scanner/gcp_connector.py:27` | `GCP_AVAILABLE` | (verify) | (verify) |
| `quirk/scanner/kerberos_scanner.py:10` | `IMPACKET_AVAILABLE` | (multiple impacket symbols imported) | (verify) |
| `quirk/scanner/db_connector.py:23, 30` | `PSYCOPG2_AVAILABLE`, `PYMYSQL_AVAILABLE` | (verify) | (verify) |
| `quirk/scanner/jwt_scanner.py:13` | `HTTPX_AVAILABLE` | (httpx in core deps; redundant safety) | (verify) |
| `quirk/scanner/k8s_connector.py:38, 55, 76` | `K8S_AVAILABLE`, `GKE_AVAILABLE`, `AKS_AVAILABLE` | (verify) | (verify) |
| `quirk/scanner/vault_connector.py:44` | `HVAC_AVAILABLE` | `hvac = None` (line 46) | `tests/test_vault_connector.py:132, 140, 156, 176, 201, 271, 344, 361, 426` patch `quirk.scanner.vault_connector.HVAC_AVAILABLE` |

**Implication for Phase 45:** the new helper coexists with these flags. The centralized probe runs once at scan start and uses `find_spec` on the *extra-level* module set; the per-scanner `*_AVAILABLE` flags continue to gate per-scanner entry points and remain the patching surface for existing tests.

**Why "do not migrate" is the right call:** All 9 test files listed above patch module-level flag names. Migrating to `is_extra_available()` would force renaming patch targets across these files, with zero functional gain in this phase.

## 10. Docs Update Locations

**`docs/installation.md`:**
- **Line 116-128 ("Optional Dependencies" table):** Add a row for the new `[all]` meta-extra at the top.
  - `| All optional scanners (recommended for consultants) | \`pip install quirk[all]\` — installs cloud, db, motion, redis, dashboard. **Excludes \`[identity]\`** (impacket pyOpenSSL conflict). Also installs Playwright browser binaries (~250MB). |`
- **Line 7 ("System Requirements"):** Add `pip ≥ 21.3 (for self-referential extras resolution)`.
- **New subsection after line 128 ("Why \`[all]\` excludes \`[identity]\`"):** 1-paragraph explanation of the impacket / pyOpenSSL / cryptography downgrade conflict so consultants understand why they must run `pip install quirk[all] quirk[identity]` in a separate venv if they need Kerberos.
- **New subsection after line 138 ("Verify Installation"):** Mention that running `quirk` in a venv missing optional extras will produce visible advisory findings (not crashes), with a sample one-liner showing the advisory format.

**`docs/UAT-SERIES.md`:** Per project's CLAUDE.md mandatory phase-completion steps, add new test cases to the relevant series:
- A test that asserts a TLS-only scan in a clean `pip install quirk` venv produces **zero** ImportError tracebacks (INSTALL-01).
- A test that asserts a scan with all `enable_*` flags set in a clean `pip install quirk` venv produces **6** advisory findings (one per registry entry where the extra is uninstalled) (INSTALL-02).
- A test that asserts `pip install quirk[all]` succeeds and `python -c "import impacket"` fails (INSTALL-03 + D-01).

**No update needed** to `docs/configuration.md`, `docs/getting-started.md`, or connector guides — coverage gaps surface in the report, not in config flags.

## Project Constraints (from CLAUDE.md)

- **PEP 8** — applies to `quirk/util/optional_extra.py`.
- **Minimal diffs** — no refactor of existing scanners; the new helper is additive (D-11 alignment).
- After changes, run `python -m compileall` and relevant tests.
- **Mandatory phase completion steps:** create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-45-Install-Day-UX.md`; update `docs/UAT-SERIES.md`; sync to vault; commit `docs/UAT-SERIES.md`.
- **Chaos lab maintenance** — N/A for this phase (no compose changes).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing — `pyproject.toml [tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` (testpaths=`tests`, addopts=`-m 'not slow'`) |
| Quick run command | `pytest tests/test_optional_extra.py -x` |
| Full suite command | `pytest` (excludes slow) + `pytest -m slow` (CI only) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INSTALL-01 | TLS-only scan in minimal venv produces no ImportError | unit (mock find_spec) | `pytest tests/test_optional_extra.py::test_no_importerror_when_extras_missing -x` | ❌ Wave 0 |
| INSTALL-02 | One advisory per enabled-but-missing scanner | unit | `pytest tests/test_optional_extra.py::test_probe_emits_one_advisory_per_missing_extra -x` | ❌ Wave 0 |
| INSTALL-02 | Coverage Gaps section renders in HTML report | unit (template render) | `pytest tests/test_html_renderer_coverage_gaps.py -x` | ❌ Wave 0 |
| INSTALL-02 | risk_engine maps ADVISORY rows to coverage_gap finding | unit | `pytest tests/test_risk_engine.py::test_advisory_row_becomes_coverage_gap_finding -x` | ❌ Wave 0 |
| INSTALL-03 | `pip install quirk[all]` succeeds + impacket absent | integration / slow | `pytest -m slow tests/test_install_all_excludes_impacket.py -x` | ❌ Wave 0 |
| INSTALL-04 | Hint string contains literal `pip install quirk[<extra>]` | unit | `pytest tests/test_optional_extra.py::test_all_hints_contain_pip_install_literal -x` | ❌ Wave 0 |
| D-07 | Coverage gap findings excluded from severity counts in renderer | unit | `pytest tests/test_html_renderer_coverage_gaps.py::test_sev_counts_exclude_coverage_gap -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_optional_extra.py tests/test_html_renderer_coverage_gaps.py -x`
- **Per wave merge:** `pytest` (full default suite, excludes slow)
- **Phase gate:** `pytest` + `pytest -m slow tests/test_install_all_excludes_impacket.py` both green

### Wave 0 Gaps
- [ ] `tests/test_optional_extra.py` — covers INSTALL-01, INSTALL-02 (probe behavior), INSTALL-04
- [ ] `tests/test_html_renderer_coverage_gaps.py` — covers INSTALL-02 (rendering) + D-07
- [ ] `tests/test_install_all_excludes_impacket.py` — covers INSTALL-03 + D-01 (slow-marked)
- [ ] Add coverage_gap branch tests to existing `tests/test_risk_engine.py` (or create if absent)

## Security Domain

> Phase 45 is install-UX wiring. No new attack surface, no new data flows.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (light) | Hint strings are static literals; install-hint must NEVER be derived from user input. Registry is module-level constant. |
| V6 Cryptography | yes (preventive) | The whole phase exists to prevent the impacket/pyOpenSSL/cryptography downgrade — a cryptographic-control regression. §7 regression test is the V6 control. |

### Known Threat Patterns for {Python packaging + import probe}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dependency confusion / malicious extra | Tampering | All extras are first-party PyPI packages with explicit version pins; no wildcard versions. |
| Transitive downgrade of crypto library | Tampering | §7 regression test asserts impacket exclusion; CI gate. |
| Hint-string injection | Tampering | Registry strings are module-level constants, never f-string-interpolated from runtime data. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | impacket 0.13 + pyOpenSSL 24 forces `cryptography<44` in some resolution paths | §8 | LOW — user's lived experience drives D-01 regardless; the regression test is the structural guard, not the version trace. |
| A2 | pip 22.2's `--report -` produces JSON usable for impacket-exclusion assertion | §7 | MEDIUM — fallback to grep on `--dry-run` text output if JSON report shape changes. |
| A3 | `find_spec` correctly returns None for fully-uninstalled modules in our target Python (3.11+) on macOS, Linux, WSL2 | §"Pattern 1" | LOW — stdlib behavior, stable since 3.4. |
| A4 | The Phase 41 inline advisory calls at `run_scan.py:782, 827` should be left in place and the registry should NOT cover `motion` (to avoid duplicate emissions) | §4 caveat | MEDIUM — alternative: deduplicate on (host, scan_error_category) post-merge. Planner should pick. |
| A5 | The dashboard API (`quirk/dashboard/api/routes/scan.py`) reads findings from the same path and will surface coverage_gap rows once the field is added to the Pydantic FindingItem | §2 | MEDIUM — verify the dashboard's findings query path during planning; out of strict scope but adjacent. |

## Open Questions for Planner

1. **A4 — duplicate-advisory mitigation strategy.** Should the centralized registry skip `motion` (option a) and let Phase 41 inline calls keep firing, OR cover `motion` and add a post-merge dedupe (option b)? **Recommendation: option (a)** — minimal diff, respects D-11 strictest reading, keeps existing tests passing without changes.

2. **Should the `redis` extra registry entry be merged into `motion`?** `motion = ["quirk[email]", "quirk[broker]", "quirk[kafka]"]` already pulls broker which transitively pulls redis. The standalone `redis = ["redis>=5.0"]` extra is somewhat redundant. **Recommendation: leave as-is** — D-01 explicitly listed `redis` in `[all]`'s expansion, so honor user intent.

3. **Should the dashboard's `FindingItem` Pydantic schema gain `category` in this phase?** It's outside the strict server-side risk_engine scope, but the dashboard would otherwise drop the field. **Recommendation: yes, add it** — additive, default None, preserves backward compatibility with the TS mirror.

## Sources

### Primary (HIGH confidence)
- `quirk/models.py:9-88` — schema reality (no FindingItem ORM; `scan_error_category` exists at line 36)
- `quirk/db.py:148-168` — Phase 41 column migration for `scan_error_category`
- `quirk/engine/risk_engine.py:246-291` — finding production for ADVISORY rows
- `quirk/run_scan.py:122-142, 311, 374-384, 779-832, 900-930` — full lifecycle map
- `quirk/reports/html_renderer.py:46-95` — renderer signature
- `quirk/reports/templates/report.html.j2:155, 209-227` — template insertion anchors
- `pyproject.toml:30-54` — current extras (verified self-referential pattern in use)

### Secondary (MEDIUM confidence)
- pip 21.3 changelog — self-referential extras support (pip docs)
- pip 22.2 changelog — `--report -` JSON output (pip docs)
- setuptools userguide — declaring optional dependencies

### Tertiary (LOW confidence — flagged in Assumptions Log)
- pyOpenSSL ↔ cryptography pin chain — empirical (driven by user's D-01 decision)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib + existing toolchain.
- Architecture: HIGH — phase 41 already proved the persistence path; this phase generalizes.
- Pitfalls: HIGH — namespace package and double-emission risks identified by direct code reading.
- Schema field name: HIGH — `category` is consistent with `scan_error_category` and `_error_category` already in the codebase.
- pyOpenSSL conflict trace: MEDIUM — user-driven; structural guard is the test, not the trace.

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days; stable Python packaging surface)

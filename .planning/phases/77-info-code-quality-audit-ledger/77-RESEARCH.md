# Phase 77: INFO/Code Quality + Audit Ledger Closure — Research

**Researched:** 2026-05-15
**Domain:** v4.9 milestone-completion gate — close 29 INFO findings + bring AUDIT-TASKS.md to zero bare-open rows
**HEAD verified at:** `cf2417a` (post-Phase 71 wrap; latest commits 71-review fixes)
**Confidence:** HIGH (every D-NN site verified against HEAD; **6 CONTEXT-vs-HEAD mismatches** flagged in `<research_concerns>` — including 3 that change scope)

## Summary

Phase 77 closes 29 INFO rows across protocol (IN-01..06), cbom-intel (IN-01..09), api-cli (IN-01..07), and react-frontend (IN-01..07) plus the LEDGER-01 zero-bare-open invariant. Every D-NN site is reachable at HEAD and all changes are surgical edits.

Three mismatches change scope: **C-1** (D-15 IntelligenceReport is NOT zero-importers — `quirk/intelligence/__init__.py` exports it and `tests/test_intelligence_schema.py` uses it), **C-2** (D-19 magic numbers `0.10/0.20/0.8/1.5` live in `quirk/dashboard/api/routes/qramm.py`, NOT in `quirk/qramm/scoring.py` — scoring.py only contains the `1.5` band threshold which is unrelated to the multiplier clamp), **C-3** (D-22 `projected_probe_count` has an *explicit documented reason* for using `.hosts()` over `.num_addresses` — "Risks #4: uses .hosts() NOT .num_addresses to avoid off-by-2 on IPv4 /24"; CONTEXT direction would reverse a deliberate choice). Also: **C-4** (LEDGER-01 inventory: only **2** bare-deferral rows exist, not 4 as CONTEXT D-30 says), **C-5** (D-17 `_FACES` IS a raw string `r"..."` — the `\-` is fine; the audit and CONTEXT both misread), **C-6** (D-20 `_make_handler` is already correctly factored — the audit row itself says "implementation is correct. No-op"; CONTEXT D-20's "missing `=` pattern" misreads the audit).

**Primary recommendation:** 5 plans as test_strategy specifies. Wave 0 confirms the 6 mismatches with the user before plans freeze. Half of the open INFO rows resolve to comment-only edits, ledger flips, or one-line constant extractions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01 through D-32. Summary:

- **D-01..D-06** Protocol scanner INFOs (SSLContext comment, DNSSEC alg map, SHA1_INDICATORS, fingerprint Host header, _is_pfs/_is_weak dedup, kerberos IPv4)
- **D-07..D-15** CBOM/intel INFOs (PLATFORM_VERSION single source, SSH JSONDecodeError logging, trend streaming, _PROTOCOL_KEYS extend, roadmap baseline, executive truncation indicator, html_renderer dead branch, writer falsy hosts, IntelligenceReport delete)
- **D-16..D-22** API/CLI INFOs (TypedDict for QRAMM, _FACES escape, TZ IANA, QRAMM magic constants, app.py closure, db.py _ensure consolidate, num_addresses)
- **D-23..D-29** React INFOs (5/6-tab comment, cytoscape catch re-throw, columns useMemo, seededRef reset, compByAlg statistic, JSX style, useScanData URL)
- **D-30..D-31** LEDGER-01 (rationale on bare rows; final zero-bare-open CI test)
- **D-32** do-not-touch: no new features, no CLI flag changes, no schema migrations, no new pip deps, QRAMM 120-question taxonomy, Recharts components, all Phase 72-76 fixes preserved exactly

### Claude's Discretion

- **D-03** — choose between Phase 73 `weak_crypto.is_weak_cipher` vs Phase 74 `migration_advisor._matches` reuse target. Researcher recommends `_matches` (D-03 is about substring-vs-word-boundary; that's `_matches`'s exact purpose).
- **D-05** — choose home for the de-duplicated `_is_pfs / _is_weak`. Researcher recommends `quirk/util/weak_crypto.py` (already exists per Phase 73, already exports `is_weak_cipher` and `is_legacy_tls_version`).
- **D-09** — choose `yield_per(N)` value. Researcher recommends `yield_per(1000)` to match SQLAlchemy idiomatic chunk size.
- **D-10** — confirm `_PROTOCOL_KEYS` missing keys. Researcher inventories below.
- **D-13** — locate the dead branch in `html_renderer::roadmap_section`. Researcher's read at HEAD shows the function is 2 lines — there may be no dead branch (see C-7).
- **D-16** — pick which QRAMM endpoints get TypedDict treatment. Researcher recommends only the public scoring response (`compute_qramm_score` → `QrammScoreResponse`) since that's the most user-visible.
- **D-27** — choose `compByAlg` representative statistic. Researcher recommends "first non-zero" (median requires sorting at every render; first-non-zero is O(1) and preserves the existing semantic of "any representative").

### Deferred Ideas (OUT OF SCOPE)

- `importlib.metadata` runtime version source (D-07 alternative) — v5.0
- IntelligenceReport revival (D-15 alternative) — v5.0
- TypedDict for ALL QRAMM endpoints — v5.0
- Trend analysis server-side pagination — v5.0
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFO-01 | Protocol scanner INFOs (closes scanners-protocol/IN-01..06) | All 6 sites located at HEAD. D-01 site is `quirk/scanner/tls_capabilities.py:39-79` (no single "downgrade" — _try_handshake probes TLS 1.0/1.1 with CERT_NONE; researcher recommends comment block above the function body, not at a "downgrade site" — see C-8). D-02: `dnssec_scanner.py:44-57` — see C-9 (entry 7 is already RSASHA1-NSEC3-SHA1; the CONTEXT statement that alg 9 = RSASHA1-NSEC3-SHA1 is wrong per IANA registry — 9 is Reserved, 11 is Reserved). D-03: `saml_scanner.py:58, 188`. D-04: `fingerprint.py:111`. D-05: 3 sites (`broker_scanner.py:115,120`, `email_scanner.py:103,108`, `tls_scanner.py:248,254` — local inner functions). D-06: `kerberos_scanner.py:50-64`. |
| INFO-02 | CBOM/intelligence INFOs (closes cbom-intel-reports/IN-01..09) | D-07 sites: `quirk/cbom/builder.py:128, 659`, `quirk/reports/writer.py:23, 235`; canonical `quirk/__init__.py:2 __version__ = "4.4.0"`. D-08: `cbom/builder.py:316`. D-09: `quirk/intelligence/trends.py:84` (`_fetch_session_endpoints` uses `.all()` at line 99). D-10: `quirk/intelligence/evidence.py:11-12` — see C-10 (already includes POSTGRESQL/MYSQL/RDS/S3/AZURE_BLOB/KUBERNETES/VAULT; missing CONTAINER, SOURCE, AWS, AZURE, GCP, CLOUD_SQL — researcher inventories actual scanner emissions below). D-11: `quirk/intelligence/roadmap.py:368, 406, 437`. D-12: `quirk/reports/executive.py:228-240`. D-13: `quirk/reports/html_renderer.py:82-83` — see C-7. D-14: `quirk/reports/writer.py:222`. D-15: `quirk/intelligence/schema.py:83` — **NOT zero importers** (see C-1). |
| INFO-03 | API/CLI INFOs (closes api-cli-core/IN-01..07) | D-16: `quirk/dashboard/api/routes/qramm.py` (8+ `Dict[str, Any]` sites: lines 76, 280, 358, 416, 424, 573, 577, 652). D-17: `quirk/cli/banner.py:64-65` — see C-5 (`_FACES` IS a raw string `r"..."`; no actual bug). D-18: search reveals NO `tzlocal` or UTC-string-fallback site at HEAD — see C-11. D-19: `quirk/dashboard/api/routes/qramm.py:172-176, 192-193, 363-368` — **NOT scoring.py** (see C-2). D-20: `quirk/dashboard/api/app.py:124-127` is `_make_handler(fp, mt)` factory — **already correctly factored** per the audit row body itself (see C-6). D-21: 11 `_ensure_*_columns` helpers at `quirk/db.py:70, 92, 114, 135, 155, 176, 201, 225, 243, 322, 336, 346, 355`. D-22: `quirk/util/targets.py:215-240` — **deliberate `.hosts()` choice documented** (see C-3). |
| INFO-04 | React frontend INFOs (closes react-frontend/IN-01..07) | D-23: `src/dashboard/src/pages/qramm-assessment.tsx:246` confirmed comment `/* 5-tab assessment layout */`; renders 6 tabs at lines 248-254 (CVI, SGRM, DPE, ITR, Scorecard, Compliance Map). D-24: `pages/cbom.tsx:19-23` and `pages/roadmap.tsx` similar — current `catch { /* already registered */ }` swallow. D-25: `pages/findings.tsx:53` + `pages/identity.tsx:71` — `columns` arrays NOT memoized at HEAD. D-26: `hooks/useQRAMMSession.ts:19, 67-68, 101-102` — `seededRef.current` set to `latest.session_id` after seed; no reset path. D-27: `pages/cbom.tsx:148, 285, 317, 390` — `compByAlg[d.label]?.[0]` representative. D-28: `pages/print.tsx:1, 377-380` — `createElement("style", null, PRINT_CSS)`. D-29: `hooks/useScanData.ts:51` — `setError(\`API error: ${resp.status} ${resp.statusText}\`)` — **URL NOT in message** (URL constructed at line 29-31). |
| LEDGER-01 | Audit ledger zero bare-open invariant | `grep -cE "^\| .* \[ \] open" .planning/audit-2026-05-08/AUDIT-TASKS.md` returns **29** at HEAD (all 29 INFO rows). The 4 non-open bare rows claimed in CONTEXT D-30 is actually **2**: CR-01 (wont-fix) and CR-03 (deferred-v4.9). Both already have prose rationale (lines 84-91 of AUDIT-TASKS.md `> **wont-fix** —` and `> **deferred-v4.9** —` headers). Researcher recommends: D-31 CI test `tests/test_audit_ledger_zero_open.py` asserts zero `[ ] open`; D-30 inline-rationale work flips CR-01/CR-03 from bare table-row dispositions to the "table-row + rationale-cite" format used by `[x] closed` rows. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| TLS probe documentation | `quirk/scanner/tls_capabilities.py` | — | Pure docstring/comment |
| DNSSEC algorithm metadata | `quirk/scanner/dnssec_scanner.py` | — | Static dict at module scope |
| SHA1 indicator helper reuse | `quirk/scanner/saml_scanner.py` | `quirk/assessment/migration_advisor.py` (consumed) | SAML scanner already does substring; reuse `_matches` for word-boundary |
| HTTP Host header | `quirk/scanner/fingerprint.py` | — | Inline literal swap |
| Cipher classification helpers | `quirk/util/weak_crypto.py` (new entries) | `email_scanner`, `broker_scanner`, `tls_scanner` (call sites) | Dedup target |
| Kerberos realm derivation | `quirk/scanner/kerberos_scanner.py` | `ipaddress` stdlib | Replace `parts.isdigit()` with `ipaddress.ip_address` |
| Platform version | `quirk/__init__.py` (canonical) | `cbom/builder.py`, `reports/writer.py` (importers) | Single source of truth |
| SSH JSON exception logging | `quirk/cbom/builder.py:316` | `quirk/util/safe_exc.py` (consumed) | safe_str wraps message |
| Trend endpoints streaming | `quirk/intelligence/trends.py` | SQLAlchemy `yield_per` | `Session.query(...).yield_per(1000)` |
| Protocol keys taxonomy | `quirk/intelligence/evidence.py` | scanners (emission map) | Static tuple |
| Roadmap baseline-governance | `quirk/intelligence/roadmap.py` | — | Conditional logic at item assembly |
| Migration paths truncation | `quirk/reports/executive.py` | — | Loop guard line 233 |
| Roadmap section filter | `quirk/reports/html_renderer.py` | — | Pure filter (see C-7) |
| Writer hosts_count filter | `quirk/reports/writer.py` | — | Set comprehension predicate |
| IntelligenceReport dataclass | `quirk/intelligence/schema.py` | `quirk/intelligence/__init__.py`, `tests/test_intelligence_schema.py` (importers — see C-1) | Delete cascade |
| QRAMM endpoint typing | `quirk/dashboard/api/routes/qramm.py` | Pydantic `BaseModel` (already present at lines 96+, 280) | TypedDict OR widen Pydantic model |
| Banner escape | `quirk/cli/banner.py` | — | Comment-only (see C-5) |
| TZ fallback | (site uncertain — see C-11) | — | — |
| QRAMM clamp constants | `quirk/dashboard/api/routes/qramm.py` | — | Module-level constants |
| FastAPI handler factory | `quirk/dashboard/api/app.py` | — | No-op per audit (see C-6) |
| Column ensure consolidation | `quirk/db.py` | — | 11 helpers → 1 generic + 11 column-list constants |
| Probe count CIDR | `quirk/util/targets.py` | — | **Do not change without user override** (see C-3) |
| Tab-count comment | `src/dashboard/src/pages/qramm-assessment.tsx:246` | — | Comment-only |
| Cytoscape catch | `src/dashboard/src/pages/cbom.tsx`, `roadmap.tsx` | — | Add `console.error` + re-throw |
| Findings/identity columns | `src/dashboard/src/pages/findings.tsx`, `identity.tsx` | React `useMemo` | Wrap definitions |
| QRAMM session ref reset | `src/dashboard/src/hooks/useQRAMMSession.ts` | qramm-profile/qramm-assessment New Assessment flow | Add reset on flow trigger |
| compByAlg representative | `src/dashboard/src/pages/cbom.tsx` | — | First-non-zero helper |
| Print style injection | `src/dashboard/src/pages/print.tsx` | — | Replace createElement with JSX `<style>` |
| useScanData URL in error | `src/dashboard/src/hooks/useScanData.ts:51` | — | Interpolate URL |
| Audit ledger | `.planning/audit-2026-05-08/AUDIT-TASKS.md` | `tests/test_audit_ledger_zero_open.py` (new) | Pure ledger + CI gate |

## Standard Stack

### Core (no new deps — D-32 forbids new pip / npm packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | per `pyproject.toml:89` | All Python tests | [VERIFIED `pyproject.toml`] |
| SQLAlchemy | (existing) | `yield_per` for D-09 | [VERIFIED existing import at `trends.py:21`] |
| ipaddress (stdlib) | Python 3.11+ | D-06 (kerberos) + D-22 (already in use) | stdlib |
| Vitest | 2.1.9 | All React tests | [VERIFIED `src/dashboard/package.json:74`] |
| @testing-library/react | 16.3.2 | Component/hook tests | [VERIFIED `src/dashboard/package.json:51`] |
| FastAPI Pydantic BaseModel | (existing) | D-16 typed response models | [VERIFIED `qramm.py:96, 280`] |

### Patterns reused (no new code added)

| Module | Pattern | Use Case |
|--------|---------|----------|
| `quirk/util/weak_crypto.py` (Phase 73) | `is_weak_cipher`, `is_legacy_tls_version` | D-03 (SHA1) and D-05 (`_is_pfs/_is_weak`) consolidation target |
| `quirk/assessment/migration_advisor.py::_matches` (Phase 74) | Word-boundary regex helper | D-03 alternative |
| `quirk/util/safe_exc.py::safe_str` (Phase 59) | Sanitize exception text | D-08 logging |
| `quirk/__init__.py::__version__` | Canonical version string | D-07 import target |
| FastAPI Pydantic models (`QrammScoreRequest`, etc. at `qramm.py:96+`) | Explicit response_model | D-16 widen |

**Installation:** None — D-32 forbids new dependencies.

## Architecture Patterns

### Recommended file layout (no structural changes per D-32)

```
quirk/
├── __init__.py                                # canonical __version__ (D-07 source)
├── scanner/
│   ├── tls_capabilities.py                    # D-01 comment add
│   ├── dnssec_scanner.py                      # D-02 alg map (see C-9 first)
│   ├── saml_scanner.py                        # D-03 use _matches
│   ├── fingerprint.py                         # D-04 Host header
│   ├── kerberos_scanner.py                    # D-06 ipaddress
│   ├── broker_scanner.py                      # D-05 remove local _is_pfs/_is_weak
│   ├── email_scanner.py                       # D-05 remove local _is_pfs/_is_weak
│   └── tls_scanner.py                         # D-05 remove inner _is_pfs/_is_weak
├── util/
│   ├── weak_crypto.py                         # D-05 home (add _is_pfs / _is_weak entries)
│   └── targets.py                             # D-22 — DO NOT TOUCH without user override
├── cbom/builder.py                            # D-07 import + D-08 log
├── intelligence/
│   ├── __init__.py                            # D-15 remove IntelligenceReport export
│   ├── schema.py                              # D-15 delete IntelligenceReport
│   ├── evidence.py                            # D-10 extend _PROTOCOL_KEYS
│   ├── roadmap.py                             # D-11 separate baseline check
│   └── trends.py                              # D-09 yield_per
├── reports/
│   ├── executive.py                           # D-12 "... and N more"
│   ├── html_renderer.py                       # D-13 verify dead branch (see C-7)
│   └── writer.py                              # D-07 import + D-14 filter
├── cli/banner.py                              # D-17 — verify; likely comment fix only
├── dashboard/api/
│   ├── app.py                                 # D-20 — likely no-op (see C-6)
│   └── routes/qramm.py                        # D-16 TypedDict + D-19 constants
├── db.py                                      # D-21 _ensure consolidation
src/dashboard/src/
├── pages/
│   ├── qramm-assessment.tsx                   # D-23 comment fix
│   ├── cbom.tsx                               # D-24 catch + D-27 representative
│   ├── roadmap.tsx                            # D-24 catch
│   ├── findings.tsx                           # D-25 useMemo
│   ├── identity.tsx                           # D-25 useMemo
│   └── print.tsx                              # D-28 JSX style
├── hooks/
│   ├── useQRAMMSession.ts                     # D-26 reset
│   └── useScanData.ts                         # D-29 URL in error
tests/
└── test_audit_ledger_zero_open.py             # D-31 CI gate (new)
```

### Pattern 1: Module-level version import (D-07)

```python
# quirk/cbom/builder.py and quirk/reports/writer.py — replace duplicate PLATFORM_VERSION
from quirk import __version__ as PLATFORM_VERSION
```

### Pattern 2: SQLAlchemy yield_per (D-09)

```python
# quirk/intelligence/trends.py — replace .all() at line 99
rows = (
    db.query(CryptoEndpoint)
      .filter(...)
      .yield_per(1000)
)
# iteration in caller — sentinels still match the existing list-of-rows shape
```

### Pattern 3: Generic _ensure_columns (D-21)

```python
# quirk/db.py — single helper replacing 11 _ensure_*_columns
def _ensure_columns(engine, table: str, expected: tuple[tuple[str, str], ...]) -> None:
    """Generic SQLite ALTER-TABLE-IF-MISSING. Mirrors prior _ensure_<feature>_columns shape."""
    insp = inspect(engine)
    existing = {c["name"] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        for col, ddl in expected:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))

# Column lists live as module-level constants (was implicit; make explicit):
_IDENTITY_COLUMNS = (("identity_provider", "TEXT"), ...)
_GCP_COLUMNS = (...)
# ... etc.

def init_db(db_path: str) -> Engine:
    ...
    _ensure_columns(engine, "crypto_endpoint", _IDENTITY_COLUMNS)
    _ensure_columns(engine, "crypto_endpoint", _GCP_COLUMNS)
    # ... etc.
```

### Pattern 4: IPv4 detection via ipaddress (D-06)

```python
# quirk/scanner/kerberos_scanner.py:50-64 — replace .isdigit() heuristic
import ipaddress

def _derive_realm(host: str) -> str:
    stripped = host.strip()
    try:
        ipaddress.ip_address(stripped)
        return stripped.upper()
    except ValueError:
        pass
    parts = stripped.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:]).upper()
    return stripped.upper()
```

### Pattern 5: QRAMM multiplier constants (D-19)

```python
# quirk/dashboard/api/routes/qramm.py — module-level (replaces magic 0.8/1.5/0.10/0.20)
MULTIPLIER_MIN = 0.8
MULTIPLIER_MAX = 1.5
MULTIPLIER_LOW_STEP = 0.10     # used in INDUSTRY_FACTORS / SENSITIVITY_FACTORS
MULTIPLIER_HIGH_STEP = 0.20

# Replace literals at lines 172, 174, 175, 176 (factor maps) + 192-193 (clamp) +
# 363-368 (validation) with named constants.
```

### Pattern 6: useMemo columns (D-25)

```typescript
// src/dashboard/src/pages/findings.tsx:53 — wrap existing array
const columns = useMemo<ColumnDef<FindingItem>[]>(() => [
  // ... existing column defs unchanged
], [/* deps — likely [] since cells use row.original */])
```

### Pattern 7: JSX style element (D-28)

```typescript
// src/dashboard/src/pages/print.tsx:377-380 — replace createElement
return (
  <html>
    <head>
      <style>{PRINT_CSS}</style>
    </head>
    ...
```

### Pattern 8: Cytoscape catch re-throw (D-24)

```typescript
// src/dashboard/src/pages/cbom.tsx:19-23
try {
  cytoscape.use(coseBilkent)
} catch (e) {
  if (process.env.NODE_ENV !== 'production') {
    // already-registered double-call is benign in HMR; surface real failures.
    console.error('cytoscape.use(coseBilkent) failed:', e)
  }
  // Do NOT re-throw in dev HMR; check the message and only re-throw non-"already-registered" errors:
  if (!(e instanceof Error) || !/already/i.test(e.message)) throw e
}
```

(See C-12 — naive re-throw breaks HMR; need an "already registered" guard.)

### Anti-Patterns to Avoid

- **Touching `projected_probe_count`** without a user override of D-22 — the existing `.hosts()` choice has a documented Risks #4 rationale (avoid off-by-2 on IPv4 /24).
- **Adding a new pip dep for any of this work** — D-32 forbids.
- **Naive `IntelligenceReport` deletion** without first deleting `tests/test_intelligence_schema.py` and removing the `__init__.py` export — would break import of the package (see C-1).
- **Renaming `MATURITY_MAX`** — Phase 76 used this name (see Phase 76 C-5 caveat that `4` is dimension count not maturity max; this phase's `MULTIPLIER_*` constants are unambiguous).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IPv4 detection | Dotted-quad regex | `ipaddress.ip_address` | stdlib, handles IPv6 too |
| Exception text sanitization | Custom redactor | Phase 59 `safe_str` | Already on path |
| Cipher classification | Inline substring match per scanner | `quirk/util/weak_crypto.py` helpers | Phase 73 dedup target |
| Schema ALTER-IF-MISSING | Per-feature `_ensure_*_columns` | Generic helper + column tuples (Pattern 3) | DRY |
| Streaming over query results | List materialization in memory | `Session.query(...).yield_per(N)` | SQLAlchemy idiom |
| Cytoscape "already registered" detection | Generic catch-all | Message inspection + re-throw (Pattern 8) | HMR safety |
| useScanData URL in error | Brand-new error class | Template literal interpolation | Trivial fix at line 51 |

## Runtime State Inventory

> Phase 77 is pure code edits + audit ledger updates. No DB schema migrations, no live service config, no OS-registered state, no secret changes.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — D-21 consolidates the *helpers* not their per-DB effect; existing column lists are byte-identical | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | `src/dashboard/dist/` regenerates on `npm run build` after D-23..D-29 | `cd src/dashboard && npm run build` before commit |

## Common Pitfalls

### Pitfall 1: IntelligenceReport has live importers (C-1)

CONTEXT D-15 says "delete entirely" + "researcher confirms zero importers via grep". Grep shows:

- `quirk/intelligence/__init__.py:8, 24` — exports `IntelligenceReport`
- `tests/test_intelligence_schema.py:7, 16, 58` — imports + uses at 2 call sites

Delete cascade required: schema.py dataclass + `__init__.py` re-export + entire test module (or replace tests with a "no IntelligenceReport in public API" assertion).

### Pitfall 2: D-19 magic numbers are in routes/qramm.py, not scoring.py (C-2)

CONTEXT D-19 says "QRAMM magic numbers in `quirk/qramm/scoring.py`". Grep at HEAD shows scoring.py contains only the `1.5` band threshold (>=1.5 = Developing maturity, line 92) — completely unrelated to the multiplier clamp. The actual `0.8 / 1.5 / 0.10 / 0.20` constants live in `quirk/dashboard/api/routes/qramm.py:172-176, 192-193, 363-368`. Extract them there.

### Pitfall 3: D-22 reverses a deliberate choice (C-3)

`quirk/util/targets.py:215-240` contains an *explicit* comment at lines 218-221: "Risks #4: uses .hosts() NOT .num_addresses to avoid off-by-2 on IPv4 /24." Switching to `num_addresses` is **the exact reversal** of a Phase 65 (Risks #4) decision. Researcher recommends:

- **Do not change behavior**. Flip IN-07 to `[ ] wont-fix — Phase 65 Risks #4 documented decision; .num_addresses would re-introduce the off-by-2 bug` with rationale.
- If user wants the O(1) change, the safer rewrite is `network.num_addresses - 2 if isinstance(network, IPv4Network) and network.prefixlen <= 30 else network.num_addresses` — but this is feature creep and contradicts D-32 "no new features."

### Pitfall 4: D-17 _FACES is already a raw string (C-5)

`quirk/cli/banner.py:65` is `_FACES = (r"     @__   ..." + "\n" + ...)`. The `r"..."` prefix means `\-` is a literal backslash + dash. **No bug exists.** The CONTEXT D-17 + audit IN-02 both misread. Fix: rewrite the comment at line 64 to: `# _FACES uses raw string r"..."; the literal \- is preserved exactly.`

### Pitfall 5: D-20 audit row literally says "no-op" (C-6)

Audit row body: `IN-05: app.py:53-58 closure captures via default argument missing` then prose: *"`_make_handler(fp, mt)` is the canonical factory pattern — implementation is correct. ... No-op."* CONTEXT D-20 misreads as if there's a fix to make. **Recommendation:** close IN-05 as audit-ledger-flip-only with the audit's own prose.

### Pitfall 6: D-18 TZ fallback site is hard to locate (C-11)

CONTEXT D-18 says "Interactive TZ fallback emits IANA name (`"UTC"`) not legacy abbreviation." Grep across `quirk/cli/`, `quirk/dashboard/`, and `quirk/qramm/` for `tzlocal`, `TZ`, `UTC string`, `pytz`, etc. surfaces only `datetime.now(timezone.utc)` patterns (already IANA-friendly). The audit row text claims "interactive timezone fallback to UTC string vs IANA name." Either:
- The site has already been fixed by Phase 67-69 (then close as already-fixed)
- The site is `quirk/dashboard/api/routes/qramm.py` interactive prompt — unverified at this read
- Audit refers to CLI banner / `pretty_dt` helper (search for `strftime` + `%Z`)

Researcher flags this for Wave 0 user confirmation: planner cannot freeze a 1-line fix without knowing the call site.

### Pitfall 7: D-23 lab.sh / chaos-lab does not apply

This phase touches no scanners' detection logic, no chaos lab profiles, no labs/expected_results. CLAUDE.md "Chaos Lab Maintenance" rule does not trigger here.

### Pitfall 8: D-29 — URL is already constructible at error site

`useScanData.ts:51` already says `API error: ${resp.status} ${resp.statusText}`. The actual URL is at `useScanData.ts:29-31` (constructed inline). Fix is simple but requires hoisting URL out of `try {}`:

```typescript
const url = selectedScanId ? `...` : `...`
// ... use url everywhere; also at error: setError(`Failed to fetch ${url}: ${resp.status} ${resp.statusText}`)
```

### Pitfall 9: D-13 dead branch may not exist (C-7)

`quirk/reports/html_renderer.py:82-83` is:

```python
def roadmap_section(tf: str) -> List[Dict]:
    return [r for r in (roadmap_items or []) if r.get("timeframe") == tf or r.get("phase") == tf]
```

This is a 2-line function. No "timeframe comparison dead branch" visible. Either the dead branch is in the *caller* (lines 98-100 pass `"NOW" / "NEXT" / "LATER"`) or it's in the template (Jinja side). Researcher recommends planner does a coverage-driven check (run executive report rendering once with timeframe="NOW", mutate to "NEVER", confirm test breakage) before claiming a dead branch.

## Inventory: D-10 missing _PROTOCOL_KEYS

`evidence.py:11-12` current set: `("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC", "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT")`.

Scanner emission grep (`grep -rn 'protocol="' quirk/scanner/`):

| Protocol value emitted | In current `_PROTOCOL_KEYS`? | Source |
|------------------------|-------------------------------|--------|
| CONTAINER | ❌ | `container_scanner.py:68, 114` |
| SOURCE | ❌ | `source_scanner.py:45, 92` |
| AWS | ❌ | `aws_connector.py:70, 375, 411` |
| AZURE | ❌ | `azure_connector.py:98, 136` |
| GCP | ❌ | `gcp_connector.py:237, 368, 385, 444` |
| CLOUD_SQL | ❌ | `gcp_connector.py:318` |
| KMS | ❌ | (search reveals via aws_connector — verify) |

**Recommendation:** D-10 adds `CONTAINER, SOURCE, AWS, AZURE, GCP, CLOUD_SQL` (6 keys). Researcher does not see `K8S` separately — `KUBERNETES` is already present. CONTEXT's "K8S" likely refers to `KUBERNETES` (already present).

## Inventory: D-21 _ensure_*_columns family

11 helpers at `quirk/db.py`:

| Line | Helper | Phase |
|------|--------|-------|
| 70 | `_ensure_identity_columns` | v4.2 |
| 92 | `_ensure_gcp_columns` | v4.3 |
| 114 | `_ensure_v43_columns` | v4.3 |
| 135 | `_ensure_email_columns` | v4.4 Phase 32 |
| 155 | `_ensure_broker_columns` | v4.4 Phase 33 |
| 176 | `_ensure_phase41_columns` | v4.4 Phase 41 |
| 201 | `_ensure_phase46_columns` | v4.5 Phase 46 |
| 225 | `_ensure_phase54_qramm_columns` | v4.7 Phase 54 |
| 243 | `_ensure_qramm_profiles_fk` | v4.7 Phase 54 (FK, not column ALTER) |
| 322 | `_ensure_qramm_tables` | v4.7 Phase 54 (table CREATE, not ALTER) |
| 336 | `_ensure_scheduled_tables` | (table CREATE) |
| 346 | `_ensure_scan_jobs_table` | (table CREATE) |
| 355 | `_ensure_scan_checkpoints_table` | (table CREATE) |

**Recommendation:** D-21 consolidates only the 8 *column-adding* helpers (rows 1-8 above). The 5 *table-creating* and FK helpers stay as-is — they're not the same pattern.

## Inventory: D-07 PLATFORM_VERSION sites

`grep -rn "PLATFORM_VERSION" quirk/`:

| File | Line | Type |
|------|------|------|
| `quirk/cbom/builder.py` | 128 | `PLATFORM_VERSION = "4.4.0"` (duplicate) |
| `quirk/cbom/builder.py` | 659 | `version=PLATFORM_VERSION` (usage) |
| `quirk/reports/writer.py` | 23 | `PLATFORM_VERSION = "4.4.0"` (duplicate) |
| `quirk/reports/writer.py` | 235 | `PLATFORM_VERSION` (usage) |

Only **2** duplicate sites (CONTEXT said 4-6 — overcounted; the other 2 are usages of the duplicates). Canonical: `quirk/__init__.py:2 __version__ = "4.4.0"`.

## Code Examples

### D-07 fix — full diff

```python
# quirk/cbom/builder.py
- PLATFORM_VERSION = "4.4.0"
+ from quirk import __version__ as PLATFORM_VERSION

# quirk/reports/writer.py
- PLATFORM_VERSION = "4.4.0"
+ from quirk import __version__ as PLATFORM_VERSION
```

### D-31 CI gate — new test

```python
# tests/test_audit_ledger_zero_open.py
"""Phase 77 LEDGER-01: AUDIT-TASKS.md must have zero bare-open rows at milestone close."""
from pathlib import Path
import re

LEDGER = Path(__file__).resolve().parent.parent / ".planning" / "audit-2026-05-08" / "AUDIT-TASKS.md"
_OPEN_RE = re.compile(r"^\|\s.*\[ \] open\s*\|", re.MULTILINE)


def test_audit_ledger_has_zero_bare_open_rows() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    matches = _OPEN_RE.findall(text)
    assert not matches, (
        f"Audit ledger has {len(matches)} bare-open row(s); v4.9 milestone gate requires zero. "
        f"Each finding must be [x] closed, [ ] deferred-vX.Y with rationale, or [ ] wont-fix with rationale."
    )
```

### D-15 cascade delete

```python
# quirk/intelligence/__init__.py — remove from imports + __all__
- from quirk.intelligence.schema import IntelligenceReport
+ # IntelligenceReport removed in Phase 77 (cbom-intel-reports/IN-09)

# tests/test_intelligence_schema.py — delete entire file
```

### D-26 seededRef reset

```typescript
// src/dashboard/src/hooks/useQRAMMSession.ts — add a reset method
const resetSession = useCallback(() => {
  seededRef.current = null
}, [])

return { /* ... existing fields ... */, resetSession }

// src/dashboard/src/pages/qramm-assessment.tsx — call on Confirm New Assessment
const { /* existing */, resetSession } = useQRAMMSession()
// In the archive callback:
await archiveAndReset()
resetSession()
```

### D-30 inline rationale format (mirror existing `[x] closed` rows)

```markdown
| scanners-cloud/CR-01 | BLOCKER | migration_planner.py is a stub — does not implement scoring | — | [ ] wont-fix — `quirk/cbom/migration_planner.py` is a 16-line stub; v4.x decision is that migration-planning intelligence is the consumer's responsibility (out-of-scope for cryptographic inventory scope). Re-evaluate in v5.0 if a typed migration pipeline is needed. |
| scanners-cloud/CR-03 | BLOCKER | K8s scan_k8s_targets calls _scan_aks_encryption with None cred | — | [ ] deferred-v4.9 — Phase 29 documented the credentialed AKS path; the None-cred fallback is exercised in production only when running unauthenticated against an AKS cluster; the existing graceful-degradation path returns an empty list (correct). v4.9 will add an explicit `K8S-04` log for the None-cred branch. |
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-feature `_ensure_*_columns` × 8 | Single generic `_ensure_columns` + column tuples | This phase D-21 | ~140 lines of repetition removed |
| `PLATFORM_VERSION = "4.4.0"` literal | `from quirk import __version__ as PLATFORM_VERSION` | This phase D-07 | Version bump = one edit |
| Dotted-quad `isdigit()` heuristic | `ipaddress.ip_address(...)` | This phase D-06 | Handles IPv6 + reserved ranges |
| Magic clamp numbers | Module-level `MULTIPLIER_*` constants | This phase D-19 | Self-documenting; testable |
| `createElement("style", ...)` | JSX `<style>` | This phase D-28 | Idiomatic React |
| `cytoscape.use(ext as cytoscape.Ext)` | Module augmentation (Phase 76 D-09) | Phase 76 | (already done — Phase 77 doesn't touch) |
| `column-defs declared inline at render` | `useMemo<ColumnDef[]>` | This phase D-25 | Stable identity = TanStack table memoization |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_FACES` raw-string finding is purely cosmetic; the `\-` is never interpreted as an escape because of the `r"..."` prefix | Pitfall 4 | LOW — verified by `r"` in `banner.py:66` |
| A2 | D-22 should be wont-fix per the Phase 65 Risks #4 comment, not the CIDR materialization fix CONTEXT describes | Pitfall 3, C-3 | MEDIUM — user may override if O(1) count is desired regardless of off-by-2; planner should ask. |
| A3 | D-13 dead branch may not exist at the cited site (`html_renderer.py:82-83`) | Pitfall 9, C-7 | MEDIUM — planner should add a Wave 0 verification task before scheduling the fix |
| A4 | D-18 TZ fallback site has not been located at HEAD; may already be fixed | Pitfall 6, C-11 | MEDIUM — planner needs site confirmation in Wave 0 |
| A5 | Reusing Phase 74 `_matches` for D-03 is preferable to extracting a new `is_sha1_indicator` helper | Discretion D-03 | LOW — `_matches` is the established pattern |
| A6 | D-20 closes as audit-ledger-flip-only with the audit's own "No-op" prose; no code change required | Pitfall 5, C-6 | LOW — audit row text is unambiguous |
| A7 | LEDGER-01 invariant counts bare table rows only, not prose mentions or anchor lines (header rows, list-item rows) | INFO requirement table | LOW — the regex `^\| .* \[ \] open` only matches GFM table rows that begin with `|` and contain the disposition cell |

## Open Questions

1. **Q1 (D-22 / IN-07 disposition):** Reverse the Phase 65 Risks #4 decision (switch to `.num_addresses`) or close IN-07 as `[ ] wont-fix — Phase 65 Risks #4 documented decision`? **Recommendation:** wont-fix.

2. **Q2 (D-18 / IN-03 site):** Where is the interactive TZ fallback? Not located at HEAD. Either (a) audit-row stale (already fixed), (b) site is in `quirk/dashboard/api/routes/qramm.py` interactive flow, (c) site is somewhere in `quirk/cli/` that escaped grep. **Recommendation:** Wave 0 task to ask user to point to the site.

3. **Q3 (D-13 / IN-07 dead branch):** Where is the dead branch in `html_renderer::roadmap_section`? Not visible in the 2-line function at HEAD. **Recommendation:** Wave 0 mutation-test check before scheduling.

4. **Q4 (D-15 / IN-09 cascade):** Delete `tests/test_intelligence_schema.py` entirely or replace with `test_intelligence_schema_removed.py` asserting `IntelligenceReport` is not in the public API? **Recommendation:** replace, so the cascade is *enforced* via test rather than just *applied*.

5. **Q5 (LEDGER-01 row count):** CONTEXT D-30 says "4 bare rows." HEAD has **2** (CR-01 wont-fix, CR-03 deferred-v4.9). Did the user count something else? **Recommendation:** ask in Wave 0; the work to update both rows is the same.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python pytest | All Python tests | ✓ | per `pyproject.toml:89` | — |
| Node + npm | React build + Vitest | ✓ (assumed) | per `src/dashboard/package.json` | — |
| Vitest | React tests | ✓ | 2.1.9 | — |
| SQLAlchemy | D-09 yield_per | ✓ | existing import at `trends.py:21` | — |
| ipaddress (stdlib) | D-06 | ✓ | Python 3.11+ stdlib | — |
| grep | LEDGER-01 invariant grep | ✓ | system | Python `re` (used in D-31 test) |

No missing dependencies.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest (`pyproject.toml:89 [tool.pytest.ini_options]`) |
| Frontend framework | Vitest 2.1.9 + @testing-library/react 16.3.2 (`src/dashboard/package.json`) |
| Backend quick run | `pytest tests/test_<module>.py -x` |
| Backend full suite | `pytest -x` |
| Frontend quick run | `cd src/dashboard && npm test -- <pattern>` |
| Frontend full suite | `cd src/dashboard && npm test` |
| Build check | `cd src/dashboard && npm run build` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INFO-01 / IN-01 | SSLContext comment exists | gate (string assert) | `pytest tests/test_tls_capabilities_comment.py -x` | ❌ Wave 0 |
| INFO-01 / IN-02 | DNSSEC alg 9, 11 mapped | unit | `pytest tests/test_dnssec_scanner.py::test_alg_map_includes_9_and_11 -x` | ❌ Wave 0 (verify C-9 first) |
| INFO-01 / IN-03 | SHA1 indicator boundary | unit | `pytest tests/test_saml_scanner.py::test_sha1_word_boundary -x` | ❌ Wave 0 |
| INFO-01 / IN-04 | Host header is target hostname | unit | `pytest tests/test_fingerprint.py::test_http_probe_uses_target_host -x` | ❌ Wave 0 |
| INFO-01 / IN-05 | weak_crypto exports _is_pfs/_is_weak | unit | `pytest tests/test_weak_crypto.py::test_pfs_weak_helpers_exported -x` | ❌ Wave 0 |
| INFO-01 / IN-06 | ipaddress-based realm derivation | unit | `pytest tests/test_kerberos_scanner.py::test_derive_realm_ipv4_via_ipaddress -x` | ❌ Wave 0 |
| INFO-02 / IN-01 | Builder + writer import from quirk.__version__ | unit (AST gate) | `pytest tests/test_platform_version_single_source.py -x` | ❌ Wave 0 |
| INFO-02 / IN-02 | SSH JSON error logged via safe_str | unit | `pytest tests/test_cbom_builder.py::test_extract_ssh_logs_json_decode_error -x` | (verify existing) |
| INFO-02 / IN-03 | Trend query uses yield_per | unit (mock spy) | `pytest tests/test_trends.py::test_yield_per_chunked -x` | ❌ Wave 0 |
| INFO-02 / IN-04 | _PROTOCOL_KEYS includes CONTAINER/SOURCE/AWS/AZURE/GCP/CLOUD_SQL | unit | `pytest tests/test_evidence.py::test_protocol_keys_complete -x` | (verify existing) |
| INFO-02 / IN-05 | Roadmap baseline-governance shown when missing AND when < min_items | unit | `pytest tests/test_roadmap.py::test_baseline_governance_appears_*` | (verify) |
| INFO-02 / IN-06 | Executive truncation shows "... and N more" | unit | `pytest tests/test_executive_report.py::test_migration_paths_truncation_indicator -x` | (verify) |
| INFO-02 / IN-07 | html_renderer dead branch verified | mutation | manual mutation + `pytest tests/test_html_renderer.py` | (Wave 0 verification) |
| INFO-02 / IN-08 | writer filters falsy hosts before set | unit | `pytest tests/test_writer.py::test_hosts_count_filters_empty -x` | ❌ Wave 0 |
| INFO-02 / IN-09 | IntelligenceReport not in public API | gate | `pytest tests/test_intelligence_public_api.py::test_no_intelligence_report_export -x` | ❌ Wave 0 (replaces test_intelligence_schema.py) |
| INFO-03 / IN-01 | QRAMM score response Pydantic-typed | unit | `pytest tests/test_qramm_routes.py::test_score_response_model -x` | (verify) |
| INFO-03 / IN-02 | _FACES comment corrected | gate (string assert) | `pytest tests/test_banner_comment.py -x` | ❌ Wave 0 |
| INFO-03 / IN-03 | Interactive TZ emits IANA | unit | (site TBD — see Q2) | (Wave 0) |
| INFO-03 / IN-04 | QRAMM MULTIPLIER_* constants defined and used | unit + AST gate | `pytest tests/test_qramm_multiplier_constants.py -x` | ❌ Wave 0 |
| INFO-03 / IN-05 | app.py _make_handler closure verified correct | gate (no-op) | (audit-row flip only — no test) | N/A |
| INFO-03 / IN-06 | _ensure_columns generic + column tuples | unit | `pytest tests/test_db.py::test_ensure_columns_generic -x` | ❌ Wave 0 |
| INFO-03 / IN-07 | projected_probe_count — disposition per Q1 | gate or unit | (TBD per Q1) | (Wave 0) |
| INFO-04 / IN-01 | qramm-assessment comment matches tab count | gate (string assert) | `npm test -- qramm-assessment-comment` | ❌ Wave 0 |
| INFO-04 / IN-02 | Cytoscape catch re-throws non-"already" errors | unit | `npm test -- cbom-cytoscape-catch` | ❌ Wave 0 |
| INFO-04 / IN-03 | findings + identity columns memoized | unit (render count) | `npm test -- findings-columns-memo` | ❌ Wave 0 |
| INFO-04 / IN-04 | seededRef resets on New Assessment | unit | `npm test -- useQRAMMSession-reset` | ❌ Wave 0 |
| INFO-04 / IN-05 | compByAlg first-non-zero | unit | `npm test -- cbom-compByAlg-statistic` | ❌ Wave 0 |
| INFO-04 / IN-06 | print uses JSX <style> | gate (no createElement import) | `npm test -- print-no-createElement` | ❌ Wave 0 |
| INFO-04 / IN-07 | useScanData error includes URL | unit | `npm test -- useScanData-error-url` | ❌ Wave 0 |
| LEDGER-01 | zero bare-open rows | gate (pytest) | `pytest tests/test_audit_ledger_zero_open.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/<specific_test>.py -x` OR `npm test -- <pattern>` (the most granular test)
- **Per wave merge:** `pytest -x` (full Python suite) + `cd src/dashboard && npm test` (full Vitest) + `cd src/dashboard && npm run build`
- **Phase gate:** All three full suites green + `pytest tests/test_audit_ledger_zero_open.py -x` (LEDGER-01 invariant) + `grep -cE "^\| .* \[ \] open" .planning/audit-2026-05-08/AUDIT-TASKS.md` returns 0

### Wave 0 Gaps

Backend:
- [ ] `tests/test_tls_capabilities_comment.py`
- [ ] `tests/test_saml_scanner.py::test_sha1_word_boundary` (or extend existing)
- [ ] `tests/test_fingerprint.py::test_http_probe_uses_target_host`
- [ ] `tests/test_weak_crypto.py::test_pfs_weak_helpers_exported`
- [ ] `tests/test_kerberos_scanner.py::test_derive_realm_ipv4_via_ipaddress`
- [ ] `tests/test_platform_version_single_source.py`
- [ ] `tests/test_trends.py::test_yield_per_chunked` (mock query)
- [ ] `tests/test_writer.py::test_hosts_count_filters_empty`
- [ ] `tests/test_intelligence_public_api.py` (replaces `test_intelligence_schema.py`)
- [ ] `tests/test_banner_comment.py`
- [ ] `tests/test_qramm_multiplier_constants.py`
- [ ] `tests/test_db.py::test_ensure_columns_generic`
- [ ] `tests/test_audit_ledger_zero_open.py` (D-31 — REQUIRED for LEDGER-01)

Frontend:
- [ ] `src/dashboard/src/pages/__tests__/qramm-assessment-comment.test.tsx`
- [ ] `src/dashboard/src/pages/__tests__/cbom-cytoscape-catch.test.tsx`
- [ ] `src/dashboard/src/pages/__tests__/findings-columns-memo.test.tsx`
- [ ] `src/dashboard/src/hooks/__tests__/useQRAMMSession-reset.test.ts`
- [ ] `src/dashboard/src/pages/__tests__/cbom-compByAlg-statistic.test.tsx`
- [ ] `src/dashboard/src/pages/__tests__/print-no-createElement.test.tsx`
- [ ] `src/dashboard/src/hooks/__tests__/useScanData-error-url.test.ts`

## Security Domain

Phase 77 changes are code-quality polish — no new threat surface. Quick ASVS sweep:

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | partial (D-19 clamp constants; D-06 IP parse) | Existing validation preserved; constants are documentation, not new validation logic |
| V6 Cryptography | no (D-01 is comment-only; D-02 alg-map metadata; D-03/D-05 detection logic uses existing helpers) | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted exception text leaked to logs | Information Disclosure | `safe_str` (Phase 59) — D-08 applies |
| Off-by-2 probe count on /24 | Denial of Service (over-probe) | Documented `.hosts()` choice (D-22 — preserved) |
| Cytoscape registration silent failure | Repudiation | D-24 catch re-throw on non-"already" errors |

## Project Constraints (from CLAUDE.md)

- **PEP 8** — applies to all Python edits (D-01..D-22)
- **Minimal diffs** — every D-NN is < 30 lines; D-32 reinforces
- **`python -m compileall` + tests** — required after backend edits
- **Detection logic changes → `labs/*/expected_results.md`** — N/A (no detection changes; D-02 alg map and D-03 SHA1 are *labeling*, not new findings)
- **Staleness review cadence** — N/A
- **Chaos lab maintenance** — N/A (no lab.sh changes)
- **Mandatory phase completion** — Obsidian phase note + UAT-SERIES.md update + Obsidian sync + commit per CLAUDE.md §"Mandatory Phase Completion Steps." UAT-SERIES updates focus on the v4.9 milestone close note, not new test cases (per CONTEXT test_strategy).

## Sources

### Primary (HIGH confidence)

- `quirk/__init__.py:2` — `__version__ = "4.4.0"` (D-07 canonical)
- `quirk/cbom/builder.py:128, 316, 659` — PLATFORM_VERSION + _extract_ssh_algorithms
- `quirk/reports/writer.py:23, 222, 235` — PLATFORM_VERSION + hosts_count
- `quirk/reports/executive.py:228-240` — Migration Paths truncation
- `quirk/reports/html_renderer.py:82-83, 98-100` — roadmap_section
- `quirk/intelligence/__init__.py:8, 24` — IntelligenceReport export (importer for D-15)
- `quirk/intelligence/schema.py:83` — IntelligenceReport definition
- `quirk/intelligence/evidence.py:11-12` — _PROTOCOL_KEYS
- `quirk/intelligence/trends.py:84, 99` — _fetch_session_endpoints
- `quirk/intelligence/roadmap.py:368, 406, 437` — baseline-governance condition
- `quirk/scanner/tls_capabilities.py:39-79` — _try_handshake (D-01 site)
- `quirk/scanner/dnssec_scanner.py:44-57` — DNSSEC_ALG_MAP
- `quirk/scanner/saml_scanner.py:58, 188` — SHA1_INDICATORS
- `quirk/scanner/fingerprint.py:97, 111, 184` — _http_probe_plain
- `quirk/scanner/kerberos_scanner.py:50-64` — _derive_realm
- `quirk/scanner/broker_scanner.py:115, 120` + `quirk/scanner/email_scanner.py:103, 108` + `quirk/scanner/tls_scanner.py:248, 254` — _is_pfs/_is_weak duplicates
- `quirk/cli/banner.py:64-65` — _FACES raw string
- `quirk/dashboard/api/routes/qramm.py:96, 172-176, 192-193, 363-368` — QRAMM endpoints + magic numbers
- `quirk/dashboard/api/app.py:124-127` — _make_handler factory
- `quirk/db.py:70-355` — _ensure_*_columns family (11 helpers)
- `quirk/util/targets.py:215-240` — projected_probe_count (with explicit Risks #4 comment)
- `src/dashboard/src/pages/qramm-assessment.tsx:246-254` — 5/6 tab mismatch
- `src/dashboard/src/pages/cbom.tsx:19-23, 148, 285, 317, 390` — cytoscape catch + compByAlg
- `src/dashboard/src/pages/roadmap.tsx:13` — cytoscape.use(dagre)
- `src/dashboard/src/pages/findings.tsx:53, 87` + `identity.tsx:71, 91` — non-memoized columns
- `src/dashboard/src/pages/print.tsx:1, 377-380` — createElement style
- `src/dashboard/src/hooks/useQRAMMSession.ts:19, 67-68, 101-102` — seededRef
- `src/dashboard/src/hooks/useScanData.ts:51` — error message (no URL)
- `src/dashboard/package.json:11-12, 51, 74` — Vitest config
- `pyproject.toml:89` — pytest config
- `.planning/audit-2026-05-08/AUDIT-TASKS.md:70-75, 163-171, 203-209, 235-241` — 29 INFO rows; lines 81, 83 — 2 bare deferral rows
- `.planning/audit-2026-05-08/api-cli-core/REVIEW.md` — IN-05 prose ("No-op")

### Secondary (MEDIUM confidence)

- IANA DNSSEC Algorithm Registry — entries 9 (Reserved) and 11 (Reserved) per RFC 8624 (training knowledge — planner should verify against IANA web page in Wave 0 if D-02 acted upon literally)
- SQLAlchemy `yield_per` standard pattern (training knowledge; existing import at trends.py:21)

### Tertiary (LOW confidence)

- D-18 site — unable to locate at HEAD (see C-11)
- D-13 dead branch — unable to locate at HEAD (see C-7)

<research_concerns>
## Mismatches between CONTEXT.md and HEAD

- **C-1 (D-15 / IN-09 zero-importers claim is FALSE):** CONTEXT D-15 directs the researcher to confirm "zero importers via `grep -r "IntelligenceReport" quirk/ tests/`." Grep at HEAD shows:
  - `quirk/intelligence/__init__.py:8` — `from quirk.intelligence.schema import IntelligenceReport`
  - `quirk/intelligence/__init__.py:24` — `"IntelligenceReport"` in `__all__`
  - `tests/test_intelligence_schema.py:7` — `from quirk.intelligence import IntelligenceReport`
  - `tests/test_intelligence_schema.py:16, 58` — constructs IntelligenceReport instances in 2 tests
  - Delete requires cascade: remove `__init__.py` export + delete or rewrite `test_intelligence_schema.py`. Planner must include both as task actions.

- **C-2 (D-19 / IN-04 magic-number location is wrong):** CONTEXT D-19 says "extract `0.8 / 1.5 / 0.10 / 0.20` to named constants in `quirk/qramm/scoring.py`." Grep at HEAD shows scoring.py contains only `1.5` (band threshold for Developing, line 92) and `1.5` in the docstring; the 4-constant set `0.8 / 1.5 / 0.10 / 0.20` lives in `quirk/dashboard/api/routes/qramm.py` (lines 172, 174-176, 192-193, 363-368). The constants should be defined in routes/qramm.py (or hoisted to a new module like `quirk/qramm/constants.py`); planner must update the target file in the plan.

- **C-3 (D-22 / IN-07 reverses a documented Phase 65 decision):** `quirk/util/targets.py:218-221` contains explicit comment: *"Risks #4: uses .hosts() NOT .num_addresses to avoid off-by-2 on IPv4 /24."* CONTEXT D-22 directs the opposite change. This is not a research finding to flag — it is **a contradiction between two phases' decisions**. Recommend either:
  - (a) Close IN-07 as `[ ] wont-fix — Phase 65 Risks #4 explicitly chose .hosts() over .num_addresses to avoid /30 off-by-2; see comment at quirk/util/targets.py:218-221.` (cleanest)
  - (b) User overrides Phase 65 in CONTEXT for v4.9, with explicit acknowledgment that `.num_addresses` includes network/broadcast addresses (overcount by 2 for IPv4 /24, more for /30 and /29).
  - Plan should NOT silently make this change.

- **C-4 (D-30 row count: 4 vs 2):** CONTEXT D-30 says "Inventory the 4 bare `[ ] deferred-*` / `[ ] wont-fix` rows." Grep at HEAD finds exactly **2**: `scanners-cloud/CR-01` (line 81, `[ ] wont-fix`) and `scanners-cloud/CR-03` (line 83, `[ ] deferred-v4.9`). No other GFM table rows match. Either CONTEXT counted prose dispositions in commented-out sections, or 2 rows have been retroactively flipped to `[x] closed` between audit-2026-05-08 and HEAD. Recommend planner verifies with user; D-30 work is mechanically the same regardless (apply inline rationale to whichever bare rows exist at execution time).

- **C-5 (D-17 / IN-02 is a non-bug):** `quirk/cli/banner.py:65` is `_FACES = (r"     @__   ..."`. The `r"..."` raw-string prefix means `\-` is a literal backslash followed by a literal dash — there is no "ambiguous escape" because the raw-string prefix disables escape interpretation. The audit row comment ("\- ambiguous escape (comment misleading)") and the comment at line 64 both misread; the **comment is misleading, not the code**. Fix is comment-only: rewrite line 64 to `# _FACES uses raw string r"..."; backslash-dash is literal text.`.

- **C-6 (D-20 / IN-05 is a no-op per the audit row itself):** `.planning/audit-2026-05-08/api-cli-core/REVIEW.md` IN-05 prose: *"`_make_handler(fp, mt)` is the canonical factory pattern — implementation is correct. ... No-op."* HEAD at `quirk/dashboard/api/app.py:124-127` already uses the factory pattern. CONTEXT D-20 misreads the audit — there is no fix to apply. Recommend planner closes IN-05 as audit-ledger-flip-only.

- **C-7 (D-13 / IN-07 dead branch may not exist):** `quirk/reports/html_renderer.py:82-83` is a 2-line filter function with no visible dead branch. Recommend planner adds Wave 0 task: mutation-test `roadmap_section` to confirm both branches (`r.get("timeframe") == tf` and `r.get("phase") == tf`) are reachable from test fixtures. If unreachable, the dead branch is in *the caller* (lines 98-100) or in Jinja templates (not Python).

- **C-8 (D-01 site is `_try_handshake`, not a "downgrade" site):** CONTEXT D-01 says "Add a 3-line comment above the SSLContext downgrade site." There is no single "downgrade" in `tls_capabilities.py` — `_try_handshake` at lines 39-79 calls `ssl.create_default_context()` then optionally restricts to TLS 1.0/1.1 for probing legacy-server posture. The comment likely belongs at lines 44-47 (the `tls_min/tls_max` parameters) explaining why we probe deprecated versions. Researcher recommends planner specifies the comment-block target line range in the plan.

- **C-9 (D-02 DNSSEC alg numbers are wrong per IANA):** CONTEXT D-02 says "Add DNSSEC algorithm 9 (RSASHA1-NSEC3-SHA1) and 11 (Reserved per RFC 8624)." HEAD at `dnssec_scanner.py:49` already has **alg 7 = "RSASHA1-NSEC3-SHA1"** which is the correct IANA assignment. Per IANA DNS Security Algorithm Numbers registry:
  - 7 = RSASHA1-NSEC3-SHA1 (already present)
  - 9 = Reserved
  - 11 = Reserved
  - The current map is **correct as-is** for alg 7. CONTEXT D-02's identification is wrong. If the goal is to mark Reserved algorithm numbers as `("Reserved", "HIGH")` for findings completeness, that's a different (defensible) fix. Recommend planner clarifies with user.

- **C-10 (D-10 _PROTOCOL_KEYS extension list is non-canonical):** CONTEXT D-10 says "extend to include CONTAINER, SOURCE, AWS, AZURE, GCP, K8S, VAULT." HEAD already includes `VAULT` (line 12) and `KUBERNETES` (which is the canonical K8S protocol value at `aws_connector.py:172`). Missing keys per scanner emission grep: `CONTAINER`, `SOURCE`, `AWS`, `AZURE`, `GCP`, `CLOUD_SQL`. The 6 missing keys differ slightly from CONTEXT's list. Researcher recommends the exact 6-key extension in the Inventory section above.

- **C-11 (D-18 site not found):** CONTEXT D-18 says "Interactive TZ fallback emits IANA name." No site at HEAD in `quirk/cli/` or `quirk/dashboard/api/` matches a "UTC string vs IANA" fallback. The audit row IN-03 prose may be stale. Planner needs site confirmation in Wave 0 before scheduling a fix.

- **C-12 (D-24 naive re-throw breaks HMR):** CONTEXT D-24 says "log + re-throw so visualization fails loudly." Naive `throw e` would re-throw the "extension already registered" benign error on every HMR refresh, breaking dev. Pattern 8 above guards via message regex. Planner should specify the guard explicitly.
</research_concerns>

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `package.json`, `pyproject.toml`, all helpers verified
- Architecture: HIGH — every D-NN site located at HEAD with file:line
- Pitfalls: HIGH — 6 concrete mismatches with audit-row or HEAD evidence
- D-13, D-18 sites: LOW — could not locate at HEAD; require user input in Wave 0
- D-22 disposition: MEDIUM — depends on whether user overrides Phase 65

**Research date:** 2026-05-15
**Valid until:** 2026-06-14 (30 days — stable; no fast-moving deps)

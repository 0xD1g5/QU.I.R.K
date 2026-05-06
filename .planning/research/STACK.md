# Stack Research

**Domain:** Governance & Compliance Platform — QRAMM maturity model + SOC2/ISO27001 mapping on top of existing Python CLI + FastAPI + React app (QU.I.R.K. v4.7)
**Researched:** 2026-05-05
**Confidence:** HIGH

---

## Context: What Already Exists (Do Not Re-Research)

The following are validated and must not be replaced or duplicated:

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Core scanner and FastAPI backend |
| FastAPI | >=0.128.8 | Already in `[dashboard]` extra |
| SQLAlchemy | >=2.0 | `declarative_base()` + `Column` pattern in `quirk/models.py` |
| SQLite | (stdlib) | Primary DB; additive schema columns only — no breaking migrations |
| React | 19.2.x | Bundled SPA in `quirk/dashboard/static/` |
| Recharts | 2.15.x | **Already in bundle** — `RadarChart`, `BarChart`, `ResponsiveContainer` all present |
| shadcn/ui + Radix | current | Component library; all new UI components follow this pattern |
| Tailwind CSS | 3.4.x | Utility CSS; already configured |
| rich | >=13.0.0 | `Console`, `Panel`, `Table` already used in `quirk/cli/banner.py` |
| cyclonedx-python-lib | >=11.7.0,<12 | CBOM pipeline; FIPS 140-3 annotations extend existing classifier |
| PCI-DSS/HIPAA/FIPS 140-3 compliance map | v4.6 | `quirk/compliance/__init__.py`; SOC2/ISO27001 are pure additive extensions |

---

## New Capabilities Needed for v4.7

### 1. QRAMM Scoring Math — Python Backend

**Verdict:** No new library needed. Pure Python arithmetic.

The QRAMM scoring formula is:
- Practice Score = sum(10 question scores) ÷ 10  (scale 1–5)
- Practice weight: Stream A (5 questions, 60%) + Stream B (5 questions, 40%)
- Dimension Score = MIN(Practice 1, Practice 2, Practice 3)  — weakest-link aggregation
- Overall Score = (CVI + SGRM + DPE + ITR) ÷ 4
- Profile multiplier: 0.8–1.5× applied to raw scores based on org context

This is scalar arithmetic over 120 float values. NumPy, pandas, and scipy are all unnecessary overhead. Implement as pure Python functions in `quirk/qramm/scoring.py`.

**Confidence:** HIGH — verified against QRAMM framework docs at qramm.org and the csnp/qramm GitHub repo (`framework/qramm-overview.md`).

---

### 2. QRAMM Data Model — SQLite / SQLAlchemy

**Verdict:** New SQLAlchemy `Table` classes following existing `CryptoEndpoint` pattern in `quirk/models.py`. No migration tool (Alembic) needed — additive `CREATE TABLE IF NOT EXISTS` on `db.py` initialization.

Required tables:

| Table | Purpose |
|-------|---------|
| `qramm_assessments` | One row per assessment run; org profile, timestamps, overall score |
| `qramm_responses` | One row per question answer (assessment_id, dimension, practice, question_id, stream, score 1–5) |
| `qramm_evidence_links` | Bridge: scanner finding → QRAMM question auto-population |
| `qramm_framework_meta` | Static metadata: `qramm_version`, `last_verified`, `source_url` for staleness gate |

Schema notes:
- 120 static question definitions: embed as a Python data structure in `quirk/qramm/questions.py` (not a table) — QRAMM questions are versioned framework content, not user data
- `qramm_assessments.calibration_profile` mirrors existing `ScanCfg` profile field for report coherence
- All new columns/tables are additive; existing scans remain readable

**Confidence:** HIGH — SQLAlchemy 2.0 `declarative_base` pattern verified in existing codebase; QRAMM data structure verified against qramm.org framework docs.

---

### 3. QRAMM Assessment UI — React Wizard

**Verdict:** No new React libraries needed. Use existing shadcn/ui components.

The 120-question wizard (4 dimensions × 3 practices × 10 questions) maps cleanly to:
- `@radix-ui/react-tabs` (already present) — tab per dimension
- shadcn/ui `<Select>` or radio group — 1–5 Likert scale per question
- `react-router-dom` (already present) — `/qramm/*` route namespace

Multi-step wizard state: `useState` or `useReducer` over a `Record<string, number>` response map. No external form library (react-hook-form, formik) needed for a flat 120-integer data set with no validation complexity.

**Confidence:** HIGH — verified existing Radix primitives in `package.json`; wizard complexity does not justify a new dependency.

---

### 4. QRAMM Scorecard Visualizations — Radar + Bar Charts

**Verdict:** `recharts` already in bundle at `^2.15.4`. No new charting library needed.

Verified via Context7 (`/recharts/recharts`):
- `<RadarChart>` + `<PolarGrid>` + `<PolarAngleAxis>` + `<Radar>` — renders 4-dimension spider chart out of the box
- `<ResponsiveContainer>` — makes it fluid in the dashboard layout
- `<BarChart>` + `<Bar>` — maturity distribution histogram per dimension

Do not add Chart.js, D3, or Apache ECharts. They are heavier, not already in the bundle, and Recharts already covers the needed chart types with React-native semantics.

**Confidence:** HIGH — verified component list in Context7 documentation; `recharts` confirmed at `^2.15.4` in `src/dashboard/package.json`.

---

### 5. SOC2 / ISO 27001 Framework Mapping Data

**Verdict:** Embed as static Python dicts in `quirk/compliance/__init__.py`, following the existing `_pci()` / `_hipaa()` / `_fips()` helper pattern. No external library or database table needed.

**Framework data sources (for authoring, not runtime dependency):**

| Framework | Controls | Data Source for Authoring |
|-----------|----------|--------------------------|
| SOC2 (AICPA TSC 2017+) | ~61 Common Criteria across 9 TSC categories (CC1–CC9) | AICPA Trust Services Criteria publication (free download); Vanta Control Set JSON (`VantaInc/vanta-control-set` on GitHub) for machine-readable reference |
| ISO 27001:2022 | 93 controls across 4 themes (Organizational/People/Physical/Technological) | ISO 27001:2022 Annex A (OSCAL-formatted community catalog at `usnistgov/OSCAL` for structure reference) |

**Why static dicts, not a library:**
- `CISO-Assistant` (intuitem/ciso-assistant-community) stores framework data as YAML but requires a full Django + PostgreSQL deployment — not embeddable
- `oscal-pydantic` (`pip install oscal-pydantic`) parses OSCAL JSON but NIST's official OSCAL catalogs do not include SOC2 or ISO27001; community-contributed mappings would require hand-authoring the control list anyway, with added library overhead
- The existing `COMPLIANCE_MAP` pattern (keyed by finding category, `last_verified` + `source_url` + `version` metadata, CI staleness gate) is already correct and enforced; SOC2/ISO27001 entries follow the same structure with zero new infrastructure

**Staleness enforcement:** The existing `STALENESS_THRESHOLD_DAYS = 365` (Phase 49 / COMPLY-08) covers PCI/HIPAA/FIPS. SOC2/ISO27001 entries added in v4.7 use the same `last_verified` field. The quarterly CI gate already gates on this. No new enforcement mechanism needed.

**Confidence:** MEDIUM-HIGH — SOC2 TSC structure verified via AICPA documentation and Vanta Control Set repo; ISO 27001:2022 control count (93) verified via multiple compliance sources. The "embed as static dict" decision is HIGH confidence given existing pattern; specific control IDs to map require framework document review during implementation.

---

### 6. CBOM FIPS 140-3 Annotations — COMPLY-10

**Verdict:** No new library. Extend existing `quirk/cbom/classifier.py` and `quirk/cbom/builder.py`.

The CycloneDX 1.6 schema (`cyclonedx-python-lib>=11.7.0`) already supports algorithm components with `cryptoProperties`. The classifier already has a 50+ entry NIST PQC lookup table. FIPS 140-3 annotation is adding a `fips_approved: bool` field and FIPS 140-3 reference to the `cryptoProperties` of each algorithm component.

No FIPS 140-3 parsing library exists or is needed — the approved algorithm list is a finite static set (AES-128/256 CBC/GCM, SHA-256/384/512, RSA-2048+ PSS, ECDSA P-256/P-384, HMAC-SHA-256+, ML-KEM, ML-DSA per FIPS 203/204).

**Confidence:** HIGH — verified against existing classifier structure and `cyclonedx-python-lib` schema capabilities.

---

### 7. `quirk doctor` Health-Check CLI Command

**Verdict:** No new library. Implement with existing `rich` (already in core deps at `>=13.0.0`) + Python stdlib `importlib.util.find_spec()` for import probing.

**Pattern:** A `quirk doctor` subcommand runs a checklist of named checks, prints a `rich.table.Table` with Pass/Warn/Fail per check, and exits with code `1` if any check is Fail. This is the established `brew doctor` / `flutter doctor` / `poetry check` pattern.

Recommended checks:
```
1. Python version >= 3.11         ← sys.version_info
2. Config file present + parseable ← Path(config_path).exists() + yaml.safe_load
3. SQLite DB path writable         ← tempfile write probe to db_path directory
4. Dashboard extras installed      ← importlib.util.find_spec("fastapi")
5. CBOM extras installed           ← importlib.util.find_spec("cyclonedx")
6. Cloud extras installed          ← importlib.util.find_spec("google.cloud")
7. Compliance map staleness        ← STALENESS_THRESHOLD_DAYS gate in compliance/__init__.py
8. QRAMM framework staleness       ← qramm_version/last_verified in qramm_framework_meta (v4.7)
```

Implementation: `quirk/cli/doctor_cmd.py` registered as `quirk doctor` in `run_scan.py` CLI entry point. Uses `rich.table.Table` + `rich.console.Console` (both already imported in `quirk/cli/banner.py`). Exit code `0` = all pass/warn, `1` = any fail.

**Confidence:** HIGH — `rich` verified in core deps and actively used in `quirk/cli/`; `importlib.util` is Python stdlib; pattern is industry-standard.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| QRAMM scoring | Pure Python floats | NumPy | 120 scalar values; numpy import cost not justified |
| Compliance framework data | Static Python dicts | `oscal-pydantic` library | OSCAL official catalogs don't include SOC2/ISO27001; adds dep for no gain |
| Compliance framework data | Static Python dicts | CISO-Assistant YAML files | Full Django + PostgreSQL app; not embeddable without extraction |
| Radar chart | Recharts (already bundled) | D3.js | Already in bundle; D3 requires imperative SVG code; no benefit |
| Radar chart | Recharts (already bundled) | Apache ECharts | Heavier bundle; not already present; same chart types |
| Assessment wizard state | `useState` / `useReducer` | react-hook-form | Overkill for flat integer map; no validation complexity |
| Doctor command | `rich` + `importlib` | Custom health check library | `rich` already a core dep; no new dependency justified |
| SQLAlchemy schema evolution | Additive `CREATE TABLE IF NOT EXISTS` | Alembic | Single-file local SQLite; migration tooling adds complexity with no benefit until SaaS phase |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| NumPy / SciPy / pandas | Maturity math is scalar; adds 50+ MB to install footprint | Pure Python arithmetic in `quirk/qramm/scoring.py` |
| `oscal-pydantic` | OSCAL doesn't have official SOC2/ISO27001 catalogs; adds dep with no usable data | Static dicts following existing `_pci()` pattern |
| `react-hook-form` or `formik` | 120 integer inputs with no validation complexity | `useState` + `useReducer` |
| Chart.js or D3.js | Recharts already bundled; D3 is imperative/verbose | `recharts` `RadarChart` (already present at `^2.15.4`) |
| Alembic | Local SQLite; additive tables don't need migration tooling | `CREATE TABLE IF NOT EXISTS` in `quirk/db.py` |
| Full GRC platform SDK | Django + PostgreSQL stack; not embeddable | Hand-authored static compliance dicts |
| Any new mandatory `pip` dependency | Zero new core deps is an explicit v4.7 constraint per PROJECT.md | Wire against existing `SQLAlchemy`, `FastAPI`, `rich`, `Recharts` |

---

## Version Compatibility Notes

| Package | Current Constraint | v4.7 Impact |
|---------|--------------------|-------------|
| `recharts` | `^2.15.4` | RadarChart present since v2.x; no upgrade needed |
| `SQLAlchemy` | `>=2.0` | `declarative_base` pattern used for new QRAMM tables |
| `cyclonedx-python-lib` | `>=11.7.0,<12` | FIPS 140-3 annotation extends `cryptoProperties`; no version bump needed |
| `rich` | `>=13.0.0` | `Table`, `Console`, `Panel` all present since v13; no upgrade |
| `@radix-ui/react-tabs` | `^1.1.13` | Already in bundle; QRAMM wizard uses it for dimension tabs |
| `react-router-dom` | `^7.4.0` | Already in bundle; add `/qramm/*` route namespace |

---

## Installation

No new `pip install` commands for v4.7 core features. All new capabilities wire against existing dependencies.

```bash
# Nothing new to install — all stack additions are code, not new packages.
# Verify existing extras still install cleanly after v4.7 schema additions:
pip install quirk[all]
pip install quirk[dashboard]
```

---

## Sources

- [QRAMM Toolkit Overview](https://qramm.org/toolkit-overview.html) — Dimension structure, scoring formula, 120-question count, 5-level maturity scale (HIGH confidence)
- [QRAMM Framework Overview on GitHub](https://github.com/csnp/qramm/blob/main/framework/qramm-overview.md) — Confirmed weakest-link Dimension Score formula, Stream A/B weighting (HIGH confidence)
- [Recharts RadarChart — Context7 `/recharts/recharts`](https://context7.com/recharts/recharts) — Verified `RadarChart`, `PolarGrid`, `PolarAngleAxis`, `ResponsiveContainer` all exported in v2.x (HIGH confidence)
- [Vanta Control Set](https://github.com/VantaInc/vanta-control-set) — Machine-readable SOC2 + ISO27001 controls in JSON; usable as authoring reference (MEDIUM confidence — low maintenance activity on the repo)
- [NIST OSCAL](https://github.com/usnistgov/OSCAL) — Official OSCAL catalogs (NIST 800-53, CSF, 800-171); SOC2/ISO27001 not in official catalog (HIGH confidence)
- [oscal-pydantic on PyPI](https://pypi.org/project/oscal-pydantic/) — Available but only useful for NIST-native catalogs (MEDIUM confidence)
- [CISO-Assistant Community](https://github.com/intuitem/ciso-assistant-community) — 130+ framework GRC platform; YAML framework data not embeddable standalone (MEDIUM confidence)
- `src/dashboard/package.json` — Confirmed `recharts@^2.15.4` already in bundle (HIGH confidence — direct file read)
- `quirk/models.py` — Confirmed `declarative_base()` + `Column` SQLAlchemy 2.0 pattern (HIGH confidence — direct file read)
- `quirk/compliance/__init__.py` — Confirmed `_pci()`/`_hipaa()`/`_fips()` dict pattern + `last_verified`/`source_url`/`STALENESS_THRESHOLD_DAYS` infrastructure (HIGH confidence — direct file read)
- `quirk/cli/banner.py` — Confirmed `rich.console.Console` + `rich.panel.Panel` already imported in core CLI (HIGH confidence — direct file read)

---
*Stack research for: QU.I.R.K. v4.7 Governance & Compliance Platform*
*Researched: 2026-05-05*

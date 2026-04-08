# Phase 17: Identity Infrastructure - Research

**Researched:** 2026-04-08
**Domain:** Python dataclass config extension, SQLAlchemy schema migration, pyproject.toml optional extras
**Confidence:** HIGH

## Summary

Phase 17 is a pure infrastructure/plumbing phase with no scanner logic. It adds three nullable
SQLite columns to `ScanResult` via an idempotent ALTER TABLE guard, three enable flags and three
target list fields to `ConnectorsCfg`, an `[identity]` optional extras group in `pyproject.toml`,
and a commented-out identity subsection in `config_template.yaml`. All patterns are direct
extensions of existing v4.1 code already in the repo.

The codebase patterns are well-established and consistent (all four prior scanner types — JWT,
container, source, cloud — follow identical conventions). The implementation risk is low. The one
notable finding is that `dnspython[dnssec]>=2.8.0` requires `cryptography>=45` as a transitive
dependency; the current pyproject.toml core pin is `cryptography>=44.0`. Since Python 3.14 + pip
will select the highest compatible version at install time (currently 46.0.6 is installed), this
is not a blocker — but the version pin in pyproject.toml may need loosening in a future phase if a
user installs into a fresh venv. For this phase's purposes, the extras group declaration is the
deliverable, not the resolution itself.

The TDD scaffold (Plan 17-01) writes RED tests that assert all three success criteria before any
production code exists. Plan 17-02 then makes them GREEN. The test patterns in this project use
`unittest.TestCase` for schema/packaging assertions and plain pytest functions for import/config
assertions — both styles are in active use.

**Primary recommendation:** Follow existing patterns exactly. Copy `ssh_audit_json` for columns,
`enable_jwt`/`jwt_targets` for config fields, and the `[dashboard]` block for the extras group.
No novel patterns needed.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Use SQLAlchemy inspector-first pattern for idempotent column additions. After
`Base.metadata.create_all(engine)`, call a helper that checks
`sa_inspect(engine).get_columns("scan_results")` and only runs `ALTER TABLE ... ADD COLUMN`
if the column name is absent. Avoid catching exceptions for control flow.

**D-02:** Add three nullable Text columns to `ScanResult`: `kerberos_scan_json`,
`saml_scan_json`, `dnssec_scan_json` — matching the existing `ssh_audit_json`, `jwt_scan_json`,
`container_scan_json` pattern in `quirk/models.py`.

**D-03:** The migration helper lives in `db.py` and is called from `init_db()` after
`create_all()` — no separate migration file or Alembic dependency.

**D-04:** Add `enable_kerberos`, `enable_saml`, `enable_dnssec` boolean flags to
`ConnectorsCfg` with `= False` defaults — matching `enable_jwt: bool = False` pattern.

**D-05:** Add separate target list fields: `kerberos_targets: list`, `saml_targets: list`,
`dnssec_targets: list` — all untyped `list` with `field(default_factory=list)`, matching
`jwt_targets`, `container_targets`, `source_targets` exactly.

**D-06:** Identity fields do NOT overlap with main scan targets — identity scanning is explicit
opt-in targeting, not a network sweep.

**D-07:** Add `[identity]` optional extras group after the existing `[dashboard]` group. Exact
packages: `impacket>=0.13.0,<0.14`, `dnspython[dnssec]>=2.8.0`, `lxml>=6.0`,
`defusedxml>=0.7.1`, `signxml>=4.4.0`.

**D-08:** `impacket` must NOT enter core dependencies — stays in `[identity]` only due to
pyOpenSSL transitive conflict risk with the core cryptography stack.

**D-09:** Add a new `# -- Identity connectors (optional) ---` subsection at the end of
`quirk/config_template.yaml`, commented out by default. Each target field gets a descriptive
inline comment.

### Claude's Discretion

- Exact helper function signature and naming in `db.py` (e.g., `_ensure_identity_columns` or
  `_ensure_columns`)
- Whether the migration helper checks one column list at once or per-column
- Inline comment verbosity in `config_template.yaml` identity section

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | SQLite schema gains `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` nullable columns with idempotent `ALTER TABLE ADD COLUMN` guard in `db.py` startup | SQLAlchemy 2.0 `inspect().get_columns()` confirmed working; full idempotent pattern verified by live test below |
| INFRA-02 | `ConnectorsCfg` gains `enable_kerberos`, `enable_saml`, `enable_dnssec` flags and corresponding target list fields wired to `config.yaml` | Existing dataclass pattern in `quirk/config.py` is directly extensible; `config_from_dict()` passes `**kwargs` from YAML dict — new fields with Python defaults survive missing keys in old config files |
| INFRA-03 | `pyproject.toml` gains `[identity]` optional extras group declaring `impacket>=0.13.0,<0.14`, `dnspython[dnssec]>=2.8.0`, `lxml>=6.0`, `defusedxml>=0.7.1`, `signxml>=4.4.0` | All packages verified on PyPI; version availability and transitive deps documented below |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- If detection logic changes, update `labs/*/expected_results.md` accordingly (N/A this phase —
  no detection logic changes).
- Stack: Python 3.11+, SQLite, pyproject.toml for packaging.

---

## Standard Stack

### Core (already in project — extend only)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.48 (installed) | ORM + inspector for schema introspection | Core dep; `inspect()` API is the documented way to reflect existing schema |
| Python dataclasses | stdlib | `ConnectorsCfg` config struct | Already used throughout `quirk/config.py` |
| PyYAML | >=6.0 | Config loading | Core dep; `yaml.safe_load()` populates `config_from_dict()` |

### New Optional Extras (to be declared in [identity])
| Library | PyPI Version | Purpose | Constraint |
|---------|-------------|---------|------------|
| impacket | 0.13.0 (latest) | Kerberos AS-REQ (Phase 20) | `>=0.13.0,<0.14` — upper bound prevents 0.14 breaking changes; NOT in core deps |
| dnspython[dnssec] | 2.8.0 (latest, Sep 2025) | DNSSEC queries (Phase 18) | `>=2.8.0`; [dnssec] extra pulls `cryptography>=45` transitively |
| lxml | 6.0.2 (latest) | SAML metadata XML parsing (Phase 19) | `>=6.0`; already installed at 6.0.1 |
| defusedxml | 0.7.1 (latest/only) | Safe XML parsing wrapper | `>=0.7.1` |
| signxml | 4.4.0 (latest) | XML signature verification (Phase 19) | `>=4.4.0` |

**Version verification (run 2026-04-08):**
- impacket: PyPI latest 0.13.0 — matches requirement
- dnspython: PyPI latest 2.8.0 (released 2025-09-07) — local pip cache shows 2.7.0 but PyPI confirms 2.8.0 exists
- lxml: PyPI latest 6.0.2; installed 6.0.1 — `>=6.0` satisfies both
- defusedxml: PyPI latest 0.7.1 — matches requirement
- signxml: PyPI latest 4.4.0 — matches requirement

**Installation (Phase 17 declaration only — not installing now):**
```bash
# When a consultant installs identity scanning support:
pip install quirk[identity]
```

**Note on dnspython[dnssec] transitive dependency:** `dnspython[dnssec]>=2.8.0` requires
`cryptography>=45` as a transitive dependency. The core pyproject.toml currently pins
`cryptography>=44.0`. In a fresh install, pip will select cryptography 46.x (latest) which
satisfies both `>=44.0` (core) and `>=45` (dnspython transitive). This is not a conflict — pip
resolves to the highest satisfying version. No pin change needed this phase.

**Note on impacket pyOpenSSL conflict:** impacket 0.13.0 depends on `pyOpenSSL` (no version pin).
`pyOpenSSL` is not currently in core deps and not installed. If a user installs
`pip install quirk[identity]`, pip will add pyOpenSSL. This does not conflict with `cryptography`
directly in modern versions (pyOpenSSL 24+ works with cryptography 40+). The isolation in
`[identity]` extras prevents contamination of users who do not need Kerberos scanning.

---

## Architecture Patterns

### Pattern 1: Inspector-First Idempotent Schema Migration
**What:** After `Base.metadata.create_all(engine)`, call a helper that reads existing column names
via `sa_inspect(engine).get_columns(table_name)` and only executes `ALTER TABLE ADD COLUMN` for
columns not already present.

**When to use:** Any time a new nullable column is added to an existing production table. Allows
`init_db()` to be called against a v4.1 quirk.db without error.

**Verified pattern (live test confirmed working with SQLAlchemy 2.0.48):**
```python
# Source: verified by live Python test on 2026-04-08
from sqlalchemy import inspect as sa_inspect, text

_IDENTITY_COLUMNS = [
    "kerberos_scan_json",
    "saml_scan_json",
    "dnssec_scan_json",
]

def _ensure_identity_columns(engine) -> None:
    """Add identity scanner JSON columns to scan_results if absent (idempotent)."""
    existing = {c["name"] for c in sa_inspect(engine).get_columns("scan_results")}
    with engine.connect() as conn:
        for col in _IDENTITY_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE scan_results ADD COLUMN {col} TEXT"))
        conn.commit()
```

**Where it goes:** Added to `db.py`, called from `init_db()` after `Base.metadata.create_all(engine)`:
```python
# In init_db():
Base.metadata.create_all(engine)
_ensure_identity_columns(engine)  # new line
return engine
```

**Anti-pattern:** Do NOT use `try/except OperationalError` to detect duplicate-column errors.
SQLite's `OperationalError: table scan_results already has a column named X` is not reliable
across SQLite versions and couples error handling to control flow.

### Pattern 2: ConnectorsCfg Dataclass Extension
**What:** Add new fields to `ConnectorsCfg` with Python-level defaults. The `config_from_dict()`
function passes `**{k: v for k, v in (raw.get("connectors") or {}).items() ...}` — any key
absent from YAML falls back to the dataclass default automatically.

**Existing field pattern (from `quirk/config.py`):**
```python
# Enable flag — copy this exact signature
enable_jwt: bool = False

# Target list — copy this exact signature
jwt_targets: list = field(default_factory=list)
```

**New fields to add (after existing scanner fields, before closing brace):**
```python
# Identity connector enable flags (v4.2)
enable_kerberos: bool = False
enable_saml: bool = False
enable_dnssec: bool = False
# Identity connector target lists (v4.2)
kerberos_targets: list = field(default_factory=list)
saml_targets: list = field(default_factory=list)
dnssec_targets: list = field(default_factory=list)
```

**Backward-compatibility:** A v4.1 config.yaml missing these keys will load without error because
all new fields have Python defaults. No `config_from_dict()` changes needed.

### Pattern 3: pyproject.toml Optional Extras Group
**What:** Declare an `[identity]` block under `[project.optional-dependencies]` following the
existing `[dashboard]` block format.

**Existing `[dashboard]` block (exact format to replicate):**
```toml
[project.optional-dependencies]
dashboard = [
    "fastapi>=0.128.8",
    "uvicorn[standard]>=0.39.0",
    "python-multipart>=0.0.20",
    "playwright>=1.58.0",
]
```

**New `[identity]` block:**
```toml
identity = [
    "impacket>=0.13.0,<0.14",
    "dnspython[dnssec]>=2.8.0",
    "lxml>=6.0",
    "defusedxml>=0.7.1",
    "signxml>=4.4.0",
]
```

### Pattern 4: Config Template Identity Section
**What:** Add a commented-out subsection at the end of `quirk/config_template.yaml`. The entire
section is commented out — consultants uncomment only the protocol they need.

**Existing section header format:**
```yaml
# -- Intelligence / scoring profile -----------------------------------------
# intelligence:
#   profile: balanced
```

**New identity section (appended after intelligence block):**
```yaml
# -- Identity connectors (optional) -----------------------------------------
# Install identity extras first: pip install quirk[identity]
# connectors:
#   enable_kerberos: false
#   kerberos_targets:
#     - "kdc.example.com"       # KDC hostname or IP (port 88, TCP with UDP fallback)
#   enable_saml: false
#   saml_targets:
#     - "https://idp.example.com/metadata.xml"  # SAML IdP metadata URL
#   enable_dnssec: false
#   dnssec_targets:
#     - "example.com"           # Domain name for DNSKEY / DS record queries
```

**Note:** The template uses a `connectors:` key that already exists in the non-commented section.
YAML allows duplicate top-level keys only if they are in separate documents. Preferred approach:
comment the sub-keys only (not the `connectors:` key again), or restructure as a separate comment
block that explains the fields to add under the existing `connectors:` key. See Anti-pattern below.

### Anti-Patterns to Avoid
- **Duplicate YAML top-level key:** `config_template.yaml` already has a `connectors:` block.
  Adding another `# connectors:` block below it would cause YAML parsers to silently drop the
  first block if uncommented. Instead, comment the identity sub-fields within a clearly labeled
  comment block — or include them as commented-out lines within the existing `connectors:` block.
- **Alembic dependency for a single migration:** Three nullable columns do not warrant adding
  Alembic (locked by D-03).
- **Exception-for-control-flow migration:** `try: ALTER TABLE ... except OperationalError: pass`
  is fragile; use inspector check (locked by D-01).
- **impacket in core deps:** Would pull pyOpenSSL for all users regardless of scan type (locked
  by D-08).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column existence check | Custom SQL `PRAGMA table_info()` parser | `sa_inspect(engine).get_columns()` | SQLAlchemy 2.0 built-in; returns normalized dict with `name` key; handles all SQLite dialects |
| Config backward-compat | Custom YAML key-presence checks | Dataclass field defaults | `config_from_dict()` already uses `**kwargs` pass-through; Python fills missing keys from defaults automatically |

---

## Runtime State Inventory

> This section is included because this phase modifies the SQLite schema of an existing database.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `quirk.db` SQLite file — existing `scan_results` table lacks `kerberos_scan_json`, `saml_scan_json`, `dnssec_scan_json` columns | Code edit: `_ensure_identity_columns()` helper in `db.py` performs live ALTER TABLE on startup; no data migration (columns are nullable, existing rows get NULL) |
| Live service config | None — no external service config references these columns | None |
| OS-registered state | None — no OS-level registration of scanner types | None |
| Secrets/env vars | None — no environment variables reference identity connector fields | None |
| Build artifacts | `quirk.egg-info/` — stale after pyproject.toml `[identity]` addition | Reinstall: `pip install -e .` after pyproject.toml edit |

---

## Common Pitfalls

### Pitfall 1: YAML Duplicate Key in Config Template
**What goes wrong:** Adding a second `connectors:` top-level key in `config_template.yaml` (even
commented out) — if a consultant uncomments it, the YAML parser uses the last definition and
silently drops all keys from the first.
**Why it happens:** The commented-out identity section mirrors the structure of the live
`connectors:` block, tempting the author to repeat the top-level key.
**How to avoid:** Embed the identity fields as commented-out lines within the existing `connectors:`
block, OR write a clearly labeled comment block that instructs consultants to add these lines under
the existing `connectors:` key.
**Warning signs:** `connectors:` appears more than once at column 0 in the YAML file.

### Pitfall 2: dnspython[dnssec] Extras Bracket in TOML
**What goes wrong:** `"dnspython[dnssec]>=2.8.0"` in a TOML file — the `[` and `]` characters
are valid in PEP 508 extras syntax and are correctly handled by pip when inside a TOML string.
**Why it happens:** Developers unfamiliar with PEP 508 may strip the `[dnssec]` extras suffix.
**How to avoid:** Keep the `[dnssec]` suffix in the quoted string — pip correctly resolves it.
Without it, the `cryptography` transitive dep for DNSSEC validation is not installed.
**Warning signs:** `pip install quirk[identity]` succeeds but `import dns.dnssec` raises
`ImportError: dnspython requires the 'cryptography' package for this operation`.

### Pitfall 3: Forgetting `field(default_factory=list)` for List Fields
**What goes wrong:** Declaring `kerberos_targets: list = []` instead of
`field(default_factory=list)` — Python dataclasses raise `ValueError: mutable default is not
allowed` at class definition time.
**Why it happens:** Works in regular Python classes but not dataclasses.
**How to avoid:** Use `field(default_factory=list)` for all list-typed fields (matches all
existing `*_targets` fields in `ConnectorsCfg`).
**Warning signs:** `ValueError: mutable default <class 'list'> for field kerberos_targets is not
allowed: use default_factory` at import time.

### Pitfall 4: Inspector Called Before `create_all`
**What goes wrong:** Calling `sa_inspect(engine).get_columns("scan_results")` before
`Base.metadata.create_all(engine)` on a fresh DB — the table does not exist yet, and
`get_columns()` raises `NoSuchTableError`.
**Why it happens:** Placing the migration guard above `create_all()` in `init_db()`.
**How to avoid:** Always call `_ensure_identity_columns(engine)` AFTER `create_all()` — the table
is guaranteed to exist.
**Warning signs:** `sqlalchemy.exc.NoSuchTableError: scan_results` on first run against new DB.

### Pitfall 5: dnspython 2.8.0 Not in Local pip Cache
**What goes wrong:** `pip install quirk[identity]` on a machine with a stale pip cache resolves
`dnspython` to 2.7.0 (latest in cache) which does not satisfy `>=2.8.0`.
**Why it happens:** dnspython 2.8.0 was released September 2025; cached index pre-dates it.
**How to avoid:** Run `pip install --upgrade quirk[identity]` or ensure PyPI index is fresh. For
automated testing of the extras group, use `pip install --no-cache-dir quirk[identity]`.
**Warning signs:** `ERROR: Could not find a version that satisfies the requirement dnspython[dnssec]>=2.8.0`.

---

## Code Examples

Verified patterns from live execution and existing codebase:

### Inspector-First Column Check (Live Verified)
```python
# Source: verified by live Python test, SQLAlchemy 2.0.48, 2026-04-08
from sqlalchemy import inspect as sa_inspect, text

_IDENTITY_COLUMNS = ["kerberos_scan_json", "saml_scan_json", "dnssec_scan_json"]

def _ensure_identity_columns(engine) -> None:
    existing = {c["name"] for c in sa_inspect(engine).get_columns("scan_results")}
    with engine.connect() as conn:
        for col in _IDENTITY_COLUMNS:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE scan_results ADD COLUMN {col} TEXT"))
        conn.commit()
```

### ScanResult Model Column Addition (Pattern Match)
```python
# Source: quirk/models.py, existing columns at lines 54-62
# v4.2 identity scanner fields — follow same comment block format
kerberos_scan_json = Column(Text, nullable=True)  # Full Kerberos scan JSON
saml_scan_json = Column(Text, nullable=True)       # Full SAML scan JSON
dnssec_scan_json = Column(Text, nullable=True)     # Full DNSSEC scan JSON
```

### ConnectorsCfg Field Addition (Pattern Match)
```python
# Source: quirk/config.py lines 48-60 (existing pattern)
# Add after source_targets:
enable_kerberos: bool = False
enable_saml: bool = False
enable_dnssec: bool = False
kerberos_targets: list = field(default_factory=list)
saml_targets: list = field(default_factory=list)
dnssec_targets: list = field(default_factory=list)
```

### Existing RED Test Scaffold Style (Phase 16 pattern)
```python
# Source: tests/test_v41_gap_closure.py — the established TDD scaffold style
import unittest

class TestIdentityInfrastructure(unittest.TestCase):
    """RED scaffold for Phase 17 INFRA-01, INFRA-02, INFRA-03."""

    def test_schema_has_kerberos_column(self):
        """INFRA-01: scan_results must have kerberos_scan_json column after init_db()."""
        # RED: column does not exist until _ensure_identity_columns() is added
        ...

    def test_config_has_enable_kerberos(self):
        """INFRA-02: ConnectorsCfg must accept enable_kerberos=True."""
        # RED: field does not exist until config.py is updated
        ...

    def test_pyproject_identity_extras(self):
        """INFRA-03: pyproject.toml must declare [identity] extras group."""
        # RED: group does not exist until pyproject.toml is updated
        ...
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.14.3 (3.11+ required) | — |
| SQLAlchemy | INFRA-01 | Yes | 2.0.48 | — |
| pytest | Test scaffold | Yes | 9.0.2 | — |
| pip | Package verification | Yes | current | — |
| impacket | INFRA-03 declaration | Not installed | — | Declaration only this phase; install tested in Phase 20 |
| dnspython 2.8.0 | INFRA-03 declaration | Not in local cache (2.7.0 cached) | — | PyPI confirmed 2.8.0 exists; use `--no-cache-dir` for verification |
| lxml | INFRA-03 declaration | Yes (installed) | 6.0.1 | — |
| defusedxml | INFRA-03 declaration | Yes (installed) | 0.7.1 | — |
| signxml | INFRA-03 declaration | Yes (installed) | 4.4.0 | — |

**Missing dependencies with no fallback:**
- None — all declarations are for the extras group; actual scanner import happens in phases 18-20.

**Missing dependencies with fallback:**
- dnspython 2.8.0 in local pip cache: use `pip install --no-cache-dir dnspython[dnssec]>=2.8.0`
  to verify resolution against PyPI; the requirement is valid per PyPI.

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (rootdir: `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK`) |
| Quick run command | `python3 -m pytest tests/test_identity_infrastructure.py -v` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `init_db()` on a v4.1 `quirk.db` (missing identity columns) does not raise; columns are present after call | unit | `python3 -m pytest tests/test_identity_infrastructure.py::TestIdentityInfra::test_schema_idempotent_add -x` | No (Wave 0 gap) |
| INFRA-01 | `init_db()` on fresh DB creates all three identity columns | unit | `python3 -m pytest tests/test_identity_infrastructure.py::TestIdentityInfra::test_schema_fresh_db_has_columns -x` | No (Wave 0 gap) |
| INFRA-02 | `ConnectorsCfg` accepts `enable_kerberos=True`, `enable_saml=True`, `enable_dnssec=True` | unit | `python3 -m pytest tests/test_identity_infrastructure.py::TestIdentityInfra::test_config_flags_accepted -x` | No (Wave 0 gap) |
| INFRA-02 | Loading a v4.1 config.yaml (missing identity fields) does not raise | unit | `python3 -m pytest tests/test_identity_infrastructure.py::TestIdentityInfra::test_config_old_yaml_backward_compat -x` | No (Wave 0 gap) |
| INFRA-02 | `quirk init` output contains commented `enable_kerberos` field | unit | `python3 -m pytest tests/test_identity_infrastructure.py::TestIdentityInfra::test_init_template_has_identity_section -x` | No (Wave 0 gap) |
| INFRA-03 | `pyproject.toml` contains `[identity]` extras group with all 5 packages | unit | `python3 -m pytest tests/test_identity_infrastructure.py::TestIdentityInfra::test_pyproject_identity_extras_declared -x` | No (Wave 0 gap) |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_identity_infrastructure.py -v`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- `tests/test_identity_infrastructure.py` — RED test scaffold covering INFRA-01, INFRA-02, INFRA-03 (Plan 17-01 creates this)
- Framework is already installed; no new test infrastructure needed

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `try: ALTER TABLE ... except OperationalError: pass` | `sa_inspect().get_columns()` check first | SQLAlchemy 2.0 | Inspector is deterministic; exception approach fails on non-SQLite or when error messages differ |
| Alembic migrations | Inline `init_db()` guard | Project decision (D-03) | No migration toolchain dependency; simpler for single-file schema evolution |
| pyOpenSSL for crypto | `cryptography` package directly | ~2020+ | Modern Python libs use `cryptography` directly; pyOpenSSL is legacy compatibility shim |

**Deprecated/outdated:**
- `sqlalchemy.engine.reflection.Inspector` (old import path): use `sqlalchemy.inspect` (or
  `from sqlalchemy import inspect as sa_inspect`) in SQLAlchemy 2.0+.
- `declarative_base()` from `sqlalchemy.ext.declarative` (2.0 moved it to `sqlalchemy.orm`): the
  project already uses `from sqlalchemy.orm import declarative_base` — correct.

---

## Open Questions

1. **Config template identity section placement inside vs. outside `connectors:` block**
   - What we know: The `config_template.yaml` has a flat `connectors:` block. Adding a second
     `connectors:` key (commented) risks YAML duplicate-key issues if uncommented naively.
   - What's unclear: Whether to embed commented identity lines inside the existing `connectors:`
     block, or place them as a standalone comment block after it.
   - Recommendation: Embed the identity fields as commented lines at the bottom of the existing
     `connectors:` block (safest — avoids YAML key collision; consultants just uncomment in place).

2. **Model columns vs. migration guard consistency**
   - What we know: `ScanResult` in `models.py` will gain three new `Column(Text)` declarations.
     On a fresh DB, `create_all()` handles this. On an existing DB, `create_all()` does NOT add
     new columns (SQLAlchemy create_all is additive for new tables only, not new columns in
     existing tables).
   - What's unclear: Whether the planner needs explicit test coverage for the case where the model
     has the column but the DB does not (fresh install vs. upgrade path).
   - Recommendation: Yes — INFRA-01 needs both a "fresh DB" test and an "existing DB without
     columns" test to fully validate the guard.

---

## Sources

### Primary (HIGH confidence)
- Live Python execution — SQLAlchemy 2.0.48 inspector-first pattern verified by running against
  in-memory SQLite; full idempotent add + second call confirmed 2026-04-08
- `quirk/config.py` — existing `ConnectorsCfg` dataclass pattern read directly
- `quirk/db.py` — existing `init_db()` function read directly
- `quirk/models.py` — existing `*_scan_json` column pattern read directly
- `quirk/config_template.yaml` — existing YAML template format read directly
- `pyproject.toml` — existing `[dashboard]` extras group format read directly
- PyPI JSON API (`https://pypi.org/pypi/dnspython/json`) — confirmed dnspython 2.8.0 released
  2025-09-07; `[dnssec]` extra requires `cryptography>=45`
- PyPI JSON API (`https://pypi.org/pypi/impacket/0.13.0/json`) — confirmed pyOpenSSL dependency
- Local pip index — impacket 0.13.0, lxml 6.0.2, defusedxml 0.7.1, signxml 4.4.0 versions

### Secondary (MEDIUM confidence)
- `tests/test_v41_gap_closure.py`, `tests/test_gap_closure.py` — established RED test scaffold
  style patterns for this project

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified on PyPI; versions confirmed live
- Architecture: HIGH — patterns read directly from existing codebase; inspector pattern live-tested
- Pitfalls: HIGH (YAML pitfall, dataclass pitfall) / MEDIUM (dnspython cache pitfall — PyPI confirmed but local cache stale)

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable domain — pyproject.toml packaging and SQLAlchemy inspector API are not fast-moving)

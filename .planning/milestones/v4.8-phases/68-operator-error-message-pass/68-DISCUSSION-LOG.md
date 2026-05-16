# Phase 68: Operator Error-Message Pass - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 68-operator-error-message-pass
**Areas discussed:** Error code namespace, Error catalog home, First-run error surface, quirk errors command

---

## Error Code Namespace

### Q1: Pattern scope

| Option | Description | Selected |
|--------|-------------|----------|
| Unified QRK-DOMAIN-NNN | Every error — CLI, scanner, dashboard, install — uses same pattern | ✓ |
| Scanner-only codes, flat for others | Scanner errors get codes; CLI/install get descriptive text | |
| You decide | Claude picks | |

**User's choice:** Unified QRK-DOMAIN-NNN
**Notes:** Clean, consistent, one pattern to document.

### Q2: Domain granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Subsystem-granular | INSTALL, TLS, SSH, JWT, CLOUD, DB, SCHED, CBOM, DASHBOARD | ✓ |
| Broad buckets | INSTALL, SCAN, API, DASHBOARD | |
| You decide | Claude picks | |

**User's choice:** Subsystem-granular
**Notes:** Makes it easier to route operators to the right fix doc and leaves room to grow.

### Q3: Numbering within domain

| Option | Description | Selected |
|--------|-------------|----------|
| Flat sequential | TLS-001, TLS-002, ... | ✓ |
| Grouped by category | 1xx = config, 2xx = network, 3xx = parse | |
| You decide | Claude picks | |

**User's choice:** Flat sequential
**Notes:** Simpler to assign, no need to pre-plan category buckets.

### Q4: Wire format

| Option | Description | Selected |
|--------|-------------|----------|
| [QRK-TLS-001] cause. Fix: hint. | Inline code + cause + Fix: prefix | ✓ |
| QRK-TLS-001: cause (remediation in docs only) | Shorter inline, look up fix in docs | |
| You decide | Claude picks | |

**User's choice:** `[QRK-TLS-001] cause message. Fix: remediation hint.`
**Notes:** Self-contained, greppable in logs.

---

## Error Catalog Home

### Q1: Registry location

| Option | Description | Selected |
|--------|-------------|----------|
| Python module quirk/errors.py | Importable dict/dataclass registry | ✓ |
| YAML/JSON file | File-parsed at startup | |
| Inline constants per-module | Scattered, collected via import hooks | |
| You decide | Claude picks | |

**User's choice:** `quirk/errors.py` Python module
**Notes:** Single source, no drift, clean imports.

### Q2: Formatting helper

| Option | Description | Selected |
|--------|-------------|----------|
| format_error(code) helper in errors.py | Returns ready-to-emit string | ✓ |
| Call sites assemble strings | More flexible, risks format drift | |

**User's choice:** `format_error(code)` helper
**Notes:** Guarantees consistent format everywhere.

### Q3: docs/error-codes.md generation

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generated via quirk errors --dump-md | CI asserts file is current | ✓ |
| Hand-maintained | Developer keeps both in sync manually | |

**User's choice:** Auto-generated
**Notes:** Prevents drift; CI enforcement pattern analogous to staleness check.

### Q4: scan_error_category relationship

| Option | Description | Selected |
|--------|-------------|----------|
| Map to QRK codes at render time | No DB change; mapping in errors.py | ✓ |
| Keep them separate | Two parallel systems internally | |

**User's choice:** Map at render time
**Notes:** No DB schema change needed; existing category values become seeds for the QRK code mapping.

---

## First-Run Error Surface

### Q1: Where to surface install-day errors

| Option | Description | Selected |
|--------|-------------|----------|
| Extend quirk doctor + inline at scan entrypoint | Both paths use format_error() | ✓ |
| Inline at scan entrypoint only | Doctor left as-is | |
| Extend quirk doctor only | Operators must know to run doctor first | |

**User's choice:** Both doctor and scan entrypoint
**Notes:** Defensive — operators get clean error regardless of whether they ran doctor.

### Q2: Smoke test location

| Option | Description | Selected |
|--------|-------------|----------|
| pytest in tests/test_install_errors.py | Subprocess calls, CI-integrated | ✓ |
| Shell script in labs/ | Manual runbook, not in CI | |

**User's choice:** pytest
**Notes:** CI picks it up automatically.

### Q3: Port-conflict fix hint detail

| Option | Description | Selected |
|--------|-------------|----------|
| Show --port flag + lsof command | Self-contained, operator can act immediately | ✓ |
| Just identify the conflict | Simpler, assumes operator knows how | |

**User's choice:** Show `quirk serve --port <other>` and `lsof -i :8512`
**Notes:** Operator can act on the error without consulting docs.

---

## quirk errors Command

### Q1: Implementation location

| Option | Description | Selected |
|--------|-------------|----------|
| New quirk/cli/errors_cmd.py module | Follows doctor_cmd.py / init_cmd.py pattern | ✓ |
| Inline in run_scan.py | Simpler but adds to already-large file | |

**User's choice:** `quirk/cli/errors_cmd.py`
**Notes:** Consistent with established CLI module pattern.

### Q2: Default display

| Option | Description | Selected |
|--------|-------------|----------|
| Full table grouped by domain | All codes visible at once; --domain filters | ✓ |
| Compact domain summary by default | Two-step drill-in | |

**User's choice:** Full table grouped by domain
**Notes:** Operators see everything at once.

### Q3: Per-code lookup

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — quirk errors QRK-TLS-001 positional arg | Great for scripts and runbooks | ✓ |
| No — full table only | Use grep for lookup | |

**User's choice:** Yes — positional arg lookup
**Notes:** Wanted for scripting (`quirk errors $CODE`).

---

## Claude's Discretion

- Exact number of initial codes per domain (researcher/planner audits existing error paths)
- CATEGORY_TO_CODE mapping details for domain-ambiguous categories
- Whether quirk/errors.py uses plain dict, NamedTuple, or @dataclass(frozen=True) for entries

## Deferred Ideas

None — discussion stayed within phase scope.

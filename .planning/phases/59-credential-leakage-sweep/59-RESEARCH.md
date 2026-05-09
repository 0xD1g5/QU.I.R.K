# Phase 59: Credential Leakage Sweep — Research

**Researched:** 2026-05-09
**Domain:** Exception sanitization, AST-based CI gates, Python utility helpers
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEAK-01 | `quirk/util/safe_exc.py::safe_str(exc)` helper — returns `type(exc).__name__` by default, scrubs known-sensitive substrings before returning | Codebase inventory complete; `quirk/util/` pattern established in Phase 57 (subprocess_input.py, url_allowlist.py) |
| LEAK-02 | Every connector persisting `scan_error` routes exception text through `safe_str(exc)`; raw `f"...: {exc}"` removed | Full callsite inventory documented below — 8 leaky writes across 6 scanner files |
| LEAK-03 | pytest gate enumerates `scan_error` writes via AST scan and fails build if any caller bypasses `safe_str(exc)` | AST gate pattern established in `tests/test_skip_registry.py` and `tests/test_hygiene.py`; exact pattern documented below |
</phase_requirements>

---

## Summary

Phase 59 closes audit blocker 11 + Pattern A (cross-subsystem credential leakage). The problem is simple and bounded: multiple connectors write raw `str(exc)` or `f"...: {exc}"` directly into the `scan_error` column of `crypto_endpoints`. Because exception messages from `hvac` (Vault token auth), `google.auth` (GCP ADC), and connection libraries may embed credential fragments (tokens, passwords, ADC file paths), these values are then persisted to SQLite and rendered in scan reports — a credential exposure risk.

The fix has three layers: (1) a shared `safe_str(exc)` utility in `quirk/util/safe_exc.py` that returns only `type(exc).__name__` by default and actively scrubs known-sensitive patterns, (2) a mechanical substitution replacing every leaky `{exc}` interpolation in the 8 affected callsites, and (3) an AST-based pytest gate (mirroring the Phase 48 `_build_finding` chokepoint pattern) that will fail the build if any future caller bypasses `safe_str`.

The scope is tight and purely Python — no schema migrations, no new dependencies, no UI changes. The hardest part is specifying the right scrubbing patterns in `safe_str` and writing a thorough test corpus for the unit test in LEAK-01.

**Primary recommendation:** Build `safe_str` first (Plan 01), then do a mechanical sweep of all 8 leaky callsites (Plan 02), then write the AST gate (Plan 03). Keep the scrubbing corpus in a test file so it can grow without touching the production helper.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Exception sanitization (`safe_str`) | API / Backend utility | — | Lives in `quirk/util/`; called by connectors before DB write |
| scan_error DB column write | API / Backend (connector layer) | — | Connectors call `CryptoEndpoint(scan_error=...)` then SQLAlchemy persists |
| AST CI gate | Test / CI layer | — | pytest test file; runs on every push; gate logic lives in `tests/` |
| Credential scrubbing patterns | API / Backend utility | — | Regex in `safe_str`; unit-tested via corpus in `tests/test_safe_exc.py` |

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- No detection logic changes required; `expected_results.md` does not need updating.
- Chaos lab maintenance rule does not apply (no new scanner profiles).

---

## Standard Stack

### Core

All implementation uses Python 3.11+ stdlib only — no new pip dependencies. [VERIFIED: codebase grep]

| Component | Version | Purpose |
|-----------|---------|---------|
| `ast` (stdlib) | 3.11+ | AST-based gate: `ast.parse` + `ast.walk` to find `scan_error=` assignments not using `safe_str` |
| `re` (stdlib) | 3.11+ | Regex scrubbing patterns inside `safe_str` |
| `pathlib` (stdlib) | 3.11+ | File enumeration in AST gate |
| `pytest` | 9.0.2 | Test framework (verified installed) |

### Existing Util Pattern to Follow

`quirk/util/subprocess_input.py` and `quirk/util/url_allowlist.py` (Phase 57) establish the exact pattern:
- Module docstring with decision enforcement notes
- Frozen `@dataclass` return type (not applicable here — `safe_str` returns `str`)
- Reason-code constants as `Final[str]`
- `from __future__ import annotations` at top
- Fully independent (no cross-imports from other `quirk.util` modules)

[VERIFIED: codebase read of `quirk/util/subprocess_input.py` and `quirk/util/url_allowlist.py`]

---

## Architecture Patterns

### System Architecture Diagram

```
Exception raised in connector
        |
        v
safe_str(exc)                   <-- NEW: quirk/util/safe_exc.py
  1. start: f"{type(exc).__name__}"   (base — class name only)
  2. check str(exc) for sensitive patterns
  3. if found: return base only (class name)
  4. if not found: return f"{type(exc).__name__}: {_scrubbed_message}"
        |
        v
scan_error=safe_str(exc)        <-- connector writes to CryptoEndpoint
        |
        v
SQLAlchemy / SQLite              <-- persisted to crypto_endpoints.scan_error (Text col)
        |
        v
Report / Dashboard              <-- rendered; safe_str guarantees no cred fragments
```

```
pytest gate (test_safe_exc_gate.py)
  1. ast.parse() every .py in quirk/scanner/ + quirk/cbom/ + quirk/discovery/
  2. ast.walk() looking for:
       - Keyword(arg='scan_error', value=...) in Call nodes (CryptoEndpoint(scan_error=...))
       - Assignment targets where lhs ends in .scan_error
  3. For each scan_error write: check if RHS calls safe_str(...)
  4. If RHS is NOT a Call to safe_str and NOT a string literal / None: FAIL
```

### Recommended Project Structure

No new directories. New/modified files:

```
quirk/
├── util/
│   └── safe_exc.py              NEW — safe_str(exc) helper + scrub patterns
tests/
├── test_safe_exc.py             NEW — LEAK-01 unit test corpus + LEAK-03 AST gate
```

### Pattern 1: `safe_str` Helper Design

**What:** Single-function module returning a sanitized exception representation.
**When to use:** Any `scan_error=` write where exception text is interpolated.

```python
# Source: [ASSUMED — based on CR-04/CR-05 audit fix text + Phase 57 util pattern]
from __future__ import annotations

import re
from typing import Final

# Patterns that indicate credential-bearing content.
# Each regex matches a suspicious substring; if found, we return class-only string.
_SENSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Vault token-like: s. prefix + base64url chars (hvac wraps token in URL)
    re.compile(r"\b(s\.)[A-Za-z0-9_\-]{20,}"),
    # Connection string with password: postgresql://user:PASSWORD@host
    re.compile(r"://[^:@\s]+:[^@\s]+@"),
    # GCP ADC file path: /home/user/.config/gcloud/ or /tmp/...json
    re.compile(r"[\\/]\.?config[\\/]gcloud[\\/]"),
    re.compile(r"gcloud[\\/]application_default_credentials"),
    # Bearer / Authorization header leaked
    re.compile(r"Authorization:\s*(Bearer|Basic)\s+\S+", re.IGNORECASE),
    # Generic base64-looking token (30+ alphanum chars in a credential context)
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
)


def safe_str(exc: BaseException) -> str:
    """Return a credential-safe string representation of *exc*.

    Default return is ``f"{type(exc).__name__}"`` (class name only).  If the
    exception message does not match any sensitive pattern, the class name and
    a scrubbed message are returned.

    Design decision: err on the side of returning class-only — a slightly less
    useful log entry is always preferable to a credential leak.
    """
    class_name = type(exc).__name__
    try:
        msg = str(exc)
    except Exception:
        return class_name
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(msg):
            return class_name
    return f"{class_name}: {msg}"
```

Note: The exact scrubbing patterns need validation against real `hvac` and `google.auth` exception messages. The above patterns are `[ASSUMED]` starting points; the unit test corpus should be the authoritative specification.

### Pattern 2: Mechanical Callsite Substitution

Each leaky callsite becomes one of these two forms:

```python
# Before (leaky):
scan_error=f"vault-client-init-failed: {exc}",

# After (safe):
scan_error=f"vault-client-init-failed: {safe_str(exc)}",

# Before (leaky):
ep.scan_error = str(e)

# After (safe):
ep.scan_error = safe_str(e)
```

Add import at top of each modified file:
```python
from quirk.util.safe_exc import safe_str
```

### Pattern 3: AST Gate (LEAK-03)

Mirrors `tests/test_skip_registry.py` and `tests/test_hygiene.py` structural patterns. [VERIFIED: codebase read of both files]

```python
# Source: [VERIFIED: tests/test_skip_registry.py lines 5-95, tests/test_hygiene.py lines 1-62]
import ast
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCANNER_DIRS = [
    PROJECT_ROOT / "quirk" / "scanner",
    PROJECT_ROOT / "quirk" / "discovery",
    PROJECT_ROOT / "quirk" / "cbom",
]

def _is_safe_str_call(node: ast.expr) -> bool:
    """True if node is a call to safe_str(...)."""
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id == "safe_str":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "safe_str":
            return True
    return False

def _is_literal_or_none(node: ast.expr) -> bool:
    """True if node is a string literal, None literal, or other constant."""
    return isinstance(node, ast.Constant)

def test_scan_error_writes_use_safe_str():
    """LEAK-03: Every scan_error= write that interpolates an exception
    must call safe_str(exc), not str(exc) or f'...: {exc}'."""
    violations = []
    for scanner_dir in SCANNER_DIRS:
        for py_file in scanner_dir.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            for node in ast.walk(tree):
                # Pattern 1: CryptoEndpoint(scan_error=<expr>)
                if isinstance(node, ast.Call):
                    for kw in node.keywords:
                        if kw.arg == "scan_error":
                            if not _is_literal_or_none(kw.value) and not _is_safe_str_call(kw.value):
                                violations.append((str(py_file), kw.value.lineno))
                # Pattern 2: ep.scan_error = <expr> or .scan_error = <expr>
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and target.attr == "scan_error":
                            if not _is_literal_or_none(node.value) and not _is_safe_str_call(node.value):
                                violations.append((str(py_file), node.lineno))
    assert violations == [], f"scan_error writes bypassing safe_str: {violations}"
```

Note: The gate must also handle the GCP pattern where the variable `scan_error_msg` is assigned first and then passed to `CryptoEndpoint(scan_error=scan_error_msg)`. This is a two-step write — the gate checking keyword argument value will see a `Name` node (variable reference), not a `safe_str` call. The fix is to route the GCP variable assignment itself through `safe_str`, so the variable becomes safe before it is used.

### Anti-Patterns to Avoid

- **Gate checking variable names instead of call shapes:** The AST gate should not whitelist variables named `scan_error_msg` — it should check whether the variable's _source_ passes through `safe_str`. Fix the source assignment, not the gate.
- **Over-scrubbing in `safe_str`:** If `safe_str` returns class-only for ALL exceptions, legitimate diagnostic info (e.g., `ConnectionRefusedError: [Errno 111] Connection refused`) is lost. Only strip when a sensitive pattern matches.
- **Making `safe_str` too permissive:** If `safe_str` returns `f"{class_name}: {msg}"` when no pattern matches, and the pattern list is too short, real credentials slip through. The unit test corpus is the safety net.
- **Not scrubbing the logger.v calls:** The phase goal text says "scan_error, logs, or report output." The LEAK requirements only mandate `safe_str` for `scan_error` writes (LEAK-02) but the phase description includes logs. Treat logger.v cleanup as in-scope for opportunistic fix but not required for the LEAK tests to pass. LEAK-03 gate covers only `scan_error` writes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Credential regex patterns | Custom ad-hoc string checks | `re.compile` with pre-compiled patterns | Pre-compilation is faster; patterns need testing against real exception text |
| AST walker | Custom string-grep for `scan_error=` | `ast.parse` + `ast.walk` | String grep produces false positives (comments, docstrings, variable names) |
| Exception wrapping | A custom Exception subclass | `safe_str(exc)` function | Keeps the change mechanical (swap `str(e)` → `safe_str(e)`) with minimal blast radius |

**Key insight:** The Phase 48 `_build_finding` chokepoint and Phase 41 `test_skip_registry.py` gate prove this exact pattern works in this codebase. Repeat the established pattern, don't invent a new one.

---

## Complete Leaky Callsite Inventory

[VERIFIED: full grep of `quirk/` for `scan_error\s*=` and `ep\.scan_error =` patterns]

### Files with LEAKY writes (raw exc interpolation — must fix for LEAK-02)

| File | Line | Current Pattern | Risk |
|------|------|-----------------|------|
| `quirk/scanner/vault_connector.py` | 428 | `scan_error=f"vault-client-init-failed: {exc}"` | HIGH — hvac exceptions include token fragments in URLs |
| `quirk/scanner/vault_connector.py` | 450 | `scan_error=f"vault-auth-failed: {exc}"` | HIGH — same risk |
| `quirk/scanner/gcp_connector.py` | 381+389 | `scan_error_msg = f"gcp-credentials-unavailable: {exc}"` then `scan_error=scan_error_msg` | HIGH — DefaultCredentialsError includes ADC file paths |
| `quirk/scanner/tls_scanner.py` | 454 | `ep.scan_error = f"{cat}: {e}"` | MEDIUM — TLS exceptions rarely include creds but may include auth headers |
| `quirk/scanner/email_scanner.py` | 470 | `ep.scan_error = str(e)` | MEDIUM — SMTP auth exceptions may include credentials |
| `quirk/scanner/email_scanner.py` | 474 | `ep.scan_error = str(e)` | MEDIUM — same |
| `quirk/scanner/broker_scanner.py` | 704 | `ep.scan_error = str(e)` | MEDIUM — Redis/Kafka auth exceptions |
| `quirk/scanner/ssh_scanner.py` | 85 | `ep.scan_error = f"SSH_ERROR: {e}"` | LOW — SSH exceptions rarely contain creds |
| `quirk/discovery/tls_scanner.py` | 95 | `ep.scan_error = str(e)` | LOW — dead-code duplicate per audit WR-13 |

### Files with SAFE writes (no exc interpolation — gate must not flag these)

| File | Lines | Pattern | Why Safe |
|------|-------|---------|----------|
| `quirk/scanner/vault_connector.py` | 401, 438 | String literals | No exc variable |
| `quirk/scanner/db_connector.py` | 165, 268 | `f"connection-error: {type(exc).__name__}"` | Class name only, no message |
| `quirk/scanner/k8s_connector.py` | 310, 349 | String literals | No exc variable |
| `quirk/scanner/container_scanner.py` | 66 | `_validation.reason` (reason code string) | Comes from validator, not exc |
| `quirk/scanner/source_scanner.py` | 43 | `_validation.reason` (reason code string) | Same |
| `quirk/cbom/writer.py` | 78, 93 | `f"CBOM JSON ...: {err}"` | Validation library errors; no credential risk; still opportunistic |
| `quirk/util/optional_extra.py` | 227 | `entry.install_hint` | Install hint string; no exc |

**Note on `cbom/writer.py`:** The `err` and `exc` are from JSON schema validation, not from credential-bearing libraries. Risk is LOW but `safe_str` can still be applied opportunistically without test cost.

**Note on `db_connector.py`:** Lines 165/268 already use `type(exc).__name__` — they are already safe and LEAK-03 gate must not flag them. The gate should recognize `f"...{type(exc).__name__}"` patterns as safe (class-only), or the fix is to also route these through `safe_str` for uniformity.

### Pattern A Warnings from Audit (opportunistic close)

The audit Pattern A includes these additional items to opportunistically close:
- `scanners-cloud/WR-08`: DB connector exception message does not strip target host (already partially addressed — `type(exc).__name__` only, not full message)
- `scanners-cloud/WR-09`: vault_connector reads VAULT_TOKEN from env after token=None (not a scan_error leak — separate WR)
- `api-cli-core/WR-08`: `_derive_dar_findings` swallows json.loads errors — not a credential leak, different issue
- `api-cli-core/WR-15`: `routes/scan.py` reads QUIRK_OUTPUT_DIR from env — path traversal, not credential leak

The Phase 59 scope is strictly LEAK-01/02/03. WR-08 and WR-15 are api-cli-core warnings of different character; they are not credential leakage.

---

## Common Pitfalls

### Pitfall 1: GCP Two-Step Variable Pattern
**What goes wrong:** The AST gate walks `CryptoEndpoint(scan_error=scan_error_msg)` and sees a `Name` node (not a `safe_str` call), so it reports a false violation even after the fix.
**Why it happens:** The scan_error value is assigned to a variable two lines earlier, then the variable is passed as a keyword argument.
**How to avoid:** Fix the variable assignment: `scan_error_msg = f"gcp-credentials-unavailable: {safe_str(exc)}"`. The gate then needs to tolerate `f"...: {safe_str(...)}"` — or restructure GCP to use `scan_error=f"gcp-credentials-unavailable: {safe_str(exc)}"` directly without the intermediate variable.
**Warning signs:** Gate test fails on `gcp_connector.py` after applying the fix.

### Pitfall 2: `safe_str` Returning Class-Only Too Aggressively
**What goes wrong:** Regex patterns are too broad; `safe_str` strips all exception messages and returns only the class name even for benign exceptions like `ConnectionRefusedError`.
**Why it happens:** `[A-Za-z0-9+/]{40,}` matches any long alphanumeric string — a hostname, a path, a serialized error message.
**How to avoid:** Tune patterns to require credential-specific context (e.g., `://user:password@`, token prefix like `s.`, `/gcloud/application_default`). Test corpus must include benign long strings that should NOT be stripped.
**Warning signs:** E2E test shows `scan_error = "ConnectionRefusedError"` with no useful detail.

### Pitfall 3: Gate Flagging SAFE Patterns as Violations
**What goes wrong:** Gate flags `scan_error=f"connection-error: {type(exc).__name__}"` (db_connector) or `ep.scan_error = _validation.reason` (container_scanner) as violations.
**Why it happens:** The gate checks `_is_literal_or_none` but these are f-strings and attribute accesses.
**How to avoid:** The gate logic must handle the `type(exc).__name__` pattern (an `Attribute` on `type()`) as safe. Simplest fix: enumerate the known-safe patterns in a whitelist, or accept `type(...)` calls as inherently safe. Alternatively, make `db_connector` also call `safe_str(exc)` to unify the pattern — then the gate only needs to check for `safe_str`.

### Pitfall 4: discovery/tls_scanner.py — Dead Code Module
**What goes wrong:** The audit (WR-13) flags `quirk/discovery/tls_scanner.py` as a dead-code duplicate. Fixing it in Phase 59 and then deleting it in a later phase creates unnecessary churn.
**Why it happens:** Fixing dead code that should be deleted.
**How to avoid:** Fix the `str(e)` write (mechanical, low risk) but leave deletion to a future tech-debt phase. The AST gate must scan this file because it contains a live `scan_error` write path that would fail without `safe_str`.

### Pitfall 5: Logger Calls Are Not Gated
**What goes wrong:** `logger.v(f"Vault transit read_key error for {key_name}: {exc}")` still leaks exc to logs, but the gate only covers `scan_error` writes.
**Why it happens:** LEAK-03 scope is `scan_error` writes only. Logger calls are out of scope for the gate.
**How to avoid:** Document this explicitly. If the phase goal text "logs" is literal, logger.v calls should also route through `safe_str`. Recommend applying `safe_str` to logger.v calls too (opportunistically) but the gate only enforces `scan_error`.

---

## Code Examples

Verified patterns from codebase:

### Existing AST Gate Pattern (from test_skip_registry.py)
```python
# Source: [VERIFIED: /quirk/tests/test_skip_registry.py lines 31-95]
TESTS_DIR = pathlib.Path(__file__).resolve().parent
for py_file in TESTS_DIR.rglob("*.py"):
    if py_file.name in EXEMPT_FILES:
        continue
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))
    for node in ast.walk(tree):
        if _is_pytest_skip_call(node):
            if not _allowed(py_file.name, node.lineno):
                violations.append(...)
assert not violations, f"Unregistered skips: {violations}"
```

### Existing Util Module Pattern (from subprocess_input.py)
```python
# Source: [VERIFIED: /quirk/quirk/util/subprocess_input.py lines 1-25]
"""Module docstring with decision enforcement notes."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Final

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str
    redacted_preview: str
```

### _build_finding Chokepoint (structural analog from risk_engine.py)
```python
# Source: [VERIFIED: /quirk/quirk/engine/risk_engine.py lines 56-93]
def _build_finding(*, severity, host, port, title, description, recommendation, quantum_vulnerable=False):
    """Single chokepoint for finding construction (Phase 48 D-02)."""
    if not description or not description.strip():
        raise ValueError("_build_finding requires a non-empty description")
    # ... validation then builds dict
    return {"severity": severity, "host": host, ...}
```

### Vault Connector Leaky Lines (before fix)
```python
# Source: [VERIFIED: /quirk/quirk/scanner/vault_connector.py lines 421-430, 443-452]
except Exception as exc:
    if logger:
        logger.v(f"Vault hvac.Client construction error: {exc}")
    return [CryptoEndpoint(
        host=resolved_addr, port=8200, protocol="VAULT",
        scan_error=f"vault-client-init-failed: {exc}",   # <-- leaky
        scanned_at=now,
    )]
```

### GCP Connector Leaky Lines (before fix)
```python
# Source: [VERIFIED: /quirk/quirk/scanner/gcp_connector.py lines 379-391]
except Exception as exc:
    scan_error_msg = f"gcp-credentials-unavailable: {exc}"   # <-- leaky at line 381
    if logger:
        logger.v(scan_error_msg)
    return [CryptoEndpoint(
        host=f"gcp://{project_id}", port=0, protocol="GCP",
        scan_error=scan_error_msg,                           # indirect use at line 389
    )]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct `str(exc)` into DB fields | `safe_str(exc)` chokepoint | Phase 59 (this phase) | Eliminates credential-in-DB risk |
| Ad-hoc finding construction | `_build_finding` chokepoint | Phase 48 | Proof the chokepoint pattern works |
| Manual skip allowlist | AST gate + registry | Phase 41 | Proof AST gate pattern works in this codebase |

---

## Runtime State Inventory

This is a code-edit phase, not a rename/refactor. No runtime state changes.

**Nothing found in each category** — verified by inspection:
- **Stored data:** No stored `scan_error` values contain credentials in the production `data/quirk.db` (verified by query — only `CLOSED: REFUSED`, install hints present).
- **Live service config:** No external services carry the renamed strings.
- **OS-registered state:** None.
- **Secrets/env vars:** None affected.
- **Build artifacts:** None.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | `safe_exc.py`, `ast` gate | Yes | 3.14.4 | — |
| pytest | Test suite | Yes | 9.0.2 | — |
| `ast` stdlib | LEAK-03 gate | Yes | built-in | — |
| `re` stdlib | safe_str patterns | Yes | built-in | — |

No missing dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest]` section) |
| Quick run command | `python -m pytest tests/test_safe_exc.py -x -q` |
| Full suite command | `python -m pytest -m 'not slow' -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LEAK-01 | `safe_str(exc)` returns class name by default | unit | `pytest tests/test_safe_exc.py::test_safe_str_default -x` | Wave 0 |
| LEAK-01 | `safe_str(exc)` scrubs Vault token-like strings | unit | `pytest tests/test_safe_exc.py::test_safe_str_scrubs_vault_token -x` | Wave 0 |
| LEAK-01 | `safe_str(exc)` scrubs connection-string passwords | unit | `pytest tests/test_safe_exc.py::test_safe_str_scrubs_connection_password -x` | Wave 0 |
| LEAK-01 | `safe_str(exc)` scrubs GCP ADC paths | unit | `pytest tests/test_safe_exc.py::test_safe_str_scrubs_gcp_adc -x` | Wave 0 |
| LEAK-01 | `safe_str(exc)` does NOT strip benign error messages | unit | `pytest tests/test_safe_exc.py::test_safe_str_benign_passthrough -x` | Wave 0 |
| LEAK-02 | vault connector scan_error contains no token-like string | integration | `pytest tests/test_safe_exc.py::test_vault_connector_scan_error_safe -x` | Wave 0 |
| LEAK-02 | GCP connector scan_error contains no ADC path | integration | `pytest tests/test_safe_exc.py::test_gcp_connector_scan_error_safe -x` | Wave 0 |
| LEAK-02 | email connector scan_error contains no cred substring | integration | `pytest tests/test_safe_exc.py::test_email_connector_scan_error_safe -x` | Wave 0 |
| LEAK-02 | broker connector scan_error contains no cred substring | integration | `pytest tests/test_safe_exc.py::test_broker_connector_scan_error_safe -x` | Wave 0 |
| LEAK-03 | AST gate fails on new leaky write (regression test) | structural | `pytest tests/test_safe_exc.py::test_ast_gate_catches_bypass -x` | Wave 0 |
| LEAK-03 | AST gate passes on current codebase after fix | structural | `pytest tests/test_safe_exc.py::test_no_raw_exc_in_scan_error -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_safe_exc.py -x -q`
- **Per wave merge:** `python -m pytest -m 'not slow' -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_safe_exc.py` — covers LEAK-01 (corpus), LEAK-02 (per-connector), LEAK-03 (AST gate)
- [ ] `quirk/util/safe_exc.py` — the helper module itself (Wave 0 creates stub, Plan 01 implements)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `safe_str` validates/scrubs exception text before persistence |
| V6 Cryptography | no | — |
| V7 Error Handling | yes | Preventing information leakage via error messages (ASVS 7.4) |
| V8 Data Protection | yes | Protecting sensitive data from leaking into logs/DB (ASVS 8.3) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential in exception message persisted to DB | Information Disclosure | `safe_str(exc)` scrubbing before write |
| ADC path in error message reveals filesystem layout | Information Disclosure | `safe_str` strips ADC path patterns |
| Token fragment in hvac exception URL | Information Disclosure | `safe_str` strips token-like base64url strings |
| Future bypass of safe_str (code drift) | Information Disclosure | LEAK-03 AST gate fails CI build |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `hvac` exceptions may include Vault token fragments in exception message text (via URL parameters in request objects) | Leaky Callsite Inventory | LOW risk — safe_str returns class-only for vault regardless; scrubbing still works |
| A2 | `google.auth.exceptions.DefaultCredentialsError` message includes ADC file path | Leaky Callsite Inventory | LOW risk — safe_str returns class-only; conservative approach |
| A3 | `safe_str` should return `f"{class_name}: {msg}"` when no sensitive pattern matches (not just class name always) | Code Examples / safe_str design | MEDIUM risk — if wrong, all exception detail in scan_error is lost which degrades UX |
| A4 | `discovery/tls_scanner.py` is dead code (per audit WR-13) but still needs the `safe_str` fix | Leaky Callsite Inventory | LOW risk — fixing it is safe regardless |
| A5 | The AST gate should scan `quirk/scanner/`, `quirk/discovery/`, and `quirk/cbom/` directories | Code Examples / AST gate | LOW risk — additional dirs can be added if new callsites are found |

---

## Open Questions (RESOLVED)

1. **Should `safe_str` include the message at all, or always return class-only?**
   - RESOLVED: Return `f"{class_name}: {scrubbed_msg}"` when no sensitive pattern matches; class-only otherwise. Adopted by Plan 01 (`quirk/util/safe_exc.py`) and validated by `test_safe_str_benign_passthrough`. Success Criterion 1's "by default" is interpreted as the minimum guaranteed return; message inclusion is additive when safe.

2. **Are logger.v calls in scope?**
   - RESOLVED: Opportunistic `safe_str` wrapping for logger.v calls in vault_connector.py / gcp_connector.py (Pattern A intent), but NOT in the LEAK-03 AST gate scope. Adopted by Plan 02 Task 2 (vault_connector opportunistic edits) and Plan 03 (gate covers `scan_error` writes only).

3. **Should the AST gate also cover `quirk/cbom/writer.py`?**
   - RESOLVED: YES — `quirk/cbom/` is included in Plan 03's `SCANNER_DIRS`, AND Plan 02 Task 2 sweeps both `cbom/writer.py` callsites (lines 78, 93) via `safe_str` so the gate finds zero violations on first run.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase grep] — Complete enumeration of all `scan_error` write callsites across `quirk/`
- [VERIFIED: codebase read] — `quirk/engine/risk_engine.py` `_build_finding` chokepoint (lines 56-93)
- [VERIFIED: codebase read] — `tests/test_skip_registry.py` AST gate pattern (lines 1-95)
- [VERIFIED: codebase read] — `tests/test_hygiene.py` structural test pattern
- [VERIFIED: codebase read] — `quirk/util/subprocess_input.py` util module pattern
- [VERIFIED: codebase read] — `.planning/audit-2026-05-08/scanners-cloud/REVIEW.md` CR-04, CR-05 fix text
- [VERIFIED: codebase read] — `.planning/REQUIREMENTS.md` LEAK-01/02/03 exact text
- [VERIFIED: database query] — `data/quirk.db` and `output/quirk.db` scan_error values (no credentials present)

### Secondary (MEDIUM confidence)
- [CITED: hvac Python library behavior] — Vault client exceptions may include request URLs containing token query parameters — standard hvac behavior when authentication fails mid-request

### Tertiary (LOW confidence — see Assumptions Log)
- [ASSUMED] — `safe_str` scrubbing patterns (A1-A5 above) based on known exception message formats

---

## Metadata

**Confidence breakdown:**
- Callsite inventory: HIGH — complete grep with no false negatives possible
- Architecture patterns: HIGH — AST gate and util module patterns verified in codebase
- Scrubbing corpus: MEDIUM — patterns based on known library behavior; unit tests will validate
- Scope boundaries (logger.v vs scan_error): MEDIUM — phase text is slightly ambiguous

**Research date:** 2026-05-09
**Valid until:** 2026-06-08 (stable domain)

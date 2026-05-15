# Phase 59: Credential Leakage Sweep - Pattern Map

**Mapped:** 2026-05-09
**Files analyzed:** 9 (2 new, 7 modified)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/util/safe_exc.py` | utility | transform | `quirk/util/subprocess_input.py` | exact |
| `quirk/scanner/vault_connector.py` | service | request-response | self (leaky lines 428, 450) | modify |
| `quirk/scanner/gcp_connector.py` | service | request-response | self (leaky line 381+389) | modify |
| `quirk/scanner/tls_scanner.py` | service | request-response | self (leaky line 454) | modify |
| `quirk/scanner/email_scanner.py` | service | request-response | self (leaky lines 470, 474) | modify |
| `quirk/scanner/broker_scanner.py` | service | request-response | self (leaky line 704) | modify |
| `quirk/scanner/ssh_scanner.py` | service | request-response | self (leaky line 85) | modify |
| `quirk/discovery/tls_scanner.py` | service | request-response | self (leaky line 95) | modify |
| `tests/test_safe_exc.py` | test | — | `tests/test_skip_registry.py` | exact |

---

## Pattern Assignments

### `quirk/util/safe_exc.py` (new utility, transform)

**Analog:** `quirk/util/subprocess_input.py` (exact match — same Phase 57 util pattern)

**Imports pattern** (`quirk/util/subprocess_input.py` lines 1-21):
```python
"""Subprocess input validators for QUIRK — Phase 57 / CR-02, CR-03.

Decision enforcement:
  D-XX: <decision note here>.

Public surface:
  safe_str(exc) -> str
"""
from __future__ import annotations

import re
from typing import Final
```

**Module docstring convention** (`quirk/util/subprocess_input.py` lines 1-13):
- Always start with a triple-quoted docstring.
- Name the phase and audit-code reference (e.g., `Phase 59 / LEAK-01`).
- List `Decision enforcement:` entries with D-XX codes.
- List `Public surface:` showing function signatures and return types.

**Constants pattern** (`quirk/util/subprocess_input.py` lines 49-53):
```python
# Reason-code constants (D-03 — fixed enum, NOT free-form strings)
RC_SHELL_METACHAR: Final[str] = "shell_metachar"
RC_PATH_TRAVERSAL: Final[str] = "path_traversal"
```
For `safe_exc.py`, use pre-compiled regex constants (not reason codes):
```python
_SENSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(s\.)[A-Za-z0-9_\-]{20,}"),
    re.compile(r"://[^:@\s]+:[^@\s]+@"),
    re.compile(r"[\\/]\.?config[\\/]gcloud[\\/]"),
    re.compile(r"gcloud[\\/]application_default_credentials"),
    re.compile(r"Authorization:\s*(Bearer|Basic)\s+\S+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
)
```

**Core function pattern** (`quirk/util/url_allowlist.py` lines 95-161 as structural model):
```python
def safe_str(exc: BaseException) -> str:
    """Return a credential-safe string representation of *exc*.

    Default return is ``f"{type(exc).__name__}"`` (class name only).  If the
    exception message does not match any sensitive pattern, the class name and
    a scrubbed message are returned.

    Design decision: err on the side of returning class-only — a slightly less
    useful log entry is always preferable to a credential leak.

    Args:
        exc: Any exception instance.

    Returns:
        ``f"{type(exc).__name__}: {msg}"`` when no sensitive pattern matches.
        ``f"{type(exc).__name__}"`` (class name only) when a sensitive pattern
        is detected or ``str(exc)`` raises.
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

**Module independence rule** (`quirk/util/subprocess_input.py` lines 27-32):
```python
# Intentionally re-defined here (not imported from url_allowlist) to keep
# this module independently testable and importable (D-02 / D-03).
```
`safe_exc.py` must have zero cross-imports from other `quirk.util` modules.

---

### `quirk/scanner/vault_connector.py` (modify — lines 428, 450)

**Analog:** self — existing leaky lines

**Current leaky pattern** (lines 421-430):
```python
except Exception as exc:  # noqa: BLE001
    if logger:
        logger.v(f"Vault hvac.Client construction error: {exc}")
    return [CryptoEndpoint(
        host=resolved_addr,
        port=8200,
        protocol="VAULT",
        scan_error=f"vault-client-init-failed: {exc}",   # line 428 — leaky
        scanned_at=now,
    )]
```

**Current leaky pattern** (lines 443-452):
```python
except Exception as exc:  # noqa: BLE001
    if logger:
        logger.v(f"Vault auth check network error: {exc}")
    return [CryptoEndpoint(
        host=resolved_addr,
        port=8200,
        protocol="VAULT",
        scan_error=f"vault-auth-failed: {exc}",          # line 450 — leaky
        scanned_at=now,
    )]
```

**Fix pattern — add import at top of file (after existing imports):**
```python
from quirk.util.safe_exc import safe_str
```

**Fix pattern — both callsites (mechanical substitution):**
```python
# line 428:
scan_error=f"vault-client-init-failed: {safe_str(exc)}",

# line 450:
scan_error=f"vault-auth-failed: {safe_str(exc)}",
```

**Opportunistic — logger.v calls (not required for LEAK-03 gate, but consistent):**
```python
logger.v(f"Vault hvac.Client construction error: {safe_str(exc)}")
logger.v(f"Vault auth check network error: {safe_str(exc)}")
```

---

### `quirk/scanner/gcp_connector.py` (modify — lines 381, 389)

**Analog:** self — existing leaky two-step variable pattern

**Current leaky pattern** (lines 379-391):
```python
except Exception as exc:
    scan_error_msg = f"gcp-credentials-unavailable: {exc}"   # line 381 — leaky
    if logger:
        logger.v(scan_error_msg)
    return [
        CryptoEndpoint(
            host=f"gcp://{project_id}",
            port=0,
            protocol="GCP",
            scan_error=scan_error_msg,                        # line 389 — indirect
        )
    ]
```

**Fix pattern — resolve two-step variable at the source (see RESEARCH.md Pitfall 1):**
```python
from quirk.util.safe_exc import safe_str
```
```python
except Exception as exc:
    scan_error_msg = f"gcp-credentials-unavailable: {safe_str(exc)}"  # fix at line 381
    if logger:
        logger.v(scan_error_msg)
    return [
        CryptoEndpoint(
            host=f"gcp://{project_id}",
            port=0,
            protocol="GCP",
            scan_error=scan_error_msg,   # line 389 now receives already-safe value
        )
    ]
```

**Critical:** The variable `scan_error_msg` is passed as a `Name` node to `CryptoEndpoint(scan_error=...)`. The AST gate will see a `Name`, not a `safe_str` call. The fix must be applied at the assignment on line 381 so the variable value is safe when it reaches line 389.

---

### `quirk/scanner/tls_scanner.py` (modify — line 454)

**Analog:** self — existing leaky line

**Current leaky pattern** (lines 451-456):
```python
except Exception as e:
    cat = _categorize_tls_error(e)
    ep.tls_blocker_reason = cat
    ep.scan_error = f"{cat}: {e}"    # line 454 — leaky
    if logger:
        logger.v(f"TLS {host}:{port} {cat} ({e})")
```

**Fix pattern:**
```python
from quirk.util.safe_exc import safe_str
```
```python
ep.scan_error = f"{cat}: {safe_str(e)}"   # line 454
```

---

### `quirk/scanner/email_scanner.py` (modify — lines 470, 474)

**Analog:** self — existing leaky lines

**Current leaky pattern** (lines 462-476):
```python
    if getattr(e, "errno", None) in (111, 113):
        ep.tls_blocker_reason = "CONNECTION_REFUSED"
        ...
    else:
        ep.scan_error = str(e)    # line 470 — leaky
        if logger:
            logger.v(f"Email fallback OSError {host}:{port}: {e}")
except Exception as e:
    ep.scan_error = str(e)        # line 474 — leaky
    if logger:
        logger.v(f"Email fallback error {host}:{port}: {e}")
```

**Fix pattern:**
```python
from quirk.util.safe_exc import safe_str
```
```python
ep.scan_error = safe_str(e)   # line 470
...
ep.scan_error = safe_str(e)   # line 474
```

---

### `quirk/scanner/broker_scanner.py` (modify — line 704)

**Analog:** self — existing leaky line

**Current leaky pattern** (lines 700-705):
```python
    except ConnectionRefusedError:
        return None
    except Exception as e:
        ep = CryptoEndpoint(host=host, port=port, protocol="REDIS-TLS")
        ep.scan_error = str(e)    # line 704 — leaky
        return ep
```

**Fix pattern:**
```python
from quirk.util.safe_exc import safe_str
```
```python
ep.scan_error = safe_str(e)   # line 704
```

---

### `quirk/scanner/ssh_scanner.py` (modify — line 85)

**Analog:** self — existing leaky line

**Current leaky pattern** (lines 84-87):
```python
    except Exception as e:
        ep.scan_error = f"SSH_ERROR: {e}"    # line 85 — leaky
        if logger:
            logger.v(f"SSH {host}:{port} SSH_ERROR ({e})")
```

**Fix pattern:**
```python
from quirk.util.safe_exc import safe_str
```
```python
ep.scan_error = f"SSH_ERROR: {safe_str(e)}"   # line 85
```

---

### `quirk/discovery/tls_scanner.py` (modify — line 95)

**Analog:** self — existing leaky line

**Current imports** (lines 1-11):
```python
import socket
import ssl

from quirk.models import CryptoEndpoint
```

**Current leaky pattern** (line 95):
```python
ep.scan_error = str(e)    # line 95 — leaky
```

**Fix pattern:**
```python
from quirk.util.safe_exc import safe_str
```
```python
ep.scan_error = safe_str(e)   # line 95
```

Note: Per RESEARCH.md Pitfall 4, this file is dead code per audit WR-13. Fix it anyway — the AST gate scans `quirk/discovery/` and would fail CI without the fix.

---

### `tests/test_safe_exc.py` (new test)

**Analog:** `tests/test_skip_registry.py` (exact structural match — AST gate test with helper predicates)

**Module header pattern** (`tests/test_skip_registry.py` lines 1-30):
```python
"""Phase 41 D-03: CI gate meta-test that fails when an unregistered
``pytest.skip`` / ``pytest.importorskip`` / ``@pytest.mark.skipif``
is encountered in tests/.

Mechanism: walk every ``tests/*.py`` file with ``ast.parse`` + ``ast.walk``
looking for:
  ...

NOTE: At creation time (Wave 0 of Phase 41) some D-04 deletions have NOT yet
happened, so this test will FAIL initially.
"""
from __future__ import annotations

import ast
import pathlib

import pytest
```

**PROJECT_ROOT convention** (`tests/test_hygiene.py` line 21 and `tests/test_skip_registry.py` line 31):
```python
# test_hygiene.py style (PROJECT_ROOT for multi-dir walks):
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# test_skip_registry.py style (TESTS_DIR for tests/ walks):
TESTS_DIR = pathlib.Path(__file__).resolve().parent
```
For `test_safe_exc.py`, use `PROJECT_ROOT` pattern from `test_hygiene.py` since the AST gate walks `quirk/scanner/`, `quirk/discovery/`, `quirk/cbom/`.

**AST walk loop pattern** (`tests/test_skip_registry.py` lines 80-96):
```python
for py_file in sorted(TESTS_DIR.glob("*.py")):
    if py_file.name in EXEMPT_FILES:
        continue
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (SyntaxError, OSError):
        continue

    for node in ast.walk(tree):
        if _is_pytest_skip_call(node):
            if not _allowed(py_file.name, node.lineno):
                violations.append((py_file.name, node.lineno, f"pytest.{attr}"))
```

**Assert-at-end pattern** (`tests/test_skip_registry.py` lines 108-116):
```python
if violations:
    formatted = "\n".join(
        f"  {fname}:{lineno} [{kind}]" for fname, lineno, kind in violations
    )
    pytest.fail(
        "Unregistered skip markers found ...\n"
        f"{formatted}"
    )
```

**AST gate structure for LEAK-03** (adapted from `test_skip_registry.py` + RESEARCH.md Pattern 3):
```python
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
                            if (not _is_literal_or_none(kw.value)
                                    and not _is_safe_str_call(kw.value)):
                                violations.append((str(py_file), kw.value.lineno))
                # Pattern 2: ep.scan_error = <expr>
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (isinstance(target, ast.Attribute)
                                and target.attr == "scan_error"):
                            if (not _is_literal_or_none(node.value)
                                    and not _is_safe_str_call(node.value)):
                                violations.append((str(py_file), node.lineno))
    assert violations == [], f"scan_error writes bypassing safe_str: {violations}"
```

**Unit test corpus pattern** (structurally mirrors how `test_hygiene.py` tests assert specific source conditions):
```python
def test_safe_str_default():
    """LEAK-01: basic class name returned."""
    result = safe_str(ValueError("some message"))
    assert result.startswith("ValueError")

def test_safe_str_scrubs_vault_token():
    """LEAK-01: hvac-style token in message -> class name only."""
    exc = Exception("request to https://vault:8200?token=s.AbCdEfGhIjKlMnOpQrSt1234")
    assert safe_str(exc) == "Exception"

def test_safe_str_scrubs_connection_password():
    """LEAK-01: connection string password -> class name only."""
    exc = Exception("cannot connect: postgresql://user:secret123@db:5432/mydb")
    assert safe_str(exc) == "Exception"

def test_safe_str_scrubs_gcp_adc():
    """LEAK-01: ADC path -> class name only."""
    exc = Exception("File not found: /home/user/.config/gcloud/application_default_credentials.json")
    assert safe_str(exc) == "Exception"

def test_safe_str_benign_passthrough():
    """LEAK-01: benign ConnectionRefusedError -> class+message returned."""
    exc = ConnectionRefusedError("[Errno 111] Connection refused")
    result = safe_str(exc)
    assert result.startswith("ConnectionRefusedError:")
    assert "Connection refused" in result
```

---

## Shared Patterns

### Import Addition Pattern
**Source:** `quirk/scanner/vault_connector.py` existing import block (lines 1-15 for context)
**Apply to:** All 7 modified scanner/connector files

Add this import line after the existing `from quirk.*` imports:
```python
from quirk.util.safe_exc import safe_str
```

Place it after the last `from quirk.*` import, alphabetically within the `quirk.*` import group. See vault_connector.py — imports from `quirk.models` at line 17 are the anchor.

### Mechanical Substitution — Three Exact Forms
**Apply to:** All 8 leaky callsites across 7 files

```python
# Form A — f-string with prefix:
# Before: scan_error=f"prefix: {exc}",
# After:  scan_error=f"prefix: {safe_str(exc)}",

# Form B — plain str() call (attribute assignment):
# Before: ep.scan_error = str(e)
# After:  ep.scan_error = safe_str(e)

# Form C — f-string attribute assignment:
# Before: ep.scan_error = f"PREFIX: {e}"
# After:  ep.scan_error = f"PREFIX: {safe_str(e)}"
```

### AST Test File Header
**Source:** `tests/test_skip_registry.py` lines 1-30
**Apply to:** `tests/test_safe_exc.py`

```python
"""Phase 59 LEAK-03: CI gate that fails when a scan_error write bypasses safe_str.

Mechanism: walk every .py in quirk/scanner/ + quirk/discovery/ + quirk/cbom/
with ast.parse + ast.walk looking for:
  - Keyword(arg='scan_error', value=...) in Call nodes
  - Attribute assignment targets where target.attr == 'scan_error'

For each occurrence, check whether the RHS is a safe_str() call, a string
literal, or None. Any other form is a violation.

Also contains LEAK-01 unit tests for safe_str scrubbing corpus.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from quirk.util.safe_exc import safe_str

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
```

---

## No Analog Found

None — all files have strong analogs in the codebase.

---

## Gate Behavior Notes (for planner)

### db_connector.py — SAFE, do not modify
Lines 165/268 of `quirk/scanner/db_connector.py` use `f"connection-error: {type(exc).__name__}"` — class-name-only pattern, already safe. The AST gate will see a `JoinedStr` (f-string) with a `Call` to `type()`, not a `safe_str` call. To prevent false positives, the gate predicate `_is_literal_or_none` only permits `ast.Constant` nodes — an f-string with `type(exc).__name__` is an `ast.JoinedStr`, not a `Constant`.

**Resolution options (planner must choose one):**
1. Also route `db_connector.py` through `safe_str` for uniformity — eliminates the gate false-positive and unifies the pattern.
2. Add a `_is_type_name_call` predicate to the gate that recognizes `type(exc).__name__` as safe.

Option 1 is recommended (minimal gate complexity, uniform pattern).

### container_scanner.py / source_scanner.py — SAFE, do not modify
`ep.scan_error = _validation.reason` — the RHS is an `ast.Attribute` access, not an exception interpolation. The gate must not flag these. Since `_validation.reason` is neither a `Constant` nor a `safe_str` call, the gate as written WILL flag these as violations.

**Resolution (planner must implement):** Add `_is_attr_access` check — if the RHS is `ast.Attribute` (attribute read, not a call), treat it as safe. Or exclude `container_scanner.py` and `source_scanner.py` from the gate's scan directories. Recommend the `ast.Attribute` exclusion since these are provably safe (the value comes from a `ValidationResult.reason` field, not from an exception).

---

## Metadata

**Analog search scope:** `quirk/util/`, `quirk/scanner/`, `quirk/discovery/`, `tests/`
**Files scanned:** 9 source files + 2 test analogs
**Pattern extraction date:** 2026-05-09

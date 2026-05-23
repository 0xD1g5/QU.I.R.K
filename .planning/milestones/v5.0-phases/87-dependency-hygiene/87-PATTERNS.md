# Phase 87: Dependency Hygiene - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 8 (1 new util, 1 new test, 2 modified source, 1 modified workflow, 3 modified tests)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/util/xml_safe.py` (NEW) | utility | transform | `quirk/scanner/saml_scanner.py` lines 4-13 (lxml primary path) | exact — same lxml XMLParser per-call pattern |
| `quirk/discovery/nmap_parser.py` (MODIFY lines 5-6) | utility | file-I/O | `quirk/scanner/saml_scanner.py` lines 4-13 | exact — same lxml etree parse call |
| `quirk/scanner/saml_scanner.py` (MODIFY lines 14-24) | scanner | request-response | self — delete fallback block | N/A (deletion only) |
| `pyproject.toml` (MODIFY line 30) | config | — | `pyproject.toml` lines 27-33 | exact — same dep list format |
| `.github/workflows/dashboard-quality.yml` (MODIFY line 22) | config | — | self — single value change | N/A (single-line edit) |
| `tests/test_xml_safe.py` (NEW) | test | transform | `tests/test_audit_ledger_zero_open.py` (CI invariant structure) | role-match — forward-locking CI invariant pattern |
| `tests/test_nmap_hardening.py` (MODIFY 2 tests) | test | file-I/O | self — rewrite existing assertions | N/A (targeted rewrites) |
| `tests/test_packaging.py` (MODIFY 1 test) | test | — | self — invert existing assertion | N/A (targeted rewrite) |
| `tests/test_identity_infra.py` (MODIFY line 239-243) | test | — | self — delete one `assertIn` block | N/A (deletion only) |

---

## Pattern Assignments

### `quirk/util/xml_safe.py` (NEW — utility, transform)

**Analog:** `quirk/scanner/saml_scanner.py` lines 4-13

**Existing lxml primary-path pattern to mirror** (saml_scanner.py lines 4-13):
```python
try:
    import lxml.etree as ET
    def _safe_ET_fromstring(xml_bytes):  # noqa: E306
        # Phase 52 DEBT-04: raw lxml.etree parser with security flags.
        # resolve_entities=False blocks XXE; no_network=True blocks SSRF.
        return ET.fromstring(
            xml_bytes,
            parser=ET.XMLParser(resolve_entities=False, no_network=True),
        )
    LXML_AVAILABLE = True
```

Key observation: `saml_scanner.py` already creates a **fresh `ET.XMLParser` per call** (inside `_safe_ET_fromstring`) — this is the correct thread-safe pattern. The `xml_safe.py` factory formalizes and extends it to the full 5-flag set required by D-04.

**Module docstring structure** — copy from `quirk/util/optional_extra.py` lines 1-36:
```python
"""Phase 45 / Plan 02: centralized optional-extra registry + probe.
...
Public surface:

- ``OptionalExtra`` — frozen dataclass describing one extra.
- ``REGISTRY`` — module-level tuple of ``OptionalExtra`` (5 entries).
...
"""
from __future__ import annotations
```
The docstring must list `make_safe_parser()` and `parse_safely()` in the same "Public surface:" format.

**Structural analog** — `quirk/util/targets.py` lines 1-30 for the `from __future__ import annotations` + module-level docstring pattern for small focused util modules.

**Core pattern for `xml_safe.py`** (mandated by D-04, D-05):
```python
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

    Returns an lxml _ElementTree.  Call sites needing fromstring() must call
    make_safe_parser() directly and pass to etree.fromstring().
    """
    return etree.parse(source, parser=make_safe_parser())
```

**Anti-pattern to avoid:** Do NOT write `_SAFE_PARSER = etree.XMLParser(...)` at module scope — lxml parsers are not thread-safe (D-04 override of any RESEARCH.md example showing a shared constant).

---

### `quirk/discovery/nmap_parser.py` (MODIFY lines 5-6)

**Analog:** `quirk/scanner/saml_scanner.py` lines 4-13

**Current state** (nmap_parser.py lines 1-6) — the exact text to replace:
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
# defusedxml per audit WR-06 — defuses XXE/billion-laughs on nmap XML output
import defusedxml.ElementTree as ET
```

**Current parse call** (nmap_parser.py line 22) — this line is NOT changed; it continues to work because lxml.etree returns a compatible ElementTree:
```python
    tree = ET.parse(xml_path)
```

**After migration** — lines 5-6 become:
```python
from lxml import etree as ET
from quirk.util.xml_safe import make_safe_parser
# WR-06 mitigation: XML parsed via quirk/util/xml_safe.py hardened lxml parser
# (resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
# huge_tree=False).  Replaces defusedxml per Phase 87 DEP-02.
# DO NOT replace make_safe_parser() with a shared parser constant — see D-04.
```

And the `ET.parse(xml_path)` call (line 22) becomes:
```python
    tree = ET.parse(xml_path, parser=make_safe_parser())
```

**Navigation API compatibility:** All existing calls — `root.findall("host")`, `host_el.find("status")`, `status_el.get("state")`, `addr_el.get("addr")` — work identically on lxml elements (D-06). No other lines change.

---

### `quirk/scanner/saml_scanner.py` (MODIFY lines 14-24 — delete fallback block)

**Current state** (saml_scanner.py lines 14-24) — the exact block to delete:
```python
except ImportError:
    ET = None  # type: ignore[assignment]
    try:
        import defusedxml.ElementTree as _defused_stdlib_ET
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            return _defused_stdlib_ET.fromstring(xml_bytes)
        LXML_AVAILABLE = True
    except ImportError:
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            raise RuntimeError("defusedxml is not installed — SAML parsing unavailable")
        LXML_AVAILABLE = False
```

**After migration** — lines 4-24 reduce to:
```python
import lxml.etree as ET
from quirk.util.xml_safe import make_safe_parser

def _safe_ET_fromstring(xml_bytes):
    # Phase 52 DEBT-04 / Phase 87 DEP-02: hardened lxml parser via xml_safe chokepoint.
    return ET.fromstring(xml_bytes, parser=make_safe_parser())

LXML_AVAILABLE = True
```

The `try/except ImportError` block is removed entirely. `lxml>=6.0` is a mandatory core dep; a missing lxml means a broken install that should fail loudly, not silently downgrade to an unsafe parser.

---

### `pyproject.toml` (MODIFY line 30)

**Current state** (pyproject.toml lines 27-33):
```toml
    "lxml>=6.0",
    "beautifulsoup4>=4.13.0",
    "defusedxml>=0.7.1",
    "signxml>=4.4.0",
    "nh3>=0.2.17",
```

**After migration** — delete line 30 (`"defusedxml>=0.7.1",`). Nothing replaces it. Result:
```toml
    "lxml>=6.0",
    "beautifulsoup4>=4.13.0",
    "signxml>=4.4.0",
    "nh3>=0.2.17",
```

The `[identity]` extras group (lines 44-47) does NOT list defusedxml separately — confirmed by inspection. Only the core deps section (line 30) requires this deletion.

---

### `.github/workflows/dashboard-quality.yml` (MODIFY line 22)

**Current state** (dashboard-quality.yml lines 19-24):
```yaml
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: src/dashboard/package-lock.json
```

**After migration** — line 22 only:
```yaml
          node-version: '24'
```

`actions/setup-node@v4` stays unchanged — it already supports Node 24 (D-01). This is the only Node pin in any workflow file.

---

### `tests/test_xml_safe.py` (NEW — test, forward-locking CI invariant)

**Analog:** `tests/test_audit_ledger_zero_open.py` (lines 1-75) — the project's canonical forward-locking CI invariant pattern.

**Structural pattern from analog** (test_audit_ledger_zero_open.py lines 1-16, 44-57):
```python
"""Phase 77 LEDGER-01 (D-31): AUDIT-TASKS.md milestone-completion invariants.

This module installs two CI gates that lock the v4.9 audit-ledger hygiene
invariants in perpetuity:
...
Together these gates guarantee the AUDIT-TASKS.md ledger stays self-documenting
across the v5.0+ lifetime of the project.
"""

from __future__ import annotations

import re
from pathlib import Path

LEDGER = (
    Path(__file__).resolve().parent.parent / ".planning" / "audit-2026-05-08" / "AUDIT-TASKS.md"
)

def test_audit_ledger_has_zero_bare_open_rows() -> None:
    """v4.9 milestone-completion gate (D-31): zero `[ ] open` rows.
    ...
    """
    text = LEDGER.read_text(encoding="utf-8")
    matches = _OPEN_RE.findall(text)
    assert not matches, (
        f"Audit ledger has {len(matches)} bare-open row(s); ..."
    )
```

**Key pattern elements to copy:**
- Module-level docstring explaining the CI gate purpose and its permanent nature
- `from __future__ import annotations` at top
- `Path(__file__).resolve().parent.parent` for repo-relative path resolution
- Named constants for test payloads (e.g., `BILLION_LAUGHS = b"""..."""`)
- Function docstrings that name the decision reference (e.g., "D-07 forward-locking invariant")
- `pytest.raises(ExceptionType)` for the payload tests
- Grep-gate test using `subprocess.run` or `Path.rglob` to assert no `defusedxml` imports remain in `quirk/`

**Tests to include in `test_xml_safe.py`:**
1. `test_make_safe_parser_returns_fresh_instance` — two calls return different objects (thread-safety invariant)
2. `test_make_safe_parser_flags` — inspect returned parser attributes for the 5-flag set
3. `test_parse_safely_accepts_valid_xml` — round-trips a minimal valid nmap XML fixture
4. `test_parse_safely_blocks_billion_laughs` — billion-laughs payload raises `lxml.etree.XMLSyntaxError`
5. `test_parse_safely_blocks_xxe_external_entity` — XXE file:// payload raises `lxml.etree.XMLSyntaxError`
6. `test_no_defusedxml_import_in_quirk` — grep `quirk/` for `defusedxml`; assert zero hits (permanent grep gate)

---

### `tests/test_nmap_hardening.py` (MODIFY 2 tests)

**Current state of the two failing tests** (test_nmap_hardening.py lines 121-136):

```python
def test_nmap_parser_uses_defusedxml():
    assert nmap_parser.ET.__name__.startswith("defusedxml")


def test_nmap_parser_blocks_xxe(tmp_path):
    """defusedxml must raise on external-entity declarations."""
    from defusedxml.common import EntitiesForbidden

    xxe = """<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>"""
    p = tmp_path / "xxe.xml"
    p.write_text(xxe)
    with pytest.raises(EntitiesForbidden):
        nmap_parser.ET.parse(str(p))
```

**After migration — replacement tests:**

`test_nmap_parser_uses_defusedxml` → `test_nmap_parser_uses_xml_safe`:
```python
def test_nmap_parser_uses_xml_safe():
    """nmap_parser must use the xml_safe chokepoint (Phase 87 DEP-02 / WR-06)."""
    from quirk.util import xml_safe
    assert callable(xml_safe.make_safe_parser)
```

`test_nmap_parser_blocks_xxe` → `test_nmap_parser_blocks_xxe_lxml`:
```python
def test_nmap_parser_blocks_xxe_lxml(tmp_path):
    """Hardened lxml parser must raise on external-entity declarations (D-07)."""
    from lxml import etree

    xxe = """<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>"""
    p = tmp_path / "xxe.xml"
    p.write_text(xxe)
    with pytest.raises(etree.XMLSyntaxError):
        nmap_parser.parse_nmap_xml(str(p))
```

Note: `test_nmap_parser_blocks_xxe_lxml` exercises the full `parse_nmap_xml` call path (not a bare `ET.parse`) so it validates the migration end-to-end.

---

### `tests/test_packaging.py` (MODIFY 1 test — lines 71-73)

**Current state** (test_packaging.py lines 71-73):
```python
def test_defusedxml_in_core_deps():
    """defusedxml must be in core deps (required by SAML scanner for XXE safety)."""
    assert "defusedxml" in _core_deps_section(), "defusedxml not found in core dependencies"
```

**After migration — replacement test:**
```python
def test_defusedxml_not_in_core_deps():
    """defusedxml must NOT be in core deps after Phase 87 DEP-02 migration."""
    assert "defusedxml" not in _core_deps_section(), (
        "defusedxml found in core dependencies — remove per Phase 87 DEP-02"
    )
```

The existing `test_lxml_in_core_deps` (lines 66-68) stays unchanged — lxml remains a core dep.

---

### `tests/test_identity_infra.py` (MODIFY line 239-243 — delete one assertIn block)

**Current state** (test_identity_infra.py lines 239-243):
```python
        self.assertIn(
            '"defusedxml>=0.7.1"',
            source,
            "pyproject.toml [identity] group missing defusedxml>=0.7.1 -- add per D-07",
        )
```

**After migration** — delete these 5 lines entirely. The surrounding `assertIn` blocks for `lxml>=6.0` (lines 234-238) and `signxml>=4.4.0` (lines 244-248) remain unchanged.

Context note: This test asserts defusedxml is in the `[identity]` extras group. The RESEARCH.md confirms defusedxml is NOT actually in `[identity]` (pyproject.toml lines 44-47 show only `impacket` and `ldap3`). The assertion searches the full file string, so it was previously passing because `defusedxml>=0.7.1` appeared in core deps (line 30). After removal from core deps, this assertion becomes the only CI break remaining after the pyproject.toml edit.

---

## Shared Patterns

### Forward-Locking CI Invariant Structure
**Source:** `tests/test_audit_ledger_zero_open.py` lines 1-75
**Apply to:** `tests/test_xml_safe.py` (new)

The canonical pattern: module-level docstring names the decision reference and explains permanence; test functions carry docstrings citing the specific decision number (D-07 etc.); `assert not matches, f"..."` format with a descriptive failure message. All new invariant tests must follow this structure.

### `_core_deps_section()` helper
**Source:** `tests/test_packaging.py` lines 51-58
**Apply to:** Modified `test_defusedxml_not_in_core_deps` in `tests/test_packaging.py`

```python
def _core_deps_section():
    """Return just the [project] dependencies list text (before optional-dependencies)."""
    root = os.path.join(os.path.dirname(__file__), "..")
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    start = pyproject.index("dependencies = [")
    end = pyproject.index("[project.optional-dependencies]")
    return pyproject[start:end]
```
The rewritten `test_defusedxml_not_in_core_deps` reuses this helper unchanged.

### lxml per-call XMLParser pattern (thread-safe)
**Source:** `quirk/scanner/saml_scanner.py` lines 6-12
**Apply to:** `quirk/util/xml_safe.py` (factory), `quirk/scanner/saml_scanner.py` (updated `_safe_ET_fromstring`)

The key invariant: parser created **inside** the function body, never at module scope. Every function that needs a parser calls `make_safe_parser()`.

---

## No Analog Found

None. All files have concrete analogs in the codebase.

---

## Metadata

**Analog search scope:** `quirk/util/`, `quirk/scanner/`, `quirk/discovery/`, `tests/`, `.github/workflows/`, `pyproject.toml`
**Files scanned:** 9 source files read in full
**Key line-number anchors verified:**
- `nmap_parser.py:5-6` — `import defusedxml.ElementTree as ET` confirmed
- `saml_scanner.py:14-24` — defusedxml fallback block confirmed (lines 14-24 per 0-indexed = lines shown as 14-24 in file)
- `pyproject.toml:30` — `"defusedxml>=0.7.1"` in core deps confirmed
- `dashboard-quality.yml:22` — `node-version: '20'` confirmed
- `test_nmap_hardening.py:121-136` — both defusedxml-dependent tests confirmed with exact assertion text
- `test_packaging.py:71-73` — `test_defusedxml_in_core_deps` confirmed
- `test_identity_infra.py:239-243` — `assertIn('"defusedxml>=0.7.1"', ...)` confirmed; searches full file string (not identity group only)
**Pattern extraction date:** 2026-05-22

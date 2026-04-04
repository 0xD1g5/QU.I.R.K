# Phase 10: v3.9 Gap Closure — Research

**Researched:** 2026-04-03
**Domain:** Python packaging, FastAPI/dashboard API bug-fix, YAML template authoring
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CBOM-03 | NIST PQC quantum-safety classification enrichment per algorithm | MISMATCH-01 fix: two call sites in scan.py pass string alg instead of int nist_level to quantum_safety_label(); correct pattern already present at lines 180-181 of the same file |
| UI-01 | FastAPI API layer — scan job management, results API, serving scanner output | PACKAGE-01 fix: pyproject.toml package-data must include dashboard/static/**/* so wheel ships the React bundle |
| UI-03 | Findings table, certificate inventory, CBOM viewer in dashboard | Same MISMATCH-01 fix as CBOM-03 — cert inventory shows raw enum strings; non-RSA vulnerability findings silently dropped |
| BRAND-04 | Packaging + installer — pip install quirk or single-file distribution; zero-to-scan < 10 min | Both PACKAGE-01 and MISSING-01 fixes; dashboard bundle in wheel + intelligence block in config_template.yaml |

</phase_requirements>

---

## Summary

Phase 10 closes three precisely-scoped defects identified by the v3.9 milestone audit. Every
defect has a known root cause, a known fix location, and a one-to-two-line change. No new
architecture is introduced. All work is corrective.

**MISMATCH-01** is a type-confusion bug in `quirk/dashboard/api/routes/scan.py`. The function
`quantum_safety_label(nist_level: int | None)` is called with a raw algorithm string at two
call sites (lines 143 and 379), instead of first calling `classify_algorithm(alg)` to obtain
the NIST level integer. The correct two-step pattern is already used at lines 180-181 of the
same file, so the fix is a copy-and-adapt of existing working code.

**PACKAGE-01** is a setuptools packaging omission. `quirk/dashboard/static/` holds the built
React bundle (12 files: HTML, JS chunks, CSS, icons), but `pyproject.toml`
`[tool.setuptools.package-data]` only declares `reports/templates/*.j2` and
`config_template.yaml`. A non-editable wheel therefore ships no UI assets. Adding
`"dashboard/static/**/*"` to the `quirk` package-data entry resolves this.

**MISSING-01** is a documentation gap in the generated config template. Phase 9 delivered the
`profile: strict/balanced/lenient` knob and `calibration_overrides` in
`intelligence/scoring.py`, but `quirk/config_template.yaml` has no `intelligence:` section.
Users who run `quirk init` cannot discover the knob. Runtime behaviour is safe (defaults apply
via `config_from_dict`). The fix is a commented-out `intelligence:` block appended to the
template.

**Primary recommendation:** Fix three isolated files in order — `scan.py` (MISMATCH-01),
`pyproject.toml` (PACKAGE-01), `config_template.yaml` (MISSING-01). Write regression tests
covering each fix. No dependency changes, no architecture changes.

---

## Standard Stack

### Core (already in project — no new installs)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| pytest | 9.0.2 (confirmed) | Test framework | Existing suite; new tests added here |
| setuptools | >=68 (pyproject.toml) | Wheel build / package-data | Glob patterns in package-data are natively supported |
| quirk.cbom.classifier | project module | `classify_algorithm`, `quantum_safety_label` | Already imported at lines 168, 178 in scan.py |

### No new dependencies required

All three fixes are code/config edits only. The correct `classify_algorithm` import is already
present in `_derive_cbom()` in the same file being patched.

---

## Architecture Patterns

### Pattern 1: Correct two-step quantum safety label derivation

The working pattern is already in `quirk/dashboard/api/routes/scan.py` lines 178-184:

```python
# Source: quirk/dashboard/api/routes/scan.py lines 178-184 (correct reference pattern)
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

def _qs_for_alg(alg: str) -> str:
    try:
        _, nist_level, _ = classify_algorithm(alg)
        raw = quantum_safety_label(nist_level)
    except Exception:
        raw = "unknown"
    return _QS_DISPLAY.get(raw, "Unknown")
```

The broken call sites must be rewritten to follow this pattern.

**MISMATCH-01 — Line 143 fix (quantum-vulnerable findings derivation):**

```python
# BEFORE (broken): quantum_safety_label receives a string, never matches "Vulnerable"/"At Risk"
qs = quantum_safety_label(ep.cert_pubkey_alg)
if qs in ("Vulnerable", "At Risk"):

# AFTER (fixed): two-step pattern; display label compared correctly
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label
_QS_DISPLAY = {
    "quantum-vulnerable": "Vulnerable",
    "quantum-safe": "Safe",
    "hybrid": "At Risk",
    "unknown": "Unknown",
}
_, nist_level, _ = classify_algorithm(ep.cert_pubkey_alg)
qs = _QS_DISPLAY.get(quantum_safety_label(nist_level), "Unknown")
if qs in ("Vulnerable", "At Risk"):
```

Note: `_QS_DISPLAY` is already defined at lines 171-176 of the same function `_derive_cbom`.
The `_derive_findings` function needs its own reference or the dict should be module-level.

**MISMATCH-01 — Line 379 fix (cert inventory quantum_safety field):**

```python
# BEFORE (broken): returns raw enum string "quantum-vulnerable" not display label
def _cert_quantum_safety(algorithm: Optional[str]) -> Optional[str]:
    if not algorithm:
        return None
    try:
        from quirk.cbom.classifier import quantum_safety_label
        return quantum_safety_label(algorithm)
    except Exception:
        return "Unknown"

# AFTER (fixed): two-step pattern returns "Vulnerable" / "Safe" / "Unknown"
def _cert_quantum_safety(algorithm: Optional[str]) -> Optional[str]:
    if not algorithm:
        return None
    _QS_DISPLAY = {
        "quantum-vulnerable": "Vulnerable",
        "quantum-safe": "Safe",
        "hybrid": "At Risk",
        "unknown": "Unknown",
    }
    try:
        from quirk.cbom.classifier import classify_algorithm, quantum_safety_label
        _, nist_level, _ = classify_algorithm(algorithm)
        raw = quantum_safety_label(nist_level)
        return _QS_DISPLAY.get(raw, "Unknown")
    except Exception:
        return "Unknown"
```

### Pattern 2: setuptools glob patterns for package-data

```toml
# Source: pyproject.toml [tool.setuptools.package-data] (PACKAGE-01 fix)
[tool.setuptools.package-data]
quirk = [
    "reports/templates/*.j2",
    "config_template.yaml",
    "dashboard/static/**/*",
]
```

The `**/*` glob is supported by setuptools>=68 (already required in `[build-system]`). It
recursively includes all files under `quirk/dashboard/static/` including the `assets/`
subdirectory. The path is relative to the package root (`quirk/`), not the repo root.

Confirmed files that must be included (present on disk):
- `quirk/dashboard/static/index.html`
- `quirk/dashboard/static/favicon.ico`, `favicon.png`, `favicon.svg`, `icons.svg`
- `quirk/dashboard/static/assets/*.js` (5 files), `assets/*.css` (1 file)

### Pattern 3: Commented intelligence block in config_template.yaml

```yaml
# Source: quirk/config_template.yaml (MISSING-01 fix — append after connectors block)

# -- Intelligence / scoring profile -----------------------------------------
# Adjust how the quantum-readiness score weights agility and identity signals.
# intelligence:
#   profile: balanced        # strict | balanced | lenient
#                            #   strict  — 1.4x agility + identity weights (conservative posture)
#                            #   balanced — default (1.0x multipliers)
#                            #   lenient  — 0.7x agility + identity weights (relaxed posture)
#   # calibration_overrides: # Fine-tune individual weight keys (advanced)
#   #   agility_high_impact_ratio: 14.0
```

This follows the existing comment style in `config_template.yaml` (hash-prefixed, inline
descriptions). Matches the `PROFILE_MULTIPLIERS` dict in `quirk/intelligence/scoring.py` and
the documentation added to `docs/configuration.md` in Phase 9.

### Anti-Patterns to Avoid

- **Passing algorithm string directly to `quantum_safety_label()`:** The function signature
  is `quantum_safety_label(nist_level: int | None)`. Passing a string silently returns the
  string through the `if nist_level is None` → `if nist_level == 0` path incorrectly.
  Python duck-types integers and strings — non-zero string is truthy, so `nist_level == 0`
  is `False`, and the function returns `"quantum-safe"` for any non-empty string. This is
  the exact mechanism of MISMATCH-01.

- **Using `MANIFEST.in` for package-data:** This project uses `pyproject.toml` with
  setuptools. Adding a `MANIFEST.in` file would be redundant and confusing. All
  package-data belongs in `[tool.setuptools.package-data]`.

- **Recursive glob without `**`:** `"dashboard/static/*"` only includes the top-level
  files and misses `dashboard/static/assets/*.js`. Must use `"dashboard/static/**/*"`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Algorithm-to-NIST-level mapping | New lookup table in scan.py | `classify_algorithm()` from `quirk.cbom.classifier` | Table already exists, thoroughly tested (32 tests passing), handles vendor suffixes and fuzzy normalization |
| Display label mapping | Inline string comparison to raw enum | `_QS_DISPLAY` dict pattern already present in `_derive_cbom()` | Consistent with existing working code in the same file |
| Package-data file listing | Explicit per-file listing | `"dashboard/static/**/*"` glob | Static dir content will change with React rebuilds; explicit listing would go stale |

---

## Common Pitfalls

### Pitfall 1: Scope of `_QS_DISPLAY` dict

**What goes wrong:** `_QS_DISPLAY` is currently defined inside `_derive_cbom()`. Copying it
into `_derive_findings()` and `_cert_quantum_safety()` creates three copies that can drift.

**How to avoid:** Promote `_QS_DISPLAY` to module-level (top of `scan.py`, after imports) so
all three functions share one authoritative definition. This is a clean refactor within the
same file.

**Warning signs:** Any future change to label strings requires updating in multiple places.

### Pitfall 2: setuptools `**` glob requires setuptools >= 68

**What goes wrong:** Older setuptools versions do not expand `**` in package-data patterns.

**How to avoid:** Not a risk here — `pyproject.toml` already requires `setuptools>=68` in
`[build-system].requires`. The constraint is already satisfied.

### Pitfall 3: `_cert_quantum_safety` is called at line 345, not line 379

**What goes wrong:** The audit document says "line 379" for `_cert_quantum_safety`. After
reading the current file, the function definition starts at line 374. The call site
`_cert_quantum_safety(ep.cert_pubkey_alg)` is at line 345. Line numbers drift during
editing.

**How to avoid:** Identify fix sites by function name, not line number.
- Fix 1: inside `_derive_findings()` — the `quantum_safety_label(ep.cert_pubkey_alg)` call
- Fix 2: inside `_cert_quantum_safety()` — replace the entire function body

### Pitfall 4: config_template.yaml YAML indentation

**What goes wrong:** YAML requires consistent indentation. A misaligned `intelligence:` block
will cause `quirk init` → `config_from_dict` to fail on user configs.

**How to avoid:** Use 2-space indentation matching the existing file. Verify with
`python3 -c "import yaml; yaml.safe_load(open('quirk/config_template.yaml'))"` after editing.

### Pitfall 5: Non-editable install test requires a built wheel

**What goes wrong:** PACKAGE-01 is only observable in a non-editable install. Running tests
against the development tree (`pip install -e .`) will always find `quirk/dashboard/static/`
because the package directory is live-linked.

**How to avoid:** The regression test for PACKAGE-01 should check `pyproject.toml` content
directly (verify the glob pattern is present) rather than building and installing a wheel.
Wheel build verification is a human/CI step, not an automated unit test.

---

## Code Examples

### Confirmed working classifier call pattern (HIGH confidence)

```python
# Source: quirk/dashboard/api/routes/scan.py lines 178-184 — already GREEN
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

_, nist_level, _ = classify_algorithm(alg)
raw = quantum_safety_label(nist_level)
# raw is one of: "quantum-vulnerable", "quantum-safe", "hybrid", "unknown"
```

### Confirmed `classify_algorithm` return for common cert algorithms

```python
# Source: quirk/cbom/classifier.py _ALGORITHM_TABLE
classify_algorithm("RSA")     # -> (CryptoPrimitive.PKE, 0, 112)       nist_level=0 -> "quantum-vulnerable"
classify_algorithm("ECDSA")   # -> (CryptoPrimitive.SIGNATURE, 0, 128) nist_level=0 -> "quantum-vulnerable"
classify_algorithm("DSA")     # -> (CryptoPrimitive.SIGNATURE, 0, 112) nist_level=0 -> "quantum-vulnerable"
classify_algorithm("ML-KEM-768")  # -> (CryptoPrimitive.KEM, 3, 192)   nist_level=3 -> "quantum-safe"
```

All classical algorithms (RSA, ECDSA, DSA, DH variants) map to `nist_level=0` →
`"quantum-vulnerable"`. This confirms the MISMATCH-01 diagnosis: RSA certificates were
accidentally "working" in the findings tab only because of the separate hard-coded
`ep.cert_pubkey_size < 2048` branch at lines 120-137.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (pytest auto-discovers) |
| Quick run command | `python -m pytest tests/test_gap_closure.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CBOM-03 / UI-03 | `_derive_findings()` emits quantum-vulnerable finding for DSA cert | unit | `pytest tests/test_gap_closure.py::test_findings_quantum_label_dsa -x` | Wave 0 |
| CBOM-03 / UI-03 | `_derive_findings()` emits quantum-vulnerable finding for ECDSA cert | unit | `pytest tests/test_gap_closure.py::test_findings_quantum_label_ecdsa -x` | Wave 0 |
| CBOM-03 / UI-03 | `_cert_quantum_safety("RSA")` returns display label "Vulnerable" not raw enum | unit | `pytest tests/test_gap_closure.py::test_cert_quantum_safety_display_label -x` | Wave 0 |
| CBOM-03 / UI-03 | `_cert_quantum_safety("ML-KEM-768")` returns "Safe" | unit | `pytest tests/test_gap_closure.py::test_cert_quantum_safety_pqc_safe -x` | Wave 0 |
| UI-01 / BRAND-04 | `pyproject.toml` package-data includes `dashboard/static/**/*` | unit | `pytest tests/test_gap_closure.py::test_pyproject_includes_dashboard_static -x` | Wave 0 |
| BRAND-04 | `config_template.yaml` contains commented `intelligence:` block | unit | `pytest tests/test_gap_closure.py::test_config_template_has_intelligence_block -x` | Wave 0 |
| BRAND-04 | `config_template.yaml` parses as valid YAML after template edit | unit | `pytest tests/test_gap_closure.py::test_config_template_valid_yaml -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_gap_closure.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_gap_closure.py` — covers all 7 new test IDs above; does not yet exist

---

## Environment Availability

Step 2.6: SKIPPED — phase is code/config-only edits with no external tool dependencies. No
new CLI tools, services, or runtimes are required.

---

## Runtime State Inventory

> Included because MISSING-01 involves a config template change — checking if runtime state
> is affected.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `config_template.yaml` is only used at `quirk init` time; no stored state embeds it | None |
| Live service config | None — template changes only affect future `quirk init` runs, not running instances | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no keys reference `intelligence:` block by name | None |
| Build artifacts | Existing `config.yaml` files generated by previous `quirk init` runs will NOT be updated; this is intentional and documented — runtime safe (defaults apply) | None — code edit only |

**Nothing found requiring data migration.** Template fix affects only future `quirk init`
output, not any running service or stored record.

---

## Open Questions

1. **`_QS_DISPLAY` dict placement**
   - What we know: dict is currently defined inline inside `_derive_cbom()`, used in a local
     helper `_qs_for_alg()`. The planner must decide whether to promote it to module-level
     or duplicate it in the two patched functions.
   - What's unclear: Either approach is correct; module-level is cleaner and avoids drift.
   - Recommendation: Promote to module-level constant (`_QS_DISPLAY = {...}`) immediately
     after imports. All three functions reference the same dict.

2. **Wheel build smoke test**
   - What we know: PACKAGE-01 is only fully validated by building a wheel and installing
     non-editable. Automated tests can verify the `pyproject.toml` text, but cannot easily
     verify the built wheel content without a CI pipeline step.
   - What's unclear: Whether the planner should include a `pip wheel . && pip install --no-editable` step as a manual verification item.
   - Recommendation: Yes — add as a human-verification item in the plan, mirroring how Phase
     7 handled browser-dependent verification items.

---

## Sources

### Primary (HIGH confidence)

- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/dashboard/api/routes/scan.py` — direct file read; bug locations verified at lines 142-143 and 374-381
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/cbom/classifier.py` — direct file read; `quantum_safety_label` signature and `classify_algorithm` return types verified
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/pyproject.toml` — direct file read; current package-data contents confirmed
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/config_template.yaml` — direct file read; confirmed no `intelligence:` section
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/v3.9-MILESTONE-AUDIT.md` — authoritative gap definitions including exact fix patterns
- `python -m pytest tests/test_cbom_classifier.py -q` — 32 tests passing; classifier module confirmed stable

### Secondary (MEDIUM confidence)

- setuptools documentation on `package-data` glob patterns — `**` expansion supported in setuptools>=68; constraint already present in `pyproject.toml`

---

## Metadata

**Confidence breakdown:**
- Bug fix locations: HIGH — verified by direct file read, cross-referenced with audit
- Package-data fix: HIGH — standard setuptools pattern, constraint already satisfied
- Config template fix: HIGH — no logic change, YAML syntax trivially verified
- Test strategy: HIGH — existing test patterns followed exactly (see `test_packaging.py`, `test_cli_init.py`)

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable codebase; no fast-moving dependencies)

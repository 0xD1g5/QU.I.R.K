# Phase 73: CBOM + Intelligence + Reports WARNINGs - Research

**Researched:** 2026-05-15
**Domain:** Reports / intelligence / CBOM hardening (13 open WARNING rows)
**Confidence:** HIGH (every file:line in CONTEXT.md verified against HEAD `cf2417a`)

## Summary

Phase 73 closes 13 open WARNING rows (`cbom-intel-reports/WR-01..WR-14`; WR-05 already closed by Phase 60). CONTEXT.md locks 10 implementation decisions (D-01..D-10) plus the D-14 do-not-touch list. This research verifies each cite, locates each fix site at HEAD, identifies reusable precedent patterns, and **surfaces six discrepancies between CONTEXT.md wording and current code** that the planner must adjudicate without re-opening decisions (see `<research_concerns>` at the bottom — none invalidate the locked decisions).

**Primary recommendation:** Three plans, one per INTEL-NN requirement (mirrors the audit cluster cleanly). The largest single planning item is the `quirk/util/weak_crypto.py` helper (D-02), which is module-shape-identical to `quirk/util/safe_exc.py` and a copy-paste exercise once token list + helper signature is fixed. All other fixes are <10-line surgical edits.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All 10 decisions D-01 through D-10 (plus D-14 do-not-touch) are locked in `.planning/phases/73-cbom-intel-reports-warnings/73-CONTEXT.md`:

- **D-01:** Narrow PDF render `except` to `(PlaywrightError, asyncio.TimeoutError, TimeoutError, OSError, RuntimeError)`; wrap in `try/finally` with defensive `browser.close()` / `context.close()`; emit stderr advisory `"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}"` (closes WR-01, WR-02, WR-14)
- **D-01a (discretion):** Import-guard pattern unchanged if Playwright missing — researcher confirms idiom.
- **D-02:** Create `quirk/util/weak_crypto.py` with `_WEAK_CIPHER_TOKENS` frozenset + `is_weak_cipher()` helper; route email + broker predicates through it; SAML SHA-1 detection also through helper.
- **D-02a (discretion):** Set private, helper public — recommended default.
- **D-03:** ECDSA detection in `evidence.py` aligns to `cert_pubkey_alg.upper().startswith(("EC", "ECDSA"))`; apply at every site.
- **D-04:** Document `SCORE_WEIGHTS` invariant (sum=261, NOT normalized); add `tests/test_score_weights_invariant.py`; cross-reference Phase 60 cap-sharing rationale.
- **D-05:** Strip double-period in `roadmap.py::_why`.
- **D-06:** Document `roadmap.py` merge rule (mutation/merge after yield); add regression test for merge.
- **D-07:** `executive.py::_build_interpretation` guards `score['score']` via `.get(...)` returning `_INTERPRETATION_UNAVAILABLE` constant when missing.
- **D-08:** TLS 1.2 RSA non-PFS returns `RSA-kex` label.
- **D-09:** `confidence.py` weight overrides → clamp `[0.0, 1.0]`, fail-loud `ValueError` on non-numeric.
- **D-10:** `motion_broker_weak_tls_count` routes through `is_weak_cipher` + sibling `is_legacy_tls_version`.
- **D-14 (do-not-touch):** No SCORE_WEIGHTS value changes (only doc+invariant); no `_apply_weighted_impacts` edits; no `cbom/builder.py` Pass-1/2/3 edits; no `trends.py` edits; no `technical.py` edits; no PDF engine swap; no TLS-scanner emitter changes.

### Claude's Discretion

- D-01a (import-guard idiom), D-02a (set private vs public)

### Deferred Ideas (OUT OF SCOPE)

- SCORE_WEIGHTS normalization (regress all scorecards — v5.0 only)
- PDF engine swap (Playwright → WeasyPrint)
- TLS scanner emitter unification (EC ↔ ECDSA at producer)
- Standalone `quirk/util/tls_versions.py` module
- Tighten `confidence` override unknown-key WARNING to ValueError
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTEL-01 | PDF render hardening (closes WR-01, WR-02, WR-14) | D-01; `quirk/reports/html_renderer.py:105-128` verified; `safe_str` confirmed in `quirk/util/safe_exc.py:36`; stderr advisory precedent at `quirk/util/optional_extra.py:225` |
| INTEL-02 | Weak-crypto predicate unification (closes WR-03, WR-04, WR-10, WR-11) | D-02, D-03, D-10; all evidence.py sites (lines 127-131, 158-161, 241-253, 256-269) verified; precedent `safe_exc.py` module shape verified |
| INTEL-03 | Score weights + roadmap + executive + KEX + confidence (closes WR-06, WR-07, WR-08, WR-09, WR-12, WR-13) | D-04..D-09; all six sites verified at HEAD |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PDF render exception handling + cleanup | Reports (`html_renderer.py`) | Reports caller (`writer.py:183-185`) | The render function owns the Playwright lifecycle; caller only consumes bool |
| User-visible PDF failure advisory | Reports (writer.py) | stdlib (`sys.stderr`) | Advisory pattern mirrors Phase 41 `_emit_missing_extra_advisory` |
| Weak-cipher predicate unification | `quirk/util/` (new `weak_crypto.py`) | `intelligence/evidence.py` (consumer) | Pure helper module; mirrors `safe_exc.py` shape |
| ECDSA detection alignment | `intelligence/evidence.py` | — | Single-module consumer fix; producer is do-not-touch (D-14) |
| Score weights doc + invariant | `intelligence/scoring.py` | `tests/test_score_weights_invariant.py` (new) | Documentation only — CI gate via test |
| Roadmap double-period + merge doc | `intelligence/roadmap.py` | — | Module-local fix |
| Executive score guard | `reports/executive.py` | — | Single-function fix |
| TLS 1.2 RSA-kex label | `cbom/builder.py::_decompose_cipher_suite` | — | **NOT `evidence.py` as CONTEXT D-08 suggests — see C-1** |
| Confidence override clamp | `intelligence/confidence.py` | — | Single-function fix |

## Standard Stack

### Core (verified present, no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `playwright` | `>=1.58.0` (pyproject.toml:38) | D-01 PDF render; `playwright.sync_api.Error` is the canonical exception type | [VERIFIED: pyproject.toml grep] Already in `dashboard` extra. Latest 1.60.0 [VERIFIED: `npm view playwright version`]. |
| stdlib `asyncio` | Python 3.11+ | D-01 `asyncio.TimeoutError` — **only relevant if async API used; current code is sync** | [VERIFIED] See C-2 below — D-01's async-flavored exception list does not match the sync API at HEAD. |
| `quirk.util.safe_exc.safe_str` | Phase 59 (verified at `quirk/util/safe_exc.py:36`) | D-01 user-visible message sanitization | Already canonical; AST gate `tests/test_safe_exc_gate.py` enforces routing |
| `sys.stderr` (stdlib) | — | D-01 advisory print | Pattern verified at `quirk/util/optional_extra.py:225` |

### Supporting (already present)

| Library | Version | Purpose | Use Case |
|---------|---------|---------|----------|
| `frozenset` (builtin) | — | D-02 `_WEAK_CIPHER_TOKENS` | Mirrors Phase 71 `_SAFE_NMAP_ARG_RE` / Phase 72 `_SEVERITY_RANK` shape |
| `textwrap.dedent` / `str.rstrip` | stdlib | D-05 double-period fix | Minimal fix — `.rstrip('.') + '.'` |

### Alternatives Considered

None. CONTEXT.md locks every decision. No library swaps. No new pip dependencies (explicit phase boundary).

**Installation:** No new packages. `pip install -e ".[dashboard]"` already provides Playwright.

**Version verification:** [VERIFIED: pyproject.toml:38] `playwright>=1.58.0` pinned; current latest 1.60.0 — well within range. The class `playwright.sync_api.Error` exists since 1.16 [CITED: playwright python changelog]; safely importable.

## Architecture Patterns

### System Architecture Diagram

```
                          ┌──────────────────────────────┐
                          │  quirk/reports/writer.py     │
                          │  write_reports()             │ ← caller
                          │  line 183: render_pdf_report │
                          └──────────────┬───────────────┘
                                         │ bool
                                         ▼
                ┌────────────────────────────────────────────┐
                │  quirk/reports/html_renderer.py            │
                │  render_pdf_report()  ← INTEL-01 fix site  │
                │    try: from playwright.sync_api import …  │
                │    except ImportError: return False        │
                │    try:                                    │
                │      with sync_playwright() as p:          │
                │        browser = p.chromium.launch()       │
                │        page = browser.new_page()           │
                │        page.goto(...); page.pdf(...)       │
                │        browser.close()                     │
                │      return True                           │
                │    except Exception: return False  ← WR-01 │
                │    # WR-02: browser leak on inner-raise    │
                └────────────────────────────────────────────┘

INTEL-02 (weak_crypto):
   ┌─────────────────────┐         ┌────────────────────────────┐
   │ NEW                 │ ◄─uses──│ intelligence/evidence.py   │
   │ util/weak_crypto.py │         │  - motion_broker (line 247)│
   │  is_weak_cipher()   │         │  - motion_email (line 265) │
   │  is_legacy_tls_ver()│         │  - SAML (line 158)         │
   │  _WEAK_CIPHER_TOKENS│         │  - ECDSA detection (line   │
   └─────────────────────┘         │    127-131) [D-03]         │
                                   └────────────────────────────┘

INTEL-03 (six independent micro-fixes):
   scoring.py:5   ─► docstring + invariant test
   roadmap.py:50  ─► .rstrip('.') in _why()
   roadmap.py:54  ─► docstring on _add_candidate merge rule
   executive.py:30 ─► score.get('score') guard
   cbom/builder.py:137-217 ─► RSA-kex label in _decompose_cipher_suite
   confidence.py:48-49 ─► clamp + ValueError in apply-weights branch
```

### Recommended Plan Structure

```
.planning/phases/73-cbom-intel-reports-warnings/
├── 73-CONTEXT.md          # locked
├── 73-RESEARCH.md         # this file
├── 73-01-PLAN.md          # INTEL-01: PDF render hardening (WR-01, WR-02, WR-14)
├── 73-02-PLAN.md          # INTEL-02: weak_crypto helper + ECDSA + SAML (WR-03, WR-04, WR-10, WR-11)
└── 73-03-PLAN.md          # INTEL-03: scoring + roadmap + executive + KEX + confidence (WR-06, WR-07, WR-08, WR-09, WR-12, WR-13)
```

Mirrors Phase 72's plan-per-requirement layout, scaled to 3 plans (vs Phase 72's 5).

### Pattern 1: `quirk/util/safe_exc.py` module shape (D-02 precedent)

**Source:** `quirk/util/safe_exc.py:1-53` [VERIFIED: read in this session]

```python
"""Module purpose docstring.

Decision enforcement:
  - <DEC-ID>: …
"""
from __future__ import annotations
import re
from typing import Final

_PRIVATE_CONSTANT: Final[…] = (…)

def public_helper(arg: str | None) -> bool:
    """Docstring."""
    if arg is None:
        return False
    upper = arg.upper()
    return any(t in upper for t in _PRIVATE_CONSTANT)
```

D-02's `weak_crypto.py` mirrors this exactly. Token set:
```python
_WEAK_CIPHER_TOKENS: Final[frozenset[str]] = frozenset({
    "DES", "3DES", "RC4", "MD5", "NULL", "EXPORT", "ANON",
    "DES-CBC", "IDEA",
    "SHA1", "SHA-1",  # SAML SHA-1 family per D-02
})
```

### Pattern 2: Stderr advisory (D-01 user-visible warning)

**Source:** `quirk/util/optional_extra.py:225` [VERIFIED]

```python
print(format_error("INSTALL-001"), file=sys.stderr)
```

Phase 41/45 `format_error()` uses an error-code registry. CONTEXT D-01 says the literal format string is `f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}"` — this is **inline string, not an INSTALL-NNN code**. The planner has two options:
- (a) Inline `print(..., file=sys.stderr)` per CONTEXT D-01 verbatim.
- (b) Register a new error code (e.g., `INSTALL-005` or `REPORT-001`) for symmetry with existing advisories.

CONTEXT D-01 is locked to (a). See C-3.

### Pattern 3: Clamp + fail-loud (D-09 precedent)

**Source:** Phase 71 D-06 coverage clamp; PROTO-03 D-04 nmap allowlist.

```python
def _as_float(v):
    try: return float(v)
    except Exception: raise ValueError(f"… must be numeric in [0.0, 1.0], got {v!r}")

w[key] = max(0.0, min(1.0, _as_float(value)))
```

### Anti-Patterns to Avoid

- **Blanket `except Exception:`** — hides programmer bugs (WR-01)
- **Unmanaged Playwright `browser.launch()` outside `with` block** — leaks chromium subprocess on inner-raise (WR-02)
- **Direct `score['score']` dict subscript** — KeyError on malformed dict (WR-09)
- **Passing user-supplied weight values into compute pipeline unbounded** — `factor_breakdown.points` shown in JSON output (WR-13)
- **Strict equality on uppercased SHA1** — misses `"SHA-1"`, `"…#rsa-sha1"` (WR-10)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Credential-safe exception text | Custom regex per site | `quirk.util.safe_exc.safe_str` | AST-gated by `tests/test_safe_exc_gate.py` |
| Weak-cipher predicate | Inline per-site `or any(s in cipher for s in …)` | `quirk.util.weak_crypto.is_weak_cipher` (NEW) | One source of truth for email/broker/SAML |
| TLS legacy version check | Inline `if tls_v in {"TLSV1", "TLSV1.0", …}` | `quirk.util.weak_crypto.is_legacy_tls_version` (NEW) | Same token-handling discipline as `is_weak_cipher` |
| Score invariant | Manual code-review checklist | `tests/test_score_weights_invariant.py` (NEW) | CI gate; new contributors learn through test failure |

## Common Pitfalls

### Pitfall 1: WR-12 cite mismatch (D-08) — function lives in `cbom/builder.py`, not `evidence.py`

**CONTEXT D-08 says:** `quirk/intelligence/evidence.py::_decompose_cipher_suite`.
**Current code:** Function defined at `quirk/cbom/builder.py:177`. `evidence.py` does not contain `_decompose_cipher_suite`. [VERIFIED via grep]
**Audit row WR-12 (REVIEW.md):** Correctly cites `quirk/cbom/builder.py:136-142, 209-217`.
**Planner action:** Apply D-08 fix at `cbom/builder.py`, not `evidence.py`. The locked behavior (RSA-kex label for TLS 1.2 RSA non-PFS) is correct. See C-1.

### Pitfall 2: WR-01/02/14 cite mismatch (D-01) — render lives in `html_renderer.py`, not `writer.py`

**CONTEXT D-01 says:** `quirk/reports/writer.py` PDF render path.
**Current code:** `writer.py:183` *calls* `render_pdf_report()`. The function body (the `except Exception:` + `browser.close()` mismanagement) is at `quirk/reports/html_renderer.py:105-128`. [VERIFIED]
**Audit row WR-01 (REVIEW.md):** Correctly cites `quirk/reports/html_renderer.py:127-128`.
**Planner action:** Apply D-01 narrowed-except + `try/finally` to `html_renderer.py::render_pdf_report`. The WR-14 user-visible warning is correctly applied at `writer.py:184` (the caller) because that's where the False return is consumed and where the user sees the failure. See C-2.

### Pitfall 3: Sync vs async Playwright API (D-01)

**CONTEXT D-01 says:** `await context.close()`, `await browser.close()`, `asyncio.TimeoutError`, `from playwright.async_api import Error as PlaywrightError`.
**Current code:** Uses `playwright.sync_api.sync_playwright` (line 111). There is no `context`, no `await`, and `asyncio.TimeoutError` is not raised by sync API. [VERIFIED]
**Planner action:** Translate D-01's async-flavored vocabulary to the sync API:
- `from playwright.sync_api import Error as PlaywrightError`
- Drop `asyncio.TimeoutError` from the except tuple — sync API raises `playwright.sync_api.TimeoutError` (subclass of `Error`), already covered by `PlaywrightError`.
- Replace `await context.close()` with `browser.close()` in the `finally` block (there is no explicit `context` object — `new_page()` creates implicit context).
- Wrap `browser.close()` in `try/except Exception` (defensive, per CONTEXT) — but since the close call is only made when `browser` is defined, restructure as:
  ```python
  browser = None
  try:
      with sync_playwright() as p:
          browser = p.chromium.launch()
          page = browser.new_page()
          page.goto(...); page.pdf(...)
      return True
  except (PlaywrightError, OSError, RuntimeError, TimeoutError) as e:
      return False
  finally:
      if browser is not None:
          try: browser.close()
          except Exception: pass
  ```
See C-2 and C-3 — neither invalidates D-01; the planner just translates async terms to sync.

### Pitfall 4: WR-08 cite says "mutation-after-yield" but `roadmap.py` does not use `yield`

**CONTEXT D-06 says:** "mutation-after-yield merge rule".
**Current code:** `quirk/intelligence/roadmap.py` is **not a generator** — `_add_candidate` mutates the `items` dict in place; `build_phased_roadmap` returns a regular dict (line 427). The closest analog to "merge" is `_add_candidate` lines 74-80: if title already exists, the lower-`(phase, _priority, title)` tuple wins. [VERIFIED]
**Audit row WR-08 (REVIEW.md):** Actually about the `_add_candidate` merge rule — REVIEW.md author corrected themselves mid-text ("downgrading to INFO. (Removing.) Actually, the real issue: …"). The merge rule "smaller key wins" is undocumented.
**Planner action:** Apply D-06 by adding a docstring to `_add_candidate` explaining the merge rule. Add a regression test asserting that adding the same title twice results in the lower-key candidate winning. **No `yield` exists** — the CONTEXT phrasing "mutation-after-yield" is figurative.

### Pitfall 5: TLS 1.2 RSA non-PFS — CONTEXT D-08 says `RSA-kex` label, but `_KEX_MAP["RSA"] = "RSA"` (no hyphen)

**Current code at `cbom/builder.py:142`:** `"RSA": "RSA"` — flat label.
**REVIEW.md says:** The bug is that for `TLS_RSA_WITH_AES_256_GCM_SHA384`, KEX is recorded as "RSA" and AUTH is empty (because the auth-loop logic skips the token already used by KEX).
**CONTEXT D-08 says:** "the correct label is `RSA-kex` (with the hyphen) to distinguish from `RSA-auth` (used elsewhere for cert signature)".
**Planner action:** Two implementation paths exist for D-08:
- (a) **Relabel `_KEX_MAP["RSA"] = "RSA-kex"`** (literal CONTEXT reading) — adds the suffix to the parts list.
- (b) **Emit both `RSA-kex` AND `RSA-auth`** when KEX==AUTH==RSA (matches REVIEW.md's "emit RSA twice once each role" suggestion).
Recommended: (a) — minimal, no logic change to auth-loop. Add parametrized test covering the 8 non-PFS RSA TLS 1.2 suites named in `<test_strategy>`. See C-4.

### Pitfall 6: SCORE_WEIGHTS sum already verified = 261.0 (D-04)

**Verification:** `python3 -c "from quirk.intelligence.scoring import SCORE_WEIGHTS; print(sum(SCORE_WEIGHTS.values()))"` → `261.0`. [VERIFIED — actually executed in this session]
**Count:** 29 weights.
**Planner action:** New test asserts `abs(sum(SCORE_WEIGHTS.values()) - 261.0) < 1e-9`. The current value is **exact** — no floating-point rounding pressure.

### Pitfall 7: total_score is already clamped to [0, 100] (relates to D-04)

**Verification:** `quirk/intelligence/scoring.py:219-223` does `int(_clamp(… , 0, 100))`. [VERIFIED]
**Implication:** WR-06 / CR-06 (cited in REVIEW.md as "score can exceed 100") is **already closed by Phase 60**. The doc requirement in D-04 stands — the runtime arithmetic is already correct.

### Pitfall 8: D-09 function name — there is no `apply_weight_overrides`

**CONTEXT D-09 says:** "`apply_weight_overrides` (researcher confirms function name)".
**Current code:** `quirk/intelligence/confidence.py:46-49` has the override behavior **inline** inside `compute_confidence()`:
```python
w = dict(CONFIDENCE_WEIGHTS)
if weights:
    for key, value in weights.items():
        w[key] = _as_float(value)
```
No separate `apply_weight_overrides` function exists. [VERIFIED via grep]
**Planner action:** Either (a) inline the clamp+fail-loud at lines 46-49 (minimal-diff), or (b) extract a private helper `_apply_weight_overrides(w, weights)` in the same file and apply the clamp there. CONTEXT does not mandate extraction — recommend (a). See C-5.

## Code Examples

Verified patterns from current code:

### INTEL-01: PDF render — current state (the bug)

```python
# quirk/reports/html_renderer.py:105-128
def render_pdf_report(html_path: str, pdf_path: str) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.pdf(path=pdf_path, format="A4", margin={...}, print_background=True)
            browser.close()
        return True
    except Exception:   # ← WR-01 blanket
        return False    # ← WR-02 browser leak if inner raise + WR-14 silent
```

### INTEL-02: ECDSA detection — current state (D-03 fix site)

```python
# quirk/intelligence/evidence.py:127-131
key_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
if key_alg.startswith("RSA"):
    cert_key_type_counts["RSA"] += 1
elif key_alg.startswith("ECDSA"):       # ← WR-04: misses "EC", "ID-ECPUBLICKEY", etc.
    cert_key_type_counts["ECDSA"] += 1
```

Fix (per D-03): `elif key_alg.startswith(("EC", "ECDSA")):`

### INTEL-02: SAML SHA-1 detection — current state (WR-10 fix site)

```python
# quirk/intelligence/evidence.py:155-161
elif proto == "SAML":
    _saml_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
    _saml_size = getattr(ep, "cert_pubkey_size", None)
    if _saml_alg == "SHA1":                                       # ← WR-10: exact equality
        saml_weak_signing_count += 1
    elif _saml_size is not None and isinstance(_saml_size, int) and _saml_size < 2048:
        saml_weak_signing_count += 1
```

Fix (per D-02 routing): `if is_weak_cipher(_saml_alg):`

### INTEL-02: motion_broker_weak_tls_count — current state (WR-03 / D-10 fix site)

```python
# quirk/intelligence/evidence.py:240-253
elif proto in {"KAFKA-TLS", "AMQPS", "AMQPS/AZURE-SERVICEBUS",
               "HTTPS/AWS-SQS", "REDIS-TLS"}:
    tls_v = str(getattr(ep, "tls_version", "") or "").upper()
    if tls_v in {"TLSV1", "TLSV1.0", "TLSV1.1", "SSLV3"}:        # ← WR-03 routes to is_legacy_tls_version
        motion_broker_weak_tls_count += 1
    cipher = str(getattr(ep, "cipher_suite", "") or "").upper()
    if cipher and (
        cipher.startswith("TLS_RSA_WITH_")
        or any(s in cipher for s in ("3DES", "RC4", "DES-CBC"))
        or (any(s in cipher for s in ("AES128-SHA", "AES256-SHA"))
            and "ECDHE" not in cipher and "DHE" not in cipher)
    ):
        motion_broker_weak_cipher_count += 1                      # ← WR-11 routes to is_weak_cipher
```

### INTEL-02: motion_email_weak_cipher — current state (WR-11 fix site)

```python
# quirk/intelligence/evidence.py:263-269
cipher = str(getattr(ep, "cipher_suite", "") or "").upper()
if cipher and (
    cipher.startswith("TLS_RSA_WITH_")
    or any(s in cipher for s in ("3DES", "RC4"))   # ← missing DES-CBC, AES128-SHA static-RSA
):
    motion_email_weak_cipher_count += 1
```

The asymmetry vs broker (which adds `DES-CBC, AES128-SHA, AES256-SHA`) is exactly WR-11.

### INTEL-03 / D-05: Roadmap _why double-period — current state

```python
# quirk/intelligence/roadmap.py:48-51
def _why(base: str, hint: str) -> str:
    if hint:
        return f"{base} Driver: {hint}."   # ← if hint already ends in '.', produces '..'
    return base
```

Fix: `return f"{base} Driver: {hint.rstrip('.')}."`.

### INTEL-03 / D-06: Roadmap merge rule — current state

```python
# quirk/intelligence/roadmap.py:54-80
def _add_candidate(items, *, phase, title, why, …, priority):
    existing = items.get(title)
    candidate = {...}
    if existing is None:
        items[title] = candidate
        return
    old_key = (_PHASE_ORDER[existing["phase"]], int(existing["_priority"]), existing["title"])
    new_key = (_PHASE_ORDER[candidate["phase"]], int(candidate["_priority"]), candidate["title"])
    if new_key < old_key:
        items[title] = candidate   # ← merge: lower tuple wins; undocumented
```

Fix (per D-06): Prepend a multi-line docstring (`"""…merge rule: …"""`) and add regression test.

### INTEL-03 / D-07: Executive score guard — current state

```python
# quirk/reports/executive.py:29-31
bullets.append(
    f"Quantum Readiness Score is **{score['score']}/100** (**{score['rating']}**)."
)
```

Fix (per D-07):
```python
_INTERPRETATION_UNAVAILABLE = "Score data unavailable for this run."
…
score_val = score.get("score") if isinstance(score, dict) else None
if score_val is None:
    return {"bullets": [_INTERPRETATION_UNAVAILABLE], …}
```

### INTEL-03 / D-08: TLS RSA-kex — current state at `cbom/builder.py:137-218`

```python
_KEX_MAP: dict[str, str] = {
    "ECDHE": "X25519",
    "ECDH":  "X25519",
    "DHE":   "DH-GroupExchange",
    "DH":    "DH-2048",
    "RSA":   "RSA",          # ← WR-12: should be "RSA-kex" per D-08
}
# … inside _decompose_cipher_suite, line 211-218:
kex_name: str | None = None
for i, token in enumerate(pre_tokens):
    if token in _KEX_MAP:
        kex_name = _KEX_MAP[token]
        break
```

Fix (recommended per Pitfall 5, path (a)): `_KEX_MAP["RSA"] = "RSA-kex"`.

### INTEL-03 / D-09: Confidence weight overrides — current state

```python
# quirk/intelligence/confidence.py:46-49
w = dict(CONFIDENCE_WEIGHTS)
if weights:
    for key, value in weights.items():
        w[key] = _as_float(value)        # ← WR-13: no clamp, no validation
```

Fix (per D-09 — inline at this site):
```python
KNOWN_KEYS = set(CONFIDENCE_WEIGHTS.keys())
if weights:
    for key, value in weights.items():
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Confidence override {key!r} must be numeric in [0.0, 1.0], got {value!r}"
            )
        w[key] = max(0.0, min(1.0, num))
        if key not in KNOWN_KEYS:
            import logging
            logging.getLogger(__name__).warning(
                "Unknown confidence override key %r — forward-compat", key
            )
```

## Test File Pattern

Existing relevant test modules at HEAD (verified `ls tests/`):

| Test file | Covers | Phase 73 use |
|-----------|--------|--------------|
| `tests/test_pdf_export.py` | UI-04 dashboard PDF export (mocks `sync_playwright`) | **Pattern reference** for INTEL-01: shows `mock.patch("…sync_playwright", side_effect=…)` and asserts the graceful-degradation path. New `tests/test_pdf_render_hardening.py` mirrors this idiom. |
| `tests/test_intelligence_confidence.py` | Existing confidence-score behavior | Extend with INTEL-03 / D-09: parametrized override-value clamp + non-numeric raises ValueError. |
| `tests/test_intelligence_evidence.py` | Existing evidence aggregation | Extend with INTEL-02 / D-03 ECDSA-alias detection + SAML SHA-1 mixed-case. |
| `tests/test_intelligence_roadmap.py` | Existing roadmap output | Extend with INTEL-03 / D-05 double-period regression + D-06 merge-rule test. |
| `tests/test_intelligence_scoring.py` | Existing score arithmetic | Extend with INTEL-03 / D-04 invariant assertion (or new dedicated module `tests/test_score_weights_invariant.py`). |
| `tests/test_html_report.py` | Existing HTML render flow | Extend with INTEL-01 stderr advisory capture (use `capsys`). |
| `tests/test_reports_writer.py` | Existing writer flow | Extend with INTEL-01 — assert `pdf_path is None` + stderr message contains "PDF generation failed" + HTML path. |
| `tests/test_cbom_writer.py` | Existing CBOM flow | INTEL-03 / D-08 RSA-kex parametrized table belongs in a **new** `tests/test_decompose_cipher_suite.py` or extension of `test_cbom_writer.py`. |
| `tests/test_score_clamp_property.py` | Phase 60 SCORE-01 property test | Confirms `total_score ≤ 100` invariant already in place. |

**No `tests/test_executive.py` exists** — INTEL-03 / D-07 needs a new module or extension of `tests/test_reports_writer.py`. Recommend: new `tests/test_executive_score_guard.py` per CONTEXT `<test_strategy>`.

**New test modules required by CONTEXT `<test_strategy>`:**
- `tests/test_pdf_render_hardening.py` — INTEL-01
- `tests/test_weak_crypto_helper.py` — INTEL-02 (covers `is_weak_cipher` + `is_legacy_tls_version`)
- `tests/test_score_weights_invariant.py` — INTEL-03 D-04
- `tests/test_roadmap_double_period.py` — INTEL-03 D-05 (or extend `test_intelligence_roadmap.py`)
- `tests/test_executive_score_guard.py` — INTEL-03 D-07
- `tests/test_confidence_clamp.py` — INTEL-03 D-09 (or extend `test_intelligence_confidence.py`)
- `tests/test_tls_kex_label.py` — INTEL-03 D-08 parametrized over 8 RSA non-PFS suites

**Recommendation:** Use the existing-module extension pattern where natural (`test_intelligence_evidence.py`, `test_intelligence_roadmap.py`, `test_intelligence_confidence.py`) and create new modules for the cross-cutting concerns (`test_weak_crypto_helper.py`, `test_score_weights_invariant.py`, `test_tls_kex_label.py`, `test_pdf_render_hardening.py`).

## Dependency Confirmation

### Playwright import paths

[VERIFIED at `quirk/reports/html_renderer.py:111`]:
```python
from playwright.sync_api import sync_playwright
```

For the narrowed-except tuple (D-01):
```python
from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
```

Both `Error` and `TimeoutError` are public exports of `playwright.sync_api` in v1.16+ [CITED: Playwright Python API docs]. Available since the project's `>=1.58.0` pin.

### `safe_str` helper availability

[VERIFIED at `quirk/util/safe_exc.py:36`]:
```python
def safe_str(exc: BaseException) -> str: ...
```

Import in `html_renderer.py` (D-01 user-visible message):
```python
from quirk.util.safe_exc import safe_str
```

AST gate at `tests/test_safe_exc_gate.py` enforces all `f"...{exc}..."` patterns route through `safe_str` — D-01's new advisory message MUST use `safe_str(e)` to pass the gate.

### `cbom/builder.py::_decompose_cipher_suite` availability

[VERIFIED at `quirk/cbom/builder.py:177`]. Two import sites in `builder.py` itself (lines 498, 616). No external module imports it.

## Runtime State Inventory

> Phase 73 is a code-hardening + documentation phase. No renames, no migrations, no data state changes.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 73 touches no DB schema, no on-disk format, no CBOM JSON shape (D-14 forbids). | None |
| Live service config | None — no n8n / Datadog / scheduled-task references. | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no env-var or secret reference is renamed. Playwright extra install is unchanged. | None |
| Build artifacts | None — no pip package renamed; `quirk/util/weak_crypto.py` is a new module (auto-discovered by import). `__pycache__` regenerates on import. | None |

**Nothing requires migration.** All changes are source-level.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `except Exception: return False` (PDF render) | Narrowed except + `try/finally` cleanup | Phase 73 (D-01) | One Phase-73 fix; pattern carries forward |
| Per-site inline weak-cipher checks (evidence.py × 3 sites + SAML) | `quirk.util.weak_crypto.is_weak_cipher` helper | Phase 73 (D-02) | Single source of truth for weak-token detection |
| `key_alg.startswith("ECDSA")` | `key_alg.startswith(("EC", "ECDSA"))` | Phase 73 (D-03) | Aligns consumer to existing TLS scanner emitter conventions |
| `score['score']` direct subscript | `score.get('score', None)` with fallback constant | Phase 73 (D-07) | Mirrors Phase 70 D-07 guard discipline |
| Unbounded user-supplied weight overrides | Clamp + fail-loud on non-numeric | Phase 73 (D-09) | Mirrors Phase 71 D-06 clamp |

**Deprecated/outdated:**
- Per-site uppercase token-set string literals — replaced by `_WEAK_CIPHER_TOKENS` frozenset.
- Inline `_decompose_cipher_suite`'s `_KEX_MAP["RSA"] = "RSA"` (ambiguous role label) — replaced by `"RSA-kex"`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-08 implementation path (a) — relabel `_KEX_MAP["RSA"] = "RSA-kex"` — is the minimal fix matching CONTEXT intent | Pitfall 5, C-4 | Planner / discuss-phase may pick path (b) (emit both KEX:RSA + AUTH:RSA) — both valid; (a) is recommended |
| A2 | D-09 inline (not extracted helper) is acceptable | Pitfall 8, C-5 | If reviewer wants helper extraction, refactor inflates diff slightly |
| A3 | D-01 sync-API translation (drop `asyncio.TimeoutError`, use `playwright.sync_api.TimeoutError`) preserves intent | Pitfall 3, C-2 | None — sync code does not raise async exceptions |
| A4 | D-06 "mutation-after-yield" figurative; real fix is documenting `_add_candidate` merge rule | Pitfall 4, C-6 | None — REVIEW.md's mid-text correction confirms |
| A5 | The `[reports]` extra cited by D-01a does not exist — Playwright lives in `[dashboard]` extra | C-7 | Plan task should reference `[dashboard]` (or just `playwright`); D-01a discretion still applies |

## Open Questions

1. **D-08 RSA label scope** — should `_KEX_MAP["RSA"] = "RSA-kex"` propagate to TLSv1.3 PSK/anonymous cases? Verified `is_tls13` branch (line 192) skips the `_KEX_MAP` lookup entirely, so TLSv1.3 unaffected. Recommendation: scope D-08 fix to non-TLSv1.3 path only.

2. **D-09 unknown-key behavior** — CONTEXT says WARNING log for unknown keys. Existing `CONFIDENCE_WEIGHTS` has 4 known keys. Any pre-existing test or doc passing extra keys today? Verified `tests/test_intelligence_confidence.py:_evidence()` does not pass `weights=`. Safe to log-and-accept unknown keys per D-09.

3. **D-02 token list completeness** — CONTEXT lists `{"DES", "3DES", "RC4", "MD5", "NULL", "EXPORT", "ANON", "DES-CBC", "IDEA", "SHA1", "SHA-1"}`. Compare to existing `weak_markers` at `tls_capabilities.py:103` = `("RC4", "3DES", "CBC3", "NULL", "EXPORT", "MD5")` and `db_connector.py:40` = `("RC4", "DES", "NULL", "EXPORT", "ANON", "MD5", "3DES")`. Difference: `CBC3` (alternate spelling of 3DES), `IDEA`, `SHA1`. Recommendation: planner verifies `CBC3` is added to D-02 frozenset (it's a real OpenSSL cipher token, e.g., `DES-CBC3-SHA`). See C-8.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `playwright` | D-01 (already gated by ImportError) | ✗ in current venv | — | Existing ImportError branch → returns False; D-01's narrowed except is unreachable in this branch |
| `python -m compileall` | CLAUDE.md mandatory check | ✓ | Python 3.11+ | — |
| `git` | docs commit | ✓ | — | — |

Playwright not being installed locally is fine — the existing `try/except ImportError: return False` branch at `html_renderer.py:112-113` handles this. D-01's narrowed-except is for the *inner* try (post-import).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | (project root) — pytest defaults |
| Quick run command | `pytest tests/test_intelligence_*.py tests/test_pdf_*.py tests/test_reports_writer.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTEL-01 / WR-01 | PDF except narrows; programmer bug surfaces | unit | `pytest tests/test_pdf_render_hardening.py::test_blanket_except_narrowed -x` | ❌ Wave 0 |
| INTEL-01 / WR-02 | Playwright browser closed in finally on inner-raise | unit | `pytest tests/test_pdf_render_hardening.py::test_finally_close -x` | ❌ Wave 0 |
| INTEL-01 / WR-14 | Stderr advisory printed on PDF failure | unit | `pytest tests/test_reports_writer.py::test_pdf_failure_advisory -x` | ✅ extend existing |
| INTEL-02 / WR-03 | motion_broker uses `is_legacy_tls_version` | unit | `pytest tests/test_weak_crypto_helper.py -x` | ❌ Wave 0 |
| INTEL-02 / WR-04 | ECDSA detection aliases EC/ECDSA | unit | `pytest tests/test_intelligence_evidence.py::test_ecdsa_alias -x` | ✅ extend existing |
| INTEL-02 / WR-10 | SAML SHA-1 mixed-case detected | unit | `pytest tests/test_intelligence_evidence.py::test_saml_sha1_mixed -x` | ✅ extend existing |
| INTEL-02 / WR-11 | email/broker predicates produce identical output | unit | `pytest tests/test_weak_crypto_helper.py::test_email_broker_parity -x` | ❌ Wave 0 |
| INTEL-03 / WR-06 | SCORE_WEIGHTS sum == 261 | unit | `pytest tests/test_score_weights_invariant.py -x` | ❌ Wave 0 |
| INTEL-03 / WR-07 | _why output has no double-period | unit | `pytest tests/test_intelligence_roadmap.py::test_why_no_double_period -x` | ✅ extend existing |
| INTEL-03 / WR-08 | _add_candidate merge rule has docstring + regression test | unit | `pytest tests/test_intelligence_roadmap.py::test_merge_rule -x` | ✅ extend existing |
| INTEL-03 / WR-09 | _build_interpretation returns fallback on missing score key | unit | `pytest tests/test_executive_score_guard.py -x` | ❌ Wave 0 |
| INTEL-03 / WR-12 | TLS 1.2 RSA non-PFS emits "RSA-kex" | unit | `pytest tests/test_tls_kex_label.py -x` | ❌ Wave 0 |
| INTEL-03 / WR-13 | confidence override clamps + raises | unit | `pytest tests/test_intelligence_confidence.py::test_override_clamp tests/test_intelligence_confidence.py::test_override_non_numeric_raises -x` | ✅ extend existing |

### Sampling Rate

- **Per task commit:** Module-scoped pytest (one file)
- **Per wave merge:** All INTEL-NN test modules
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_pdf_render_hardening.py` — new module, mirrors `test_pdf_export.py` mock idiom
- [ ] `tests/test_weak_crypto_helper.py` — new module, parametrized cipher-string table
- [ ] `tests/test_score_weights_invariant.py` — new module, single-assertion + golden-file regression
- [ ] `tests/test_executive_score_guard.py` — new module, mocks score dict missing keys
- [ ] `tests/test_tls_kex_label.py` — new module, parametrized over 8 RSA non-PFS suites

*Framework already installed; no install command needed.*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (D-09 confidence override clamp; D-07 score guard) | Inline clamp + `dict.get` fallback |
| V7 Error Handling & Logging | yes (D-01 narrowed except; D-09 fail-loud) | Phase 59 `safe_str`; explicit `ValueError` |
| V8 Data Protection | yes (D-01 user-visible message routes through `safe_str` — avoids credential leak in exception text) | `quirk.util.safe_exc.safe_str` (AST-gated) |

### Known Threat Patterns for reports/intelligence stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Programmer-bug-hidden-by-blanket-except | Tampering / Denial-of-Service (silent failure) | Narrow except to expected types (D-01) |
| Process leak via unmanaged subprocess (Playwright Chromium) | DoS (resource exhaustion) | `try/finally` cleanup (D-02 / WR-02) |
| User-supplied override values poisoning compute pipeline | Tampering (output integrity) | Clamp + fail-loud (D-09) |
| Credential text in user-visible advisory | Information Disclosure | `safe_str(e)` (D-01) |

## Project Constraints (from CLAUDE.md)

- **PEP 8** for all Python changes — applies to new `weak_crypto.py` module and all edits.
- **Minimal diffs** — D-14 do-not-touch list enforces this explicitly.
- After changes, run `python -m compileall` and relevant tests.
- **Staleness review cadence does NOT apply** — no QRAMM model or compliance catalog edits.
- **Chaos lab maintenance does NOT apply** — no Docker Compose profile changes.
- **Mandatory phase completion:** Create Obsidian Phase 73 note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-73-CBOM-Intel-Reports-Warnings.md`; update `docs/UAT-SERIES.md` (Phase 73 wrap note); sync to vault; commit UAT-SERIES.md update.

## Sources

### Primary (HIGH confidence)

- `quirk/reports/html_renderer.py:105-128` — D-01 / WR-01 / WR-02 site verified
- `quirk/reports/writer.py:182-185` — D-01 / WR-14 caller site verified
- `quirk/reports/executive.py:29-31` — D-07 / WR-09 site verified
- `quirk/intelligence/scoring.py:5-36, 219-223` — D-04 / WR-06 site + total clamp verified; sum=261.0 confirmed via `python3` execution
- `quirk/intelligence/roadmap.py:48-51, 54-80` — D-05 / WR-07 + D-06 / WR-08 sites verified
- `quirk/intelligence/evidence.py:127-131, 158-161, 240-269` — D-03 / WR-04, WR-10, WR-03, WR-11 sites verified
- `quirk/intelligence/confidence.py:46-49` — D-09 / WR-13 site verified
- `quirk/cbom/builder.py:137-218` — D-08 / WR-12 site verified (in `cbom/builder.py`, NOT `evidence.py`)
- `quirk/util/safe_exc.py:36` — D-01 dependency verified
- `quirk/util/optional_extra.py:225` — stderr advisory pattern verified
- `pyproject.toml:33-40` — `playwright>=1.58.0` in `dashboard` extra verified
- `.planning/audit-2026-05-08/AUDIT-TASKS.md:149-162` — all 13 open WR rows confirmed
- `.planning/audit-2026-05-08/cbom-intel-reports/REVIEW.md:142-227` — file:line cites confirmed
- `.planning/phases/60-score-arithmetic-correctness/60-02-SUMMARY.md:88-89` — Phase 60 cap-sharing rationale verified

### Secondary (MEDIUM confidence)

- `tests/test_pdf_export.py:23-30` — mock pattern reference for INTEL-01 tests
- `tests/test_intelligence_confidence.py:1-30` — test-shape reference for INTEL-03 / D-09 extension
- `.planning/phases/72-cloud-scanner-warnings/72-RESEARCH.md` — research template + planning layout precedent
- `quirk/scanner/tls_capabilities.py:103-111` — existing `_is_weak_cipher` precedent (`weak_markers = ("RC4", "3DES", "CBC3", "NULL", "EXPORT", "MD5")`)
- `quirk/scanner/db_connector.py:40-48` — existing `_is_weak_mysql_cipher` + `MYSQL_WEAK_CIPHER_PREFIXES` precedent

### Tertiary (LOW confidence)

- D-08 implementation path choice (a vs b) — planner adjudicates
- D-02 token list completeness re: `CBC3` token (open question 3)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Playwright pin verified; `safe_str` verified; no new deps
- Architecture: HIGH — every file:line in CONTEXT.md verified against HEAD; six cite mismatches documented in concerns
- Pitfalls: HIGH — `sum(SCORE_WEIGHTS) == 261.0` executed in session; `_decompose_cipher_suite` confirmed in `cbom/builder.py` not `evidence.py`
- Test gaps: HIGH — 5 new test modules identified; existing module extension points clear

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable phase; no fast-moving dependencies)

<research_concerns>
## Research Concerns (planner adjudication needed)

These are NOT new decisions. CONTEXT.md remains authoritative. Each concern surfaces a discrepancy between CONTEXT wording and current HEAD, with recommended handling.

### C-1 (D-08): `_decompose_cipher_suite` lives in `cbom/builder.py`, not `evidence.py`

**CONTEXT D-08 says:** `quirk/intelligence/evidence.py::_decompose_cipher_suite (or wherever the cipher decomposer lives — researcher to confirm)`.
**Current code:** Function defined at `quirk/cbom/builder.py:177`. [VERIFIED via grep]
**REVIEW.md WR-12:** Correctly cites `cbom/builder.py:136-142, 209-217`.
**Adjudication:** Apply D-08 at `cbom/builder.py`. CONTEXT explicitly invited researcher confirmation. No decision change.

### C-2 (D-01): Current Playwright code is sync API; CONTEXT vocabulary is async

**CONTEXT D-01 says:** `await context.close()`, `await browser.close()`, `asyncio.TimeoutError`, `from playwright.async_api import Error as PlaywrightError`.
**Current code:** `from playwright.sync_api import sync_playwright` at line 111. No `await`, no `context` variable. [VERIFIED]
**Adjudication:** Translate D-01's async-flavored terms to sync API:
- Import: `from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError`
- Except tuple: `(PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError)` — drop `asyncio.TimeoutError` (unreachable in sync path)
- `finally` block: `if browser is not None: try: browser.close() except Exception: pass` (no `context` to close — `new_page()` creates implicit context)
The locked decision (narrowed except + finally cleanup + stderr advisory) is correct; the implementation translates to sync vocabulary.

### C-3 (D-01): User-visible PDF message location — `html_renderer.py` (callee) vs `writer.py` (caller)?

**CONTEXT D-01 says:** "wraps the browser/context lifecycle in a `try/finally`. … On exception: print `f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}"` to stderr".
**Ambiguity:** The narrowed-except site is `html_renderer.py:127`. The caller `writer.py:184` is where `pdf_ok=False` is consumed and where the user expects to see the failure context. The stderr message must include `html_path` — `html_renderer.py::render_pdf_report` receives `html_path` as a parameter, so emitting from either site is feasible.
**Adjudication:** Emit from `html_renderer.py::render_pdf_report` (callee) inside the narrowed `except` block — has direct access to both `e` and `html_path`. WR-14's "user-visible warning on PDF failure" is satisfied via the callee print. No code change to `writer.py:184` needed beyond keeping the `pdf_path = None` assignment.

### C-4 (D-08): `RSA-kex` label — relabel KEX_MAP vs emit both KEX+AUTH?

**CONTEXT D-08 says:** "The correct label is `RSA-kex` (with the hyphen) to distinguish from `RSA-auth` (used elsewhere for cert signature). Fix the conditional: when `tls_version == "TLSv1.2"` AND cipher suite lacks `(EC)DHE`, return `RSA-kex` regardless of how the cipher string spells it."
**REVIEW.md WR-12 says:** "Should ideally emit RSA twice (once each role) or annotate the dual role."
**Current code:** `_KEX_MAP["RSA"] = "RSA"` produces single "RSA" token. Auth-loop at lines 220-237 skips RSA token (already used as KEX) → no `RSA-auth` emitted.
**Adjudication:** Minimal-diff path: `_KEX_MAP["RSA"] = "RSA-kex"`. This emits `["RSA-kex", "AES-256-GCM", "SHA-384"]` for non-PFS RSA suites. The "RSA-auth" mirror is a separate consideration — CONTEXT D-08 does not require dual emission. If the planner / `/gsd-discuss-phase` prefers dual emission, restructure the auth-loop. Recommended: stick with relabel.

### C-5 (D-09): `apply_weight_overrides` function does not exist

**CONTEXT D-09 says:** "`apply_weight_overrides` (researcher confirms function name)".
**Current code:** No such function. Override behavior is inline at `confidence.py:46-49` inside `compute_confidence`. [VERIFIED]
**Adjudication:** Apply clamp + validation inline at lines 46-49. CONTEXT explicitly invited researcher confirmation. No decision change — the clamp + fail-loud semantics are correct regardless of code organization.

### C-6 (D-06): "mutation-after-yield" — `roadmap.py` does not use `yield`

**CONTEXT D-06 says:** "callers MUST consume each yielded dict before calling `next()`, … merge-after-yield".
**Current code:** `roadmap.py` returns a regular dict (no `yield`). The merge happens in `_add_candidate` (lines 74-80) when a duplicate title arrives. [VERIFIED]
**REVIEW.md WR-08:** Acknowledges mid-text that the original "mutation-after-yield" framing was wrong, then corrects: "the real issue: when two candidates collide, … the comparison `new_key < old_key` chooses the lexically smaller phase-priority-title tuple".
**Adjudication:** Apply D-06 by adding a docstring to `_add_candidate` explaining the "lower-key wins" merge rule. Add regression test asserting duplicate-title behavior. No `yield` exists — CONTEXT's "yield" phrasing is figurative; the merge behavior IS the real undocumented contract.

### C-7 (D-01a): The `[reports]` extra does not exist

**CONTEXT D-01a says:** "the import-guard pattern from Phase 41 / 45 still applies — `[reports]` extra".
**Current code:** `pyproject.toml:33-40` defines `[project.optional-dependencies]` with extras `dashboard` (contains Playwright), `identity`, etc. There is no `[reports]` extra. [VERIFIED]
**Adjudication:** The import-guard idiom (`try: from playwright… except ImportError: return False`) IS in place at `html_renderer.py:110-113`. The extra name is `[dashboard]`, not `[reports]`. No code change — D-01a's discretion point is satisfied by the existing pattern.

### C-8 (D-02): Token list — should `CBC3` (alt 3DES spelling) be included?

**CONTEXT D-02 lists:** `{"DES", "3DES", "RC4", "MD5", "NULL", "EXPORT", "ANON", "DES-CBC", "IDEA", "SHA1", "SHA-1"}`.
**Existing precedent at `tls_capabilities.py:103`:** `("RC4", "3DES", "CBC3", "NULL", "EXPORT", "MD5")`.
**OpenSSL ciphers containing `CBC3`:** `DES-CBC3-SHA`, `EDH-RSA-DES-CBC3-SHA`, `ECDH-RSA-DES-CBC3-SHA`, etc.
**Adjudication:** Recommend planner add `"CBC3"` to the D-02 frozenset. CONTEXT D-02 token list is "the locked starting set" — the helper is the locked decision, not the exact token list. Add `CBC3` for parity with existing `tls_capabilities.py` semantics. Surface to user via discuss-phase if planner disagrees.
</research_concerns>

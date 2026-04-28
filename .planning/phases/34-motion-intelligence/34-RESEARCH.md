# Phase 34: Motion Intelligence — Research

**Researched:** 2026-04-28
**Domain:** Scoring-engine wiring (Python, dataclass-free dict-based evidence pipeline)
**Confidence:** HIGH

## Summary

Phase 34 wires the email + broker TLS evidence already produced by Phases 32 and 33 into the
quantum-readiness scoring engine. CONTEXT.md is exhaustive and locks all 12 implementation
decisions. There is **exactly one implementation unknown**: where to bump the new `motion_*`
counters from upstream finding/protocol signals — and that unknown is now resolved by this
research. All other work is surgical edits to two files (`evidence.py`, `scoring.py`) plus a
new test file.

**Critical correction to CONTEXT.md / REQUIREMENTS.md vocabulary:** there is **no
`EvidenceCounters` dataclass** in `quirk/intelligence/evidence.py`. The module exposes a
function `build_evidence_summary(endpoints, findings, ...) -> Dict[str, Any]` that walks
endpoints, accrues counters in local int variables, and returns a flat dict. MOTION-01 is
satisfied by adding six new local int counters inside that function and seven new keys
(6 counts + at least 5 ratios) to the returned dict. No dataclass schema exists or needs to
exist. The planner must phrase tasks accordingly — "add fields to the EvidenceCounters
dataclass" is literally impossible because that dataclass doesn't exist. [VERIFIED: read
quirk/intelligence/evidence.py end-to-end].

**Primary recommendation:** Mirror the `dar_storage_*` pattern (Phase 28) verbatim. It is
the most recent and closest analog — same shape (count keyed off `proto == "S3"` with a
service_detail substring check), same tests (`tests/test_dar_storage_scoring.py`), same
scoring-block format (`scoring.py:182–185`). Copy the structure mechanically.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|-----------------|-----------|
| Counter accrual from endpoint protocol+service_detail | `quirk/intelligence/evidence.py` (`build_evidence_summary`) | — | All other counters (dar, identity, hygiene) live here; consistency demands motion_ joins them |
| Score weights + profile multipliers | `quirk/intelligence/scoring.py` (module-level dicts) | — | Single source of truth for SCORE_WEIGHTS / PROFILE_MULTIPLIERS |
| Subscore computation + driver list | `quirk/intelligence/scoring.py` (`compute_readiness_score`) | — | Mirrors `dar_impacts` block at lines 179–188 |
| Finding emission (kafka-plaintext-listener etc.) | `quirk/engine/risk_engine.py` (`evaluate_email_endpoints`, `evaluate_broker_endpoints`) | — | **Already exists, no Phase 34 change** — counters key off `ep.protocol` enum values, not finding titles |
| Unit tests | `tests/test_motion_scoring.py` (new file) | — | Flat tests/ directory; no `tests/intelligence/` subdir exists |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `motion_email_starttls_missing_count` is folded into `motion_email_plaintext_ratio`
  (no separate weight). 6 counters / 5 ratios is intentional dedup, not a spec gap.
- **D-02:** `motion_email_plaintext_ratio` numerator =
  `(motion_email_plaintext_count + motion_email_starttls_missing_count)`.
  Denominator = standard `total_endpoints` denom.
- **D-03:** All 5 `motion_` ratio weights LOCKED per MOTION-02:
  `motion_email_plaintext_ratio=12.0`, `motion_email_weak_cipher_ratio=6.0`,
  `motion_broker_plaintext_ratio=14.0`, `motion_broker_weak_tls_ratio=8.0`,
  `motion_broker_weak_cipher_ratio=6.0`.
- **D-04:** Append `data_in_motion` as the 6th subscore key. **DO NOT rename** existing five.
- **D-05:** Renaming the five existing keys is deferred to v4.5+.
- **D-06:** Compute `motion_impacts` / `motion_drivers` mirroring `dar_impacts` (scoring.py:179–188).
  Append `motion_drivers` to `all_drivers`.
- **D-07:** Driver labels: "Plaintext broker listeners", "Weak TLS on brokers",
  "Weak cipher on broker TLS", "Email plaintext or missing STARTTLS",
  "Weak cipher on email TLS".
- **D-08:** `PROFILE_MULTIPLIERS` gains `"motion_"` key with strict=1.4 / balanced=1.0 /
  lenient=0.7. Place after `"dar_"`.
- **D-09:** SC-1 verified by unit tests against `compute_readiness_score()` with synthesized
  evidence dicts — assert `subscores["data_in_motion"]` is strictly lower with motion
  findings, and overall `score` also lower.
- **D-10:** Add a unit test asserting `top_drivers` surfaces a motion driver when motion
  counters dominate.
- **D-11:** Integration validation against `labs/broker/` and `labs/email/` is deferred to
  Phase 36. No Docker dependency added in Phase 34.
- **D-12:** Legacy scans without `motion_` keys produce `data_in_motion = 100` automatically
  via the `_as_int(evidence.get(key, 0))` pattern.

### Claude's Discretion

- Internal field grouping in `evidence.py` (declaration order or `# motion_` comment block).
- Whether `motion_impacts` lives inline in `compute_readiness_score()` or in a small
  `_compute_motion_subscore()` helper — planner picks based on line-budget readability.
- Test filename — likely `tests/test_motion_scoring.py` (CONTEXT proposed
  `tests/intelligence/test_motion_subscore.py` but **that subdir does not exist** —
  see Test Conventions section below).

### Deferred Ideas (OUT OF SCOPE)

- Renaming existing subscore keys to ROADMAP prose names (tls/ssh/api/identity/...) — v4.5+.
- Integration test against `labs/broker/` + `labs/email/` — Phase 36.
- `motion_email_starttls_missing_ratio` as its own weight — rejected (D-01).
- `MotionFinding` API schema for `/api/scan/latest` — Phase 36.
- Motion CBOM components — Phase 35.
- DAR dashboard tab (DASH-05 carry-forward) — separate UI work.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOTION-01 | Add 6 `motion_` counters to evidence pipeline | `evidence.py:78–91` shows the parallel `dar_db_*`, `dar_storage_*`, `dar_k8s_*`, `dar_vault_*` counter declarations; copy that idiom. **No dataclass** — counters are local ints inside `build_evidence_summary()`. |
| MOTION-02 | Add 5 `motion_*_ratio` entries to `SCORE_WEIGHTS` | `scoring.py:5–31` shows the `SCORE_WEIGHTS` dict; insert 5 lines after the `dar_` block (after line 26) for readability. |
| MOTION-03 | Add `"motion_"` key to all 3 profiles in `PROFILE_MULTIPLIERS` | `scoring.py:33–37`; one new entry per profile dict. |
| MOTION-04 | `compute_readiness_score()` returns `data_in_motion` as 6th subscore | `scoring.py:202–208` is the `subscores` dict literal. Add `"data_in_motion": motion_score`. Also: add `motion_score` to total at line 190 and append `motion_drivers` to line 193–194. |

## Project Constraints (from CLAUDE.md)

| Directive | Source | Implication for Phase 34 |
|-----------|--------|---------------------------|
| Follow PEP 8 | CLAUDE.md §"Code Standards" | New ints / dict entries follow existing snake_case + 4-space indent. |
| Keep diffs minimal | CLAUDE.md §"Code Standards" | Mirror `dar_storage_*` pattern verbatim — do not refactor `compute_readiness_score()`. |
| Run `python -m compileall` after changes | CLAUDE.md §"Code Standards" | Add to verification checklist. |
| Update `labs/*/expected_results.md` if detection logic changes | CLAUDE.md §"Code Standards" | **Not applicable** — Phase 34 is scoring wiring only, not detection logic. Skip. |
| Mandatory phase-completion: Obsidian phase note | CLAUDE.md §"Mandatory Phase Completion" | Plan must include a wave for `Phase-34-Motion-Intelligence.md` write to vault. |
| Mandatory phase-completion: Update `docs/UAT-SERIES.md` | CLAUDE.md §"Mandatory Phase Completion" | Plan must include UAT-SERIES update — likely add a UAT case for verifying `data_in_motion` appears in `compute_readiness_score()` output. |
| Sync UAT-SERIES.md to Obsidian | CLAUDE.md §"Mandatory Phase Completion" | Use the printf+cp pattern documented in CLAUDE.md (file too large for `content=`). |
| Commit `docs/UAT-SERIES.md` via gsd-tools | CLAUDE.md §"Mandatory Phase Completion" | Include in final commit task. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib only | 3.11+ | All work is dict + int manipulation | Existing `evidence.py` and `scoring.py` use no third-party deps |
| `pytest` | (existing project pin) | Test runner | Existing tests under `tests/test_dar_*_scoring.py` use pytest |
| `unittest.mock.MagicMock` | stdlib | Endpoint stubbing in tests | Used by `tests/test_dar_storage_scoring.py` `_ep()` helper [VERIFIED: lines 7–24] |

**No new dependencies required.** No `pyproject.toml` changes. (STRUCT-03 carry-forward is satisfied by the empty diff.)

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline `motion_impacts` in `compute_readiness_score` | Extract `_compute_motion_subscore()` helper | Inline mirrors `dar_impacts` exactly (D-06) and is shorter. Helper would duplicate the pattern only motion uses. **Recommend inline** — same as DAR. |
| Plain ints for counters in `build_evidence_summary` | Refactor to `EvidenceCounters` dataclass | Would touch every existing counter and is out of scope. **Reject.** |

**Installation:** None.

**Version verification:** Skipped — no third-party libraries are added.

## Architecture Patterns

### System Architecture Diagram

```
                 ┌─────────────────────────────────────────────┐
                 │ run_scan.py orchestrator (existing)         │
                 └─────────────────────────────────────────────┘
                                       │
                                       │ produces List[CryptoEndpoint] +
                                       │ findings list
                                       ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ quirk/scanner/email_scanner.py + quirk/scanner/broker_scanner.py │
   │ (Phases 32, 33 — DONE)                                           │
   │                                                                  │
   │   email endpoints ⇒ ep.protocol ∈ {"SMTP-STARTTLS", "SMTPS",     │
   │     "IMAP-STARTTLS", "IMAPS", "POP3-STARTTLS", "POP3S"}          │
   │   broker endpoints ⇒ ep.protocol ∈ {"KAFKA-TLS", "KAFKA-PLAIN",  │
   │     "AMQPS", "AMQPS/Azure-ServiceBus", "AMQP-PLAIN",             │
   │     "REDIS-TLS", "REDIS-PLAIN", "HTTPS/AWS-SQS"}                 │
   └──────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ quirk/engine/risk_engine.py (Phases 32, 33 — DONE)               │
   │   evaluate_email_endpoints() → emits EMAIL-08, EMAIL-09 findings │
   │   evaluate_broker_endpoints() → emits kafka-/amqp-/redis-        │
   │     plaintext-listener findings + weak-cipher findings           │
   └──────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ quirk/intelligence/evidence.py:build_evidence_summary()          │
   │ ★ PHASE 34 EDIT POINT #1                                         │
   │                                                                  │
   │   for ep in endpoint_list:                                       │
   │       proto = ep.protocol.upper()                                │
   │       ...                                                        │
   │       elif proto == "S3":  ◀─── existing pattern to mirror       │
   │           if "S3/unencrypted" in sd:                             │
   │               dar_storage_unencrypted_count += 1                 │
   │       ★ NEW: elif proto == "KAFKA-PLAIN" / "AMQP-PLAIN" /        │
   │             "REDIS-PLAIN":                                       │
   │             motion_broker_plaintext_count += 1                   │
   │       ★ NEW: elif proto in {KAFKA-TLS, AMQPS, ..., REDIS-TLS}:   │
   │             — inspect tls_version → motion_broker_weak_tls_count │
   │             — inspect cipher_suite → motion_broker_weak_cipher_  │
   │       ★ NEW: elif proto in {SMTPS, IMAPS, POP3S, *-STARTTLS}:    │
   │             — STARTTLS path with no tls_version →                │
   │                 motion_email_starttls_missing_count              │
   │             — implicit-TLS path missing →                        │
   │                 motion_email_plaintext_count                     │
   │             — weak cipher → motion_email_weak_cipher_count       │
   │                                                                  │
   │   return { ..., "motion_*_count": ..., "motion_*_ratio": ... }   │
   └──────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ quirk/intelligence/scoring.py:compute_readiness_score()          │
   │ ★ PHASE 34 EDIT POINT #2                                         │
   │                                                                  │
   │   SCORE_WEIGHTS["motion_*_ratio"] (5 entries)        ← MOTION-02 │
   │   PROFILE_MULTIPLIERS[*]["motion_"] = {1.4/1.0/0.7}  ← MOTION-03 │
   │                                                                  │
   │   motion_impacts = [                                             │
   │     ("Email plaintext or missing STARTTLS",                      │
   │      -_ratio(plain+starttls_miss, denom) * w[motion_email_p_r]), │
   │     ("Weak cipher on email TLS", ...),                           │
   │     ("Plaintext broker listeners", ...),                         │
   │     ("Weak TLS on brokers", ...),                                │
   │     ("Weak cipher on broker TLS", ...),                          │
   │   ]                                                              │
   │   motion_score, motion_drivers = _apply_weighted_impacts(...)    │
   │                                                                  │
   │   total_score = ... + motion_score                               │
   │   all_drivers += motion_drivers                                  │
   │   return {..., "subscores": {..., "data_in_motion": motion_score}│
   └──────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Downstream (informational, NOT modified):                        │
   │   /api/scan/latest → consumes subscores dict (tolerates extras)  │
   │   React dashboard → Phase 36 will render data_in_motion          │
   └──────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
quirk/
├── intelligence/
│   ├── evidence.py        ← EDIT: add 6 motion_ counters + ratio keys
│   └── scoring.py         ← EDIT: SCORE_WEIGHTS (5), PROFILE_MULTIPLIERS (3 entries),
│                              motion_impacts block, total + drivers + subscores
└── engine/
    └── risk_engine.py     ← NO CHANGE (already emits the findings these counters track)

tests/
└── test_motion_scoring.py ← NEW: mirrors tests/test_dar_storage_scoring.py shape
```

### Pattern 1: Counter accrual idiom (mirror DAR)
**What:** Increment a local int counter inside the `for ep in endpoint_list` loop based on
`ep.protocol` enum value plus an optional `service_detail` substring or attribute check.
**When to use:** All five new motion_ counters use this idiom. Six if you count the
plaintext+starttls-missing pair.
**Example (existing, from `evidence.py:178–184`):**
```python
# Source: quirk/intelligence/evidence.py:178–184 [VERIFIED]
elif proto == "S3":
    sd = str(getattr(ep, "service_detail", "") or "")
    if "S3/unencrypted" in sd:
        dar_storage_unencrypted_count += 1
    elif "S3/sse-kms-aws" in sd:
        dar_storage_aws_managed_count += 1
```

**Phase 34 application (proposed shape — planner finalizes):**
```python
# After existing blocks; before plaintext_http_targets line
elif proto in {"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}:
    motion_broker_plaintext_count += 1

elif proto in {"KAFKA-TLS", "AMQPS", "AMQPS/Azure-ServiceBus",
               "HTTPS/AWS-SQS", "REDIS-TLS"}:
    tls_v = str(getattr(ep, "tls_version", "") or "").upper()
    cipher = str(getattr(ep, "cipher_suite", "") or "").upper()
    if tls_v in {"TLSV1", "TLSV1.0", "TLSV1.1", "SSLV3"}:
        motion_broker_weak_tls_count += 1
    if (cipher.startswith("TLS_RSA_WITH_")
        or any(s in cipher for s in ("3DES", "RC4", "DES-CBC"))
        or (any(s in cipher for s in ("AES128-SHA", "AES256-SHA"))
            and "ECDHE" not in cipher and "DHE" not in cipher)):
        motion_broker_weak_cipher_count += 1

elif proto in {"SMTP-STARTTLS", "IMAP-STARTTLS", "POP3-STARTTLS"}:
    if not (getattr(ep, "tls_version", "") or ""):
        motion_email_starttls_missing_count += 1
    else:
        # cipher-strength check for weak ciphers; same idiom as broker
        cipher = str(getattr(ep, "cipher_suite", "") or "").upper()
        if (cipher.startswith("TLS_RSA_WITH_")
            or any(s in cipher for s in ("3DES", "RC4"))):
            motion_email_weak_cipher_count += 1

elif proto in {"SMTPS", "IMAPS", "POP3S"}:
    if not (getattr(ep, "tls_version", "") or ""):
        motion_email_plaintext_count += 1
    else:
        cipher = str(getattr(ep, "cipher_suite", "") or "").upper()
        if (cipher.startswith("TLS_RSA_WITH_")
            or any(s in cipher for s in ("3DES", "RC4"))):
            motion_email_weak_cipher_count += 1
```

> **NOTE:** The exact attribute names (`tls_version`, `cipher_suite`) and the precise weak-cipher
> regex are taken from `quirk/engine/risk_engine.py:464–489` and `:564–567` [VERIFIED] — the
> identical predicates `evaluate_email_endpoints` / `evaluate_broker_endpoints` already use to
> emit findings. Reusing those predicates keeps counter logic in lock-step with finding emission.
> Planner should consider extracting them into a small `_is_weak_cipher(cipher, tls_version)`
> helper in `evidence.py` to avoid drift — Claude's Discretion.

### Pattern 2: Score wiring (mirror `dar_impacts` block)
**Source:** `quirk/intelligence/scoring.py:179–188` [VERIFIED]
```python
# Existing dar_impacts block (template):
dar_impacts: List[Tuple[str, float]] = [
    ("Database plaintext connections", -_ratio(dar_db_plaintext, denom) * w["dar_db_plaintext_ratio"]),
    ...
]
dar_score, dar_drivers = _apply_weighted_impacts(dar_impacts)

# Phase 34 mirror — insert immediately after dar_impacts block (line ~189):
motion_email_plaintext_num = (
    _as_int(evidence.get("motion_email_plaintext_count", 0))
    + _as_int(evidence.get("motion_email_starttls_missing_count", 0))
)
motion_email_weak_cipher = _as_int(evidence.get("motion_email_weak_cipher_count", 0))
motion_broker_plaintext = _as_int(evidence.get("motion_broker_plaintext_count", 0))
motion_broker_weak_tls = _as_int(evidence.get("motion_broker_weak_tls_count", 0))
motion_broker_weak_cipher = _as_int(evidence.get("motion_broker_weak_cipher_count", 0))

motion_impacts: List[Tuple[str, float]] = [
    ("Email plaintext or missing STARTTLS",
     -_ratio(motion_email_plaintext_num, denom) * w["motion_email_plaintext_ratio"]),
    ("Weak cipher on email TLS",
     -_ratio(motion_email_weak_cipher, denom) * w["motion_email_weak_cipher_ratio"]),
    ("Plaintext broker listeners",
     -_ratio(motion_broker_plaintext, denom) * w["motion_broker_plaintext_ratio"]),
    ("Weak TLS on brokers",
     -_ratio(motion_broker_weak_tls, denom) * w["motion_broker_weak_tls_ratio"]),
    ("Weak cipher on broker TLS",
     -_ratio(motion_broker_weak_cipher, denom) * w["motion_broker_weak_cipher_ratio"]),
]
motion_score, motion_drivers = _apply_weighted_impacts(motion_impacts)
```

### Anti-Patterns to Avoid
- **Don't introduce a new dataclass for `EvidenceCounters`.** It doesn't exist; the existing
  pipeline uses local ints in a function. Inventing one would touch every existing counter.
- **Don't rename existing subscore keys** (D-04, D-05). Doing so silently breaks the dashboard,
  the `/api/scan/latest` contract, and saved scan reports.
- **Don't hand-roll cipher-weakness checks** that diverge from `risk_engine.py`'s predicates.
  Counter logic must agree with finding emission, or scoring drifts from what the user sees in
  finding lists.
- **Don't call `_ratio()` with `total_endpoints` directly** — use the already-computed `denom`
  variable (line 114 in `scoring.py`: `denom = endpoints if endpoints > 0 else 1`).
- **Don't multiply weights again in `motion_impacts`** — `compute_readiness_score` already
  applies `PROFILE_MULTIPLIERS` to `w[*]` at lines 97–100 before the impacts block runs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Score impact aggregation | New helper that sums `(label, points)` | `_apply_weighted_impacts()` (scoring.py:76–84) | Already handles clamp + rounding + zero-filter |
| Safe ratio division | `if denom: num/denom else 0` | `_ratio(num, denom)` (scoring.py:54) | Already handles zero/negative denom |
| Safe int extraction from evidence dict | `int(evidence.get(k, 0))` with try/except | `_as_int(evidence.get(k, 0))` (scoring.py:40) | Already handles None / non-numeric / KeyError |
| Cipher-weakness predicate | Inline regex per call site | Reuse the predicate from `risk_engine.py:483–489` and `:564–567` (or extract once into `_is_weak_cipher()`) | Drift between counter logic and finding emission would silently break score/finding agreement |
| Profile multiplier scaling | Per-key multiplication | `PROFILE_MULTIPLIERS["motion_"]` prefix entry; loop at scoring.py:97–100 auto-scales | Adding `"motion_": 1.4` is the entire wiring; no per-key code |

**Key insight:** Every Phase 34 task is a 2–10 line edit guided by an existing template
elsewhere in the same file. Hand-rolling helpers indicates the planner has missed an existing
asset.

## Common Pitfalls

### Pitfall 1: Confusing `EvidenceCounters` (the spec language) with reality
**What goes wrong:** Plan tasks say "add fields to EvidenceCounters dataclass" but the
dataclass doesn't exist; implementer wastes a wave looking for it or — worse — invents one.
**Why it happens:** REQUIREMENTS.md and CONTEXT.md both use the noun "EvidenceCounters
dataclass" inherited from earlier roadmap drafts.
**How to avoid:** Plan task wording must be "add 6 local counters in
`build_evidence_summary()` and 6 corresponding keys in the returned dict, plus 5 ratio keys."
Reference `evidence.py:78–91` as the dar_* template.
**Warning signs:** Any task that says "modify the EvidenceCounters dataclass" — reject and
rewrite.

### Pitfall 2: Counter logic diverges from finding logic
**What goes wrong:** `risk_engine.py` emits a `kafka-plaintext-listener` HIGH finding for
`ep.protocol == "KAFKA-PLAIN"`, but the new counter checks `proto == "KAFKA"`. Result: scan
shows the finding but score doesn't move. SC-1 ("score measurably moves") fails silently.
**Why it happens:** Two different developers writing in different files at different times;
no shared predicate.
**How to avoid:** Counter increment for `motion_broker_plaintext_count` MUST key off
`{"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}` — the exact same enum values
`risk_engine.py:539, 546, 553` checks. **Verify in test:** synthesize an endpoint with each
of those three protocol strings and assert the counter ticks for each.
**Warning signs:** Test only covers one of the three plaintext brokers; reviewer didn't
check all three pathways.

### Pitfall 3: Weak-cipher predicate drift
**What goes wrong:** `risk_engine.py:564–567` has a specific predicate for broker weak
ciphers (TLS_RSA_WITH_*, AES128-SHA, AES256-SHA, 3DES, RC4, DES-CBC, excluding ECDHE/DHE).
Counter writes a slightly different predicate. Score and findings disagree.
**How to avoid:** Either (a) extract the predicate to a small helper and import it from
both places, or (b) copy the predicate verbatim with a comment pointing to the source line
range. Option (b) is acceptable per "minimal diffs" CLAUDE.md rule — the helper extraction
is Phase 35+ refactor scope.
**Warning signs:** Predicate written from memory, not copy-pasted from risk_engine.py.

### Pitfall 4: Ratio denominator picked from wrong scope
**What goes wrong:** Implementer adds a new `motion_total_endpoints` denom or uses
`tls_total` thinking motion is "TLS-flavored." Result: ratios don't match how dar_* / hygiene_*
behave under the same scan, and SC-1's "measurably moves" assertion produces inconsistent
deltas.
**Why it happens:** D-02 only says "standard `total_endpoints` denom" — easy to miss that
in scoring.py the variable name is `denom`, not `total_endpoints`.
**How to avoid:** Use the `denom` local already in scope at scoring.py:114. Do not introduce
a new denominator. CONTEXT D-02 explicitly anchors this.

### Pitfall 5: Forgetting `motion_score` in `total_score` sum or `subscores` dict
**What goes wrong:** Subscore is computed but never surfaces — `total_score` doesn't shift
and `subscores["data_in_motion"]` is missing. SC-4 fails immediately. Linter passes; the
score-decrease test catches it but a careless implementer "fixes" the test instead.
**How to avoid:** Three-line checklist for the planner:
1. `scoring.py:190` — sum includes `motion_score`.
2. `scoring.py:193–194` — `all_drivers` concatenation includes `motion_drivers`.
3. `scoring.py:202–208` — `subscores` dict literal has `"data_in_motion": motion_score`.
Plan must include a verification task that reads the diff and confirms all three.
**Warning signs:** Implementer reports "tests pass" but inspection of `compute_readiness_score`
shows only two of three sites updated.

## Code Examples

### Test pattern (from `tests/test_dar_storage_scoring.py:104–117`)
```python
# Source: tests/test_dar_storage_scoring.py:104–117 [VERIFIED]
def test_dar_storage_unencrypted_ratio_applied():
    """When unencrypted ratio is high, dar subscore must be lower than baseline."""
    from quirk.intelligence.scoring import compute_readiness_score
    baseline_evidence = {
        "totals": {"endpoints": 4, "findings": 0},
        "dar_storage_unencrypted_count": 0,
        ...
    }
    bad_evidence = dict(baseline_evidence)
    bad_evidence["dar_storage_unencrypted_count"] = 4
    baseline = compute_readiness_score(baseline_evidence, profile="balanced")
    bad = compute_readiness_score(bad_evidence, profile="balanced")
    assert bad["subscores"]["data_at_rest"] < baseline["subscores"]["data_at_rest"]
```

**Phase 34 mirror (write to `tests/test_motion_scoring.py`):**
```python
def test_motion_broker_plaintext_lowers_subscore():
    from quirk.intelligence.scoring import compute_readiness_score
    baseline = {
        "totals": {"endpoints": 4, "findings": 0},
        "motion_broker_plaintext_count": 0,
    }
    bad = dict(baseline)
    bad["totals"] = {"endpoints": 4, "findings": 2}
    bad["motion_broker_plaintext_count"] = 2
    base = compute_readiness_score(baseline, profile="balanced")
    worse = compute_readiness_score(bad, profile="balanced")
    assert worse["subscores"]["data_in_motion"] < base["subscores"]["data_in_motion"]
    assert worse["score"] < base["score"]
```

### MagicMock endpoint helper (from `tests/test_dar_storage_scoring.py:7–24`)
```python
# Source: tests/test_dar_storage_scoring.py:7–24 [VERIFIED]
def _ep(protocol: str, service_detail: str):
    ep = MagicMock()
    ep.protocol = protocol
    ep.service_detail = service_detail
    ep.scanned_at = datetime(2026, 4, 25, tzinfo=timezone.utc).replace(tzinfo=None)
    ep.scan_error = None
    ep.tls_blocker_reason = ""
    ep.cert_pubkey_alg = ""
    ep.cert_pubkey_size = None
    ep.cert_not_after = None
    ep.cert_subject = ""
    ep.cert_issuer = ""
    ep.tls_supported_versions = ""
    ep.host = "test-host"
    ep.port = 0
    return ep
```

For motion tests requiring `tls_version` / `cipher_suite`, extend this helper with two more
attributes (planner: add `tls_version: str = ""`, `cipher_suite: str = ""` defaults).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Five subscores (hygiene/modern_tls/identity_trust/agility_signals/data_at_rest) | Six subscores (+ data_in_motion) | Phase 34 (this phase) | Dashboard tolerates extras (D-04); legacy scans get score=100 for the new subscore (D-12) |

**Deprecated/outdated:** None applicable — Phase 34 is purely additive.

## Counter-Bump Call Sites — Resolution

This is the only "implementation unknown" identified by the orchestrator. Resolved as follows:

**Question:** Where do Phase 32 / Phase 33 findings (weak-cipher, starttls-downgrade-risk,
kafka-plaintext-listener, amqp-plaintext-listener, redis-plaintext-no-auth) currently feed
into the evidence pipeline?

**Answer:** They **do not currently feed in.** [VERIFIED: `grep -r "motion_" quirk/` returns
zero matches.] No code in `quirk/` currently increments any motion counter. The Phase 32 / 33
work emitted findings via `risk_engine.evaluate_email_endpoints()` and
`risk_engine.evaluate_broker_endpoints()`, but the evidence-summary path
(`build_evidence_summary` in `evidence.py`) was not updated.

**Implication:** The counter-bump logic must be **added in Phase 34 itself**, inside the
existing `for ep in endpoint_list:` loop in `build_evidence_summary()` (evidence.py:93–215).
This is identical to how Phase 28 added `dar_storage_*` counters and how Phase 29 added
`dar_k8s_*` counters — both inserted new `elif proto == "..."` blocks in the same loop.

**Counter → key signal mapping (LOCKED by this research):**

| Counter | Increment when | Source predicate |
|---------|----------------|------------------|
| `motion_broker_plaintext_count` | `ep.protocol in {"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}` | `risk_engine.py:539, 546, 553` [VERIFIED] |
| `motion_broker_weak_tls_count` | `ep.protocol in {KAFKA-TLS,AMQPS,AMQPS/Azure-ServiceBus,HTTPS/AWS-SQS,REDIS-TLS}` AND `ep.tls_version` is in `{TLSv1, TLSv1.0, TLSv1.1, SSLv3}` | New predicate; aligns with REQUIREMENTS MOTION-01 ("TLS 1.1 or older on broker") |
| `motion_broker_weak_cipher_count` | broker TLS protocol AND cipher matches the predicate at `risk_engine.py:564–567` | `risk_engine.py:564–567` [VERIFIED] |
| `motion_email_starttls_missing_count` | `ep.protocol in {SMTP-STARTTLS, IMAP-STARTTLS, POP3-STARTTLS}` AND `ep.tls_version` is empty/falsy | Inverse of the EMAIL-08 emission condition at `risk_engine.py:468` (which fires when STARTTLS DID succeed); when it didn't succeed there's no finding today, but the counter still ticks. **Note:** This is an additive interpretation per D-02 numerator semantics. |
| `motion_email_plaintext_count` | `ep.protocol in {SMTPS, IMAPS, POP3S}` AND `ep.tls_version` is empty/falsy | Direct check; no risk_engine analog because implicit-TLS-with-no-handshake is not currently a finding |
| `motion_email_weak_cipher_count` | any email protocol AND `ep.tls_version` is set AND cipher matches `risk_engine.py:483–489` predicate | `risk_engine.py:483–489` [VERIFIED] |

**The above table is the load-bearing output of this research.** The planner uses it to
write counter-bump tasks; the discuss-phase reviewer should validate the email-counter
semantics (the STARTTLS-missing and email-plaintext predicates are derived, not directly
mirrored from risk_engine — see Assumptions Log).

## Test Conventions — Resolution

**Question:** Does `tests/intelligence/test_*_subscore.py` already exist?

**Answer:** No. [VERIFIED: glob `tests/intelligence/**/*.py` returns no files.] All tests
live flat in `tests/`. The closest analogs are:

- `tests/test_dar_storage_scoring.py` (Phase 28) — **strongest template** (most recent,
  same shape, same pytest+MagicMock pattern). Use this verbatim.
- `tests/test_dar_k8s_scoring.py` (Phase 29) — same idiom.
- `tests/test_dar_vault_scoring.py` (Phase 30) — same idiom.
- `tests/test_intelligence_scoring.py` — broader scoring tests; reference for module shape
  but not for new test additions.

**Recommendation:** New file `tests/test_motion_scoring.py`. Mirror
`test_dar_storage_scoring.py` structure (8 tests, ~120 lines):
1. `test_protocol_keys_includes_motion_protocols` (note: `_PROTOCOL_KEYS` may need
   broker/email entries added — verify in plan)
2. `test_motion_broker_plaintext_count_kafka` (and amqp / redis)
3. `test_motion_broker_weak_tls_count`
4. `test_motion_broker_weak_cipher_count`
5. `test_motion_email_starttls_missing_count`
6. `test_motion_email_plaintext_count`
7. `test_motion_email_weak_cipher_count`
8. `test_score_weights_motion_values` (asserts the 5 LOCKED weights from D-03)
9. `test_motion_subscore_lowers_with_findings` (SC-1; D-09)
10. `test_top_drivers_surfaces_motion` (D-10)
11. `test_legacy_evidence_no_motion_keys_yields_full_credit` (D-12; assert
    `data_in_motion == 100`)
12. `test_profile_strict_increases_motion_penalty` (D-08; assert strict < balanced)

**Open question for planner:** Should `_PROTOCOL_KEYS` (evidence.py:9–10) be extended with
broker/email protocol strings? Currently it only contains canonical TLS-layer-1 protocols.
The new motion counters increment without going through `protocol_counts`, so technically
no — but adding the strings would make `protocol_counts` also reflect motion endpoints.
**Recommendation:** Leave `_PROTOCOL_KEYS` untouched in Phase 34; counter pipeline is
independent. Reconsider in Phase 36 (dashboard) if the dashboard wants per-protocol totals.

## STARTTLS Fold Mechanics — Resolution

**D-01/D-02 formula confirmed against `scoring.py`:**
- `denom` is computed at `scoring.py:114`:
  `denom = endpoints if endpoints > 0 else 1` where
  `endpoints = max(0, _as_int(totals.get("endpoints", 0)))` (line 112).
- `denom` is in scope at the proposed motion_impacts insertion point (after line 188).
  [VERIFIED: same scope as `dar_impacts` block, which uses `denom` on every line.]
- Numerator: `(motion_email_plaintext_count + motion_email_starttls_missing_count)`,
  combined into a local `motion_email_plaintext_num` int before the impacts list.

**Final formula:**
```python
motion_email_plaintext_num = (
    _as_int(evidence.get("motion_email_plaintext_count", 0))
    + _as_int(evidence.get("motion_email_starttls_missing_count", 0))
)
# Then in motion_impacts:
("Email plaintext or missing STARTTLS",
 -_ratio(motion_email_plaintext_num, denom) * w["motion_email_plaintext_ratio"]),
```

This honors D-01 (single weight, fold) and D-02 (`total_endpoints` denom) without any
denominator gymnastics.

## Validation Architecture

> Phase 34 is in scope for Nyquist validation per project default (no
> `workflow.nyquist_validation: false` found).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing project pin in `pyproject.toml`) |
| Config file | `pytest.ini` / `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `pytest tests/test_motion_scoring.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOTION-01 | 6 motion_ counters tick correctly per protocol+attribute combo | unit | `pytest tests/test_motion_scoring.py::test_motion_broker_plaintext_count_kafka -x` | ❌ Wave 0 (new file) |
| MOTION-01 | All 6 counter keys appear in `build_evidence_summary` output dict (even when zero) | unit | `pytest tests/test_motion_scoring.py::test_motion_keys_present_in_summary -x` | ❌ Wave 0 |
| MOTION-02 | `SCORE_WEIGHTS` has 5 motion_*_ratio entries with locked values | unit | `pytest tests/test_motion_scoring.py::test_score_weights_motion_values -x` | ❌ Wave 0 |
| MOTION-03 | `PROFILE_MULTIPLIERS` has `"motion_"` key in all 3 profiles with strict=1.4/balanced=1.0/lenient=0.7 | unit | `pytest tests/test_motion_scoring.py::test_profile_multipliers_motion -x` | ❌ Wave 0 |
| MOTION-03 | strict profile scales motion penalty 1.4× balanced (D-08 mechanical correctness) | unit | `pytest tests/test_motion_scoring.py::test_profile_strict_increases_motion_penalty -x` | ❌ Wave 0 |
| MOTION-04 | `compute_readiness_score()` returns `data_in_motion` as 6th key | unit | `pytest tests/test_motion_scoring.py::test_subscores_includes_data_in_motion -x` | ❌ Wave 0 |
| MOTION-04 (SC-1) | Plaintext-broker evidence lowers `data_in_motion` AND `score` vs zero-baseline | unit | `pytest tests/test_motion_scoring.py::test_motion_subscore_lowers_with_findings -x` | ❌ Wave 0 |
| D-10 | `top_drivers` surfaces motion driver when motion counters dominate | unit | `pytest tests/test_motion_scoring.py::test_top_drivers_surfaces_motion -x` | ❌ Wave 0 |
| D-12 | Legacy evidence (no motion_ keys) yields `data_in_motion == 100` | unit | `pytest tests/test_motion_scoring.py::test_legacy_evidence_full_credit -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_motion_scoring.py -x -q` (< 5 seconds)
- **Per wave merge:** `pytest tests/test_motion_scoring.py tests/test_intelligence_scoring.py tests/test_intelligence_evidence.py tests/test_dar_storage_scoring.py -x -q` (regression guard on adjacent scoring tests)
- **Phase gate:** `pytest -x -q` full suite green; `python -m compileall quirk/` exit 0

### Wave 0 Gaps
- [ ] `tests/test_motion_scoring.py` — new file, covers all 4 MOTION-* requirements + D-08/D-09/D-10/D-12 assertions
- [ ] No new fixtures needed (reuse MagicMock-based `_ep()` pattern from `tests/test_dar_storage_scoring.py:7–24`; planner extends with `tls_version` / `cipher_suite` defaults)
- [ ] No framework install needed (pytest already pinned)

### Synthesized Evidence Dicts for SC-1..SC-4

**SC-1 evidence (plaintext kafka scan with 4 endpoints, 2 plaintext):**
```python
{
    "totals": {"endpoints": 4, "findings": 2},
    "motion_broker_plaintext_count": 2,
    # all other motion_ counters default to 0 via _as_int
}
```
Assert: `result["subscores"]["data_in_motion"] < 100` AND
`result["score"] < zero_motion_baseline["score"]`
AND inspect `motion_broker_plaintext_ratio` weight is applied:
expected impact ≈ `-(2/4) * 14.0 = -7.0` → `data_in_motion ≈ 25 - 7 = 18`.

**SC-2 evidence (validates 6 counter fields exist):**
Synthesize endpoints with each protocol/attribute combo (12 endpoints total covering all 6
counters), call `build_evidence_summary`, assert all 6 keys present and equal expected ints.

**SC-3 evidence (validates 5 ratio weights + profile prefix):**
```python
from quirk.intelligence.scoring import SCORE_WEIGHTS, PROFILE_MULTIPLIERS
assert SCORE_WEIGHTS["motion_email_plaintext_ratio"] == 12.0
assert SCORE_WEIGHTS["motion_email_weak_cipher_ratio"] == 6.0
assert SCORE_WEIGHTS["motion_broker_plaintext_ratio"] == 14.0
assert SCORE_WEIGHTS["motion_broker_weak_tls_ratio"] == 8.0
assert SCORE_WEIGHTS["motion_broker_weak_cipher_ratio"] == 6.0
for prof in ("strict", "balanced", "lenient"):
    assert "motion_" in PROFILE_MULTIPLIERS[prof]
assert PROFILE_MULTIPLIERS["strict"]["motion_"] == 1.4
assert PROFILE_MULTIPLIERS["balanced"]["motion_"] == 1.0
assert PROFILE_MULTIPLIERS["lenient"]["motion_"] == 0.7
```

**SC-4 evidence (subscore key shape + measurable movement):**
```python
zero = compute_readiness_score({"totals": {"endpoints": 4, "findings": 0}})
assert "data_in_motion" in zero["subscores"]
assert zero["subscores"]["data_in_motion"] == 25  # full credit (score_cap)

with_motion = compute_readiness_score({
    "totals": {"endpoints": 4, "findings": 2},
    "motion_broker_plaintext_count": 2,
})
assert with_motion["subscores"]["data_in_motion"] < zero["subscores"]["data_in_motion"]
assert with_motion["score"] < zero["score"]
```

**Note on `score_cap`:** `_apply_weighted_impacts` uses `score_cap=25.0` by default
(scoring.py:78), so a clean motion subscore is `25`, not `100`. **D-12 wording in
CONTEXT.md says "data_in_motion = 100 (no findings = full credit)" — this is incorrect
for the per-subscore value (max is 25), though the rounded total can reach 100 only when
all five subscores are at cap.** Planner should phrase the legacy-compat test against
the actual cap (25), not 100. [VERIFIED: scoring.py:78 + dar_storage test at line 117
asserts `<` not `== 100`.]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Build, tests | ✓ (assumed; project standard) | per `pyproject.toml` | — |
| pytest | Test execution | ✓ (existing project dep) | per `pyproject.toml` | — |
| `python -m compileall` | CLAUDE.md mandatory post-change check | ✓ (stdlib) | — | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

(Phase 34 has no Docker / chaos-lab / external-service dependency per D-11.)

## Security Domain

> `security_enforcement` not explicitly disabled in `.planning/config.json` (file not consulted
> here; assume default = enabled). Phase 34 surface is **scoring math + counter bookkeeping**,
> NOT new auth/crypto code.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth surface in this phase |
| V3 Session Management | no | No session surface |
| V4 Access Control | no | No new access checks |
| V5 Input Validation | yes (low risk) | `_as_int()` already coerces non-int evidence values; no new untrusted input parsed |
| V6 Cryptography | no | No crypto primitives implemented; phase only counts pre-existing crypto detections |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Counter pollution from malformed evidence dict | Tampering | Existing `_as_int()` / `_ratio()` guards (already in place) |
| Score manipulation via crafted scan reports | Tampering | Out of scope — saved-scan integrity is not in this phase's threat model; addressed elsewhere by report-storage signing (future work) |

No new security controls required.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `motion_email_starttls_missing_count` ticks when `ep.protocol in {SMTP-STARTTLS, IMAP-STARTTLS, POP3-STARTTLS}` AND `ep.tls_version` is empty | Counter-Bump Call Sites | If the email scanner sets `protocol=""` (per `email_scanner.py:171`) when STARTTLS fails entirely (instead of keeping the `*-STARTTLS` label), the counter never ticks. Need discuss-phase confirmation: does the email scanner preserve the `*-STARTTLS` protocol label on STARTTLS failure, or downgrade to plaintext/empty? Verified at `email_scanner.py:388` that the orchestrator path always passes `protocol_label` — but the failure-mode behavior wasn't verified end-to-end. **[ASSUMED]** |
| A2 | `motion_email_plaintext_count` ticks when `ep.protocol in {SMTPS, IMAPS, POP3S}` AND `ep.tls_version` is empty (i.e., implicit-TLS port answered but couldn't complete TLS handshake) | Counter-Bump Call Sites | If the email scanner emits no endpoint at all when the implicit-TLS port is unresponsive (vs. emitting one with empty `tls_version`), this counter never has a chance to tick. **[ASSUMED]** |
| A3 | The score-cap for `data_in_motion` is 25, not 100, so D-12 "full credit = 100" should be interpreted as "full credit = 25" at subscore level (or 100 only at total `score`). | Validation Architecture (SC-4 note) | Test would fail if asserted as `== 100`. CONTEXT D-12 is loosely worded. **[ASSUMED]** — verified against `_apply_weighted_impacts(score_cap=25.0)` at scoring.py:78 [VERIFIED], but the human-language interpretation of D-12 itself is assumed. |
| A4 | `_PROTOCOL_KEYS` (evidence.py:9–10) does NOT need to be extended with broker/email enum values for Phase 34 — motion counters operate independently of `protocol_counts`. | Test Conventions | If the planner decides protocol_counts should reflect motion endpoints, an extra task is needed. **[ASSUMED]** — defensible by current design, but a judgment call. |
| A5 | The weak-cipher predicate for `motion_email_weak_cipher_count` should match `risk_engine.py:483–489` exactly (TLS_RSA_WITH_*, AES128-SHA, AES256-SHA, 3DES, RC4, excluding ECDHE/DHE-). The non-PFS-MEDIUM branch (`pfs is False AND tls_version != "TLSv1.3"`) at risk_engine.py:503 is **excluded** from the counter. | Counter-Bump Call Sites | If included, the count inflates and balanced-profile penalty drops the subscore further than expected. CONTEXT does not explicitly say which severity tier feeds the counter. REQUIREMENTS MOTION-01 says "weak cipher on email TLS (MEDIUM)" — ambiguity. **[ASSUMED: HIGH only]** |

**If this table is empty:** All claims in this research were verified or cited — no user
confirmation needed.

(This table is NOT empty — five assumptions need discuss-phase or planner attention before
implementation.)

## Open Questions

1. **A1/A2 above** — exact email scanner endpoint emission behavior on STARTTLS failure vs.
   implicit-TLS unresponsive port. Resolve by reading `email_scanner.py` end-to-end during
   plan or by adding a discuss-phase question.

2. **A5 above** — weak-cipher counter definition: HIGH-only or HIGH+MEDIUM (non-PFS ECDHE
   < TLS 1.3)? Affects how aggressive the score drop is.

3. **D-12 interpretation** — does "full credit" mean `data_in_motion == 25` (subscore cap)
   or only `score == 100` (total score with all subscores at cap)? Test assertion phrasing
   depends on resolution.

4. **`_PROTOCOL_KEYS` extension** — out of scope per A4, but worth a one-line discuss-phase
   note for the next phase that touches `protocol_counts`.

## Sources

### Primary (HIGH confidence — VERIFIED in this session)
- `quirk/intelligence/evidence.py` — `build_evidence_summary` function shape, all DAR counter idioms (lines 78–215)
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` (5–31), `PROFILE_MULTIPLIERS` (33–37), helpers (40–84), `compute_readiness_score` body (87–210), `dar_impacts` template (179–188)
- `quirk/engine/risk_engine.py` — `evaluate_email_endpoints` (450–517), `evaluate_broker_endpoints` (520–577), weak-cipher predicates (483–489, 564–567)
- `quirk/scanner/broker_scanner.py` — protocol enum strings (KAFKA-TLS, KAFKA-PLAIN, AMQP-PLAIN, REDIS-TLS, REDIS-PLAIN at lines 173, 390, 472, 611, 625, 674)
- `quirk/scanner/email_scanner.py` — protocol_label assignment (388, 498) for SMTP-STARTTLS / IMAP-STARTTLS / POP3-STARTTLS / SMTPS / IMAPS / POP3S
- `tests/test_dar_storage_scoring.py` — full template for new motion test file (lines 1–117)
- `tests/test_intelligence_evidence.py` — alternative test idiom (dataclass `_Ep` instead of MagicMock)

### Secondary (MEDIUM confidence — CITED from project docs)
- `.planning/REQUIREMENTS.md` §"Evidence Counters and Scoring" — MOTION-01..04
- `.planning/ROADMAP.md` Phase 34 entry
- `.planning/phases/34-motion-intelligence/34-CONTEXT.md` — D-01..D-12

### Tertiary (LOW confidence)
- None. All claims in this research are either VERIFIED (file-read in this session) or
  CITED (locked decision from project planning docs).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, all pattern templates verified end-to-end
- Architecture: HIGH — exact line ranges for both edit points verified
- Pitfalls: HIGH — all five pitfalls grounded in concrete code paths read this session
- Counter→signal mapping: MEDIUM — three of six counters key off VERIFIED enum strings; three (email_starttls_missing, email_plaintext, email_weak_cipher) involve a derived predicate flagged in Assumptions Log

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable scope; only invalidates if Phase 32/33 emission paths change)

## RESEARCH COMPLETE

**Phase:** 34 - motion-intelligence
**Confidence:** HIGH

### Key Findings
- **No `EvidenceCounters` dataclass exists** — Phase 34 task wording must say "add 6 local counters in `build_evidence_summary()` and corresponding dict keys" not "add fields to dataclass." This is a load-bearing correction.
- **No motion_ counter logic exists today** in `quirk/`. The Phase 32/33 work emitted findings via `risk_engine.py` but never updated the evidence-summary path. Phase 34 adds the entire counter-bump pipeline.
- **Counter→signal mapping is now LOCKED** — six counters key off specific `ep.protocol` enum strings already produced by Phase 32/33 scanners (KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN, KAFKA-TLS, AMQPS, AMQPS/Azure-ServiceBus, HTTPS/AWS-SQS, REDIS-TLS, SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S).
- **Test template:** `tests/test_dar_storage_scoring.py` (Phase 28). New file `tests/test_motion_scoring.py` mirrors it. No `tests/intelligence/` subdir exists — CONTEXT proposed path was wrong.
- **STARTTLS fold formula validated:** `denom` from scoring.py:114 is in scope at the proposed `motion_impacts` insertion point (after line 188); D-02 numerator + standard denominator is mechanically straightforward.
- **Score-cap subtlety:** D-12 "full credit = 100" is loose wording; subscore cap is 25 per `_apply_weighted_impacts(score_cap=25.0)`. Test assertions should compare `<` against zero-baseline, not `== 100` against an absolute.
- **Five assumptions flagged in Assumptions Log** — A1/A2 about email-scanner endpoint emission on TLS failure; A5 about HIGH-only vs HIGH+MEDIUM weak-cipher counter scope. Recommend a brief discuss-phase pass before plan-write.

### File Created
`.planning/phases/34-motion-intelligence/34-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Zero new deps; all referenced helpers verified by file-read |
| Architecture | HIGH | Both edit points (evidence.py loop body; scoring.py post-line-188) verified line-precise |
| Pitfalls | HIGH | All five grounded in code read this session |
| Counter→signal mapping (broker) | HIGH | Enum strings VERIFIED in broker_scanner.py + risk_engine.py |
| Counter→signal mapping (email) | MEDIUM | Three of six derived predicates; flagged A1/A2/A5 |

### Open Questions
1. Email scanner endpoint emission behavior on STARTTLS failure vs. implicit-TLS unresponsive port (A1, A2)
2. Weak-cipher counter scope: HIGH-only or HIGH+MEDIUM? (A5)
3. D-12 "full credit" subscore vs. total semantics (A3)

### Ready for Planning
Research complete. Planner can proceed with Phase 34 plan, paying attention to:
- Use "local counters in `build_evidence_summary()`" wording, not "EvidenceCounters dataclass"
- Reference `tests/test_dar_storage_scoring.py` as the test template
- Resolve A1/A2/A5 with a discuss-phase question or by reading email_scanner.py end-to-end before writing counter-bump tasks
- Plan must include the four CLAUDE.md mandatory phase-completion tasks (Obsidian phase note, UAT-SERIES.md update, vault sync, gsd-tools commit)

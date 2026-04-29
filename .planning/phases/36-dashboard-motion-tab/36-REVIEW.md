---
phase: 36-dashboard-motion-tab
reviewed: 2026-04-28T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - quirk/dashboard/api/schemas.py
  - quirk/dashboard/api/routes/scan.py
  - tests/test_dashboard_api.py
  - src/dashboard/src/types/api.ts
  - src/dashboard/src/pages/executive.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/App.tsx
  - src/dashboard/src/pages/motion.tsx
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: needs-fix
---

# Phase 36: Code Review Report

**Reviewed:** 2026-04-28
**Depth:** standard
**Files Reviewed:** 8
**Status:** needs-fix

## Summary

Phase 36 delivers the backend `_derive_motion_findings` derivation function, the `MotionFinding`
Pydantic model, `SubScores.data_in_motion`, the TypeScript contract mirrors, the sixth Executive
ScoreGauge, the Motion sidebar entry, the `/motion` route, and the new `MotionPage` component.
The implementation is broadly correct and the critical "Pitfall 1" (silent subscore drop) has been
fixed. One critical bug was found: `scan.py` shadows its `scan_id` query-parameter variable at line
700, which on every `GET /api/scan/latest` (no `?scan_id=`) call causes the response `meta.scan_id`
to silently overwrite the function parameter — while this is harmless today, the re-assignment is
a real variable-shadowing bug that will break any future code that reads `scan_id` after line 700
inside the same function. Four warnings cover a TS/Pydantic contract mismatch for `ConfidenceData`,
a missing broker-protocol filter on the frontend for `HTTPS/AWS-SQS`, an incomplete confidence
label fallback on the Executive page, and a `starttls_warning=True` finding that never gets a
severity of `MEDIUM` for email-protocol endpoints because the severity rule is only applied when
`proto in BROKER_TLS`. Three info-level nits round out the review.

---

## Critical Issues

### CR-01: Variable shadowing — `scan_id` query param overwritten at line 700

**File:** `quirk/dashboard/api/routes/scan.py:700`

**Issue:** The function signature at line 555 declares `scan_id: Optional[str]` as the incoming
query parameter. At line 700, deep inside the same function body, the code unconditionally
reassigns the local name `scan_id`:

```python
scan_id = latest_ts.isoformat() if hasattr(latest_ts, "isoformat") else str(latest_ts)
```

This means from line 700 onwards the original query-parameter value is lost.  If any future code
path reads `scan_id` after that assignment (e.g. for a second conditional, an audit log, or a
cache key) it will silently receive the *derived* timestamp string rather than the user-supplied
value.  The current code happens to work only because `scan_id` is not read again after line 700,
but static analysers (mypy, pylance) flag this as shadowing, and it is a latent correctness trap.

**Fix:** Use a distinct variable name for the derived value:

```python
# line 700 — rename to avoid shadowing the query parameter
response_scan_id = latest_ts.isoformat() if hasattr(latest_ts, "isoformat") else str(latest_ts)

return ScanLatestResponse(
    meta=ScanMeta(
        scan_id=response_scan_id,   # was: scan_id
        ...
    ),
    ...
)
```

---

## Warnings

### WR-01: TS `ConfidenceData` declares `factor_breakdown` but Pydantic does not; API contract drift

**File:** `src/dashboard/src/types/api.ts:20` / `quirk/dashboard/api/schemas.py:36-39`

**Issue:** The TypeScript `ConfidenceData` interface declares a third field:

```ts
export interface ConfidenceData {
  confidence_score: number
  confidence_rating: string
  factor_breakdown: Record<string, unknown>   // line 20
}
```

The Pydantic model only exposes two fields:

```python
class ConfidenceData(BaseModel):
    confidence_score: int
    confidence_rating: str
    # factor_breakdown is NOT declared here
```

The FastAPI response will never serialise `factor_breakdown` (Pydantic filters by model fields),
so the frontend will always receive `undefined` for that property.  Any frontend code that tries to
read `data.confidence.factor_breakdown` will silently get `undefined` rather than a type error,
which can produce unexpected runtime behaviour.  This is not a Phase 36 regression — the mismatch
pre-dates this phase — but it is visible in the files under review and should be resolved.

**Fix (choose one):**
- Add `factor_breakdown: Optional[Dict[str, Any]] = None` to the Pydantic `ConfidenceData` model and populate it from `confidence_raw.get("factor_breakdown", {})` in `scan.py:677`; OR
- Remove `factor_breakdown` from the TypeScript interface if it is never consumed.

---

### WR-02: `HTTPS/AWS-SQS` protocol rendered in neither Email nor Broker table on the Motion page

**File:** `src/dashboard/src/pages/motion.tsx:27-31`

**Issue:** The backend `BROKER_TLS` set includes `"HTTPS/AWS-SQS"` (scan.py line 344).
`getBrokerFamily` in motion.tsx classifies protocols by prefix:

```ts
if (protocol.startsWith("KAFKA-")) return "Kafka"
if (protocol.startsWith("AMQP-") || protocol.startsWith("AMQPS")) return "AMQP"
if (protocol.startsWith("REDIS-")) return "Redis"
return null   // <-- HTTPS/AWS-SQS falls here
```

`"HTTPS/AWS-SQS"` starts with `"HTTPS"`, which matches none of those branches, so it returns
`null`.  It is also not in `EMAIL_PROTOS`.  Therefore any `HTTPS/AWS-SQS` `MotionFinding` is
silently dropped from both the Email table and the Broker grouped sections — the user sees nothing
for AWS SQS endpoints even though the backend correctly detected and scored them.

**Fix:** Add an `"HTTPS"` / AWS prefix branch in `getBrokerFamily`:

```ts
export function getBrokerFamily(protocol: string): "Kafka" | "AMQP" | "Redis" | "Cloud" | null {
  if (protocol.startsWith("KAFKA-")) return "Kafka"
  if (protocol.startsWith("AMQP-") || protocol.startsWith("AMQPS")) return "AMQP"
  if (protocol.startsWith("REDIS-")) return "Redis"
  if (protocol.startsWith("HTTPS/")) return "Cloud"   // HTTPS/AWS-SQS etc.
  return null
}
```

Then add a `"Cloud"` section (or fold into an existing broker group) in `BrokerGroupedSections`.

---

### WR-03: `VERY_LOW` and `NO_DATA` confidence ratings silently fall through to "Low Confidence" label

**File:** `src/dashboard/src/pages/executive.tsx:140-143`

**Issue:** The confidence badge label chain covers only `HIGH`, `MEDIUM`, and `LOW`; the final
`else` arm maps both `VERY_LOW` and `NO_DATA` to the string `"Low Confidence"`:

```tsx
{confidence.confidence_rating === "HIGH" ? "High Confidence"
  : confidence.confidence_rating === "MEDIUM" ? "Medium Confidence"
  : confidence.confidence_rating === "LOW" ? "Low Confidence"
  : "Low Confidence"}   // VERY_LOW and NO_DATA land here
```

The badge variant is set correctly (`"destructive"` for `VERY_LOW`, `"outline"` for `NO_DATA` via
`CONFIDENCE_BADGE_VARIANT`), but the displayed text is wrong.  A `VERY_LOW` badge will appear as
orange/red ("destructive" variant) but say "Low Confidence", and a `NO_DATA` badge will say "Low
Confidence" instead of "No Data".

**Fix:**

```tsx
{confidence.confidence_rating === "HIGH" ? "High Confidence"
  : confidence.confidence_rating === "MEDIUM" ? "Medium Confidence"
  : confidence.confidence_rating === "LOW" ? "Low Confidence"
  : confidence.confidence_rating === "VERY_LOW" ? "Very Low Confidence"
  : "No Data"}
```

---

### WR-04: `_derive_motion_findings` processes `SMTP-STARTTLS` on port 587 and assigns `starttls_warning=False` but severity defaults to `LOW` — missing `description` and `remediation` for email TLS findings

**File:** `quirk/dashboard/api/routes/scan.py:363-394`

**Issue:** For email-protocol endpoints that are not plaintext and do not match the STARTTLS port-25
rule and are not in `BROKER_TLS`, the code falls to the `else` branch and creates a `MotionFinding`
with `severity="LOW"` and `title=f"{proto} TLS endpoint"` — but `description` and `remediation`
are never populated (they remain `None`).  `MotionFinding.description` and `MotionFinding.remediation`
are both `Optional[str]` in the schema, so this is not a crash, but the Findings table will show
blank description and remediation columns for every healthy email TLS endpoint.  `IdentityFinding`
and `FindingItem` both set description/remediation on every finding; the new function is
inconsistent with that established pattern.

**Fix:** Populate `description` and `remediation` in the `else` branch:

```python
else:
    severity = "LOW"
    title = f"{proto} TLS endpoint"
    quantum_risk = "quantum-vulnerable" if cipher_suite and "RSA" in cipher_suite else "quantum-unknown"
    description = f"{proto} is using TLS. Verify cipher suite and certificate strength."
    remediation = "Enforce TLS 1.2+, disable weak ciphers, and plan PQC migration."
```

And pass them to the `MotionFinding(...)` constructor (which currently omits `description=` and
`remediation=` entirely on all branches).

---

## Info

### IN-01: `_derive_motion_findings` protocol sets defined inside the function on every call

**File:** `quirk/dashboard/api/routes/scan.py:341-347`

**Issue:** `EMAIL_PROTOS`, `BROKER_PLAIN`, `BROKER_TLS`, `MOTION_PROTOS`, and `LEGACY_TLS` are
module-level `set` literals in the analogous `_derive_findings` / `_derive_identity_findings`
function bodies, but here they are allocated fresh on every invocation.  For a request-handling
path these sets are small so it is not a performance concern (out of v1 scope), but it is
inconsistent with the "constant" idiom used in the same file and in `_derive_identity_findings`
(which uses `_DNSSEC_WEAK_MAP` and `_severity_order` as module-level dicts).  PEP 8 convention
prefers module-level constants for values that do not change between calls.

**Fix:** Hoist the sets to module level:

```python
_MOTION_EMAIL_PROTOS = {"SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS", "IMAPS", "POP3-STARTTLS", "POP3S"}
_MOTION_BROKER_PLAIN = {"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"}
_MOTION_BROKER_TLS   = {"KAFKA-TLS", "AMQPS", "AMQPS/Azure-ServiceBus", "HTTPS/AWS-SQS", "REDIS-TLS"}
_MOTION_PROTOS       = _MOTION_EMAIL_PROTOS | _MOTION_BROKER_PLAIN | _MOTION_BROKER_TLS
_MOTION_LEGACY_TLS   = {"TLSv1", "TLSv1.0", "TLSv1.1"}
```

---

### IN-02: `from types import SimpleNamespace` import is mid-file in test module

**File:** `tests/test_dashboard_api.py:97`

**Issue:** PEP 8 requires all imports at the top of the module.  The `from types import
SimpleNamespace` import appears at line 97, between test functions.  This does not affect
correctness but violates the project's PEP 8 requirement stated in CLAUDE.md.

**Fix:** Move `from types import SimpleNamespace` to the top of the file alongside the other
stdlib imports (`subprocess`, `sys`).

---

### IN-03: `_import_as` guard on `quirk.cbom.classifier` in hot path re-imports on every finding

**File:** `quirk/dashboard/api/routes/scan.py:160`

**Issue:** Within `_derive_findings`, for every non-RSA endpoint the code executes a bare
`from quirk.cbom.classifier import classify_algorithm, quantum_safety_label` inside a `try`
block on line 160.  Python caches modules in `sys.modules` so this is effectively free after the
first call, but the pattern is inconsistent with all other callsites in the same file, where the
same imports are done at module level (e.g. lines 403, 481).  This is pre-existing (not Phase 36),
but the pattern is worth flagging for consistency.

**Fix:** Hoist the import to module level alongside the other `quirk` imports at the top of the
file, and remove the inner `try/except` block wrapping the import itself (keep the `try/except`
for the function call if classifier failures should be swallowed).

---

_Reviewed: 2026-04-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

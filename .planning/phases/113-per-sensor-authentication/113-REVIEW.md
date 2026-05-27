---
phase: 113-per-sensor-authentication
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - quirk/dashboard/api/middleware/sensor_auth.py
  - quirk/dashboard/api/routes/sensor.py
  - quirk/dashboard/api/app.py
  - quirk/cli/console_cmd.py
  - quirk/cli/sensor_cmd.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 113: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 113 wakes the dormant `sensor_tokens` table into a working per-sensor auth
path. The core security design is sound: token identity is authoritative (D-04),
the push route is split onto a dedicated `sensor_push_router` with
`require_sensor_auth` while operator surfaces stay on `require_auth` (D-01/D-02),
SHA-256 is hashed before lookup (no raw-token comparison), `hmac.compare_digest`
is used on the matched row, revoked tokens are rejected, and audit rows are written
on every branch. No timing oracle exists because the attacker-controlled raw token
is SHA-256-hashed before the indexed lookup, and `compare_digest` runs on
equal-length hex.

I found **no Critical (auth-bypass / injection / data-loss) defects**. The auth
ladder behaves per D-04/D-05/D-09: unknown→401, revoked→401, mismatch→403, valid→200,
each with an `IntegrationDelivery` row. The findings below are robustness and
correctness-hardening issues (Warning) plus minor quality items (Info).

## Warnings

### WR-01: `request.state.sensor_id` accessed with no defensive fallback

**File:** `quirk/dashboard/api/routes/sensor.py:317`
**Issue:** The handler reads `request.state.sensor_id` directly. This attribute is
*only* set by `require_sensor_auth` (sensor_auth.py:97), which runs as a
router-level dependency on `sensor_push_router`. The contract holds today, but the
coupling is implicit and unguarded: if the route is ever re-registered on a router
without `require_sensor_auth` (a plausible future refactor, and exactly the kind of
mistake the two-router split is meant to prevent), `request.state.sensor_id` raises
`AttributeError`, producing an unhandled 500 *after* the body has already been read
and partially processed — and, worse, masking an auth-bypass rather than failing
closed at the auth layer. Defense-in-depth for a security-critical invariant.
**Fix:** Fail closed explicitly:
```python
token_sensor_id = getattr(request.state, "sensor_id", None)
if token_sensor_id is None:
    _audit(db, scan_id, "failed", "missing_sensor_identity")
    raise HTTPException(status_code=401, detail="Sensor authentication required")
```

### WR-02: Success response echoes `envelope.sensor_id` instead of the token-resolved id

**File:** `quirk/dashboard/api/routes/sensor.py:382`
**Issue:** The 200 response returns `"sensor_id": envelope.sensor_id` — the
*body-supplied* value. D-04 makes the token the source of truth, and the entire
point of the mismatch check (L324) is that the body must never drive identity. The
two are guaranteed equal here only because the D-05 check passed, so this is not a
live bug — but it contradicts the token-authoritative invariant and is fragile: any
future loosening of the D-05 check (or reordering) would let the body's value leak
into the response. The same applies to `_ingest_envelope(envelope_dict, ...)` at
L332, which ingests using the body's sensor_id rather than the token-resolved id.
**Fix:** Return and ingest the authoritative value:
```python
return {"status": "accepted", "sensor_id": token_sensor_id, "payload_id": envelope.payload_id}
```
For the ingest call, prefer overwriting `envelope_dict["sensor_id"] = token_sensor_id`
before passing it in, so the authoritative identity is what gets persisted.

### WR-03: Audit row in `require_sensor_auth` commits on the shared request session, silently persisting partial writes on commit failure

**File:** `quirk/dashboard/api/middleware/sensor_auth.py:67-71`
**Issue:** `_audit_and_raise` calls `db.add(row); db.commit()` on the same session
later used by the handler (FastAPI caches `Depends(get_db)` per request). On the
401 branches this is fine because the dependency raises and the handler never runs.
However, the `except Exception` around `db.commit()` swallows *all* commit failures
and proceeds to `raise HTTPException` without a `db.rollback()`. A failed commit
leaves the session in a dirty/failed transaction state; because `get_db` only calls
`db.close()` (deps.py:60) and never rolls back, the next operation on a reused
connection could surface a stale `PendingRollbackError`. The audit row may also be
silently lost with only a `logger.warning`, weakening the D-09 "every branch writes
an audit row" guarantee under DB pressure.
**Fix:** Roll back on commit failure before raising:
```python
try:
    db.commit()
except Exception as exc:
    db.rollback()
    logger.warning("Audit row commit failed: %s", safe_str(exc))
```

### WR-04: `revoke-sensor` is not idempotent and gives a misleading error on an already-revoked sensor

**File:** `quirk/cli/console_cmd.py:274-288`
**Issue:** `_cmd_revoke_sensor` filters `revoked_at.is_(None)` and, if no *active*
rows match, prints `ERROR: no active token found for sensor_id` and `sys.exit(1)`.
This conflates two very different states: (a) the sensor_id never existed, and
(b) the sensor was already revoked. An operator re-running `revoke-sensor` on an
already-revoked sensor (a natural reaction during incident response) gets a hard
error exit code, which can abort a remediation script mid-run and reads as "the
revoke failed" when the token is in fact already inert. Revocation should be
idempotent for a security-control command.
**Fix:** Distinguish the two cases — exit 0 if the sensor exists but all its tokens
are already revoked:
```python
all_rows = db.query(SensorToken).filter(SensorToken.sensor_id == sensor_id).all()
if not all_rows:
    print(f"ERROR: no token found for sensor_id {sensor_id!r}", file=sys.stderr)
    sys.exit(1)
active = [r for r in all_rows if r.revoked_at is None]
if not active:
    print(f"sensor_id {sensor_id} already revoked (no-op)")
    return
```

## Info

### IN-01: Unreachable defense-in-depth branch is documented as such but still incurs a query-result compare

**File:** `quirk/dashboard/api/middleware/sensor_auth.py:87-90`
**Issue:** The `hmac.compare_digest(hashed, token_row.token_hash)` branch can never
be False — the ORM filter `token_hash == hashed` already guarantees equality, as the
inline comment acknowledges ("Should be unreachable given the ORM filter"). It is
harmless belt-and-suspenders, but the comment claiming a timing-safe *benefit* is
slightly misleading: the timing-sensitive comparison already happened inside SQLite's
indexed lookup, not here. Keeping it is fine; consider trimming the comment's
timing-oracle claim to avoid implying the lookup itself is timing-safe.
**Fix:** No code change required. Optionally reword the comment to state this is a
schema-invariant assertion, not the timing-attack mitigation.

### IN-02: Unused import `hmac` would be flagged if the dead branch (IN-01) is ever removed

**File:** `quirk/dashboard/api/middleware/sensor_auth.py:19`
**Issue:** `hmac` is used only by the IN-01 belt-and-suspenders branch. Noting for
traceability: if a future cleanup removes that branch, drop the `hmac` import too to
keep the module lint-clean (PEP 8 / project standard).
**Fix:** Track alongside IN-01; no change now.

### IN-03: 401 audit rows use a synthetic timestamp `scan_id`, decoupling them from the eventual handler audit row

**File:** `quirk/dashboard/api/middleware/sensor_auth.py:54-55`
**Issue:** The dependency derives `scan_id` from `datetime.now(...).strftime("%Y-%m-%dT%H:%M:%SZ")`
(second-resolution), while the handler later overrides `scan_id` to the parsed
`envelope.pushed_at` (sensor.py:277). For the 401 cases the handler never runs, so
this is consistent — but it means 401 audit rows are correlated only by coarse
wall-clock second, and two near-simultaneous rejected pushes share an identical
`scan_id`. This is acceptable for an M2M reject trail but limits forensic precision.
**Fix:** Optional — include a short random suffix or the request id in the synthetic
scan_id for the pre-parse reject rows.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

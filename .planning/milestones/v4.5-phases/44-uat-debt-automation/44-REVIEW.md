---
phase: 44-uat-debt-automation
reviewed: 2026-05-03T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - quirk/dashboard/api/routes/pdf.py
  - src/dashboard/src/pages/data-at-rest.tsx
  - src/dashboard/src/pages/motion.tsx
  - src/dashboard/src/pages/print.tsx
  - tests/skip_registry.py
  - tests/test_dashboard_trends.py
  - tests/test_kerberos_scanner.py
  - tests/test_saml_scanner.py
  - tests/test_uat_db_integration.py
  - tests/test_vault_connector.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 44: Code Review Report

**Reviewed:** 2026-05-03T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Ten files reviewed across the dashboard API (pdf export route), three React pages
(data-at-rest, motion, print), the skip registry, and five test modules covering
trends, Kerberos, SAML, DB integration, and Vault. No security vulnerabilities or
data-loss risks were found. The issues cluster into two areas: (1) a logic bug in
the AMQPS protocol matcher in `motion.tsx` that causes AMQP/AMQPS-prefixed
endpoints to route incorrectly, (2) a race condition in `print.tsx`'s `data-ready`
signal that can let Playwright capture a blank PDF, (3) deprecated `datetime.utcnow()`
calls in `test_saml_scanner.py`, (4) a skip-registry line-number mismatch for
`test_vault_connector.py`, and (5) credentials hardcoded in the DB integration
test (acceptable for a chaos-lab fixture but worth noting).

## Warnings

### WR-01: `getBrokerFamily` matches bare `"AMQPS"` but the backend emits `"AMQPS"` only for plaintext port 5672; TLS variant is `"AMQPS/Azure-ServiceBus"` — handled by `"Cloud"`, but the discriminator `startsWith("AMQPS")` also grabs the Cloud variant before the `"HTTPS/"` check can fire

**File:** `src/dashboard/src/pages/motion.tsx:29-33`

**Issue:** `getBrokerFamily` checks the branches in this order:
```
if (protocol.startsWith("AMQP-") || protocol.startsWith("AMQPS")) return "AMQP"
if (protocol.startsWith("HTTPS/")) return "Cloud"
```
The backend (`broker_scanner.py:467`) emits `"AMQPS/Azure-ServiceBus"` for the
Azure cloud variant. That string starts with `"AMQPS"`, so it matches the AMQP
branch and is rendered in the AMQP table instead of the Cloud table. The intent
(per scanner comments) is for `"AMQPS/Azure-ServiceBus"` to fall through to the
`"Cloud"` family. This is a silent mis-classification — Azure AMQP endpoints will
appear under "AMQP" rather than "Cloud" in the dashboard.

**Fix:** Tighten the AMQP check so it only matches strings that do NOT contain a
slash (the slash is the cloud-variant delimiter), or check cloud variants first:
```typescript
export function getBrokerFamily(protocol: string): "Kafka" | "AMQP" | "Redis" | "Cloud" | null {
  if (protocol.startsWith("KAFKA-")) return "Kafka"
  if (protocol.startsWith("HTTPS/")) return "Cloud"                      // cloud first
  if (protocol === "AMQPS" || protocol.startsWith("AMQP-")) return "AMQP" // exact match for bare AMQPS
  if (protocol.startsWith("REDIS-")) return "Redis"
  return null
}
```

---

### WR-02: `print.tsx` — `data-ready` set only when `data` is truthy; error state never signals Playwright, causing a 15-second timeout on every failed scan export

**File:** `src/dashboard/src/pages/print.tsx:151-158`

**Issue:** The `useEffect` only calls `document.body.setAttribute('data-ready', 'true')`
when `data` is truthy. When `useScanData` resolves with an error (i.e., `error` is
set and `data` is `null/undefined`), `loading` becomes `false` and the component
renders the red error div, but `data-ready` is never set. Playwright in `pdf.py`
waits up to 15 seconds for `body[data-ready="true"]` and then throws, causing a
500 response instead of a clean error message. On slow networks this is a
guaranteed 15-second hang per failed export.

**Fix:** Signal readiness in both the success and error paths:
```typescript
useEffect(() => {
  if (data || error) {
    document.body.setAttribute('data-ready', 'true')
  }
  return () => {
    document.body.removeAttribute('data-ready')
  }
}, [data, error])
```
The PDF export route already handles a blank/error page gracefully (it returns
whatever Playwright captures), so the content of the PDF when there's an error is
acceptable; eliminating the timeout is the important fix.

---

### WR-03: `skip_registry.py` line 30 — registered line number for `test_vault_connector.py` skip does not match actual decorator position

**File:** `tests/skip_registry.py:30`

**Issue:** The registry entry is:
```python
("test_vault_connector.py", 455, "live_infra", "Requires Vault-30 chaos lab (vault profile)"),
```
The `@_pytest_uat.mark.skipif` decorator in `test_vault_connector.py` is at **line 455**.
That matches. However, `test_skip_registry.py` uses a `+/-2` line tolerance, so this
is borderline: if any future edit to the file shifts this decorator by more than 2
lines, the CI gate will fire and block CI with no obvious root cause. This is not
a current break, but the pattern of importing `os` and `pytest` under aliases at
the bottom of the file (lines 451-452) means the decorator line is fragile. This
is worth a registration audit after any further additions to that file.

**Fix:** After each edit to `test_vault_connector.py`, re-verify the decorator is
still at line 455. Alternatively, add a comment on line 455 such as
`# skip_registry.py line 30` to make drift visible during diff review.

---

### WR-04: `test_saml_scanner.py:44-45` — `datetime.utcnow()` is deprecated in Python 3.12+ and will emit `DeprecationWarning` on every test run

**File:** `tests/test_saml_scanner.py:44-45`

**Issue:**
```python
.not_valid_before(datetime.datetime.utcnow())
.not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
```
`datetime.utcnow()` is deprecated since Python 3.12 and emits `DeprecationWarning`
at import time in newer interpreter versions. The project targets Python 3.11+ per
`CLAUDE.md`; on 3.12+ CI this will produce noisy warnings and may become an error
in future releases.

**Fix:**
```python
from datetime import datetime, timezone, timedelta
.not_valid_before(datetime.now(timezone.utc))
.not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
```
Note: the `cryptography` library's `CertificateBuilder` accepts timezone-aware
datetimes as of version 42+. If an older version of `cryptography` is pinned that
requires naive datetimes, use `datetime.now(timezone.utc).replace(tzinfo=None)` as
an intermediate.

---

### WR-05: `test_dashboard_trends.py` — imports at module scope inside test functions create unreliable isolation; re-import inside `test_uat_31_...` each call but also at lines 61-66 at module scope

**File:** `tests/test_dashboard_trends.py:61-66`

**Issue:** The module-level imports (`uuid`, `datetime`, `sqlalchemy`, `TestClient`)
are placed after the first two test functions, mid-file, with private alias names
(`_uuid_uat31`, `_dt_uat31`, etc.). This is unusual and fragile: if collection
order changes or the file is split, the aliased names may be unavailable when
earlier tests reference shared helpers. More concretely, `_PREV_TS_UAT31` and
`_CURR_TS_UAT31` are module-level constants that depend on the mid-file `datetime`
import having completed. If pytest ever re-orders collection before full module
execution this will raise `NameError`. The standard pattern is all imports at the
top of the file.

**Fix:** Move all imports to the top of the file and remove the `_*_uat31` aliases.
The UUID and SQLAlchemy imports needed only for the seeded-DB test can be placed in
the normal import block at the top. The constants `_PREV_TS_UAT31` / `_CURR_TS_UAT31`
can use the standard `datetime` name.

---

## Info

### IN-01: `data-at-rest.tsx` — React table row keys use array index as tiebreaker, masking duplicate `host:port` rows during re-renders

**File:** `src/dashboard/src/pages/data-at-rest.tsx:85`

**Issue:** Row keys are constructed as `` `${f.host}-${f.port}-${i}` `` across all
four table components (`DatabaseTable`, `ObjectStorageTable`, `KubernetesTable`,
`VaultTable`). Including the index `i` means React can always produce a unique
key, but if the sorted order changes (e.g., after a new scan), React will re-render
all rows rather than reconciling existing ones. This is a minor reconciliation
quality issue, not a crash. The same pattern exists in `motion.tsx:63` and
`motion.tsx:147`.

**Fix:** Use a stable identifier when available. For DAR findings, combining
`host`, `port`, and `title` (or a backend-supplied `id`) produces a stable key
without requiring the index.

---

### IN-02: `pdf.py` — `sync_playwright` runs in a FastAPI async worker thread; blocking I/O on the event loop is not guarded with `run_in_executor`

**File:** `quirk/dashboard/api/routes/pdf.py:55-71`

**Issue:** The route is defined as a synchronous `def` (not `async def`), which
FastAPI correctly runs in a thread pool, so this is not a correctness bug. This
annotation is for awareness: if the function is ever inadvertently converted to
`async def`, the blocking `sync_playwright()` call would stall the event loop.
The current implementation is safe as-is.

**Fix:** Add a module-level comment noting why this must remain a sync function.

---

### IN-03: `test_kerberos_scanner.py:196` — nested `with patch.object` inside an already-active `with patch.object` for the same attribute creates an unused outer context manager

**File:** `tests/test_kerberos_scanner.py:193-197`

**Issue:** In `test_as_req_both_fail_graceful`, `_patch_probe_kdc_udp(kmod, None)` is
entered as a context manager (binding `mock_udp_fail`), and then immediately
overridden by an inner `patch.object(kmod, '_probe_kdc_udp', side_effect=...)`.
The outer mock object `mock_udp_fail` is never used and the outer patch is
superseded. This is dead code that confuses readers about which mock is actually
active.

**Fix:** Remove the outer `_patch_probe_kdc_udp` call and use only the inner
`patch.object` with `side_effect=OSError("UDP timeout")`.

---

_Reviewed: 2026-05-03T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

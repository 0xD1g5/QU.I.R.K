# Phase 69: Deferred BLOCKERs — Scanner + Cloud - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 69-deferred-blockers-scanner-cloud
**Areas discussed:** TokenBucket fix depth, Azure Blob absent severity, Resource leak test fixtures

---

## TokenBucket Fix Depth

### Q1: How should CR-08 (sleep+busy-wait contention) be fixed?

| Option | Description | Selected |
|--------|-------------|----------|
| threading.Condition | Replace sleep loop with Condition.wait(timeout). Threads block properly until notified on refill — no CPU spin, fair wakeup. | ✓ |
| Minimal patch | Keep sleep loop, add capacity guard, bump sleep to smarter interval (sleep until next refill, not 0.01s). | |

**User's choice:** threading.Condition
**Notes:** User accepted the recommended approach showing the exact acquire() implementation with Condition.wait(timeout=wait_secs) and notify_all() on token grant.

### Q2: Should rate <= 0 return immediately or enter the Condition path?

| Option | Description | Selected |
|--------|-------------|----------|
| Return immediately | rate <= 0 means unlimited — skip Condition entirely. Zero overhead for unlimited callers. | ✓ |
| Enter Condition path | Treats rate <= 0 as 'infinite rate' — simpler but adds unnecessary lock overhead. | |

**User's choice:** Return immediately
**Notes:** Preserves current behavior for unlimited callers.

---

## Azure Blob Absent Severity

### Q1: What severity/description for absent/null key_source?

| Option | Description | Selected |
|--------|-------------|----------|
| Same MEDIUM, distinct description | microsoft.storage → MEDIUM 'Platform-managed AES-256'. Absent → MEDIUM 'Encryption key source unavailable'. | ✓ |
| Absent = HIGH | Unknown state treated as worse than known platform-managed. Raises noise floor. | |
| microsoft.storage = LOW, absent = MEDIUM | Reframes platform-managed as lower risk. Requires touching severity ladder docs. | |

**User's choice:** Same MEDIUM, distinct description
**Notes:** Keeps severity parity, distinction lives in finding_id and description text.

### Q2: What finding_id for absent-key-source branch?

| Option | Description | Selected |
|--------|-------------|----------|
| BLOB-UNKNOWN | Distinct finding_id from BLOB-PLATFORM. Makes test assertions unambiguous. | ✓ |
| Reuse BLOB-PLATFORM | Same ID, rely solely on description. Simpler but harder for downstream programmatic differentiation. | |

**User's choice:** BLOB-UNKNOWN

---

## Resource Leak Test Fixtures

### Q1: How should leak tests be implemented?

| Option | Description | Selected |
|--------|-------------|----------|
| monkeypatch/mock injection | Patch socket.create_connection and sslyze internals to raise at specific points. Assert close() called via MagicMock. | ✓ |
| Local TCP echo server | Real local server, inject errors by closing mid-handshake. Higher confidence, slower. | |
| Both | Unit mock + single integration smoke test. Most thorough, adds fixture complexity. | |

**User's choice:** monkeypatch/mock injection
**Notes:** Consistent with existing test patterns in tests/.

### Q2: CR-07 fix approach in scan_tls_targets?

| Option | Description | Selected |
|--------|-------------|----------|
| try/finally in scan_tls_targets | Outer ThreadPoolExecutor with-block already handles outer pool. Fix is try/finally inside _scan_one_sslyze for sslyze Scanner cleanup. | ✓ |
| Wrap sslyze Scanner in with block | Use sslyze Scanner as context manager if it supports CM protocol. | |

**User's choice:** try/finally in scan_tls_targets

---

## Claude's Discretion

None — all areas had explicit user choices.

## Deferred Ideas

None — discussion stayed within phase scope.

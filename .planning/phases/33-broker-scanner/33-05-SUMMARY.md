---
phase: 33-broker-scanner
plan: "05"
subsystem: broker-scanner
tags: [phase-33, broker-scanner, redis, raw-ssl, tdd, struct-01]
requires: [33-04-SUMMARY.md]
provides: [REDIS-01, REDIS-02, REDIS-03, BROKER-ARCH]
affects: [quirk/scanner/broker_scanner.py, tests/test_broker_scanner_redis.py]
tech-stack:
  added: [ssl.SSLContext.wrap_socket (Redis TLS raw probe)]
  patterns: [raw-ssl-redis, optional-import-guard, struct-01-session-start, NOAUTH-NOPERM-degrade]
key-files:
  modified:
    - quirk/scanner/broker_scanner.py
  created:
    - tests/test_broker_scanner_redis.py
decisions:
  - "Used raw ssl.SSLContext.wrap_socket for Redis TLS probe — sslyze cannot speak Redis (no app-layer banner handshake)"
  - "NOAUTH/NOPERM exception classes mocked as concrete subclasses of Exception in tests (not MagicMock) to ensure except clauses match"
  - "_is_ip_redis defined inline in broker_scanner.py (not imported from tls_capabilities) to avoid internal module coupling"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-28"
  tasks_completed: 3
  files_changed: 2
---

# Phase 33 Plan 05: Redis Scanner Functions Summary

**One-liner:** Raw ssl.SSLContext PING/TLS Redis scanner (REDIS-01..03) appended to broker_scanner.py, completing BROKER-ARCH with all three protocol-family drivers.

## What Was Built

### Task 1 — `_detect_redis_plaintext` + `_probe_redis_tls` + `_enrich_redis_config`

Three helper functions appended to `quirk/scanner/broker_scanner.py` after the RabbitMQ section:

**`_detect_redis_plaintext(host, port, timeout)` — REDIS-02**
Sends `b"PING\r\n"` over a raw TCP socket and returns `True` if the first byte of the response is one of `b'+'`, `b'-'`, or `b'*'` (RESP protocol prefixes). This accepts `+PONG`, `-NOAUTH Authentication required`, or `*<array>` responses — all of which confirm a plaintext Redis listener. Connection errors return `False`.

**`_probe_redis_tls(host, port, timeout)` — REDIS-01**
Uses `ssl.create_default_context()` with `CERT_NONE` and `check_hostname=False`, then `ctx.wrap_socket()` directly on a raw TCP socket. Returns a `CryptoEndpoint` with `protocol="REDIS-TLS"`, `tls_version`, `cipher_suite`, and cert metadata (subject, issuer, pubkey_alg, pubkey_size via `_pubkey_info`). On `ConnectionRefusedError` returns `None`; on any other exception populates `ep.scan_error`.

**Why sslyze was NOT used for Redis TLS:**
sslyze performs its TLS probe by sending an application-layer handshake specific to the target protocol (SMTP STARTTLS, HTTPS, etc.). Redis has no such banner sequence — the TLS handshake happens directly at the TCP layer with no Redis-specific greeting. sslyze's protocol handlers would stall waiting for a protocol banner that never arrives. The raw `ssl.SSLContext.wrap_socket()` approach (identical to `tls_capabilities.py:_try_handshake`) works correctly because it performs a plain TLS ClientHello without expecting any Redis-layer negotiation.

**`_enrich_redis_config(host, port, logger)` — REDIS-03 / D-08**
Returns `{}` immediately if `REDIS_AVAILABLE` is `False`. When `redis-py` is present, calls `redis_lib.Redis(..., ssl=True, ssl_cert_reqs="none").config_get("tls-*")`. Catches `AuthenticationError` (NOAUTH) and `NoPermissionError` (NOPERM) with silent DEBUG logging, returning `{}` for both — these are authorization conditions, not scan errors. Any other exception also returns `{}` (D-08: enrichment is opportunistic).

**NOAUTH/NOPERM exception class hierarchy note:**
In tests, `redis_lib.exceptions.AuthenticationError` and `redis_lib.exceptions.NoPermissionError` must be set to concrete `Exception` subclasses (not `MagicMock` objects). Python's `except` clause uses `isinstance()`, which requires real exception classes. Using `MagicMock()` for the exception class causes the `except` clause to be bypassed, making tests appear to pass while the real code path is never exercised.

### Task 2 — `scan_one_redis` + `scan_redis_targets`

**`scan_one_redis(host, port, timeout, logger, session_start)`**
Port 6379: calls `_detect_redis_plaintext`; on success emits `ep.protocol="REDIS-PLAIN"`.
Port 6380 (or any non-6379): calls `_probe_redis_tls`; on success sets `ep.protocol="REDIS-TLS"`, then optionally enriches with `_enrich_redis_config` (stored as `ep._redis_config_enrichment`).
STRUCT-01: `ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)`.

**`scan_redis_targets(hosts, timeout, logger, session_start)`**
Schedules probes on ports 6379 and 6380 for each host via `ThreadPoolExecutor` (up to 50 workers). Collects non-None results. Satisfies BROKER-ARCH: `scan_kafka_targets`, `scan_rabbitmq_targets`, and `scan_redis_targets` are all now exposed from the single `broker_scanner.py` module.

### Task 3 — `tests/test_broker_scanner_redis.py` (15 tests)

15 tests covering REDIS-01..03, STRUCT-01, and BROKER-ARCH:

| # | Requirement | Test |
|---|-------------|------|
| 1 | REDIS-02 | `+PONG` → True |
| 2 | REDIS-02 | `-NOAUTH` → True |
| 3 | REDIS-02 | `*array` → True |
| 4 | REDIS-02 | garbage → False |
| 5 | REDIS-02 | ConnectionRefused → False |
| 6 | REDIS-02 | scan_one_redis 6379 → REDIS-PLAIN protocol |
| 7 | REDIS-01 | wrap_socket success → REDIS-TLS + tls_version |
| 8 | REDIS-01 | ConnectionRefused → None |
| 9 | REDIS-01 | ssl.SSLError → ep with scan_error populated |
| 10 | REDIS-03 | REDIS_AVAILABLE=False → {} |
| 11 | REDIS-03 | config_get success → dict returned |
| 12 | REDIS-03/D-08 | AuthenticationError (NOAUTH) → {} |
| 13 | REDIS-03/D-08 | NoPermissionError (NOPERM) → {} |
| 14 | BROKER-ARCH | all three drivers importable |
| 15 | STRUCT-01 | session_start → ep.scanned_at exact match |

All 15 tests pass. Full cross-suite: `test_broker_scanner_kafka.py` + `test_broker_scanner_rabbitmq.py` + `test_broker_scanner_redis.py` = 41 tests green.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Minor implementation note:** `_is_ip_redis` was named with a suffix to avoid shadowing the `_is_ip` function already imported from `tls_capabilities.py` (which was not imported in broker_scanner.py, but the name collision avoidance is correct). The plan template named it `_is_ip`; the inline variant is `_is_ip_redis`. No behavioral difference.

## Threat Flags

None. The T-33-14 mitigation (wrap_socket hang via `socket.create_connection(timeout=timeout)`) is implemented as specified.

## Known Stubs

None.

## Self-Check: PASSED

- [x] `quirk/scanner/broker_scanner.py` exists and contains `scan_redis_targets` — FOUND
- [x] `tests/test_broker_scanner_redis.py` exists with 281 lines (> 150 min) — FOUND
- [x] Commit a12d403 (Task 1 — helpers) — FOUND
- [x] Commit 5caeef3 (Task 2 — drivers) — FOUND
- [x] Commit 951931e (Task 3 — tests) — FOUND
- [x] `python -c "from quirk.scanner.broker_scanner import scan_kafka_targets, scan_rabbitmq_targets, scan_redis_targets"` exits 0 — PASSED
- [x] 15/15 Redis tests green, 41/41 full broker suite green — PASSED

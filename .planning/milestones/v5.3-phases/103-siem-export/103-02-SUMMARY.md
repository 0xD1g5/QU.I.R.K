---
phase: 103-siem-export
plan: "02"
subsystem: siem
tags: [siem, config-loader, transport, udp, tcp, syslog, cef, stdlib]
dependency_graph:
  requires: [103-01]
  provides: [quirk.siem.config.load_siem_config, quirk.siem.transport.send_syslog_raw]
  affects: []
tech_stack:
  added: []
  patterns:
    - "QUIRK_CONFIG_PATH discipline (mirrors load_notifications_config)"
    - "RFC 3164 <PRI> framing (LOG_USER*8+LOG_WARNING = <12>)"
    - "stdlib socket UDP sendto + TCP connect/sendall"
    - "socketserver.UDPServer/TCPServer port-0 capture pattern (in-test receivers)"
key_files:
  created:
    - quirk/siem/config.py
    - quirk/siem/transport.py
    - tests/test_siem_config.py
    - tests/test_siem_transport.py
  modified: []
decisions:
  - "Format-only endpoint validation (host non-empty, 1<=port<=65535) — no SSRF block (D-02)"
  - "OSError propagates from transport; dispatcher wraps per-send — transport never swallows"
  - "pri = (1*8)+4 = 12 hardcoded (LOG_USER/LOG_WARNING) per research recommendation"
metrics:
  duration_minutes: 2
  completed: "2026-05-25"
  tasks_completed: 2
  files_created: 4
---

# Phase 103 Plan 02: SiemCfg Loader + syslog UDP/TCP Transport Summary

**One-liner:** SiemCfg dataclass loaded from QUIRK_CONFIG_PATH YAML + raw socket send_syslog_raw with RFC 3164 <PRI> prefix, UDP/TCP selectable, format-only validation, loopback not blocked.

## What Was Built

### Task 1: Failing tests (RED)

Two test files created covering all must-have behaviors:

**tests/test_siem_config.py** (14 tests):
- `test_no_env_no_path_returns_none` — unset env + no path → None
- `test_loads_siem_block` — full SiemCfg populated from YAML (host, port, protocol, export_after_scan, timeout_seconds)
- `test_missing_siem_block_returns_none` — valid YAML without `[siem]` key → None
- `test_db_path_returns_none` / `test_binary_file_returns_none` / `test_binary_env_path_returns_none` — Pitfall 2 DB-path trap
- Default field value tests (port=514, protocol="udp", export_after_scan=False, timeout_seconds=5)
- `test_protocol_lowercased` — "UDP" in YAML → "udp" in SiemCfg

**tests/test_siem_transport.py** (13 tests):
- `test_send_cef_udp_delivers` / `test_send_cef_udp_has_pri_prefix` — socketserver.UDPServer capture; asserts b"CEF:0" and b"<12>"
- `test_send_cef_tcp_delivers` / `test_send_cef_tcp_has_pri_prefix` — socketserver.TCPServer equivalent
- `test_unreachable_raises` — refused TCP port → OSError
- `test_rejects_empty_host` / `test_rejects_port_zero` / `test_rejects_port_too_high` / `test_rejects_port_negative` — ValueError
- `test_does_not_block_loopback` — 127.0.0.1 with live UDP server succeeds (no internal-IP block)

All 27 tests failed with `ModuleNotFoundError` — RED gate confirmed.

### Task 2: Implementation (GREEN)

**quirk/siem/config.py**:
- Module docstring with CRITICAL CONSTRAINT (Pitfall 2) warning
- `@dataclass SiemCfg(host, port=514, protocol="udp", export_after_scan=False, timeout_seconds=5)`
- `load_siem_config(path=None)`: mirrors `load_notifications_config` structure verbatim; `effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")`; returns None on missing/non-file/missing-siem-key/any-exception; binary/SQLite files silently return None
- `_parse_siem_cfg(raw)`: flat dataclass construction from `raw.get()` calls with defaults; protocol lowercased

**quirk/siem/transport.py**:
- `send_syslog_raw(cef_msg, host, port, protocol="udp", timeout=5) -> None`
- Validates format only: `not host` → ValueError("host must be non-empty"); `not (1 <= port <= 65535)` → ValueError("port…")
- Does NOT call `validate_external_url` — syslog collectors are internal (D-02)
- `pri = (1*8)+4 = 12`; `payload = f"<12>{cef_msg}".encode("utf-8")`
- `SOCK_STREAM` for TCP, `SOCK_DGRAM` for UDP; `sock.settimeout(timeout)`; TCP: `connect + sendall`; UDP: `sendto`
- `OSError` propagates to caller (dispatcher wraps in try/except)

All 27 tests pass. `compileall` clean.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. `config.py` and `transport.py` are fully functional implementations. All tests pass against live socket behavior (not mocks).

## Threat Flags

No new security surface beyond what is documented in the plan's threat model (T-103-04, T-103-05, T-103-06). All mitigations tested:
- T-103-04: `test_db_path_returns_none`, `test_binary_env_path_returns_none`
- T-103-05: `test_rejects_empty_host`, `test_rejects_bad_port`, `test_does_not_block_loopback`
- T-103-06: Accepted (plaintext syslog baseline; TLS deferred)

## TDD Gate Compliance

- RED commit: `a1639d2` — `test(103-02): add failing tests for SiemCfg loader and syslog transport`
- GREEN commit: `2d30f95` — `feat(103-02): implement SiemCfg loader and syslog UDP/TCP transport`

## Self-Check

- [x] `quirk/siem/config.py` exists
- [x] `quirk/siem/transport.py` exists
- [x] `tests/test_siem_config.py` exists
- [x] `tests/test_siem_transport.py` exists
- [x] RED commit `a1639d2` exists
- [x] GREEN commit `2d30f95` exists
- [x] 27/27 tests pass
- [x] compileall clean

## Self-Check: PASSED

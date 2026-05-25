---
phase: 103-siem-export
verified: 2026-05-25T00:00:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run `quirk export --siem` against a live syslog receiver (e.g. `nc -ul 514`) and verify CEF events arrive with the correct `<12>CEF:0|QUIRK|scanner|...` prefix, `dhost=`, `dpt=`, `cs1=`, `cs2=`, `msg=` extension fields populated, and no cert PEM / compliance data present"
    expected: "One CEF event per finding appears in the receiver within the socket timeout; the raw line starts with `<12>CEF:0`; extension contains dhost/dpt correctly mapped from the finding; cert_pem, cert_sans, and compliance strings are absent"
    why_human: "Requires a live syslog receiver (Splunk/QRadar/nc); automated tests monkeypatch send_syslog_raw — actual datagram format is not verified end-to-end"
  - test: "Configure a scheduled scan with `export_after_scan: true` in the YAML config, run the scheduler, and confirm CEF events arrive at the receiver automatically after the scan completes"
    expected: "Findings appear in the SIEM receiver within seconds of scan completion; the scheduler does not fail even if the receiver is unavailable (check scheduled_runs.status='completed' in the DB)"
    why_human: "Requires a live scheduled scan + syslog receiver; the scheduler hook path is exercised only end-to-end with a real running scheduler"
---

# Phase 103: SIEM Export Verification Report

**Phase Goal:** Security teams can push QU.I.R.K. findings into their existing SIEM (Splunk, Elastic, QRadar, or any syslog-ingesting platform) in vendor-neutral syslog/CEF format without installing additional pip packages.
**Verified:** 2026-05-25
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every finding maps to a CEF:0 line with exactly 8 pipe-delimited header fields | VERIFIED | `build_cef_event` assembles `CEF:0|QUIRK|scanner|{ver}|{sig}|{name}|{sev}|{ext}` — live `str.split('|')` on a test finding returned 8 parts |
| 2 | Severity maps CRITICAL->10, HIGH->8, MEDIUM->5, LOW->3 | VERIFIED | `_CEF_SEVERITY` dict in `formatter.py` L27-32; live verification confirms CRITICAL->10 |
| 3 | Header escapes backslash then pipe; extension escapes backslash then equals then newlines; backslash escaped first in both | VERIFIED | `_cef_escape_header`: `replace("\\\\", "\\\\\\\\")` then `replace("|", "\\|")`; `_cef_escape_extension`: backslash first, then `=`, then `\r\n`/`\r`/`\n`; live: `_cef_escape_header('a\\|b')` -> `'a\\\\\\|b'` confirms backslash-first |
| 4 | cert PEM, SANs, and compliance list never appear in the CEF payload; host and port do appear | VERIFIED | `to_cef_finding` uses explicit named `.get()` extraction only (ISEC-03); live: `SECRET` absent, `dhost=h`, `dpt=80` present in output |
| 5 | signature falls back to slugified title when category/id absent | VERIFIED | `to_cef_finding` L125: `finding.get("category") or finding.get("id") or _slugify(title)`; live: finding with no category key produces `tls-weak-cipher` |
| 6 | `[siem]` YAML block loads from QUIRK_CONFIG_PATH into a SiemCfg dataclass | VERIFIED | `load_siem_config` in `config.py` L83: `effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")`; 14-test suite covers all load paths |
| 7 | A SQLite DB path or binary/malformed file returns None (never raises) | VERIFIED | `config.py` L93-95: `except Exception: return None`; tests `test_db_path_returns_none` and `test_binary_env_path_returns_none` pass |
| 8 | send_syslog_raw delivers over UDP and TCP with RFC3164 `<12>` prefix; validates host non-empty and 1<=port<=65535 only; does NOT block loopback | VERIFIED | `transport.py` L66: `payload = f"<{_SYSLOG_PRI}>{cef_msg}".encode("utf-8")`; format-only validation (no `validate_external_url` call); `test_does_not_block_loopback` passes |
| 9 | Unreachable/misconfigured endpoint yields clear error + WARNING + `integration_deliveries(destination="siem")` row; never aborts/corrupts scan record | VERIFIED | `dispatcher.py` export_findings wraps each send in try/except; writes ONE `IntegrationDelivery` row with `status="failed"` and `error_summary=safe_str(...)`; `test_unreachable_endpoint` passes; scheduler hook wrapped in outer try/except (L157 BLE001) |
| 10 | `quirk export --siem` reads latest findings-*.json or `--input` path, pushes one CEF event per finding | VERIFIED | `export_cmd.py` `run_export`: `_find_latest_findings` glob + max by mtime; per-finding loop in `export_findings`; `test_find_latest_findings` and `test_input_path_used` pass |
| 11 | run_scan.py intercepts `export` subcommand before scan argparse | VERIFIED | `run_scan.py` L496-500: `if len(_sys.argv) > 1 and _sys.argv[1] == "export": from quirk.cli.export_cmd import run_export; run_export(_sys.argv[2:]); return` |
| 12 | After-scan hook in scheduler_cmd fires only when `export_after_scan=True`, guarded by try/except isolation; zero new pip deps | VERIFIED | `scheduler_cmd.py` L186-197: deferred import + try/except BLE001; `dispatcher.export_after_scan_hook` guards on `cfg.export_after_scan`; all siem code uses only stdlib (socket, logging, json, glob, os, argparse, sys) + PyYAML (pre-existing dep) |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/siem/__init__.py` | Package marker | VERIFIED | Exists |
| `quirk/siem/formatter.py` | CEF escaping, severity map, `to_cef_finding`, `build_cef_event` | VERIFIED | 188 lines; all four exports present and substantive |
| `quirk/siem/config.py` | `SiemCfg` dataclass + `load_siem_config` | VERIFIED | 96 lines; QUIRK_CONFIG_PATH discipline; DB-path trap handled |
| `quirk/siem/transport.py` | `send_syslog_raw` via stdlib socket | VERIFIED | 79 lines; UDP + TCP; RFC3164 `<12>` prefix; no new deps |
| `quirk/siem/dispatcher.py` | `export_findings` + `export_after_scan_hook` | VERIFIED | 161 lines; one audit row per batch; full failure isolation |
| `quirk/cli/export_cmd.py` | `run_export` argparse entrypoint | VERIFIED | 160 lines; `--siem`, `--input`, `--output-dir`; clear error on missing file |
| `tests/test_siem_cef.py` | CEF format/escaping/severity tests | VERIFIED | 269 lines; covers all escaping, severity, fallback cases |
| `tests/test_siem_payload_whitelist.py` | Cert/compliance exclusion + host/port inclusion | VERIFIED | 197 lines; ALLOWED_FIELDS/FORBIDDEN_FIELDS frozensets |
| `tests/test_siem_config.py` | Loader + DB-path trap tests | VERIFIED | Passes |
| `tests/test_siem_transport.py` | socketserver UDP/TCP capture + format tests | VERIFIED | Passes |
| `tests/test_siem_dispatcher.py` | Dispatch, audit row, failure isolation, hook tests | VERIFIED | 187 lines; 6 tests pass |
| `tests/test_siem_export_cmd.py` | CLI argparse + interception tests | VERIFIED | 110 lines; 6 tests pass |
| `docs/configuration.md` | SIEM Export section | VERIFIED | L992-1082: covers all 5 config keys, CLI usage, CEF field mapping, payload safety note, deferred items |
| `docs/sample-config.yaml` | Commented `siem:` block | VERIFIED | L41-42+ present |
| `docs/UAT-SERIES.md` | Series 103 UAT cases + updated Last Updated | VERIFIED | L11977+: UAT-103-01..04; Last Updated 2026-05-25 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `quirk/siem/formatter.py` | `build_cef_event` consumes `to_cef_finding` | explicit named `.get()` extraction | WIRED | `build_cef_event` L162: `safe = to_cef_finding(finding)` |
| `quirk/siem/config.py::load_siem_config` | `QUIRK_CONFIG_PATH` env var | `effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")` | WIRED | L83 confirmed |
| `run_scan.py` | `quirk.cli.export_cmd.run_export` | `argv[1]=='export'` interception block | WIRED | L496-500 confirmed |
| `quirk/cli/scheduler_cmd.py` | `quirk.siem.dispatcher.export_after_scan_hook` | deferred import + try/except after notification hook | WIRED | L186-197 confirmed; before `return run` |
| `quirk/siem/dispatcher.py` | `IntegrationDelivery` audit row | `destination="siem"` single-commit | WIRED | L95-107: `IntegrationDelivery(finding_hash=None, destination="siem", ...)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `dispatcher.py::export_findings` | `findings` list | caller-provided (findings-*.json loaded in `run_export` / hook) | Yes — JSON from disk scan output | FLOWING |
| `dispatcher.py::export_findings` | `IntegrationDelivery` row | live `db.add + db.commit` | Yes — one row per batch written | FLOWING |
| `export_cmd.py::run_export` | `findings` | `json.load(open(findings_path))` from real scan output file | Yes | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 84 SIEM tests pass | `python -m pytest tests/test_siem_cef.py tests/test_siem_payload_whitelist.py tests/test_siem_config.py tests/test_siem_transport.py tests/test_siem_dispatcher.py tests/test_siem_export_cmd.py -q` | `84 passed in 0.29s` | PASS |
| CEF line has 8 header fields | `python -c "from quirk.siem.formatter import build_cef_event; print(len(build_cef_event({'severity':'CRITICAL','title':'x','host':'h','port':443}, '1.0.0').split('|')))"` | `8` | PASS |
| SECRET excluded from CEF output | `python -c "from quirk.siem.formatter import build_cef_event; print('SECRET' in build_cef_event({'severity':'HIGH','title':'x','host':'h','port':80,'cert_pem':'SECRET'}, '1.0.0'))"` | `False` | PASS |
| compileall clean on siem package | `python -m compileall quirk/siem/ quirk/cli/export_cmd.py -q` | No output (clean) | PASS |
| run_scan.py intercepts export | `grep -q "run_export" run_scan.py` | Match found L498 | PASS |
| scheduler_cmd wires hook | `grep -q "export_after_scan_hook" quirk/cli/scheduler_cmd.py` | Match found L189 | PASS |

---

### Probe Execution

Step 7c: SKIPPED — no `probe-*.sh` files declared or found for Phase 103. CEF delivery probes are superseded by the socketserver-based automated test suite.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| SIEM-01 | 103-02, 103-03 | User can export findings to SIEM in syslog/CEF format — landing in any syslog-ingesting platform | SATISFIED | `send_syslog_raw` (UDP+TCP, RFC3164), `run_export` CLI, `export_after_scan_hook` scheduler integration, all wired and tested |
| SIEM-02 | 103-01, 103-03 | CEF field mapping (severity, host, signature/category, evidence), invokable from CLI and optionally after scan | SATISFIED | `build_cef_event` + `to_cef_finding` explicit whitelist; `quirk export --siem` CLI; `export_after_scan_hook`; 84 tests green |

---

### Deferred / Not-Implemented (Correctly)

Per REQUIREMENTS.md "Future Requirements" and CONTEXT.md decisions:

| Feature | Status in Code | Correct? |
|---------|----------------|----------|
| Splunk HEC native export | Not implemented — no HEC code in `quirk/siem/` | Correct (deferred per REQUIREMENTS.md + CONTEXT.md) |
| Elasticsearch/ECS native client | Not implemented | Correct (deferred) |
| TLS-wrapped syslog (RFC 5425) | Not implemented (documented as deferred in `docs/configuration.md`) | Correct |

---

### Anti-Patterns Found

No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) found in any Phase 103 files. No stub return patterns. No empty handlers. No hardcoded empty data flowing to rendering paths.

---

### Human Verification Required

#### 1. Live syslog/CEF delivery verification

**Test:** Configure `QUIRK_CONFIG_PATH` pointing to a YAML with a `[siem]` block (e.g., `host: 127.0.0.1, port: 5514, protocol: udp`). Start a local receiver (`nc -ul 5514`). Run `quirk export --siem` against a findings file.

**Expected:** One raw datagram per finding appears in `nc` output. Each line starts with `<12>CEF:0|QUIRK|scanner|`. Extension fields include `dhost=`, `dpt=`, `cs1=`, `cs2=`, `msg=`. No `cert_pem`, `cert_sans`, `private_key`, or `compliance` substrings in any event.

**Why human:** Requires a live syslog receiver. Automated tests monkeypatch `_send_raw` — the actual datagram bytes are not verified end-to-end on a real socket.

#### 2. After-scan scheduler hook live verification

**Test:** Configure a scheduled scan with `export_after_scan: true` in the YAML config. Start a local syslog receiver. Trigger a scheduled scan run via the scheduler. Observe the SIEM receiver during and after the scan.

**Expected:** CEF events arrive at the receiver automatically after the scan completes. The scheduled scan's status in the DB remains `completed` even if the SIEM receiver is subsequently shut down and the hook fires against an unreachable endpoint.

**Why human:** Requires a running scheduler and a live syslog receiver. The hook fires only in a real `_dispatch_schedule` execution context.

---

### Gaps Summary

No gaps found. All 12 automated must-haves are verified. Two items require live human testing (live syslog receiver) per UAT-103-02 and UAT-103-04, which are already documented in `docs/UAT-SERIES.md`.

---

_Verified: 2026-05-25_
_Verifier: Claude (gsd-verifier)_

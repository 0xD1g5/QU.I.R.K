---
phase: 89-chaos-lab-profiles
plan: "02"
subsystem: infra
tags: [dnssec, kerberos, saml, identity, chaos-lab, lab-config, scanner]

requires:
  - phase: 88-v50-cli-render
    provides: stable scanner pipeline that calls scan_dnssec_targets

provides:
  - "config.yaml identity connector settings (enable_kerberos/saml/dnssec + targets + dnssec_resolver)"
  - "dnssec_scanner.py resolver-port override (host:port, default None → system resolver)"
  - "ConnectorsCfg.dnssec_resolver field (Optional[str], backwards-compatible default None)"
  - "13-test config-presence suite (test_phase89_lab_config_identity.py, all GREEN)"

affects: [phase-90-oqs-nginx, phase-92-v50-close]

tech-stack:
  added: []
  patterns:
    - "DNSSEC resolver override via host:port config key routes queries to lab bind9 on non-standard port"
    - "ConnectorsCfg Optional[str] field for per-connector resolver override"

key-files:
  created:
    - tests/test_phase89_lab_config_identity.py
    - tests/test_phase89_logger_stdlib_compat.py
  modified:
    - config.yaml
    - quirk/config.py
    - quirk/scanner/dnssec_scanner.py
    - run_scan.py
    - quirk/logging_util.py

key-decisions:
  - "Added _parse_resolver() helper to dnssec_scanner.py to extract host:port — keeps all call sites clean"
  - "DNSSEC endpoint port field reflects resolver_port (53 or override) rather than hardcoding 53"
  - "dnssec_resolver defaults to None in ConnectorsCfg so existing configs without the key continue using system resolver (backwards-compatible)"
  - "When resolver is set, _resolve_ns falls back to using resolver_host as the NS IP if no A glue found — lab bind9 is authoritative for the zone so direct queries work without glue records"

patterns-established:
  - "resolver-override pattern: Optional[str] = None in config + _parse_resolver() in scanner + kwarg threaded through public API"

requirements-completed: [LAB-06]

duration: 20min
completed: 2026-05-22
---

# Phase 89, Plan 02: Identity Lab Config + DNSSEC Resolver Override Summary

**DNSSEC resolver-port override added to dnssec_scanner.py (127.0.0.1:15353 for lab bind9), Kerberos/SAML/DNSSEC identity connectors wired in config.yaml; human-verify checkpoint cleared against the live lab — dnssec_weak_algo_count=2 and saml_weak_signing_count=2 flow non-zero into the identity subscore (kerberos etype deferred: needs impacket + KDC). End-to-end verification surfaced and fixed a latent Logger-API crash (LAB-06).**

## Performance

- **Duration:** ~20 min implementation + live verification
- **Started:** 2026-05-22T00:00:00Z
- **Completed:** 2026-05-22 (Task 2 human-verify cleared via orchestrator-run live scan)
- **Tasks:** 2/2 complete
- **Files modified:** 6 (5 from Task 1 + quirk/logging_util.py fix)

## Accomplishments

- config.yaml now has `enable_kerberos: true`, `enable_saml: true`, `enable_dnssec: true` with the lab targets for the chaos lab's identity profiles (samba-dc on 127.0.0.1, simplesamlphp on localhost:8080, bind9-dnssec on weak.example.com via resolver 127.0.0.1:15353).
- `dnssec_scanner.py` gained a `resolver` kwarg (host:port string) threaded through `_resolve_ns`, `_query_rrset`, `_detect_nsec_type`, and `_scan_domain` — queries bypass the system resolver and go to the lab's bind9 on port 15353.
- `ConnectorsCfg.dnssec_resolver: Optional[str] = None` added to config.py; `run_scan.py` passes it through to `scan_dnssec_targets`.
- 13 automated tests in `tests/test_phase89_lab_config_identity.py` all pass — cover config key presence, resolver API shape, `_parse_resolver` unit checks, and `ConnectorsCfg` field acceptance.
- No new test failures introduced; pre-existing baseline reduced from 43 to 38 failures (our new config fields resolved 5 pre-existing identity-infra test failures).

## Task Commits

1. **Task 1: Identity config + DNSSEC resolver override** - `1f58f93` (feat)
2. **Task 2 (human-verify): live-lab confirmation + Logger fix** - `5d22d98` (fix)

## Human-Verify Checkpoint Result (Task 2)

Cleared by the orchestrator running the live scan against the lab's `saml` +
`dnssec` profiles (kerberos left for the user — needs `impacket` + a live KDC,
and the macOS port-88 caveat applies). Results from
`output/intelligence-20260522-191551.json`:

| Counter | Result |
|---|---|
| `dnssec_weak_algo_count` | **2** (both unsigned zones; `cert_pubkey_alg=NONE`) |
| `saml_weak_signing_count` | **2** (simplesamlphp weak signing) |
| `identity_weak_etype_count` | 0 — **deferred**, kerberos KDC not exercised |
| `identity_trust` | 22 (subscore reflects the weak evidence) |

**Lab-usage note:** the chaos lab binds to loopback, so live verification
requires `--allow-internal-targets`; without it QUIRK's loopback guard blocks
the SAML fetch and all counters read 0.

### Latent defect surfaced + fixed (the point of LAB-06)

The first true end-to-end exercise of the BACK-78 identity wiring revealed that
all three identity connectors crashed inside `_wrapped_phase` (which swallowed
the exceptions, silently zeroing the counters):

- `Logger.info() takes 2 positional arguments but 4 were given` — `run_scan.py`
  phase wrappers (lines 1439/1459/1478/1499/1522/1558) call the custom
  `quirk.logging_util.Logger` with printf `%d` varargs it didn't support.
- `'Logger' object has no attribute 'warning'` — `kerberos_scanner.py:274`
  (impacket-missing path) calls `.warning()` on that same custom Logger.

Fixed at the root in `quirk/logging_util.py`: the custom `Logger` now honors the
subset of the stdlib logging interface the scanner layer relies on — lazy
`%`-substitution in `info`/`v` plus `warning`/`warn`/`error`/`critical`/
`exception`/`debug` (debug verbose-gated). One change fixes all six phase
wrappers and every scanner that passes this logger. Pinned by
`tests/test_phase89_logger_stdlib_compat.py` (5 tests).

## Files Created/Modified

- `config.yaml` — identity connector block added (enable_kerberos/saml/dnssec + targets + dnssec_resolver: 127.0.0.1:15353)
- `quirk/config.py` — `ConnectorsCfg.dnssec_resolver: Optional[str] = None` field added
- `quirk/scanner/dnssec_scanner.py` — `_parse_resolver()` helper; `resolver` param on `_resolve_ns`, `_query_rrset` (ns_port kwarg), `_detect_nsec_type` (ns_port kwarg), `_scan_domain`, `scan_dnssec_targets`; endpoint port fields reflect resolver_port
- `run_scan.py` — passes `cfg.connectors.dnssec_resolver` to `scan_dnssec_targets`
- `tests/test_phase89_lab_config_identity.py` — 13 config-presence + API tests (all GREEN)

## Decisions Made

- `_parse_resolver()` helper keeps `host:port` parsing in one place — all callers receive `(host, port)` tuple cleanly.
- Resolver port is reflected in the `port` field of emitted `CryptoEndpoint` objects (not hardcoded to 53), so the evidence records correctly identify the queried endpoint.
- When a custom resolver is configured and NS A-record lookup returns no results, the scanner falls back to using `resolver_host` directly as the NS IP. Lab bind9 is authoritative for the configured zones so this ensures the scan always reaches the lab without requiring proper glue records.
- `ConnectorsCfg.dnssec_resolver` defaults to `None` (not empty string) for a clean `if resolver:` guard; existing configs without the field continue using the system resolver unchanged.

## Deviations from Plan

- **In-scope bug fix beyond the plan's file list.** Clearing the human-verify
  checkpoint required fixing `quirk/logging_util.py` (+ a new regression test) —
  files not in the plan's `files_modified`. This was a latent crash the live
  verification existed to catch (LAB-06: "confirm the BACK-78 wiring end-to-end"),
  so the fix is squarely within the plan goal. Committed separately as `5d22d98`.
- **Kerberos counter deferred, not verified.** `identity_weak_etype_count` stays
  0 because `impacket` is not installed in this environment and the kerberos KDC
  profile was not brought up (macOS port-88 collision caveat). The wiring is
  confirmed correct (graceful degradation, no crash); the user verifies the
  non-zero kerberos path separately.

## Issues Encountered

The DNSSEC resolver override itself was straightforward (`dns.query.udp_with_fallback`
accepts a `port` kwarg). The real issue surfaced only at live verification: the
identity connectors crashed on a custom-Logger API mismatch (see the Human-Verify
Checkpoint Result section). Root-caused and fixed in `quirk/logging_util.py`.

## Known Stubs

None — no placeholder data, all fields are live lab targets.

## Threat Flags

No new trust-boundary surface beyond what the plan's threat model covers (T-89-04 and T-89-05 in the plan):
- `config.yaml` targets are all localhost/lab fixtures (127.0.0.1, localhost:8080, *.example.com zones).
- `dnssec_resolver` override is opt-in via config; defaults to None (system resolver).

## Next Phase Readiness

- Both tasks complete and committed (`1f58f93`, `5d22d98`).
- LAB-06 confirmed end-to-end for DNSSEC + SAML against the live lab.
- **Open user follow-up:** verify `identity_weak_etype_count` non-zero by
  installing the `identity` extra (`pip install -e '.[identity]'` → impacket)
  and bringing up the kerberos profile (`LAB_INCLUDE_KERBEROS=1`, system KDC
  stopped on macOS). Tracked for HUMAN-UAT.

## Self-Check: PASSED

- `tests/test_phase89_lab_config_identity.py` (13) + `tests/test_phase89_logger_stdlib_compat.py` (5) all GREEN.
- Commits `1f58f93` + `5d22d98` exist.
- Live scan confirms dnssec=2, saml=2 counters flow into the identity subscore.
- No unexpected file deletions.

---
*Phase: 89-chaos-lab-profiles*
*Completed: 2026-05-22*

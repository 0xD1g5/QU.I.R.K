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
  modified:
    - config.yaml
    - quirk/config.py
    - quirk/scanner/dnssec_scanner.py
    - run_scan.py

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

**DNSSEC resolver-port override added to dnssec_scanner.py (127.0.0.1:15353 for lab bind9), Kerberos/SAML/DNSSEC identity connectors wired in config.yaml, 13-test config-presence suite all GREEN — awaiting human-verify against live identity profiles**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-22T00:00:00Z
- **Completed:** 2026-05-22 (partial — paused at checkpoint:human-verify)
- **Tasks:** 1/2 complete (Task 2 = checkpoint:human-verify, awaiting user)
- **Files modified:** 5

## Accomplishments

- config.yaml now has `enable_kerberos: true`, `enable_saml: true`, `enable_dnssec: true` with the lab targets for the chaos lab's identity profiles (samba-dc on 127.0.0.1, simplesamlphp on localhost:8080, bind9-dnssec on weak.example.com via resolver 127.0.0.1:15353).
- `dnssec_scanner.py` gained a `resolver` kwarg (host:port string) threaded through `_resolve_ns`, `_query_rrset`, `_detect_nsec_type`, and `_scan_domain` — queries bypass the system resolver and go to the lab's bind9 on port 15353.
- `ConnectorsCfg.dnssec_resolver: Optional[str] = None` added to config.py; `run_scan.py` passes it through to `scan_dnssec_targets`.
- 13 automated tests in `tests/test_phase89_lab_config_identity.py` all pass — cover config key presence, resolver API shape, `_parse_resolver` unit checks, and `ConnectorsCfg` field acceptance.
- No new test failures introduced; pre-existing baseline reduced from 43 to 38 failures (our new config fields resolved 5 pre-existing identity-infra test failures).

## Task Commits

1. **Task 1: Identity config + DNSSEC resolver override** - `1f58f93` (feat)

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

None — plan executed exactly as written. The DNSSEC resolver override was the planned deliverable; it was implemented (not surfaced as a blocker) because `dns.query.udp_with_fallback` accepts a `port` kwarg, making the override straightforward without a broader refactor.

## Issues Encountered

None. The `dns.query.udp_with_fallback` API accepts `port` as a keyword argument, so the override required only adding the `_parse_resolver()` helper and threading the port through the existing call sites. No structural changes needed.

## Known Stubs

None — no placeholder data, all fields are live lab targets.

## Threat Flags

No new trust-boundary surface beyond what the plan's threat model covers (T-89-04 and T-89-05 in the plan):
- `config.yaml` targets are all localhost/lab fixtures (127.0.0.1, localhost:8080, *.example.com zones).
- `dnssec_resolver` override is opt-in via config; defaults to None (system resolver).

## Next Phase Readiness

- Task 1 complete and committed (`1f58f93`).
- Awaiting **human-verify checkpoint** (Task 2): user must bring up the chaos lab's saml, dnssec, and kerberos profiles and run `quirk scan --config config.yaml` to confirm all three evidence counters (`identity_weak_etype_count`, `saml_weak_signing_count`, `dnssec_weak_algo_count`) are non-zero in the intelligence output.

## Self-Check: PASSED

- `tests/test_phase89_lab_config_identity.py` exists and all 13 tests GREEN.
- Commit `1f58f93` exists: `git log --oneline | head -1` confirms.
- No unexpected file deletions in the commit.

---
*Phase: 89-chaos-lab-profiles*
*Completed: 2026-05-22 (partial — paused at checkpoint)*

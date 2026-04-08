# Phase 18: DNSSEC Scanner - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can audit the DNSSEC posture of any domain — detecting unsigned zones, weak signing
algorithms, NSEC zone enumeration exposure, and broken DS chains — with results in the CBOM.
Scanner module, classifier extension, CBOM integration, and BIND9 chaos lab profile.

</domain>

<decisions>
## Implementation Decisions

### Finding Granularity
- **D-01:** One CryptoEndpoint per DNSKEY record — each DNSKEY produces its own row with algorithm, key size, and flags (ZSK/KSK role + key_tag in `service_detail`). Matches JWT scanner pattern (one per key).
- **D-02:** Unsigned zones, NSEC exposure, and DS chain breaks also produce CryptoEndpoint rows — every finding is a CBOM entry. Unsigned zone uses `algorithm="NONE"`, `service_detail="unsigned-zone"`. NSEC exposure uses `service_detail="nsec-exposure"`. DS chain break uses `service_detail="ds-chain-broken"`.
- **D-03:** `dnssec_scan_json` stores a flat per-domain dict: `domain`, `ns_queried`, `signed` boolean, `dnskeys[]` array (flags, alg, tag, key_size, role), `ds_records[]` array (key_tag, algorithm, digest_type), `nsec_type`, `chain_valid`.

### Severity Classification
- **D-04:** 3-tier DNSSEC algorithm severity map per RFC 8624/9905:
  - CRITICAL: RSAMD5 (alg 1), DSA/SHA1 (alg 3), RSASHA1 (alg 5), DSA-NSEC3 (alg 6), RSASHA1-NSEC3 (alg 7)
  - HIGH: RSASHA256 (alg 8), RSASHA512 (alg 10) — quantum-vulnerable RSA
  - Safe (no finding): ECDSAP256SHA256 (alg 13), ECDSAP384SHA384 (alg 14), ED25519 (alg 15), ED448 (alg 16)
- **D-05:** NSEC zone-enumeration exposure = MEDIUM severity. Not a cryptographic weakness but an operational information-disclosure risk.
- **D-06:** SHA-1 DS digest type (type 1) = MEDIUM severity. SHA-256 (type 2) and SHA-384 (type 4) are acceptable.
- **D-07:** Unsigned zone = HIGH severity (per DNSSEC-03). Broken DS chain = HIGH severity (per DNSSEC-06).

### Chaos Lab
- **D-08:** 4 BIND9 zones for full requirement coverage:
  1. `weak.chaos.local` — RSASHA1 + NSEC records (tests DNSSEC-02 + DNSSEC-05)
  2. `safe.chaos.local` — ECDSAP256SHA256 + NSEC3 (clean baseline)
  3. `broken.chaos.local` — valid DNSKEY but DS key_tag mismatch (tests DNSSEC-06)
  4. `unsigned.chaos.local` — no DNSSEC (tests DNSSEC-03)
- **D-09:** Pre-signed zone files baked into Docker image — deterministic key tags and algorithms every time. No runtime key generation. Zone files generated with `dnssec-keygen` + `dnssec-signzone`, committed to repo under `quantum-chaos-enterprise-lab/bind9/zones/`.
- **D-10:** Dedicated `dnssec` Docker Compose profile — starts just BIND9 container. Not grouped under the `identity` profile. Maps to `docker compose --profile dnssec up` per success criteria 5.

### Scan Error Handling
- **D-11:** On unreachable NS or SERVFAIL: retry once, then skip the domain with a warning log. Error details optionally stored in `dnssec_scan_json` for forensics.
- **D-12:** Auto-resolve authoritative NS from domain name — given `example.com` in `dnssec_targets`, scanner resolves NS records first, then queries DNSKEY/DS against those NS directly (per DNSSEC-01).
- **D-13:** UDP first, TCP fallback — standard DNS transport. Try UDP, if TC (truncated) bit is set, retry over TCP. dnspython handles this natively.

### run_scan.py Integration
- **D-14:** DNSSEC scan phase block added after Azure cloud connector, before endpoint aggregation. Guarded by `cfg.connectors.enable_dnssec and cfg.connectors.dnssec_targets`. Wrapped in `_phase_timer(run_stats, "dnssec_scanning")`.
- **D-15:** Function signature: `scan_dnssec_targets(targets: list, timeout: int = 10, logger=None) -> list[CryptoEndpoint]`. Matches JWT scanner pattern exactly.

### CBOM Builder Mapping
- **D-16:** DNSSEC algorithm stored in `cert_pubkey_alg` field (e.g., "RSASHA256"). Key size in `cert_pubkey_size` for RSA algorithms. Builder branch: `elif ep.protocol == "DNSSEC": _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)`.

### Scan Timeout + Concurrency
- **D-17:** Sequential domain scanning — no threading. DNS queries are fast enough (~50ms) that sequential is sufficient for typical 20-domain target lists.
- **D-18:** 5-second per-query timeout for DNS UDP/TCP calls. With single retry, worst case per domain is ~10s for a timeout scenario.

### Claude's Discretion
- BIND9 Dockerfile specifics and base image version
- Internal helper function naming (`_scan_domain`, `_resolve_ns`, `_parse_dnskeys`, etc.)
- Exact BIND9 named.conf structure for the 4 zones
- How to construct the broken DS chain scenario (e.g., wrong key_tag in parent zone file)
- `DNSSEC_ALG_MAP` constant placement (in `dnssec_scanner.py` or `cbom/classifier.py`)
- Whether to add `DNSSEC_AVAILABLE` import guard (matching `HTTPX_AVAILABLE` in jwt_scanner.py)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §DNSSEC — DNSSEC-01 through DNSSEC-07 full requirement text
- `.planning/ROADMAP.md` §Phase 18 — success criteria, plan structure, dependencies

### Phase 17 infrastructure (already implemented)
- `quirk/config.py` — `ConnectorsCfg.enable_dnssec`, `ConnectorsCfg.dnssec_targets` fields
- `quirk/models.py` — `ScanResult.dnssec_scan_json` column
- `quirk/db.py` — migration helper ensuring `dnssec_scan_json` column exists
- `quirk/config_template.yaml` — identity connectors section with `dnssec_targets` format

### Scanner patterns to follow
- `quirk/scanner/jwt_scanner.py` — reference scanner pattern: entry point, import guard, CryptoEndpoint construction
- `quirk/scanner/ssh_scanner.py` — ThreadPoolExecutor pattern (for reference, not used here) and error handling

### CBOM integration
- `quirk/cbom/builder.py` — `build_cbom()` protocol dispatch (line ~322+), `_register_algorithm()` usage
- `quirk/cbom/classifier.py` — `classify_algorithm()` function, existing algorithm maps

### Scan orchestration
- `run_scan.py` — connector scan phase pattern (lines ~399-461), endpoint aggregation, `_phase_timer` usage

### Chaos lab
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing profile structure (jwt, ssh-weak, identity, etc.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CryptoEndpoint` model fields: `cert_pubkey_alg`, `cert_pubkey_size`, `service_detail`, `protocol` — all reused for DNSSEC findings
- `_register_algorithm()` in `cbom/builder.py` — handles algorithm registration with key size
- `_phase_timer` context manager in `run_scan.py` — wraps scan phases for timing
- `ConnectorsCfg` already has `enable_dnssec` and `dnssec_targets` from Phase 17

### Established Patterns
- Scanner module in `quirk/scanner/` with `scan_<type>_targets()` entry point returning `List[CryptoEndpoint]`
- Import guard pattern: `try: import X; X_AVAILABLE = True except: X_AVAILABLE = False`
- Error handling: catch exceptions, log warning, continue to next target (sentinel return, not exceptions)
- CBOM builder: `elif ep.protocol == "TYPE":` dispatch for algorithm registration

### Integration Points
- `run_scan.py` line ~457 — insert DNSSEC scan phase after Azure connector
- `quirk/cbom/builder.py` line ~338 — add `elif ep.protocol == "DNSSEC"` branch
- `quirk/cbom/classifier.py` — add `DNSSEC_ALG_MAP` for algorithm classification
- `quantum-chaos-enterprise-lab/docker-compose.yml` — add `dnssec` profile with BIND9 service

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions captured above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 18-dnssec-scanner*
*Context gathered: 2026-04-08*

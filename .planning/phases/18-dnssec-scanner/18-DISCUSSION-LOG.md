# Phase 18: DNSSEC Scanner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 18-dnssec-scanner
**Areas discussed:** Finding granularity, Full severity map, Chaos lab scenarios, Scan error handling, run_scan.py integration, CBOM builder mapping, Scan timeout + concurrency

---

## Finding Granularity

### Q1: How should DNSSEC results map to CryptoEndpoint rows?

| Option | Description | Selected |
|--------|-------------|----------|
| One per DNSKEY record | Each DNSKEY becomes its own CryptoEndpoint with algorithm, key size, flags (ZSK/KSK). Matches JWT pattern. | ✓ |
| One per domain | Single CryptoEndpoint per domain with all algorithms aggregated in service_detail JSON. | |
| One per algorithm | Group DNSKEY records by algorithm number. One CryptoEndpoint per unique algorithm per domain. | |

**User's choice:** One per DNSKEY record (Recommended)
**Notes:** Finest granularity for CBOM. Consistent with JWT scanner (one per key).

### Q2: Should unsigned zones and NSEC exposure also produce CryptoEndpoint rows?

| Option | Description | Selected |
|--------|-------------|----------|
| Everything gets a row | Unsigned zone, NSEC exposure, DS chain break all become CryptoEndpoint entries. | ✓ |
| Only DNSKEY records | Only actual keys found get CryptoEndpoints. Other issues become findings only. | |

**User's choice:** Everything gets a row (Recommended)
**Notes:** Keeps CBOM comprehensive — all DNSSEC findings are CBOM entries.

### Q3: What JSON structure for dnssec_scan_json?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat per-domain dict | domain, ns_queried, signed, dnskeys[], ds_records[], nsec_type, chain_valid | ✓ |
| Nested with metadata | Richer structure with query_meta (timing, resolver) wrapping zone data | |

**User's choice:** Flat per-domain dict (Recommended)
**Notes:** Mirrors jwt_scan_json simplicity.

---

## Full Severity Map

### Q4: NSEC zone-enumeration exposure severity?

| Option | Description | Selected |
|--------|-------------|----------|
| MEDIUM | Info disclosure risk but not cryptographic weakness. Matches TLS info-disclosure ratings. | ✓ |
| LOW | Well-known and commonly accepted configuration. | |
| HIGH | Serious — reveals internal hostnames and infrastructure topology. | |

**User's choice:** MEDIUM (Recommended)
**Notes:** Operational exposure, not a crypto weakness.

### Q5: Full DNSSEC_ALG_MAP severity scheme?

| Option | Description | Selected |
|--------|-------------|----------|
| 3-tier map | CRITICAL (deprecated/broken), HIGH (quantum-vulnerable RSA), Safe (ECDSA/EdDSA). | ✓ |
| 2-tier (CRITICAL + safe only) | Only flag actively deprecated algorithms. Miss quantum angle. | |
| 4-tier with quantum warning | Add MEDIUM for ECDSA (quantum-vulnerable). Reserve "safe" for post-quantum only. | |

**User's choice:** 3-tier map (Recommended)
**Notes:** RSASHA256/512 as HIGH aligns with quantum-readiness focus of the tool.

### Q6: Should DS record digest types be classified?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, flag SHA-1 DS as MEDIUM | SHA-1 DS gets MEDIUM finding. SHA-256/384 are fine. | ✓ |
| Skip DS digest classification | Focus only on DNSKEY algorithms per requirements. | |
| Flag SHA-1 DS as HIGH | More aggressive stance on SHA-1 digest. | |

**User's choice:** Yes, flag SHA-1 DS as MEDIUM
**Notes:** RFC 8624 deprecates SHA-1 DS. MEDIUM is proportionate — requires second-preimage for exploitation.

---

## Chaos Lab Scenarios

### Q7: How many BIND9 zones?

| Option | Description | Selected |
|--------|-------------|----------|
| 4 zones — full coverage | weak (RSASHA1+NSEC), safe (ECDSAP256+NSEC3), broken DS, unsigned. Covers all 7 requirements. | ✓ |
| 2 zones — minimal | Just RSASHA1 and ECDSAP256 per DNSSEC-07. Other tests via mocks. | |
| 3 zones — skip unsigned | weak, safe, broken DS. Unsigned tested against non-DNSSEC domain. | |

**User's choice:** 4 zones — full coverage (Recommended)
**Notes:** Full requirement coverage in one container.

### Q8: Pre-signed zone files or inline-signing?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-signed zone files | Baked into Docker image. Deterministic, fast, CI-friendly. | ✓ |
| Inline-signing at runtime | BIND9 manages keys at startup. More realistic but non-deterministic. | |
| Hybrid | Pre-signed for weak/safe, inline for broken chain. | |

**User's choice:** Pre-signed zone files (Recommended)
**Notes:** Deterministic key tags every time. Zone files committed to repo.

### Q9: Dedicated `dnssec` profile or under `identity`?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated `dnssec` profile | Just BIND9. Matches roadmap language. Lightweight. | ✓ |
| Under `identity` profile | Groups all identity containers. Heavier startup. | |

**User's choice:** Dedicated `dnssec` profile (Recommended)
**Notes:** Matches success criteria 5: `docker compose --profile dnssec up`.

---

## Scan Error Handling

### Q10: Unreachable NS / SERVFAIL behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Log + skip domain | Warning log, return empty for that domain. SSH scanner pattern. | |
| Produce error CryptoEndpoint | CryptoEndpoint with scan_error set. More visible but noisy. | |
| Retry once then skip | Single retry with backoff before giving up. Catches transient DNS failures. | ✓ |

**User's choice:** Retry once then skip
**Notes:** DNS can be flaky — one retry catches transient failures.

### Q11: How to discover authoritative NS?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-resolve NS | Resolve NS records from domain, then query those NS directly. | ✓ |
| User provides NS | Require NS addresses in config alongside domains. | |
| Auto-resolve with override | Auto by default, optional NS override in config. | |

**User's choice:** Auto-resolve NS (Recommended)
**Notes:** Keeps `dnssec_targets` config simple — just domain names.

### Q12: DNS query transport?

| Option | Description | Selected |
|--------|-------------|----------|
| UDP first, TCP fallback | Standard DNS. Try UDP, TCP on truncation. | ✓ |
| TCP only | Skip UDP. DNSKEY usually >512 bytes. | |
| You decide | | |

**User's choice:** UDP first, TCP fallback (Recommended)
**Notes:** Standard behavior. dnspython handles TC bit natively.

---

## run_scan.py Integration

### Q13: Where in the scan sequence?

| Option | Description | Selected |
|--------|-------------|----------|
| After Azure, before aggregation | Groups identity scanners after cloud connectors. | ✓ |
| Grouped with future identity scanners | Same location with section header comment. | |
| You decide | | |

**User's choice:** After Azure, before aggregation (Recommended)
**Notes:** Keeps existing order undisturbed.

### Q14: Function signature?

| Option | Description | Selected |
|--------|-------------|----------|
| Match JWT pattern exactly | `scan_dnssec_targets(targets, timeout, logger)` | ✓ |
| Add resolver parameter | Optional `resolver` param for test injection. | |

**User's choice:** Match JWT pattern exactly (Recommended)
**Notes:** Consistent API across all scanners.

---

## CBOM Builder Mapping

### Q15: How to map DNSSEC to CBOM components?

| Option | Description | Selected |
|--------|-------------|----------|
| Use cert_pubkey_alg field | Store algorithm name in cert_pubkey_alg, key size in cert_pubkey_size. Simple. | ✓ |
| Parse dnssec_scan_json | Read from JSON blob in builder. More explicit but adds parsing. | |
| You decide | | |

**User's choice:** Use cert_pubkey_alg field (Recommended)
**Notes:** Mirrors JWT pattern. Simple builder branch.

---

## Scan Timeout + Concurrency

### Q16: Parallelization strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential with timeout | Scan domains one at a time. Fast enough for DNS. Simple. | ✓ |
| ThreadPoolExecutor | Parallel like SSH scanner. Overkill for DNS queries. | |
| You decide | | |

**User's choice:** Sequential with timeout (Recommended)
**Notes:** DNS is fast enough. Can add threading later if needed.

### Q17: Per-query DNS timeout?

| Option | Description | Selected |
|--------|-------------|----------|
| 5 seconds per query | Standard DNS timeout. Safe for slow NS. 10s worst case with retry. | ✓ |
| Use scan.timeout_seconds from config | Global timeout. May be too generous for DNS. | |
| 2 seconds (aggressive) | Fast but may miss slow nameservers. | |

**User's choice:** 5 seconds per query (Recommended)
**Notes:** Balanced — catches most cases without slowing down the scan.

---

## Claude's Discretion

- BIND9 Dockerfile specifics and base image version
- Internal helper function naming
- Exact BIND9 named.conf structure
- How to construct broken DS chain scenario
- DNSSEC_ALG_MAP constant placement
- Whether to add DNSSEC_AVAILABLE import guard

## Deferred Ideas

None — discussion stayed within phase scope.

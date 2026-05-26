# Backlog 999.85 — Distributed lab needs a weak-crypto target (segment-filter testability)

**Type:** testability
**Source:** v5.4 live human-UAT (UAT-112-03 sweep, Test 7), 2026-05-26
**Candidate for:** v5.5

## Problem

Every segment in `docker-compose.distributed.yml` points at `nginx:1.28.0`, which uses
strong, modern TLS → **0 quantum-vulnerable findings**. The Phase 111 segment filter on
the Findings and CBOM dashboard pages filters *findings* by segment, so with no findings
there is nothing to filter and the filter toolbar does not render. Test 7 of the v5.4
deferred-UAT sweep was therefore **BLOCKED** — the segment filter could not be exercised
end-to-end.

**Not a product bug:** pushed `crypto_endpoints` rows DO carry `segment` (segment-a /
segment-b) in the console DB. The data path is correct; the lab simply produces no
findings to filter.

## Fix

Add a deliberately weak-crypto TLS target to each segment (e.g. RSA-1024 / TLS 1.0 /
expired cert) in `docker-compose.distributed.yml` so segmented findings exist. Then
re-run the UAT-112 segment-filter verification (Findings + CBOM pages, including the
"All segments" / per-segment / NULL-segment cases).

## References

- `.planning/v5.4-deferred-uat.md` (Test 7)
- `src/dashboard/src/pages/findings.tsx:149`, `src/dashboard/src/pages/cbom.tsx:461`

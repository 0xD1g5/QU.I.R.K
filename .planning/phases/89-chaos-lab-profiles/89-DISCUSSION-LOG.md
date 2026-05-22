# Phase 89: Chaos Lab Profiles - Discussion Log

> **Audit trail only.** Decisions are in CONTEXT.md.

**Date:** 2026-05-22
**Phase:** 89-chaos-lab-profiles
**Areas discussed:** smtp-starttls disposition, TLS config posture, gRPC endpoint/ALPN-h2, identity evidence scope

---

## LAB-03 — smtp-starttls disposition

| Option | Selected |
|--------|----------|
| Close as already-covered (existing email profile) | ✓ |
| Add distinct smtp-starttls profile | |
| Alias/rename email profile | |

**Choice:** Close as already-covered. The existing `email` profile (Postfix+Dovecot, STARTTLS 587) covers smtp-starttls; add an expected-results/UAT note proving detection; no new service. Phase delivers 4 new profiles, not 5.

---

## TLS config posture (postgres/redis/kafka/grpc)

| Option | Selected |
|--------|----------|
| Weak/legacy config (triggers findings) | ✓ |
| Clean modern baseline only | |
| Both weak + modern per profile | |

**Choice:** Weak/legacy single variant per profile (exercises detection; expected_results assert findings). Clean baselines already exist via tls-modern.

---

## LAB-05 — gRPC endpoint + ALPN-h2

| Option | Selected |
|--------|----------|
| Custom Go image, confirm ALPN-h2 at execution (task 1) | ✓ |
| Spike ALPN-h2 first | |
| Off-the-shelf gRPC-TLS image | |

**Choice:** Custom minimal Go image; executor confirms sslyze negotiates ALPN-h2 as the first task before wiring the probe; failure = in-flight blocker. No separate spike.

---

## LAB-06 — identity evidence verification

| Option | Selected |
|--------|----------|
| Existing scan config + evidence-flow UAT | ✓ |
| New dedicated identity scan config | |
| Unit assertion only (no live scan) | |

**Choice:** Add Kerberos/SAML/DNSSEC targets to an existing lab scan config + a UAT asserting all three evidence counters flow into the identity subscore end-to-end.

## Deferred Ideas

- Standalone smtp-starttls service (email profile covers it).
- Per-protocol modern-baseline variants (tls-modern already provides a clean baseline).

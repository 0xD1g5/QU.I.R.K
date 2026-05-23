# Phase 89: Chaos Lab Profiles - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add new TLS chaos-lab profiles and verify identity-lab evidence end-to-end (LAB-01..06). Per the LAB-03 decision below, this delivers **four new profiles** (postgres-tls, redis-tls, kafka-tls, grpc-tls) — smtp-starttls is closed as already-covered. Every profile change carries the mandatory CLAUDE.md lab-sync (docker-compose.yml + lab.sh ALL_PROFILES + README + expected_results_*.md in the same change).

**Not in scope:** new scanner capabilities (the scanners already handle these protocols — this is lab/config + verification work), modern-baseline duplicates (tls-modern already exists), a standalone smtp-starttls service.
</domain>

<decisions>
## Implementation Decisions

### LAB-03 — smtp-starttls disposition
- **D-01:** **Close LAB-03 as already-covered** by the existing `email` profile (Postfix+Dovecot, weak RSA-2048 TLS, STARTTLS on 587 — `quantum-chaos-enterprise-lab/docker-compose.yml` ~line 991, `labs/email/`). Do NOT add a separate smtp-starttls service. Deliverable: add an explicit expected-results / UAT note proving the scanner detects STARTTLS posture on the email profile's 587, and document in the requirement closure that smtp-starttls coverage lives in the `email` profile. This is a documented "already-covered" closure, not a skipped requirement.

### TLS config posture (postgres/redis/kafka/grpc)
- **D-02:** Each new profile exposes an **intentionally weak/legacy TLS config** (single variant) so the scanner emits real findings — the lab's purpose is to exercise detection. `expected_results_*.md` assert those findings. Clean modern baselines already exist via `tls-modern`; do NOT add modern duplicates. (Mirrors the existing `tls-cert-defects` weak-config pattern.)

### LAB-05 — gRPC endpoint + ALPN-h2
- **D-03:** Build the **custom minimal Go gRPC-TLS image** (ALPN `h2`) as specced. The executor's FIRST task for this profile brings the service up and runs sslyze to **confirm ALPN-h2 negotiation before wiring the probe approach**. If sslyze cannot negotiate h2, that surfaces as an in-flight blocker/deviation (not a silent fallback). No separate spike phase — the empirical confirmation is execution-time task 1. (Honors the pending todo's "verify sslyze negotiates ALPN h2 before finalizing probe approach.")

### LAB-06 — identity evidence verification
- **D-04:** Add Kerberos/SAML/DNSSEC targets to an **existing lab scan config** (not a new dedicated config) + a **UAT asserting all three evidence counters flow end-to-end into the identity subscore** against the live identity profile. Research confirms the counter code is already wired (BACK-78); the gap is scan-config + UAT coverage, so this is verification + config, not new detection code.

### Claude's Discretion
- Exact weak-TLS knobs per protocol (cipher/version/cert choices), port assignments, the gRPC Dockerfile internals, and which existing scan config hosts the identity targets — implementation details for the planner/researcher, grounded in the v5.0 research files and existing lab patterns.

### Carried forward (locked — not re-asked)
- **Digest-pin every new image** (not `:latest`) — enforced by `tests/test_chaos_lab_image_pinning.py` (Phase 82). The Bitnami-free namespace lesson applies (`bitnamilegacy/*` for any Bitnami images).
- **Lab-sync rule (CLAUDE.md):** every profile add/change updates `docker-compose.yml` + `lab.sh` ALL_PROFILES + the chaos-lab README + the `expected_results_*.md` oracle in the SAME change. A profile is not "done" until all four reflect it.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v5.0 project research (protocol TLS specifics)
- `.planning/research/kafka-tls-research.md` — Kafka TLS listener (apache/kafka:3.9.0, PEM keystore, 9093 TLS + 9092 plaintext healthcheck) — LAB-04.
- `.planning/research/redis-broker-architecture-research.md` — Redis direct-socket TLS on 6380 against redis:7.4.1-alpine — LAB-02.
- `.planning/research/email-tls-research.md` — email/STARTTLS specifics — relevant to the LAB-03 already-covered closure.
- `.planning/research/rabbitmq-amqp-research.md` — broker TLS context.

### Chaos lab infrastructure (lab-sync targets)
- `quantum-chaos-enterprise-lab/docker-compose.yml` — profile definitions (existing `email` profile ~line 991; `tls-modern`, `tls-cert-defects` patterns).
- `quantum-chaos-enterprise-lab/lab.sh` — ALL_PROFILES list (MUST include every new profile) + status/logs.
- `quantum-chaos-enterprise-lab/README.md` and `expected_results_v4.md` — the oracle each new profile's ports/services/expected findings must be added to.
- `labs/{broker,email,...}/` — existing per-profile Dockerfile/cert-gen patterns to mirror.

### Scanner code (verify-works, not modify)
- `quirk/scanner/broker_scanner.py` — Redis-TLS probe (LAB-02 confirm), Kafka.
- identity scanners (Kerberos/SAML/DNSSEC) + evidence counters → identity subscore (LAB-06 confirm flow).

### Gates / rules
- `tests/test_chaos_lab_image_pinning.py` — digest-pin gate (Phase 82).
- `./CLAUDE.md` — Chaos Lab Maintenance rule (lab.sh + README + expected_results in same change).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `email` profile (Postfix+Dovecot STARTTLS) — already covers smtp-starttls (D-01).
- `tls-cert-defects` weak-config profile — the template for D-02 weak TLS configs.
- `lab.sh` ALL_PROFILES + `--profile` arg pattern — new profiles plug in here.
- `broker_scanner.py` Redis/Kafka probes — already handle the protocols; lab provides targets.

### Established Patterns
- Digest-pinned images; `bitnamilegacy/*` namespace for Bitnami images (Phase 82 lesson).
- Per-profile `labs/<name>/` Dockerfile + cert-gen Makefile.
- expected_results_*.md oracle entry per profile (ports, services, expected findings).

### Integration Points
- docker-compose.yml profiles; lab.sh ALL_PROFILES; README profile table; expected_results oracle.
- Identity scan config (LAB-06 targets).
</code_context>

<specifics>
## Specific Ideas

- The lab's purpose is to *exercise detection* — hence weak configs over clean baselines (D-02).
- gRPC ALPN-h2 is the known risk: confirm sslyze handles it empirically before committing the probe (D-03).
</specifics>

<deferred>
## Deferred Ideas

- A standalone `smtp-starttls` service — not needed; the `email` profile covers it (D-01). Revisit only if smtp-starttls must be scannable independently of the fuller email stack.
- Modern-baseline variants for the 4 new protocols — `tls-modern` already provides a clean baseline; per-protocol modern duplicates deferred unless a future phase needs them.
</deferred>

---

*Phase: 89-chaos-lab-profiles*
*Context gathered: 2026-05-22*

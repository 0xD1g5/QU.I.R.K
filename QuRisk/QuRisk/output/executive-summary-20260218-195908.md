# Quantum Crypto Readiness - Interactive

## Executive Summary
- **Generated:** 2026-02-18 19:59 UTC
- **Owner:** Security Team
- **Data classification:** confidential

## Quantum Readiness Score
**Score:** **82/100**  
**Rating:** **GOOD**

### Score Breakdown (drivers)
- No successful TLS/SSH deep scans (visibility gap) (**-10**)
- Moderate-long confidentiality requirement (7+ years) (**-3**)
- Plaintext HTTP services detected (**-2**)
- Mixed exposure (internal + internet-facing) (**-2**)
- Unknown open services detected (**-1**)

## Discovery and Coverage
- **TLS endpoints successfully scanned:** 0
- **SSH endpoints successfully scanned:** 0
- **Plaintext HTTP services detected:** 4
- **Unknown open services detected:** 2

## Findings Overview (Executive-Relevant)
- **High-impact items (CRITICAL + HIGH):** 0
- **CRITICAL:** 0
- **HIGH:** 0
- **MEDIUM:** 4
- **LOW:** 2

## Interpretation
- Quantum Readiness Score is **82/100** (**GOOD**).
- Top score drivers: No successful TLS/SSH deep scans (visibility gap) (-10); Moderate-long confidentiality requirement (7+ years) (-3); Plaintext HTTP services detected (-2).
- No successful deep TLS/SSH handshakes were captured in this run; expand visibility (scope, segmentation allowances, and ports) to improve confidence.
- High-impact items (CRITICAL+HIGH): **0**. Near-term hygiene accelerates crypto agility and reduces baseline risk.

## Transition Roadmap

### Wave 1 — Hygiene (0–6 months)
- **Eliminate plaintext HTTP where feasible (especially management interfaces)** — Plaintext endpoints undermine identity, session security, and governance.
  - Deliverable: HTTP→HTTPS migration list; TLS termination pattern selection
  - Owner: Infra + Platform Teams | Effort: M
- **Certificate lifecycle hygiene and ownership validation** — Operational discipline reduces outages and enables future algorithm agility.
  - Deliverable: Inventory with owners; renewal SLAs; automation backlog (managed PKI/ACME where possible)
  - Owner: PKI/Identity + Service Owners | Effort: S

### Wave 2 — Modernization (6–24 months)
- **Centralize crypto where possible (termination/offload patterns)** — Centralization improves agility: fewer places to change algorithms, keys, and policies.
  - Deliverable: Approved termination architectures (LB/WAF/Gateway patterns) + exceptions process
  - Owner: Architecture + Platform | Effort: L
- **Dependency and library baselining (crypto-agility workstream)** — Most PQC blockers are dependencies (libraries, runtimes, embedded stacks).
  - Deliverable: Crypto dependency SBOM-lite; upgrade candidates; deprecation schedule
  - Owner: AppSec + Engineering | Effort: L

### Wave 3 — PQC Preparation (24+ months)
- **Vendor capability mapping + PQC/hybrid pilot selection** — PQC readiness is vendor- and system-dependent; pilots de-risk timelines.
  - Deliverable: Vendor matrix (TLS/SSH/PKI/Signing); pilot shortlist; success criteria
  - Owner: Security Leadership + Procurement + Architecture | Effort: M
- **Hybrid key exchange and certificate strategy planning** — Hybrid approaches are likely early path to PQC for many stacks.
  - Deliverable: Hybrid design patterns; PKI impact assessment; migration playbook draft
  - Owner: PKI/Identity + Platform Security | Effort: L
- **Program governance (metrics, waves, and change management)** — PQC transition is a multi-year program; governance prevents stall-out.
  - Deliverable: Roadmap cadence; readiness KPI tracking; wave execution plan
  - Owner: Security Program Mgmt | Effort: M

## Recommended Migration Paths (Top Items)
- **Hygiene** — Migrate HTTP→HTTPS. If legacy, front with TLS-terminating reverse proxy and enforce redirects + HSTS where applicable.
  - Target: 192.168.4.1:80 | Severity: MEDIUM
- **Hygiene** — Migrate HTTP→HTTPS. If legacy, front with TLS-terminating reverse proxy and enforce redirects + HSTS where applicable.
  - Target: 192.168.4.21:80 | Severity: MEDIUM
- **Hygiene** — Migrate HTTP→HTTPS. If legacy, front with TLS-terminating reverse proxy and enforce redirects + HSTS where applicable.
  - Target: 192.168.4.21:443 | Severity: MEDIUM
- **Hygiene** — Migrate HTTP→HTTPS. If legacy, front with TLS-terminating reverse proxy and enforce redirects + HSTS where applicable.
  - Target: 192.168.4.21:8080 | Severity: MEDIUM
- **Modernization** — Fingerprint with a deeper probe or validate service ownership and purpose.
  - Target: 192.168.4.23:8443 | Severity: LOW
- **Modernization** — Fingerprint with a deeper probe or validate service ownership and purpose.
  - Target: 192.168.4.54:80 | Severity: LOW

## Recommended Next Actions (30–60 days)
1. Confirm ownership for TLS termination points and certificate authorities (internal and cloud).
2. Establish certificate lifecycle automation and renewal SLAs; address near-term expirations.
3. Launch crypto-agility baselining (standard TLS patterns, dependency mapping, upgrade paths).
4. Identify 2–3 pilot candidates for PQC/hybrid readiness planning and vendor capability mapping.

# Scorecard Sample Run

## Executive Summary
- **Generated:** 2026-02-19 22:49 UTC
- **Owner:** Security Team
- **Data classification:** internal

## Quantum Readiness Score
**Score:** **85/100**  
**Rating:** **STRONG**

### Score Drivers (Top)
- No successful TLS/SSH deep scans (visibility gap) (**-10**)
- Moderate-long confidentiality requirement (7+ years) (**-3**)
- Mixed exposure (internal + internet-facing) (**-2**)

## Confidence & Coverage (v3.7)
- **Confidence:** **LOW** (58/100)
- **Coverage:** 0.0% (TLS+SSH successful / total in-scope endpoints)
- **TLS Enumeration Coverage:** 0% (TLS-success endpoints with capabilities captured)
- **Top visibility blockers:**
  - CLOSED: 3

## Discovery and Coverage
- **TLS endpoints successfully scanned:** 0
- **SSH endpoints successfully scanned:** 0
- **Plaintext HTTP services detected:** 0
- **Unknown open services detected:** 0

## Findings Overview (Executive-Relevant)
- **High-impact items (CRITICAL + HIGH):** 0
- **CRITICAL:** 0
- **HIGH:** 0
- **MEDIUM:** 0
- **LOW:** 0

## Interpretation
- Quantum Readiness Score is **85/100** (**STRONG**).
- Top score drivers: No successful TLS/SSH deep scans (visibility gap) (-10); Moderate-long confidentiality requirement (7+ years) (-3); Mixed exposure (internal + internet-facing) (-2).
- No successful deep TLS/SSH handshakes were captured in this run; expand visibility (scope, segmentation allowances, and ports) to improve confidence.
- High-impact items (CRITICAL+HIGH): **0**. Near-term hygiene accelerates crypto agility and reduces baseline risk.

## Transition Roadmap

### Wave 1 — Hygiene (0–6 months)
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

## Recommended Next Actions (30–60 days)
1. Confirm ownership for TLS termination points and certificate authorities (internal and cloud).
2. Establish certificate lifecycle automation and renewal SLAs; address near-term expirations.
3. Launch crypto-agility baselining (standard TLS patterns, dependency mapping, upgrade paths).
4. Identify 2–3 pilot candidates for PQC/hybrid readiness planning and vendor capability mapping.

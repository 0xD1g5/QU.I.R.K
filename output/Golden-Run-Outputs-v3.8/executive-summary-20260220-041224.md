# Quantum Crypto Readiness - CLIENT NAME

## Executive Summary
- **Generated:** 2026-02-20 04:12 UTC
- **Owner:** CLIENT NAME
- **Data classification:** confidential

## Quantum Readiness Score
**Score:** **73/100**  
**Rating:** **GOOD**

### Score Drivers (Top)
- High severity items present (**-4**)
- Moderate-long confidentiality requirement (7+ years) (**-3**)
- RSA-2048 widespread (quantum transition needed) (**-2**)
- TLS 1.2 present (TLS 1.3 recommended) (**-2**)
- Mixed exposure (internal + internet-facing) (**-2**)
- Plaintext HTTP services detected (**-1**)
- Unknown open services detected (**-1**)

## Confidence & Coverage (v3.7)
- **Confidence:** **MEDIUM** (78/100)
- **Coverage:** 70.0% (TLS+SSH successful / total in-scope endpoints)
- **TLS Enumeration Coverage:** 100.0% (TLS-success endpoints with capabilities captured)

## Discovery and Coverage
- **TLS endpoints successfully scanned:** 6
- **SSH endpoints successfully scanned:** 1
- **Plaintext HTTP services detected:** 2
- **Unknown open services detected:** 1

## Findings Overview (Executive-Relevant)
- **High-impact items (CRITICAL + HIGH):** 2
- **CRITICAL:** 0
- **HIGH:** 2
- **MEDIUM:** 1
- **LOW:** 0

## Interpretation
- Quantum Readiness Score is **73/100** (**GOOD**).
- Top score drivers: High severity items present (-4); Moderate-long confidentiality requirement (7+ years) (-3); RSA-2048 widespread (quantum transition needed) (-2).
- Successfully profiled **6 TLS** and **1 SSH** endpoints in scope for cryptographic posture.
- High-impact items (CRITICAL+HIGH): **2**. Near-term hygiene accelerates crypto agility and reduces baseline risk.

## Transition Roadmap

### Wave 1 — Hygiene (0–6 months)
- **Eliminate plaintext HTTP where feasible (especially management interfaces)** — Plaintext endpoints undermine identity, session security, and governance.
  - Deliverable: HTTP→HTTPS migration list; TLS termination pattern selection
  - Owner: Infra + Platform Teams | Effort: M
- **Certificate lifecycle hygiene and ownership validation** — Operational discipline reduces outages and enables future algorithm agility.
  - Deliverable: Inventory with owners; renewal SLAs; automation backlog (managed PKI/ACME where possible)
  - Owner: PKI/Identity + Service Owners | Effort: S

### Wave 2 — Modernization (6–24 months)
- **Adopt TLS 1.3 at termination points and standardize modern configs** — TLS 1.3 reduces downgrade/config risk and simplifies crypto baselines.
  - Deliverable: TLS 1.3 enablement plan; standard cipher policy; rollout checklist
  - Owner: Network/LB + App Owners | Effort: M
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
- **Modernization** — Fingerprint with a deeper probe or validate service ownership and purpose.
  - Target: 127.0.0.1:5555 | Severity: MEDIUM
- **Modernization** — A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry.
  - Target: 127.0.0.1:8000 | Severity: HIGH
- **Modernization** — A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry.
  - Target: 127.0.0.1:8444 | Severity: HIGH

## Recommended Next Actions (30–60 days)
1. Confirm ownership for TLS termination points and certificate authorities (internal and cloud).
2. Establish certificate lifecycle automation and renewal SLAs; address near-term expirations.
3. Launch crypto-agility baselining (standard TLS patterns, dependency mapping, upgrade paths).
4. Identify 2–3 pilot candidates for PQC/hybrid readiness planning and vendor capability mapping.

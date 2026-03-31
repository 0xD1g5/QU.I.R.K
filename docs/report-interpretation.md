# QU.I.R.K. Report Interpretation Guide

## 1. Introduction

This guide maps every number, label, and finding in a QU.I.R.K. report to plain English. Use the reference tables offline to prepare for client conversations, and the **Client Conversation** sideboxes during a live meeting when a client asks "what does this mean for us?"

---

## 2. Quantum-Readiness Score

The Quantum-Readiness Score is a single integer from 0 to 100. It summarizes your organization's cryptographic posture across four dimensions: how clean your network is from a cryptographic hygiene standpoint, whether your TLS is up to modern standards, how trustworthy your certificates are, and how well-positioned you are to migrate algorithms when the quantum timeline arrives.

| Score | Rating | What It Means |
|-------|--------|---------------|
| 85–100 | EXCELLENT | Cryptographic posture is strong. Minor gaps exist but pose low near-term risk before quantum timelines. |
| 70–84 | GOOD | Solid posture with addressable gaps. Prioritized improvements recommended within 12 months. |
| 55–69 | MODERATE | Material gaps present. A remediation roadmap is needed and should begin within 90 days. |
| 35–54 | FAIR | Significant exposure. Executive attention and funded remediation required. |
| 0–34 | POOR | Critical gaps. Urgent remediation required before quantum-timeline milestones (CNSA 2.0 migration deadline: 2030). |

> **Client Conversation — Quantum-Readiness Score:**
> "Your score of [X] puts you in the [RATING] band. In practical terms, this means [plain-English for that band]. The score reflects four dimensions: how clean your network is from a cryptographic hygiene standpoint, whether your TLS is up to modern standards, how trustworthy your certificates are, and how well-positioned you are to migrate algorithms when the time comes. We'll walk through each dimension."

---

## 3. The Four Subscores

Each subscore is worth 0–25 points. The four are summed to produce the total Quantum-Readiness Score (0–100). The subscore key names used in the report output are: `hygiene`, `modern_tls`, `identity_trust`, and `agility_signals`.

### 3.1 Hygiene (0–25 points)

Hygiene measures whether your services are using encryption in the first place. It captures plaintext HTTP exposure, HTTP misconfigured on TLS-designated ports, and hosts that couldn't be reached at all.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Plaintext HTTP exposure | −18 pts | HTTP services responding on non-TLS ports |
| HTTP on TLS-designated ports | −16 pts | HTTP found on ports expected to serve TLS (443, 8443, etc.) |
| Scan error rate | −6 pts | Hosts that refused connections or timed out |

> **Client Conversation — Hygiene:**
> "Hygiene measures whether your services are using encryption in the first place. A low score here often means HTTP services are publicly accessible — not a quantum problem, a basic security problem. We recommend addressing these before the quantum migration work."

---

### 3.2 Modern TLS (0–25 points)

Modern TLS measures whether your encryption is current. Legacy TLS versions (1.0 and 1.1) are deprecated by all major browsers and frameworks and have known weaknesses. Services that blocked the assessment also contribute to a lower score.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Legacy TLS versions allowed | −14 pts | TLS 1.0 or 1.1 accepting connections |
| Unknown open services | −6 pts | Open ports that didn't respond to TLS, HTTP, or SSH |
| Assessment visibility blockers | −5 pts | Hosts that blocked the scan |

> **Client Conversation — Modern TLS:**
> "Modern TLS measures whether your encryption is current. TLS 1.0 and 1.1 have known weaknesses and are officially deprecated by all major browsers and frameworks. If this score is low, some of your services are still advertising support for these versions — which needs to be addressed regardless of the quantum timeline."

---

### 3.3 Identity Trust (0–25 points)

Identity Trust measures certificate health. This subscore captures expired and self-signed certificates (which cause browser warnings and break trust chains) and rewards services that enforce mutual TLS (mTLS).

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Expired certificates | −14 pts | Certificates past their `Not After` date |
| Expiring certificates | −7 pts | Certificates expiring within 30 days |
| Self-signed certificates | −9 pts | Certificates not issued by a trusted CA |
| mTLS enforcement | +6 pts | Mutual TLS required — services verify client identity |

> **Client Conversation — Identity Trust:**
> "Identity Trust measures certificate health. Expired and self-signed certs cause browser warnings and break trust chains — clients see padlock errors before you even get to quantum risk. The mTLS bonus reflects services that require both parties to authenticate, which is a positive signal for your zero-trust posture."

---

### 3.4 Agility Signals (0–25 points)

Agility measures how ready you are to swap out cryptographic algorithms when the time comes. RSA is quantum-vulnerable and harder to migrate than ECDSA because it's more deeply embedded in older infrastructure. ECDSA adoption is a positive signal that engineering teams are already comfortable with modern key types.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| High-impact findings ratio | −14 pts | Proportion of findings rated HIGH or CRITICAL |
| Unknown service inventory | −6 pts | Services that couldn't be identified |
| RSA-only posture | −8 pts | Only RSA key types found, no ECDSA (harder to migrate) |
| ECDSA adoption | +4 pts | At least one ECDSA certificate found |

> **Client Conversation — Agility Signals:**
> "Agility measures how ready you are to swap out cryptographic algorithms when the time comes. RSA is quantum-vulnerable, but it's also harder to migrate than ECDSA because it's more deeply embedded in older infrastructure. Seeing ECDSA adoption is a good signal — it means your engineering team is already comfortable with modern key types, which makes the quantum migration path shorter."

---

## 4. Severity Tiers

Every finding in a QU.I.R.K. report is assigned one of five severity levels. CRITICAL and HIGH indicate active risk that should be addressed immediately or within 30 days, independent of any quantum threat. MEDIUM and LOW require a remediation schedule. INFO items are planning advisories.

| Severity | Color | What It Means | Recommended Response |
|----------|-------|---------------|---------------------|
| CRITICAL | Red | Cryptographic failure with no mitigation — e.g., `alg:none` JWT (unsigned tokens), broken cipher in active use | Immediate remediation — stop using this in production |
| HIGH | Orange | Active risk with known exploit path — e.g., plaintext HTTP, HTTP on TLS port | Remediate within 30 days |
| MEDIUM | Yellow | Risk that degrades posture but no immediate exploit — e.g., TLS handshake blocked assessment, unknown services | Investigate and validate within 90 days |
| LOW | Blue | Technical debt or deprecated standard — e.g., legacy TLS 1.0/1.1 allowed | Schedule upgrade — typically 1–2 sprint cycles |
| INFO | Gray | Observations and planning advisories — e.g., quantum migration advisories, mTLS signals | Awareness — no immediate action required |

> **Client Conversation — Severity Tiers:**
> "We use five severity levels. CRITICAL and HIGH are things we'd want fixed in the next 30 days — they're risks you have right now, today, independent of any quantum threat. MEDIUM and LOW are things that need a remediation schedule. INFO items are planning advisories — they tell you what to think about for the quantum migration, but there's no immediate action required."

---

## 5. Common Finding Types

The table below maps every common finding title to its plain-English explanation and the recommended client action.

| Finding | Severity | Plain-English Explanation | Client Action |
|---------|----------|--------------------------|---------------|
| Plaintext HTTP service detected | HIGH | Service responding over HTTP with no TLS | Enable TLS, redirect HTTP → HTTPS |
| HTTP on TLS-designated port | HIGH | HTTP found on port 443 or 8443 (expected TLS) | Check service config — likely misconfigured |
| Legacy TLS versions allowed (TLS 1.0/1.1) | LOW | Server still advertises deprecated protocol versions | Disable TLS 1.0/1.1 in server config |
| Expired certificate | CRITICAL | Certificate past its `Not After` date | Renew certificate immediately |
| Self-signed certificate | MEDIUM | Certificate not issued by a trusted CA | Replace with CA-issued cert |
| TLS handshake blocked assessment | MEDIUM | Service refused connection or required client cert | Validate service config; add to exclusions if expected |
| SSH quantum planning advisory | INFO | SSH host key or KEX algorithm is quantum-vulnerable (RSA/ECDH) | Plan CRYSTALS-Kyber/ML-KEM migration for post-quantum OpenSSH |
| Unknown open service | MEDIUM | Open port did not respond to TLS, HTTP, or SSH probes | Inventory this service; close if unneeded |
| mTLS required | INFO | Service requires client certificate — positive signal | No action; note for zero-trust posture documentation |

---

## 6. CBOM Quantum Safety Labels

The Cryptographic Bill of Materials (CBOM) is an inventory of every cryptographic algorithm found in your environment. Each algorithm is classified with one of three quantum safety labels.

| Label | Meaning | Example Algorithms |
|-------|---------|-------------------|
| `quantum-safe` | Resistant to both classical and quantum attacks at current NIST security levels | AES-256-GCM, AES-128, SHA-384, HMAC-SHA512, ML-KEM-768, ML-DSA-65, SLH-DSA |
| `quantum-vulnerable` | Broken by Shor's algorithm (asymmetric) or Grover-weakened (symmetric with < 256-bit key) | RSA (any size), ECDSA, ECDH, DH, SHA-256, AES-128 (marginal) |
| `unknown` | Algorithm not recognized or no cryptography present (e.g., `alg:none` JWT) | `alg:none`, unrecognized algorithm names |

> **Client Conversation — CBOM Quantum Labels:**
> "The CBOM — Cryptographic Bill of Materials — is an inventory of every cryptographic algorithm we found in your environment. Each algorithm is labeled quantum-safe, quantum-vulnerable, or unknown. Quantum-vulnerable doesn't mean you're at risk today — it means these algorithms will be broken when large-scale quantum computers become available, which NIST projects around 2030–2035 for currently deployed RSA key sizes. The CBOM gives you a roadmap of what to migrate."

---

## 7. Migration Roadmap

The migration roadmap organizes findings and recommendations into three planning horizons. This structure maps to the NOW / NEXT / LATER framework in the QU.I.R.K. report output.

| Horizon | Scope | Typical Timeline |
|---------|-------|-----------------|
| **NOW** | Critical and High severity items; classical security risks requiring immediate action | Within 30 days |
| **NEXT** | Medium severity items; modernization work for quantum-vulnerable algorithms still widely supported | 90 days to 12 months |
| **LATER** | Long-horizon quantum migration; CRYSTALS-Kyber (ML-KEM), ML-DSA adoption when standards finalize in your ecosystem | 2026–2030 (NIST FIPS 203/204/205 window) |

- **NOW** — Fix active classical security problems first. These are risks you have today, regardless of quantum. A client cannot justify deferring an expired certificate or plaintext HTTP service because "we'll handle everything during the quantum migration."
- **NEXT** — Early quantum preparation that fits into the normal modernization cycle. Disabling legacy TLS, replacing self-signed certificates, and adopting ECDSA are all work your team can do in regular sprint cycles without waiting for post-quantum standards to stabilize.
- **LATER** — The full post-quantum migration. This is the NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA) work. Most organizations will execute this between 2026 and 2030, aligned with the NSA CNSA 2.0 migration deadline.

> **Client Conversation — Migration Roadmap:**
> "The migration roadmap is organized in three horizons. 'Now' items are things with known classical risk today — they need to be fixed regardless of quantum. 'Next' items are the early quantum-preparation work you can do in your normal modernization cycle. 'Later' items are the full post-quantum migration — that's the NIST FIPS 203/204/205 standards work that most organizations will execute between 2026 and 2030."

---

*For scoring implementation details, see `quirk/intelligence/scoring.py`. For finding severity logic, see `quirk/engine/risk_engine.py`. For CBOM classification, see `quirk/cbom/classifier.py`.*

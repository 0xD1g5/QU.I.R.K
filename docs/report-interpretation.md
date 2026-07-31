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
| Code-signing cert weak algorithm | −6 pts | Ratio of code-signing certificates with weak algorithm (RSA < 2048-bit, EC < 256-bit, or SHA-1) to total code-signing certificates found (Phase 95, `agility_codesign_weak_algo_ratio`; SCORE_WEIGHTS sum: 299.0) |

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
| SSH quantum planning advisory | INFO | SSH host key or KEX algorithm is quantum-vulnerable (RSA/ECDH) | Plan migration to post-quantum SSH using ML-KEM (FIPS 203) when OpenSSH support lands |
| Unknown open service | MEDIUM | Open port did not respond to TLS, HTTP, or SSH probes | Inventory this service; close if unneeded |
| mTLS required | INFO | Service requires client certificate — positive signal | No action; note for zero-trust posture documentation |
| CODE-SIGN/weak-algorithm | HIGH | Code-signing certificate uses a weak key or hash: RSA < 2048-bit, EC < 256-bit, or SHA-1 signature algorithm | Replace the signing certificate with RSA ≥ 2048-bit / SHA-256 or an ECDSA P-256+ key; re-sign artifacts with the new cert |

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
| **LATER** | Long-horizon quantum migration: adopt ML-KEM (FIPS 203) for key exchange and ML-DSA (FIPS 204) or SLH-DSA (FIPS 205) for signatures as your ecosystem ships PQC support. Per NIST IR 8547, RSA and ECC are deprecated after 2030 and disallowed after 2035. | 2026–2030 (NIST FIPS 203/204/205 window) |

- **NOW** — Fix active classical security problems first. These are risks you have today, regardless of quantum. A client cannot justify deferring an expired certificate or plaintext HTTP service because "we'll handle everything during the quantum migration."
- **NEXT** — Early quantum preparation that fits into the normal modernization cycle. Disabling legacy TLS, replacing self-signed certificates, and adopting ECDSA are all work your team can do in regular sprint cycles without waiting for post-quantum standards to stabilize.
- **LATER** — The full post-quantum migration. This is the NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA) work. Most organizations will execute this between 2026 and 2030, aligned with the NSA CNSA 2.0 migration deadline.

> **Client Conversation — Migration Roadmap:**
> "The migration roadmap is organized in three horizons. 'Now' items are things with known classical risk today — they need to be fixed regardless of quantum. 'Next' items are the early quantum-preparation work you can do in your normal modernization cycle. 'Later' items are the full post-quantum migration — that's the NIST FIPS 203/204/205 standards work that most organizations will execute between 2026 and 2030."

---

## 8. Compliance Summary

QU.I.R.K. now maps each finding to **PCI-DSS 4.0.1, HIPAA 45 CFR, and FIPS 140-3** control references and renders them in a "Compliance Summary" section of the HTML and PDF reports. This makes the report directly usable as evidence in client compliance assessments — the assessor doesn't have to translate technical findings to control language.

The section is grouped into three framework subsections (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3). Each subsection renders a table with four columns: **Severity**, **Finding**, **Control reference + version** (e.g., `4.2.1` at `4.0.1`), and a **Source URL with the last-verified date**. The source URL points to the authoritative regulator publication (PCI Security Standards Council, the eCFR, or NIST CSRC) — never a third-party summary — so an assessor can click through and confirm the control text directly.

A separate "**Findings without compliance mapping**" subsection lists any findings whose title is not in `COMPLIANCE_MAP`. This surfaces coverage gaps so the assessor (or the operator preparing for the engagement) can confirm whether the absence is intentional — informational findings, observability advisories, scan-error categories — or a real gap that needs a mapping update before the report ships.

The compliance map's review cadence and upgrade procedure for regulator revisions is documented in `docs/operators-guide.md` (Phase 50 — TODO at the time of writing).

Operators can verify compliance map freshness before a client engagement by running `quirk compliance status` (use `--format json` for machine-readable output). The command prints the map version, oldest `last_verified` date, and source URL per framework, so the operator can confirm the map hasn't gone stale (default staleness threshold: 365 days) since the last release.

> **Client Conversation — Compliance Summary:**
> "We've mapped each finding to the controls your auditor cares about — PCI-DSS, HIPAA, and FIPS 140-3. Each row links back to the regulator's official publication so your assessor can confirm the control text directly. The 'Findings without compliance mapping' section is intentional transparency — it tells you which findings are informational versus which are unmapped gaps we're actively closing."

---

---

## 9. QRAMM Governance Assessment Section

The combined PDF includes a QRAMM (Quantum Readiness & Maturity Model) Governance Assessment section that begins on a new page after the Migration Roadmap. This section is intended to be read alongside the technical findings — it gives executives and CISOs the governance context for the scanner-derived crypto inventory.

### What the section contains

- **Radar chart (inline SVG)** — Rendered first in the section. A four-axis polygon plotting the four QRAMM dimensions: CVI (Cryptographic Visibility & Inventory), SGRM (Standards & Governance Risk Management), DPE (Data Protection & Encryption), and ITR (Incident & Transition Readiness). The polygon shows the session's raw dimension scores on a 0–4 scale; closer to the outer edge means higher maturity.
- **Executive intro paragraph** — A one-sentence summary identifying that the section reflects the most recent completed QRAMM assessment.
- **Dimension Scorecard table** — Four rows (one per dimension) with raw score, weighted score, and overall maturity level.
- **Compliance Framework Coverage summary** — An 8-row table mapping the assessment to NIST PQC Standards, NSM-10, CNSA 2.0, ISO 27001:2022, ETSI Quantum-Safe, PCI-DSS v4.0, Common Criteria, and BSI TR-02102. Each framework shows a coverage tier badge: **Scanner-informed** (the QUIRK scanner contributes signal — currently CVI only) or **Manual only** (the framework's relevance is derived purely from manual assessment answers).
- **Per-framework practice detail** — Below the summary table, eight subsections (one per framework) flow continuously without page breaks. Each shows every practice area's relevance score and whether it was scanner-informed.

### When no QRAMM assessment has been completed

The QRAMM section heading still appears in the PDF, but the body shows only:

> "No QRAMM assessment completed — run an assessment from the dashboard to populate this section."

This keeps the PDF structure consistent across all engagements and signals that the QRAMM capability exists.

### Coverage caveat

QUIRK's scanner directly informs the CVI dimension (cryptographic visibility from real findings). SGRM, DPE, and ITR require manual assessment input via the dashboard's QRAMM questionnaire. The footnote in the PDF reflects this:

> "Coverage reflects QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment."

> **Client Conversation — QRAMM Governance Assessment:**
> "The QRAMM section of the PDF gives you the governance layer — how your organization's policies, processes, and readiness posture map to the cryptographic risks we found in the technical scan. The radar chart shows maturity across four dimensions. CVI — Cryptographic Visibility — is the only dimension informed directly by the scanner findings. The other three dimensions reflect your answers in the assessment questionnaire. If you haven't completed an assessment yet, that section will show a placeholder — we can walk through it together after the technical findings review."

---

## 10. Hardware Inventory

When hardware scanning is enabled, QUIRK fingerprints network and IoT devices — switches, routers, and similar equipment — via SSH, HTTP, and SNMP probes. Fingerprinted devices are recorded in the CBOM and surfaced in the dashboard as a structured DEVICE/FIRMWARE component hierarchy alongside the algorithm inventory.

### 10.1 The DEVICE / FIRMWARE Component Hierarchy

Each hardware device found during a scan is represented by two linked components in the CBOM:

**DEVICE parent component** — the device identity. The CBOM component name is formatted as `"{vendor} {model}"` (for example, `"Cisco Catalyst 9300"` or `"Unknown Unknown"` when fingerprinting is incomplete). The DEVICE component carries the `quirk:hw-tier` property, which holds the CNSA 2.0 remediation tier assigned to that device class.

**FIRMWARE child component** — the endpoint detail found at the probe address. The CBOM component name is formatted as `"hw:{host}:{port}"` (for example, `"hw:192.168.1.1:443"`). The FIRMWARE component carries these properties:

- `quirk:hw-vendor` — vendor name from SNMP fingerprinting
- `quirk:hw-model` — model name from SNMP fingerprinting
- `quirk:hw-pqc-supported` — whether the device has a known PQC firmware upgrade path
- `quirk:hw-remediation-tier` — CNSA 2.0 tier assigned to this endpoint
- `quirk:hw-bridge-status` — crypto-bridge status, when crypto-bridge detection applies
- `quirk:hw-snmp-oid` — raw sysObjectID OID string, when SNMP fingerprinting was used

**Reading the Hardware Inventory section of the dashboard CBOM tab**

The Hardware Inventory section appears on the CBOM tab, below the existing algorithm table on the same scrollable page (there is no separate sub-tab). It is omitted entirely when no hardware devices were found in the scan. Each row is tagged with a `[DEVICE]` badge (showing device identity) or a `[FIRMWARE]` badge (showing nested endpoint detail).

| Field | Meaning |
|-------|---------|
| `host` | IP address or hostname of the probed endpoint |
| `port` | Port number of the probed endpoint |
| `vendor` | Device vendor from SNMP fingerprinting (e.g., `"Cisco"`, `"Juniper"`, `"Unknown"`) |
| `model` | Device model from SNMP fingerprinting (e.g., `"Catalyst 9300"`, `"Unknown"`) |
| `pqc_status` | Whether the device has a known PQC upgrade path: `"supported"`, `"unsupported"`, or `"unknown"` |
| `remediation_tier` | CNSA 2.0 remediation tier: `"Tier 1"`, `"Tier 2"`, `"Tier 3"`, or `"Tier N/A"` |

### 10.2 Hardware Findings Are Advisory-Only

Hardware devices appear in the CBOM and on the dashboard, but **do not contribute points to any of the four subscores**. They are advisory-only findings. CNSA 2.0 remediation tiers are informational guidance that informs the remediation roadmap — not inputs to the numeric quantum-readiness score. The score measures the cryptographic posture of scanned services and endpoints; hardware device tiers are informational guidance layered on top of that posture.

> **Client Conversation — Hardware Devices Detected:**
> "The hardware devices we found are captured in the CBOM and assigned CNSA 2.0 remediation tiers — those are the Tier 1 through Tier N/A labels you see in the Hardware Inventory section. They're advisory findings, which means they inform your remediation roadmap but they don't change the quantum-readiness score. The score measures your services' and endpoints' cryptographic posture — TLS health, certificate validity, algorithm agility. Hardware device tiers are a separate informational layer that tells you which network devices need to be replaced or upgraded on the quantum timeline, but they don't feed into the four subscores. So yes, the score stayed the same when we found those devices — that's by design."

### 10.3 Enabling Hardware Scanning

Hardware scanning is disabled by default and requires the `[hw]` optional extra. For configuration steps — including enabling SNMP, setting the community string, understanding CNSA 2.0 tier definitions, and crypto-bridge detection — see `docs/operators-guide.md §9` (§9.1 Enable SNMP Scanning, §9.2 CNSA 2.0 Remediation Tiers, §9.3 Crypto-Bridge Detection).

### 10.4 SNMP Version / Security-Level Column (Phase 139)

As of Phase 139, HTML and DOCX Hardware Inventory tables (and the dashboard hardware view)
include an **SNMP** column showing the negotiated SNMP version and security level for each
probed endpoint. This reflects the v3 → v2c → none fallback ladder documented in
`docs/operators-guide.md` §9.1.1, and is distinct from — and independent of — the
`pqc_status`/`remediation_tier` advisory columns.

| Label | Meaning |
|-------|---------|
| `v3 auth+priv` | SNMPv3 succeeded with **both** authentication and encryption (privacy) negotiated — the strongest supported mode. Only this label writes the `snmp_auth_protocol`/`snmp_priv_protocol` values shown elsewhere in the report. |
| `v3 noAuthNoPriv` | SNMPv3 succeeded but **without** authentication or encryption negotiated. **This is NOT authenticated v3** — it carries essentially the same trust posture as an SNMPv2c community-string scan, despite using the v3 protocol version. Do not read this label as "v3 was secured." |
| `v2c` | The endpoint was scanned with plain SNMPv2c (community string) — either no `snmp_v3_credentials` entry was configured for this host, or v3 was never attempted. This is the original, still-fully-supported scanning path from v5.8. |
| `v3 failed → v2c` | A `snmp_v3_credentials` entry **was** configured for this host, but the v3 authentication attempt failed (bad username/passphrase/protocol mismatch), and QUIRK fell back to v2c. **This signals a real credential problem worth investigating** — it is not the same as an intentional v2c-only scan and should not be dismissed as normal. |
| `No SNMP` | SNMP was attempted (v3 and/or v2c) but the host produced no response at all. |
| `—` (em-dash) | SNMP was never attempted against this host (e.g. `--enable-snmp` was not set, or hardware scanning found this device via SSH/HTTP only). |

> **Client Conversation — SNMPv3 vs SNMPv2c:**
> "The SNMP column tells you how strongly each device's management interface was authenticated during the scan. `v3 auth+priv` is the gold standard — encrypted and authenticated. `v3 noAuthNoPriv` looks like v3 but offers no real security improvement over the plain community-string scan, so don't read too much into the version number alone. And if you see `v3 failed → v2c`, that's worth a follow-up — it means we had credentials configured for that device and they didn't work, which is different from simply not having configured v3 credentials at all."

### 10.5 SNMP-Confirmed Bridge Mitigation (Phase 140)

As of Phase 140, the crypto-bridge annotation introduced in §9.3 of `docs/operators-guide.md`
has a second, stronger status alongside `partial_only`: `upstream_mitigated`. Both values are
advisory-only and both appear in the same Bridge Status column/badge across the HTML, PDF, DOCX,
and dashboard `/hardware` surfaces.

| `bridge_status` | Badge label | Color | What it means |
|------------------|-------------|-------|----------------|
| `partial_only` | "Partial (assumed)" | Amber | A PQC-capable gateway and a legacy backend were both found on the same /24 subnet (proximity heuristic — see §9.3). No confirmation that traffic actually flows through the gateway. |
| `upstream_mitigated` | "SNMP-confirmed" | Blue | The paired gateway's own ARP table (`ipNetToMediaTable`, walked via SNMP) was found to list the legacy backend's IP address — a stronger, evidence-gated signal that the legacy device sits behind the gateway on this network segment. |

**`upstream_mitigated` is never auto-assigned from subnet co-presence alone.** It requires SNMP
evidence collected from the gateway itself (a sensor-side ARP-table walk against
`ipNetToMediaTable`, OID `1.3.6.1.2.1.4.22.1.2`) that lists the legacy device's IP. If that
evidence is absent or doesn't match, the pair stays `partial_only` — QUIRK never guesses.

**The mandatory caveat.** Every surface where `upstream_mitigated` renders — HTML, PDF, DOCX,
and the dashboard `/hardware` tab (as a tooltip and an inline banner) — carries this verbatim
sentence:

> "Based on SNMP-derived network-path evidence; not independently confirmed by traffic inspection."

This is intentional: SNMP ARP-table evidence is a network-path signal, not a traffic-inspection
confirmation (e.g. packet capture or flow analysis). Treat `upstream_mitigated` as a stronger
signal than `partial_only`, not as an unqualified guarantee of end-to-end quantum-safe coverage.

**Blue, never green.** The `upstream_mitigated` badge uses blue, deliberately never the green
"fully resolved" color used elsewhere in the report — a confirmed bridge is still advisory
context, not a clean bill of health.

**Score impact: none.** Like `partial_only`, `upstream_mitigated` does **not** reduce the
device's remediation requirement and does **not** affect the quantum-readiness score. The legacy
backend still needs replacement or firmware upgrade per its CNSA 2.0 tier (§9.2). The bridge
annotation — at either status — is advisory context about network topology, never a mitigation
credit.

> **Client Conversation — `upstream_mitigated`:**
> "You'll notice some devices show a blue 'SNMP-confirmed' badge instead of the amber 'Partial
> (assumed)' one. That means we found direct SNMP evidence — the gateway's own ARP table lists
> that legacy device — rather than just inferring it from subnet proximity. It's a stronger
> signal, but it's still based on network-path evidence, not traffic inspection, and it doesn't
> change the readiness score or the remediation timeline. The legacy device still needs to be
> replaced or upgraded on schedule."

---

*For scoring implementation details, see `quirk/intelligence/scoring.py`. For finding severity logic, see `quirk/engine/risk_engine.py`. For CBOM classification, see `quirk/cbom/classifier.py`. For the compliance mapping module, see `quirk/compliance/__init__.py`. For QRAMM implementation details, see `quirk/qramm/` and `src/dashboard/src/pages/print.tsx`. For hardware scanning and CBOM device hierarchy, see `quirk/scanner/hardware/` and `quirk/cbom/builder.py`.*

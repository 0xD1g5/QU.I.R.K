# QU.I.R.K. Report Interpretation Guide

## 1. Introduction

This guide maps every number, label, and finding in a QU.I.R.K. report to plain English. Use the reference tables offline to prepare for client conversations, and the **Client Conversation** sideboxes during a live meeting when a client asks "what does this mean for us?"

---

## 2. Quantum-Readiness Score

The Quantum-Readiness Score is a single integer from 0 to 100. It summarizes your organization's cryptographic posture across up to six domains: how clean your network is from a cryptographic hygiene standpoint, whether your TLS is up to modern standards, how trustworthy your certificates are, how well-positioned you are to migrate algorithms when the quantum timeline arrives, and how well stored data (data at rest) and data in transit over email and message brokers (data in motion) are protected. A domain the scan had no evidence for is left out of the score rather than counted (see §3.6).

| Score | Rating | What It Means |
|-------|--------|---------------|
| 85–100 | EXCELLENT | Cryptographic posture is strong. Minor gaps exist but pose low near-term risk before quantum timelines. |
| 70–84 | GOOD | Solid posture with addressable gaps. Prioritized improvements recommended within 12 months. |
| 55–69 | MODERATE | Material gaps present. A remediation roadmap is needed and should begin within 90 days. |
| 35–54 | FAIR | Significant exposure. Executive attention and funded remediation required. |
| 0–34 | POOR | Critical gaps. Urgent remediation required before quantum-timeline milestones. |

> **Client Conversation — Quantum-Readiness Score:**
> "Your score of [X] puts you in the [RATING] band. In practical terms, this means [plain-English for that band]. The score reflects up to six dimensions: how clean your network is from a cryptographic hygiene standpoint, whether your TLS is up to modern standards, how trustworthy your certificates are, how well-positioned you are to migrate algorithms when the time comes, and how well your stored data and your data in transit are protected where we scanned them. We'll walk through each dimension."

**The table above shows the band a score maps to.** An open CRITICAL finding limits the score
itself, not only the band: a scan with at least one open CRITICAL finding scores 34 or lower, which
is `POOR`, and five or more score 25 or lower (see §3.6 for the ceilings). That holds for the
headline score in the reports and on the dashboard's Executive page, scan history and Compare page.
The trend timeline and the multi-sensor merge scores are computed without findings, so this
ceiling never binds there (§3.6). On reports from before
scoring v3 the same protection was a band-only floor, so an 89/100 score could read `FAIR` rather
than `EXCELLENT` — see §19, "The Severity Floor," for both behaviours.

---

## 3. The Six Subscores

Each subscore is worth 0–25 points. The headline Quantum-Readiness Score (0–100) is computed from the subscores of the domains that were actually assessed, rescaled to 0–100 (see §3.6). The subscore key names used in the report output are: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, and `data_in_motion`. §3.1–§3.4 describe the first four; §3.5 describes the last two. The impact figures in the §3.1–§3.4 tables are maximums, reached when every assessed endpoint or certificate is affected: a ratio-based driver scales with the square root of the affected share, so a quarter of the certificates being expired costs half of its maximum (7 of 14 points).

### 3.1 Hygiene (0–25 points)

Hygiene measures whether your services are using encryption in the first place. It captures plaintext HTTP exposure, HTTP misconfigured on TLS-designated ports, and endpoints whose probe recorded an error.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Plaintext HTTP exposure | −18 pts | HTTP services responding on non-TLS ports |
| HTTP on TLS-designated ports | −16 pts | HTTP found on ports expected to serve TLS (by default 443, 4433, 5001, 8443, 9443 and 10443, plus any `scan.tls_designated_ports` you configure) |
| Scan error rate | −6 pts | Share of probed endpoints whose probe recorded a scan error (for example a connection error or timeout) |

> **Client Conversation — Hygiene:**
> "Hygiene measures whether your services are using encryption in the first place. A low score here often means HTTP services are publicly accessible — not a quantum problem, a basic security problem. We recommend addressing these before the quantum migration work."

---

### 3.2 Modern TLS (0–25 points)

Modern TLS measures whether your encryption is current. Legacy TLS versions (1.0 and 1.1) were formally deprecated by the IETF in RFC 8996 and have known weaknesses. Services that blocked the assessment also contribute to a lower score.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Legacy TLS versions allowed | −14 pts | TLS 1.0 or 1.1 accepting connections |
| Unknown open services | −6 pts | Open ports that didn't respond to TLS, HTTP, or SSH |
| Assessment visibility blockers | −5 pts | The same share of endpoints with a recorded scan error, weighted separately because it also limits how much of the TLS posture could be assessed |

> **Client Conversation — Modern TLS:**
> "Modern TLS measures whether your encryption is current. TLS 1.0 and 1.1 have known weaknesses and were formally deprecated by the IETF in RFC 8996. If this score is low, some of your services are still advertising support for these versions — which needs to be addressed regardless of the quantum timeline."

---

### 3.3 Identity Trust (0–25 points)

Identity Trust measures certificate and identity-protocol health. This subscore captures expired and self-signed certificates (which cause browser warnings and break trust chains), weak Kerberos, SAML, DNSSEC, S/MIME and AD CS configurations where those scanners ran, and rewards services that enforce mutual TLS (mTLS). The impact values in the §3.1–§3.4 tables are the default (balanced) profile weights.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Expired certificates | −14 pts | Certificates past their `Not After` date |
| Expiring certificates | −7 pts | Certificates expiring within 30 days |
| Self-signed certificates | −9 pts | Certificates whose subject and issuer are identical |
| mTLS enforcement | +6 pts | Mutual TLS required — services verify client identity |
| Weak Kerberos encryption types | −10 pts | DES, RC4 or AES-128 Kerberos encryption types detected |
| Weak SAML signing key | −8 pts | SAML metadata signing key rated weak |
| Weak DNSSEC signing algorithm | −8 pts | DNSSEC zones signed with a weak algorithm, or left unsigned |
| S/MIME problems | −2 pts each | Weak S/MIME signing algorithm, expired S/MIME certificate, or weak S/MIME key (three separate drivers) |
| AD CS problems | −2 pts each | Weak AD CS template, template misconfiguration, weak signing algorithm, or an ESC4/5/7/8 coverage gap (four separate drivers) |

> **Client Conversation — Identity Trust:**
> "Identity Trust measures certificate health. Expired and self-signed certs cause browser warnings and break trust chains — clients see padlock errors before you even get to quantum risk. The mTLS bonus reflects services that require both parties to authenticate, which is a positive signal for your zero-trust posture."

---

### 3.4 Agility Signals (0–25 points)

Agility measures how ready you are to swap out cryptographic algorithms when the time comes. RSA is quantum-vulnerable and harder to migrate than ECDSA because it's more deeply embedded in older infrastructure. ECDSA adoption is a positive signal that engineering teams are already comfortable with modern key types.

| Driver | Max Impact | Trigger |
|--------|-----------|---------|
| Unknown service inventory | −6 pts | Services that couldn't be identified |
| RSA-only posture | −8 pts | Only RSA key types found, no ECDSA (harder to migrate) |
| ECDSA adoption | +4 pts | At least one ECDSA certificate found (Ed25519 and Ed448 keys count as ECDSA here) |
| Certificate key types undetermined | −8 pts | Certificates were observed but none was recognised as RSA, EC or EdDSA: no key type was recorded, or the key type is another algorithm such as DSA or ML-DSA (treated as the worst case, the same penalty as RSA-only) |
| PQC-hybrid key exchange | +8 pts | At least one endpoint negotiated the hybrid post-quantum key exchange X25519MLKEM768 (a scan run from a host whose own OpenSSL is too old to probe it also records a placeholder that currently counts here, so the bonus can appear without a real detection) |
| Bearer token weak algorithm | −6 pts | Share of assessable endpoints with a bearer token declaring any algorithm other than `none`. Every declared algorithm counts, including one the CBOM classifier labels quantum-safe such as `ML-DSA-65` (a token declaring `alg:none` is not counted here; `quirk analyze-token` flags it as CRITICAL) |
| OpenAPI plaintext servers | −4 pts | Share of assessable endpoints whose OpenAPI spec declares `http://` servers |
| Code-signing cert weak algorithm | −6 pts | Share of assessable endpoints with a code-signing certificate that the code-signing scanner flagged: a weak algorithm (RSA < 2048-bit, EC < 256-bit, or SHA-1), an expired certificate, or one expiring within 90 days (`agility_codesign_weak_algo_ratio`) |
| Active REST fuzz crypto-posture findings | −4 pts | Share of assessable endpoints with CRITICAL/HIGH crypto-posture findings from active REST fuzzing |

The "High-impact findings ratio" driver that earlier scoring versions listed here no longer exists. Open CRITICAL and HIGH findings now limit the headline score through the ceilings described in §3.6, not through the agility subscore.

> **Client Conversation — Agility Signals:**
> "Agility measures how ready you are to swap out cryptographic algorithms when the time comes. RSA is quantum-vulnerable, but it's also harder to migrate than ECDSA because it's more deeply embedded in older infrastructure. Seeing ECDSA adoption is a good signal — it means your engineering team is already comfortable with modern key types, which makes the quantum migration path shorter."

---

### 3.5 Data at Rest and Data in Motion (0–25 points each)

Beyond the four subscores above, two additional domains contribute to the headline score when the
scan actually assessed them: **Data at Rest** (database, object-storage, Kubernetes and vault
encryption posture — fed by the database, storage, Kubernetes and vault connector scanners) and
**Data in Motion** (email and message-broker transport encryption — fed by the email and broker
scanners). Together with the four subscores in §3, these
are the **six domains** referenced throughout §3.6 below. A scan that does not enable or reach
these scanners simply does not assess these two domains — see §3.6 for what that means for the
headline score.

---

### 3.6 Coverage, Exclude-and-Rescale, and the Not-Computed State (Phase 188, SCORE-06)

Before Phase 188, an unassessed domain (one your scan configuration or network access never gave
QU.I.R.K. any evidence for) was silently credited a full 25/25 — the same as a domain that was
actually clean. That inflated the headline score and hid the fact that part of the estate was
never looked at. As of scoring v2, this is no longer the case.

**Exclude-and-rescale.** The headline score is now computed only from the domains that were
actually assessed:

```
total_score = round( sum(assessed domain subscores) / (domains_assessed * 25) * 100 )
```

An unassessed domain neither helps nor hurts the score — it is simply excluded from both the
numerator and the denominator, rather than contributing a fabricated 25. This is why the rollup
arithmetic you see in a report (for example, "÷ 1.0" for a 4-of-6-domain scan, because the divisor is the number of assessed domains times 25, divided by 100) is not always the
same divisor from scan to scan: **a rollup divisor other than 1.5 is expected and correct** for any
scan with partial domain coverage. A full 6-of-6 scan still divides by 1.5 exactly as before.

**"N of 6 domains assessed."** The executive summary and scorecard markdown, the HTML report,
the DOCX report, the dashboard executive page, and `intelligence-{stamp}.json` disclose this
coverage sentence next to the headline score. The dashboard's Export PDF (the `/print` page)
shows the headline score without it. It tells you how many of the six domains (§3, §3.5)
had assessable evidence for this scan. If you expect a domain to be missing, check what to scan to
raise coverage: `data_at_rest` needs the database, storage, Kubernetes or vault connector scanners enabled and reachable;
`data_in_motion` needs the email or broker scanners enabled and reachable (see
[`docs/operators-guide.md`](operators-guide.md) for the operator-facing guidance).

**The not-computed state.** If a scan assesses zero of the six domains, QU.I.R.K. does not print a
`0/100` — a `0` would misleadingly read as "posture is bad" when the truth is "we have no evidence
at all." Instead the report shows an explicit statement: *"Readiness score not computed — no domain
had assessable evidence."* Treat a not-computed report as a scan-configuration problem to fix, not
a security finding.

**Unassessed subscores render as an em-dash, not a zero.** On the dashboard executive page, a
subscore category with no assessable evidence renders as `—` in place of a numeric gauge, in the
same layout slot a real gauge would occupy — a `0` there would misrepresent an untested category as
"tested and terrible."

> **Client Conversation — Coverage & the Not-Computed State:**
> "The score you're looking at is computed only from the parts of your estate we actually got
> evidence for this run — the report tells you exactly how many of the six domains that was. An
> unassessed area doesn't drag your score down or prop it up; it's just excluded until we scan it.
> If a domain shows as not assessed, that's a to-do for widening scan coverage, not a finding about
> your posture in that area."

**Scores are not comparable across scoring versions.** Because the aggregation formula itself
changes — not just the underlying findings — a score computed under one scoring version is not
directly comparable to one computed under another, even for the identical estate. The executive
and scorecard markdown, the HTML and DOCX reports, the dashboard executive page and
`intelligence-{stamp}.json` carry a version marker next to the headline score, currently
`Scoring version: 3.0` (on the dashboard, hovering it shows `scoring v3 — not comparable with v2 or
earlier scores`), for
exactly this reason; see `CHANGELOG.md`'s 5.25.0 entry for the full migration decision record.
The dashboard's Export PDF (`/print`), trend timeline, scan history and Compare page show scores
without the marker. QU.I.R.K. does not rewrite old report files or `intelligence-{stamp}.json`
files to make old and new scores artificially comparable, so compare those only within the same
scoring version. The dashboard keeps no per-scan score: its trend timeline, scan history and
Compare page rescore every past scan from its stored endpoints with the current scoring code, so
an old scan shows a v3 score there.

**Expect scores to drop under scoring v3, and that is the intended correction.** Every reference
estate the project re-scored dropped (a 31-host estate went from 87 to 18). v3 makes two
changes a client will notice:

- **Consequence is now absolute, not proportional.** Previously every penalty was
  `prevalence × weight`, so five CRITICAL findings counted less in a large estate than in a small
  one. An attacker needs one. A count of open CRITICAL or HIGH findings now sets a **ceiling**
  on the score regardless of how small a fraction of the estate they represent: 1 or more CRITICAL
  caps the score at 34, 5 or more CRITICAL at 25, 3 or more HIGH at 54, and 1 or 2 HIGH at 69 (the
  lowest applicable ceiling wins). The ceiling
  *compresses* the score into the permitted range rather than flattening it, so remediation still
  moves the number — a capped estate is not a frozen one.
- **A perfect classical score no longer reaches 100.** An estate with no observed hybrid
  post-quantum key exchange is capped at the top of GOOD (84). On a quantum-readiness assessment, 100
  has to mean quantum-ready; an estate that is immaculate by every classical measure is still
  exactly as exposed to harvest-now-decrypt-later as it was before the engagement began.

**A capped headline score says so.** Whenever a ceiling binds, the headline score in the executive
summary and scorecard markdown, the HTML and DOCX reports, and the dashboard Executive page,
Executive Verdict and Export PDF carries a reason naming what capped it and disclosing the uncapped
figure — for example *"5 open CRITICAL findings — score limited to 20 (computed 81)"*. The trend
timeline, scan history, Compare page and per-segment gauges show the number without a reason.

**Not every dashboard score applies the finding ceilings.** The trend scores (`/api/trends` and
`/api/trends/timeline`) and the multi-sensor merge scores (`/api/merge/latest`, including the
per-segment gauges) are computed from the endpoints alone, without findings, so the CRITICAL and
HIGH ceilings never bind there; only the no-hybrid cap at 84 does. In one test scan with a single
expired certificate the headline score was 32 and the trend score 78.

> **Client Conversation — Why the score dropped after an upgrade:**
> "Your infrastructure didn't get worse and we didn't start grading harder for its own sake. The
> old formula measured what *proportion* of your estate was affected, which meant a serious problem
> could be diluted by everything around it that happened to be fine. It now measures consequence
> directly, because an attacker only needs the one. Where a cap applies, the report tells you which
> finding set it and what the number would otherwise have been — and clearing that finding set
> lifts the cap."

**Gauge colors now agree with the report band (SCORE-07).** The dashboard's subscore gauges (the
0–25 gauges on the Executive page, including Data at Rest and Data in Motion) used to derive their
green/amber/red boundaries independently of the report's EXCELLENT/GOOD/MODERATE/FAIR/POOR band
table in §2. As of Phase 188, both read from the same single source (`quirk/severity_bands.py`),
so the gauge color and the report band can never silently disagree. The gauge converts a subscore
to a percentage of its maximum and applies the band thresholds to that percentage. This moved the
gauges' visible color boundaries: green now begins at 70% (previously 80%), amber covers 35–69%
(previously roughly 50–79%), and red begins below 35% (previously below 50%) — the gauge did not
get more lenient, it got *correct*, now matching the GOOD/FAIR boundaries in §2's table exactly.
The large Overall Readiness gauge is not band-colored: it is always drawn in the dashboard's accent
colour, and its band is shown by the Executive Verdict panel above it (§19.5).

**The honest-absence convention now extends to per-segment gauges, the trend timeline, and scan
history (Phase 199, TRIAGE-10).** The em-dash-not-zero rule described above for the six subscores
applies identically to three more surfaces: the executive dashboard's per-segment gauges row, the
trend timeline's per-session points, and the scan-history list's per-scan score column. A
per-segment gauge, timeline point, or scan-history score showing `—` means that segment or session
was not assessed, and it must never be read as a score of `0` or as worst-case risk. For a
per-segment gauge this includes a segment whose scoring raised an exception (logged as a warning).
On the trend timeline and the scan-history list a scoring exception fails the whole request
instead of producing a `—`. Because scoring failures on one segment now surface as
unassessed rather than a fabricated `0`, a single gauges row can legitimately show a mix of scored
and unassessed segments side by side.

Readiness scores are also now float-capable in transport, even though scoring itself still only
ever emits whole numbers today: the `/api/merge/latest`, `/api/trends`, `/api/trends/timeline`, and
`/api/scans` JSON responses may serialize a score with a decimal point (for example `71.0` rather
than `71`). Anything that consumes these endpoints programmatically should parse score fields as
numbers, not as integers, rather than assuming an integer-shaped response body.

---

## 4. Severity Tiers

Every finding in a QU.I.R.K. report is assigned one of five severity levels. CRITICAL and HIGH indicate active risk that should be addressed immediately or within 30 days, independent of any quantum threat. MEDIUM and LOW require a remediation schedule. INFO items are planning advisories.

| Severity | Color (HTML/PDF report) | What It Means | Recommended Response |
|----------|-------|---------------|---------------------|
| CRITICAL | Red | Cryptographic failure with no mitigation — e.g., an expired TLS certificate, an undersized SAML signing key (RSA below 2048 bits), a REST API that accepts a forged token | Immediate remediation — stop using this in production |
| HIGH | Orange | Active risk with known exploit path — e.g., plaintext HTTP, HTTP on TLS port | Remediate within 30 days |
| MEDIUM | Yellow | Risk that degrades posture but no immediate exploit — e.g., TLS handshake blocked assessment, unknown services | Investigate and validate within 90 days |
| LOW | Blue | Technical debt or deprecated standard — e.g., legacy TLS 1.0/1.1 allowed | Schedule upgrade — typically 1–2 sprint cycles |
| INFO | Gray | Observations and planning advisories — e.g., quantum migration advisories, mTLS signals | Awareness — no immediate action required |

**Badge colours are unchanged; the HIGH badge text got darker for legibility (Phase 165, A11Y-03,
released in 5.18.0).** The severity colour coding above still means exactly what it always meant —
HIGH is still the same orange, CRITICAL is still the same red. What changed is the *text drawn on
top* of the orange HIGH badge on the dashboard's Findings page: it now renders in a dark foreground
instead of white, closing a WCAG 2.1 AA contrast gap (2.85:1 white-on-orange, now 5.97:1
dark-on-orange). The red CRITICAL badge keeps white text, which
already clears AA (4.80:1 in the dark theme). Do not read any change in what a colour signifies from
this — only legibility moved.

> **Client Conversation — Severity Tiers:**
> "We use five severity levels. CRITICAL and HIGH are things we'd want fixed in the next 30 days — they're risks you have right now, today, independent of any quantum threat. MEDIUM and LOW are things that need a remediation schedule. INFO items are planning advisories — they tell you what to think about for the quantum migration, but there's no immediate action required."

---

## 5. Common Finding Types

The table below maps common finding titles to their plain-English explanation and the recommended client action.

| Finding | Severity | Plain-English Explanation | Client Action |
|---------|----------|--------------------------|---------------|
| Plaintext HTTP service detected | HIGH | Service responding over HTTP with no TLS | Enable TLS, redirect HTTP → HTTPS |
| HTTP on TLS-designated port | HIGH | HTTP found on a port expected to serve TLS (by default 443, 4433, 5001, 8443, 9443 or 10443) | Check service config — likely misconfigured |
| Legacy TLS versions allowed (TLS 1.0/1.1) | LOW | Server still advertises deprecated protocol versions | Disable TLS 1.0/1.1 in server config |
| TLS certificate expired | CRITICAL | Certificate past its `Not After` date | Renew certificate immediately |
| TLS certificate is self-signed | HIGH | Certificate not issued by a trusted CA | Replace with CA-issued cert |
| TLS certificate issued by untrusted CA | MEDIUM | Certificate chain does not validate to a trusted root | Replace with a cert from a trusted CA, or install the correct chain |
| TLS handshake blocked assessment | MEDIUM | The TLS handshake failed or timed out, so the negotiated version, cipher suite and certificate could not be assessed | Validate service config; add to exclusions if expected |
| SSH quantum planning advisory | INFO | Emitted once for every SSH endpoint whose probe recorded no error (an SSH probe that errored gets an INFO "Informational protocol observation" instead). Its text says the host key or key exchange relies on RSA or classical ECDH, but the finding does not check which algorithms the server offers, so it also appears for a server that already uses a post-quantum hybrid key exchange | Plan migration to post-quantum SSH key exchange using ML-KEM (FIPS 203). OpenSSH has offered the hybrid `mlkem768x25519-sha256` key exchange since 9.9 and uses it by default since 10.0 |
| Unknown open service | MEDIUM | Open port did not respond to TLS, HTTP, or SSH probes | Inventory this service; close if unneeded |
| mTLS required | INFO | Service requires client certificate — positive signal | No action; note for zero-trust posture documentation |
| JWKS fetched with TLS certificate verification disabled | HIGH | A JWKS URL was fetched with `allow_insecure_jwks` on, so its TLS certificate check was turned off. One finding per URL fetched | Turn off `security.allow_insecure_jwks` (or `--allow-insecure-jwks`) and fix the endpoint certificate. Counted in the findings totals, but does not change the readiness score |
| Code-signing certificate uses weak algorithm: *subject* | HIGH | Code-signing certificate uses a weak key or hash: RSA < 2048-bit, EC < 256-bit, or a weak signature hash such as SHA-1 or MD5 | Replace the signing certificate with RSA ≥ 2048-bit / SHA-256 or an ECDSA P-256+ key; re-sign artifacts with the new cert |

Some findings are configuration advisories, such as the JWKS row above. They are listed and counted in the findings totals but are excluded from the readiness score, so they never move the score or its ceilings.

---

## 6. CBOM Quantum Safety Labels

The Cryptographic Bill of Materials (CBOM) is an inventory of the cryptographic algorithms the scan recorded in use in your environment. For a TLS endpoint that is the negotiated cipher suite and the certificate's key and signature algorithms; the other cipher suites the server accepts (the enumeration sample) are not added. Each algorithm is classified with one of three quantum safety labels.

| Label | Meaning | Example Algorithms |
|-------|---------|-------------------|
| `quantum-safe` | Assigned a NIST quantum security level of 1 or higher in QU.I.R.K.'s algorithm table | AES-256-GCM, AES-128, SHA-384, `hmac-sha2-512`, ML-KEM-768, ML-DSA-65, SLH-DSA-128 |
| `quantum-vulnerable` | Assigned NIST quantum security level 0: asymmetric algorithms broken by Shor's algorithm, and legacy or weak primitives the table rates at level 0 | RSA (any size), ECDSA, `ecdh-sha2-nistp256`, DH-2048, X25519, SHA-256, SHA-1, 3DES |
| `unknown` | Algorithm name not recognized by the algorithm table | Unrecognized algorithm names |

**The green Safe badge's text is getting darker (Phase 165 tokens, applied in Phase 217; released
in 5.27.0).** On the dashboard's Certificates and Hardware pages,
the green fill behind labels such as `Safe` or `supported` is unchanged, but the text drawn on it
moves from white (2.30:1) to a dark foreground (7.40:1). The CBOM tab's own Safe badge uses a deeper
green with white text (4.83:1), and its quantum-safety graph labels follow the active theme (white
in the dark theme, dark in the light theme). The green still means quantum-safe; nothing about the
label's meaning changed, only its legibility.

> **Client Conversation — CBOM Quantum Labels:**
> "The CBOM — Cryptographic Bill of Materials — is an inventory of the cryptographic algorithms we found in use in your environment. Each algorithm is labeled quantum-safe, quantum-vulnerable, or unknown. Quantum-vulnerable doesn't mean you're at risk today — it means these algorithms would be broken by a large-scale quantum computer, and NIST's draft transition guidance (NIST IR 8547) schedules RSA and elliptic-curve algorithms to be disallowed after 2035. The CBOM gives you a roadmap of what to migrate."

---

## 7. Migration Roadmap

The migration roadmap organizes findings and recommendations into three planning horizons. This structure maps to the NOW / NEXT / LATER framework in the QU.I.R.K. report output.

| Horizon | Scope | Typical Timeline |
|---------|-------|-----------------|
| **NOW** | Active classical risks: remove plaintext HTTP exposure, triage high-impact findings, replace expired certificates, increase scan coverage, assign remediation owners and SLAs | 0–30 days |
| **NEXT** | Modernization work: classify unknown open services, renew near-expiry certificates, migrate self-signed certificates to managed PKI, disable legacy TLS versions, increase TLS enumeration coverage, automate evidence refresh | 31–90 days |
| **LATER** | Longer-horizon agility work: plan ECDSA adoption, standardize mTLS lifecycle operations, establish crypto governance review | 90+ days |

Which items appear depends on what the scan found: only items whose trigger is present are listed. Up to three baseline process items (assign remediation owners and SLAs, automate evidence refresh, establish crypto governance review) are added, in that order, until six items are listed, and the governance item is always present, so a scan that triggers nothing shows exactly those three. A scan that observed no endpoints at all gets three placeholder items after those three (collect initial asset scope, run baseline discovery and fingerprinting, establish recurring readiness reporting), six items in all. The list never exceeds twelve items.

- **NOW** — Fix active classical security problems first. These are risks you have today, regardless of quantum. A client cannot justify deferring an expired certificate or plaintext HTTP service because "we'll handle everything during the quantum migration."
- **NEXT** — Early quantum preparation that fits into the normal modernization cycle. Disabling legacy TLS, replacing self-signed certificates, and renewing near-expiry certificates are all work your team can do in regular sprint cycles without waiting for post-quantum standards to stabilize.
- **LATER** — Agility work that prepares the estate for algorithm migration, such as planning ECDSA adoption and standardizing mTLS lifecycle operations, plus governance review. The post-quantum standards themselves are NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA); for the dated federal deadlines see §16.

> **Client Conversation — Migration Roadmap:**
> "The migration roadmap is organized in three horizons. 'Now' items are things with known classical risk today — they need to be fixed regardless of quantum. 'Next' items are the early quantum-preparation work you can do in your normal modernization cycle. 'Later' items are the longer-horizon agility and governance work that sets you up for the post-quantum migration — the NIST FIPS 203/204/205 standards."

### 7.1 Score-Lift and the Projected Score (Phase 201, LIFT-01..LIFT-05)

Every roadmap item that can carry a quantified score movement shows a `(+N pts)` badge next to
its title. **This is not a heuristic points table.** `(+N pts)` is the number of points the readiness
score of this exact scan would rise if that one item — and only that one item — were resolved,
computed by re-running the real, unmodified scoring function (`compute_readiness_score`) a second
time over a copy of the scan's own evidence with that item's underlying findings marked resolved. The number is a genuine
second scoring pass, not a lookup table or a fixed weight assigned to a finding category.

**Why some items carry no number at all.** Nine kinds of roadmap item can be modeled this way as
of Phase 201. Five cannot, because resolving them changes no input the scoring model reads: three
process/governance items (assigning remediation owners and SLAs, automating evidence-refresh
cadence, establishing crypto governance review) and two coverage/lifecycle items (increasing TLS
enumeration coverage, standardizing mTLS lifecycle operations). These five items render with **no
badge at all** — never `0 pts`, never a dash, never "N/A." A blank means "not measurable by the
scoring model," not "worth zero." Treat the absence itself as information: it tells you the item
is real remediation work that the score simply has no input for, not that the item is unimportant.
An item that can be modeled but would raise the score by zero points on this scan also shows no
badge.

**"Projected score if all items resolved: {N}"** is a separate number from the sum of the
per-item badges, and it is deliberately not their sum. It comes from exactly one additional,
independent rescore — the same evidence, with every resolvable item's findings marked resolved
simultaneously, scored once. It can be smaller than adding up the individual `(+N pts)` badges:
each of the six subscores is capped, so once a subscore reaches its ceiling, a second item that
would have pushed it further has nothing left to add in the aggregate, even though that same item
shows a real, positive number on its own. It can also be larger: while an open CRITICAL or HIGH
finding keeps the score under one of the §3.6 ceilings, resolving only some other item (an expired
certificate, say) lifts the score only a little, whereas resolving everything at once also lifts
the ceiling. Read the projected score as "the level this scan could reach," not as "what you get
by adding up the badges."

**Neither number moves the readiness score you see today.** The badge and the projected score are
both advisory simulations, machine-firewalled from every real score surface — the scan's stored
score, its `score` block in the intelligence JSON, and its API response are computed exactly as
they always were, before this phase existed. Every surface that shows the projected score carries
this line, verbatim:

> Advisory — this projection is a simulation and does not affect the readiness score.

**Where you'll see both numbers:** the CLI roadmap markdown, the scorecard's top-3 "Next 30–60
days" actions (per-item badge only), the HTML and PDF reports, the DOCX report, the dashboard's roadmap detail panel
(per-item badge) and its Projected Score card (aggregate), and the print/export view.
`tests/test_score_lift_cross_surface_numbers.py` checks that the CLI markdown, HTML, DOCX and
dashboard roadmap numbers agree for one set of evidence scored with default weights. The
dashboard can still show different numbers for the same scan in two cases. With
`intelligence.calibration_overrides` set, the CLI, HTML/PDF and DOCX numbers apply
them and the dashboard's roadmap numbers do not. And the dashboard derives some findings the
scanner's report does not, for example a HIGH finding for an S/MIME certificate with an RSA-1024
key. That can change the §3.6 ceiling, and with it the badges: in one test scan the report showed
a score of 83 with no badges and the dashboard 68 with a `+15` badge.

**Precondition: the four-surface equality guarantee assumes unmodified templates (999.112).**
The numeric-equality guarantee described above — the same badge and the same projected score on
every one of the CLI, HTML/PDF, DOCX, and dashboard surfaces — holds only for **unmodified**
report templates. The operator [`report.template_dir`](configuration.md#report-block-phase-200-v525--rpt-01rpt-02rpt-03rpt-04)
override (RPT-02) is a **full-file** template override, not a section-level patch: an
operator-authored `.j2` template can omit the migration roadmap section entirely, and nothing in
the render pipeline validates that the section is present in the output. The report still renders
successfully, with the score-lift roadmap simply absent — no error, no warning, and no test flags
the omission. For a consulting-grade deliverable this means a client-facing report can ship
missing the score-lift roadmap without any signal that it happened; an operator supplying a custom
`template_dir` must manually verify the roadmap section survives in the rendered output before
delivering it to a client.

**The console "Migration Waves" table's second column changed meaning (BACK-51 / LIFT-04).**
Before Phase 201, that column counted raw *findings* bucketed by severity (Critical/High/other),
computed independently of the roadmap shown everywhere else in the report. As of Phase 201 it
counts roadmap *items* per NOW/NEXT/LATER phase, using the exact same categorization
(`build_phased_roadmap()`) that already fed the CLI markdown, HTML, DOCX, and dashboard roadmap
sections — the column is labeled "Items," not "Findings," to make that change legible on sight. A
report generated before Phase 201 and one generated after it can show different NOW/NEXT/LATER
counts for what looks like the same underlying findings, because the two are now counting
different things by design: items to act on, not findings to triage.

> **Client Conversation — Score-Lift and Projected Score:**
> "Each roadmap item that carries a number — the '+N pts' badge — is a real second scoring pass:
> we re-run the actual scoring engine as if that one item were already fixed, and show you the
> difference. It's not a guess or a fixed point value per finding type. Some items don't carry a
> number at all — that's honest, not an oversight: those are process items like assigning owners
> or automating evidence refresh, and our scoring model has no input to move for them. The
> 'Projected score if all items resolved' number at the top is a single independent rescore with
> everything fixed at once — it won't match adding up the individual badges: it can be smaller,
> because our six subscores each have a ceiling and two fixes can compete for the same headroom,
> or larger, because clearing an open critical finding also lifts the cap on the whole score. And
> to be clear: none of this changes the score you see today. It's a simulation, labeled as one
> everywhere it appears."

---

## 8. Compliance Summary

QU.I.R.K. now maps each finding to **PCI-DSS 4.0.1, HIPAA 45 CFR, and FIPS 140-3** control references and renders them in a "Compliance Summary" section of the HTML report and the PDF printed from it (the DOCX report and the dashboard's Export PDF have no such section). This makes the report directly usable as evidence in client compliance assessments — the assessor doesn't have to translate technical findings to control language.

The section is grouped into three framework subsections (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3). Each subsection renders a table with four columns: **Severity**, **Finding**, **Control reference + version** (e.g., `4.2.1` at `4.0.1`), and a **Source URL with the last-verified date**. The source URL points to the authoritative regulator publication (PCI Security Standards Council, the eCFR, or NIST CSRC) — never a third-party summary — so an assessor can click through and confirm the control text directly.

A separate "**Findings without compliance mapping**" subsection lists any findings whose title is not in `COMPLIANCE_MAP`. This surfaces coverage gaps so the assessor (or the operator preparing for the engagement) can confirm whether the absence is intentional — informational findings, observability advisories, scan-error categories — or a real gap that needs a mapping update before the report ships.

The compliance map also carries ISO 27001:2022 and SOC2 CC entries, which `quirk compliance status` lists but the Compliance Summary section does not render. The compliance map's review cadence and upgrade procedure for regulator revisions is documented in `docs/operators-guide.md` §7, "Compliance Map Maintenance".

Operators can verify compliance map freshness before a client engagement by running `quirk compliance status` (use `--format json` for machine-readable output). The command prints each framework's map version, `last_verified` date, and source URL, so the operator can confirm the map hasn't gone stale (default staleness threshold: 365 days) since the last release.

> **Client Conversation — Compliance Summary:**
> "We've mapped each finding to the controls your auditor cares about — PCI-DSS, HIPAA, and FIPS 140-3. Each row links back to the regulator's official publication so your assessor can confirm the control text directly. The 'Findings without compliance mapping' section is intentional transparency — it tells you which findings are informational versus which are unmapped gaps we're actively closing."

---

---

## 9. QRAMM Governance Assessment Section

The dashboard's Export PDF (the `/print` page) includes a QRAMM (Quantum Readiness & Maturity Model) Governance Assessment section that begins on a new page after the Migration Roadmap. The HTML, PDF and DOCX reports written by the scanner (§26) do not include this section. This section is intended to be read alongside the technical findings — it gives executives and CISOs the governance context for the scanner-derived crypto inventory.

### What the section contains

- **Radar chart (inline SVG)** — Rendered first in the section. A four-axis polygon plotting the four QRAMM dimensions: CVI (Cryptographic Visibility & Inventory), SGRM (Strategic Governance & Risk Management), DPE (Data Protection Engineering), and ITR (Implementation & Technical Readiness). The polygon shows the session's raw dimension scores on a 0–4 scale; closer to the outer edge means higher maturity.
- **Executive intro paragraph** — A one-sentence summary identifying that the section reflects the most recent completed QRAMM assessment.
- **Dimension Scorecard table** — Four rows (one per dimension) with raw score and weighted score, followed by one "Overall maturity" line.
- **Compliance Framework Coverage summary** — An 8-row table mapping the assessment to NIST PQC Standards, NSM-10, CNSA 2.0, ISO 27001:2022, ETSI Quantum-Safe, PCI-DSS v4.0, Common Criteria, and BSI TR-02102. Each framework shows a coverage tier badge: **Scanner-informed** (the QUIRK scanner contributes signal — currently CVI only) or **Manual only** (the framework's relevance is derived purely from manual assessment answers).
- **Per-framework practice detail** — Below the summary table, eight subsections (one per framework) flow continuously, with no forced page break between them. Each shows every practice area's relevance score and whether it was scanner-informed.

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

QUIRK fingerprints network and IoT devices — switches, routers, and similar equipment — on every SSH endpoint a fresh scan finds (the SSH banner first, then, while the vendor is still unidentified, the HTTP management page and then an SNMP probe; a resumed run that reloads the SSH stage from the database does not re-fingerprint), and on more hosts when the Modbus, BACnet or bulk SNMP probes are enabled. Fingerprinted devices are recorded in the CBOM and surfaced in the dashboard as a structured DEVICE/FIRMWARE component hierarchy alongside the algorithm inventory.

**The PDF shows the hardware section collapsed.** The PDF report is a print of the HTML report, and the HTML report's Hardware PQC Advisory section is a collapsed `<details>` block.
The PDF therefore carries only that section's one-line heading: not the device table, its SNMP, Modbus, BACnet, Bridge Status and CVEs columns, or the caveat paragraphs described in §10.4–§10.7.
Use the HTML report (expand the section) or the DOCX report to read them.

### 10.1 The DEVICE / FIRMWARE Component Hierarchy

Each hardware device found during a scan is represented by two linked components in the CBOM:

**DEVICE parent component** — the device identity. The CBOM component name is formatted as `"{vendor} {model}"` (for example, `"Cisco Catalyst 9300"`). The `"Unknown Device at {host}:{port}"` fallback applies only when both values are the literal string `Unknown`. A device with no recorded model, which includes every unidentified device, currently gets the literal text `None` in the model's place (for example `"Unknown None"`, with `quirk:hw-model` set to `None`). The DEVICE component carries the `quirk:hw-tier` property, which holds the CNSA 2.0 remediation tier assigned to that device class.

**FIRMWARE child component** — the endpoint detail found at the probe address. The CBOM component name is formatted as `"hw:{host}:{port}"` (for example, `"hw:192.168.1.1:443"`; an IPv6 host is bracketed, `"hw:[host]:port"`). The FIRMWARE component carries these properties:

- `quirk:hw-vendor` — vendor name from device fingerprinting (SSH banner, HTTP, SNMP, Modbus or BACnet)
- `quirk:hw-model` — model name from device fingerprinting
- `quirk:hw-pqc-supported` — whether the device has a known PQC firmware upgrade path
- `quirk:hw-remediation-tier` — CNSA 2.0 tier assigned to this endpoint
- `quirk:hw-bridge-status` — crypto-bridge status, when crypto-bridge detection applies
- `quirk:hw-snmp-oid` — raw sysObjectID OID string, when SNMP fingerprinting was used
- `quirk:hw-snmp-version`, `quirk:hw-snmp-auth-protocol`, `quirk:hw-snmp-priv-protocol` — the negotiated SNMP mode and the SNMPv3 protocol names (never secrets), when present
- `quirk:hw-modbus-vendor`/`-model`/`-firmware` and `quirk:hw-bacnet-vendor`/`-model`/`-firmware` — OT/ICS fingerprint values, when a Modbus or BACnet probe identified the device
- `quirk:hw-cve-ids` and `quirk:hw-cve-confidence` — matched firmware CVE IDs (comma-separated) and the overall confidence label, when any CVE matched

**Reading the Hardware Inventory section of the dashboard CBOM tab**

The Hardware Inventory section appears in the CBOM tab's Table view, below the existing algorithm table on the same scrollable page (there is no separate sub-tab for it). It is not scoped to the scan you are viewing: like every Hardware Inventory surface it lists each device's most recent successful observation from the whole database (§10.9), so it is omitted only when the database holds no such device. Each device appears as two rows, mirroring the CBOM's DEVICE/FIRMWARE pair: a `[DEVICE]` row and, beneath it, a muted `[FIRMWARE]` row. Both rows show the same six fields below.

| Field | Meaning |
|-------|---------|
| `host` | IP address or hostname of the probed endpoint |
| `port` | Port number of the probed endpoint |
| `vendor` | Device vendor from fingerprinting (e.g., `"Cisco"`, `"Juniper"`, `"Unknown"`) |
| `model` | Device model from fingerprinting (e.g., `"Catalyst 9300"`, `"Unknown"`) |
| `pqc_status` | Whether the device has a known PQC upgrade path: `"supported"`, `"partial"`, `"unsupported"`, or `"unknown"`. Today the hardware catalogs assign only `"partial"` or `"unsupported"`, and a device no catalog entry matches is `"unknown"`. `"supported"` and `"VENDOR-SILENT"` are also valid values (the data model lists both, and tier assignment and the `/hardware` page handle them), but no catalog entry assigns either today. |
| `remediation_tier` | CNSA 2.0 remediation tier: `"Tier 1"`, `"Tier 2"`, `"Tier 3"`, or `"Tier N/A"` |

### 10.2 Hardware Findings Are Advisory-Only

Hardware devices appear in the CBOM and on the dashboard, but **do not contribute points to any subscore**. They are advisory-only findings. CNSA 2.0 remediation tiers are informational guidance shown in the Hardware Inventory — not inputs to the numeric quantum-readiness score, and not items in the NOW/NEXT/LATER migration roadmap, which is built from service-level evidence only. The score measures the cryptographic posture of scanned services and endpoints; hardware device tiers are informational guidance layered on top of that posture.

> **Client Conversation — Hardware Devices Detected:**
> "The hardware devices we found are captured in the CBOM and assigned CNSA 2.0 remediation tiers — those are the Tier 1 through Tier N/A labels you see in the Hardware Inventory section. They're advisory findings, which means they sit alongside your remediation plan rather than inside the numbers: they don't change the quantum-readiness score or the migration roadmap. The score measures your services' and endpoints' cryptographic posture — TLS health, certificate validity, algorithm agility. Hardware device tiers are a separate informational layer that tells you which network devices need to be replaced or upgraded on the quantum timeline, but they don't feed into any subscore. So yes, the score stayed the same when we found those devices — that's by design."

### 10.3 Enabling Hardware Scanning

The bulk SNMP sweep, which probes every host the TLS, SSH and PQC phases found, is disabled by default (`enable_snmp` is `false`), and every SNMP probe needs the `[hw]` optional extra. Separately, hardware fingerprinting sends an SNMP probe (SNMPv3 first when an `snmp_v3_credentials` entry applies, then SNMPv2c with the community `public`) to an SSH host whose banner and HTTP management page did not identify a vendor, whether or not `enable_snmp` is set (see the `No SNMP` row in §10.4). For configuration steps — including enabling SNMP, setting the community string, understanding CNSA 2.0 tier definitions, and crypto-bridge detection — see `docs/operators-guide.md §9` (§9.1 Enable SNMP Scanning, §9.2 CNSA 2.0 Remediation Tiers, §9.3 Crypto-Bridge Detection).

### 10.4 SNMP Version / Security-Level Column (Phase 139)

As of Phase 139, HTML and DOCX Hardware Inventory tables (headed "Hardware PQC Advisory" in the reports) and the dashboard `/hardware` table
include an **SNMP** column showing the negotiated SNMP version and security level for each
probed endpoint. This reflects the v3 → v2c → none fallback ladder documented in
`docs/operators-guide.md` §9.1.1, and is distinct from — and independent of — the
`pqc_status`/`remediation_tier` advisory columns.

| Label | Meaning |
|-------|---------|
| `v3 auth+priv` | SNMPv3 succeeded with **both** authentication and encryption (privacy) negotiated — the strongest supported mode. The configured `snmp_auth_protocol`/`snmp_priv_protocol` names are recorded on any successful v3 probe (this label or `v3 noAuthNoPriv`) and never on a failed one. |
| `v3 noAuthNoPriv` | SNMPv3 succeeded but **without** encryption (privacy). QUIRK uses this label for every v3 success that is not auth+priv: a credential with no authentication key (true noAuthNoPriv, which carries essentially the same trust posture as an SNMPv2c community-string scan) and also a credential with an authentication key but no privacy key (authNoPriv: authenticated, but the traffic is not encrypted). Do not read this label as "v3 was secured." |
| `v2c` | The endpoint was scanned with plain SNMPv2c (community string) — no `snmp_v3_credentials` entry applied to this host (neither a host entry nor a `default` entry), so v3 was never attempted, and the v2c probe returned a sysDescr. This is the original, still-fully-supported scanning path from v5.8. |
| `v3 failed → v2c` | A `snmp_v3_credentials` entry (for this host, or the `default` entry) **was** configured, but the v3 attempt failed (for example bad username or passphrase), and QUIRK fell back to a v2c probe. The label records the failed v3 attempt whether or not the v2c fallback then answered. **This signals a real credential problem worth investigating** — it is not the same as an intentional v2c-only scan and should not be dismissed as normal. |
| `v3-protocol-mismatch` | A v3 credential was configured, but the device offered only authentication or privacy protocols weaker than the configured ones, so v3 was refused and QUIRK probed v2c for continuity. This is a distinct crypto-hygiene finding about the device, not a credential typo. It is shown as the raw value. |
| `No SNMP` | No v3 credential applied to this host, an SNMPv2c probe was attempted, and no sysDescr came back: the host did not answer, or the `[hw]` extra is not installed, in which case the probe returns nothing without sending a packet. An unidentified SSH device gets this label even when `--enable-snmp` was not set (§10.3). |
| `—` (em-dash) | No SNMP result is recorded for this device: its SSH banner or HTTP management page had already identified the vendor, or it was found only by the Modbus/BACnet probes. With `enable_snmp` on, the bulk SNMP sweep still probes the host of an already-identified device but does not record that result on the device. |

> **Client Conversation — SNMPv3 vs SNMPv2c:**
> "The SNMP column tells you how strongly each device's management interface was authenticated during the scan. `v3 auth+priv` is the gold standard — encrypted and authenticated. `v3 noAuthNoPriv` looks like v3 but the traffic is not encrypted, and without an authentication key it offers no real security improvement over the plain community-string scan, so don't read too much into the version number alone. And if you see `v3 failed → v2c`, that's worth a follow-up — it means we had credentials configured for that device and they didn't work, which is different from simply not having configured v3 credentials at all."

### 10.5 SNMP-Confirmed Bridge Mitigation (Phase 140)

As of Phase 140, the crypto-bridge annotation introduced in §9.3 of `docs/operators-guide.md`
has a second, stronger status alongside `partial_only`: `upstream_mitigated`. Both values are
advisory-only and both appear in the same Bridge Status column/badge across the HTML, DOCX
and dashboard `/hardware` surfaces (the PDF omits the table; see the note at the top of §10).

| `bridge_status` | Badge label | Color | What it means |
|------------------|-------------|-------|----------------|
| `partial_only` | "Partial (assumed)" | Amber | A PQC-capable gateway (`pqc_status` `partial` or `supported`) and a legacy backend (`unsupported`, `VENDOR-SILENT` or `unknown`) were both found on the same /24 subnet (proximity heuristic — see §9.3); every PQC-capable and legacy device in that /24 gets this status. No confirmation that traffic actually flows through the gateway. |
| `upstream_mitigated` | "SNMP-confirmed" | Blue | The paired gateway's own ARP table (`ipNetToMediaTable`, walked via SNMP) was found to list the legacy backend's IP address — a stronger, evidence-gated signal that the legacy device sits behind the gateway on this network segment. |

**`upstream_mitigated` is never auto-assigned from subnet co-presence alone.** It requires SNMP
evidence collected from the gateway itself (a sensor-side ARP-table walk against
`ipNetToMediaTable`, OID `1.3.6.1.2.1.4.22.1.2`) that lists the legacy device's IP. If that
evidence is absent or doesn't match, the pair stays `partial_only` — QUIRK never guesses.

**The mandatory caveat.** Every Hardware Inventory table where `upstream_mitigated` renders — HTML, DOCX,
and the dashboard `/hardware` tab (as a tooltip and an inline banner) — carries this verbatim
sentence:

> "Based on SNMP-derived network-path evidence; not independently confirmed by traffic inspection."

The CLI executive summary carries a longer paraphrase of this caveat instead of the verbatim sentence.
The CBOM's `quirk:hw-bridge-status` property and the dashboard exposure map's hardware crypto-bridge edges (drawn only for `upstream_mitigated` devices) show the status with no caveat.

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

### 10.6 Modbus / BACnet OT-ICS Columns (Phase 141)

As of Phase 141, HTML/DOCX Hardware Inventory tables (and the dashboard `/hardware`
table) include two additional columns — **Modbus** and **BACnet** — placed immediately
after the SNMP column (§10.4) and before the Bridge Status column (§10.5). Each renders
one of the states below, independently for its own protocol:

| State | Badge (dashboard; the reports show the same text without colour) | Meaning |
|-------|-------|---------|
| Identified | Modbus: blue. BACnet: purple. | Vendor/model/firmware successfully read via that protocol's fingerprint probe. Hover for the vendor/model string. |
| No response | Gray | The probe was attempted (flag on, port/Who-Is gate satisfied) but got no answer: for Modbus the client could not connect; for BACnet no I-Am reply arrived within the Who-Is timeout. A timeout raised during the Modbus connect or request, or during the BACnet property reads, is **Probe aborted** instead. |
| No match | Gray | A response was received but carried no usable vendor identity. |
| **Probe aborted** | Red | The scanner's one-strike circuit breaker (`docs/operators-guide.md` §9.4) fired — a real anomalous response (timeout mid-exchange, malformed frame, connection reset), not "nothing happened." |
| — (em dash) | none | Not attempted — the corresponding `--enable-modbus`/`--enable-bacnet` flag was off, or (Modbus only) port 502 was never observed open on that host. |
| `aborted_error_response` (Modbus only) | none (no label defined) | The device answered the identification request with a Modbus error response. No label exists for this state, so every surface shows the raw value. |

**The "Probe aborted" state is deliberately distinct** from both "No response" and the
em-dash not-attempted state — mirroring the Phase 139 SNMPv3 `v3 failed → v2c` precedent
(§10.4) of never letting a real signal (the device may be fragile or misbehaving) look
identical to "nothing happened." A red "Probe aborted" badge is operationally useful: it
tells the consultant this specific device is worth a closer, more careful manual look
before any follow-up querying, rather than being dismissed as simply unreachable.

**Abort caveat.** When any row in the Hardware Inventory table carries a "Probe aborted"
Modbus or BACnet state, a persistent caveat sentence renders near the table in the HTML and
DOCX reports as a paragraph, not a hover-only tooltip (the PDF omits the table and this
caveat; see the note at the top of §10):

> "Modbus/BACnet probe aborted — anomalous response. The device returned a malformed frame,
> reset the connection, or timed out; QU.I.R.K. stopped probing this host per its one-strike
> safety policy. Worth a closer manual look."

**Score impact: none.** Like all hardware fingerprinting signals (§10.2, §9.4 of
`docs/operators-guide.md`), Modbus and BACnet findings are advisory-only and never affect
the quantum-readiness score.

> **Client Conversation — Modbus / BACnet Columns:**
> "The Modbus and BACnet columns identify OT/ICS devices we found using their own
> industrial protocols, separate from the IT-facing SNMP column next to them. If you see a
> red 'Probe aborted' badge, that's a signal worth flagging to the operations team — it
> means the device gave an unexpected response to our brief, read-only identification
> probe (one request for Modbus; a Who-Is and up to two property reads for BACnet), which can indicate a fragile or already-stressed device. It doesn't mean anything
> was broken by the scan — QUIRK stops immediately on any anomaly and never retries — but
> it's worth a closer look."

### 10.7 Firmware CVE Advisory (Phase 142)

As of Phase 142, every fingerprinted hardware device whose vendor was identified (§10.1–§10.6) is additionally checked
against QUIRK's curated, NVD-cited firmware CVE catalog. This surfaces in two places:

**HTML/DOCX report.** A CVEs column in the Hardware Inventory table lists the matched CVE
IDs for each device (a "N CVEs (confidence)" badge with clickable NVD detail links in HTML —
`https://nvd.nist.gov/vuln/detail/<CVE-ID>` — and the plain IDs in DOCX, whose caveat tells the
reader to verify each CVE at the NVD page, since DOCX cells are plain text), plus a section-level
advisory-only note. A separate staleness caveat paragraph appears with the table whenever the local CVE snapshot
has aged past its 30-day freshness window (`docs/configuration.md`), telling the reader the shown
CVE list may be outdated without blocking report generation.

**Dashboard `/hardware` tab.** A single-colour "N CVEs" badge (amber, the same hue for every
match count and severity, so it is not a severity signal) appears in a new CVEs column. Clicking/expanding the badge (a `Collapsible`) reveals each
matched CVE as a link to its NVD detail page plus the overall confidence label.

**Confidence vocabulary:**

| Confidence | Meaning |
|------------|---------|
| high | The device's parsed firmware version falls inside a curated CVE entry's documented affected-version range. |
| medium | Only a vendor+model match exists: the matching curated entry carries no version boundary. When an entry does carry an affected-version range and the device's firmware string is missing or cannot be parsed, that entry does not match at all, so QUIRK never guesses whether the specific firmware is affected. |
| *(no badge)* | Either the device's vendor is unidentified ("Unknown") or absent, so no lookup was made and every surface shows an em dash; or a lookup was made and the curated catalog has no matching entry for the vendor and model (or none matching the firmware). In the second case the HTML and DOCX cells read **"no CVE correlation attempted"** (despite the wording, the lookup did run and nothing matched) and the dashboard shows an em dash. Neither case means the device has no vulnerabilities, only that the curated catalog has no match. |

**Advisory-only — never a score or remediation-tier input.** Like every other hardware
fingerprinting signal in this guide, firmware CVE matches never affect the quantum-readiness
score or the CNSA 2.0 remediation tier (§10.2). They exist purely to give the consultant a
starting point for a deeper, out-of-band vulnerability conversation with the client.

> **Client Conversation — Firmware CVE Advisory:**
> "The CVE badge on a hardware device means we found a published vulnerability associated
> with that device's vendor/model — and, where we could parse the firmware version, its
> specific firmware range. This is informational, not a scored finding: it doesn't change your
> readiness score, and we deliberately don't guess when we can't confirm the exact firmware
> in range. Click through to the NVD link to read the official advisory and confirm
> applicability against your asset inventory before prioritizing remediation."

### 10.8 BACnet Vendor Name Resolution & CVE Coverage (Phase 147, decision D-147-02-A)

Phase 147 closed a real fix-or-defer call on BACnet CVE coverage: as of this phase,
**BACnet-identified devices whose vendor ID is in QUIRK's curated table now display a resolved vendor name and — where recognized — a
resolved product family, instead of a bare numeric ASHRAE vendor ID.** The project chose to
build the curated resolution layer rather than formally marking BACnet CVE correlation
out-of-scope.

**What changed.** Before this phase, a BACnet Who-Is/I-Am probe returned a raw numeric
vendor ID (e.g. `"5"`) and a raw model string (e.g. `"FX16"`) straight into the Hardware
Inventory's Vendor/Model columns, and those raw values could never match the curated firmware
CVE catalog's `("Johnson Controls", "Facility Explorer")` entry — so BACnet devices got zero
CVE correlation despite that entry existing specifically to cover this device family. As of
this phase, `quirk/scanner/bacnet_vendors.py` resolves the numeric vendor ID and raw model
string against a small curated table (e.g. vendor ID `5` → "Johnson Controls", model `FX16` →
product family "Facility Explorer") **before** the value ever reaches the firmware CVE
correlation step (§10.7). A recognized Johnson Controls FX16 field controller now surfaces a
real CVE advisory row (CVE-2017-16744, HIGH) in the same way any other fingerprinted device
does. The resolved names replace the headline vendor and model only when no earlier method (SSH banner, HTTP, SNMP, Modbus) had already identified the device.

**Curated, not exhaustive.** Today the table holds one vendor ID (`5` → Johnson Controls) and one model family (`FX16` → Facility Explorer). It covers only a small, individually-verified
subset of the ASHRAE/BACnet Committee's 1000+-entry vendor-ID registry (`bacnet.org/assigned-
vendor-ids/`) — the same curated-catalog philosophy already used by the firmware CVE table
(§10.7), the compliance framework mappings, and the QRAMM model catalog. **An unrecognized
vendor ID still displays as the raw numeric string exactly as before this phase** — there is
no behavior change or crash risk for the majority of BACnet vendor IDs QUIRK has not curated.
The raw, unresolved probe values are kept on the device record as the `bacnet_vendor` /
`bacnet_model` fields, independent of whether QUIRK's curated table recognized them.
The dashboard `/hardware` BACnet badge's hover text and the CBOM's `quirk:hw-bacnet-vendor` / `quirk:hw-bacnet-model` properties show them; the HTML and DOCX reports do not.

**Advisory-only, same as every other hardware signal.** Like every hardware fingerprinting
signal in this guide (§10.1–§10.7), BACnet vendor-name resolution and any resulting CVE
correlation are purely advisory — they never affect the quantum-readiness score or the CNSA
2.0 remediation tier (§10.2). The catalog is staleness-gated on a 365-day cadence (ASHRAE
vendor-ID assignments are append-only and essentially never change once issued, unlike CVE
data's 30-day cadence).

> **Client Conversation — BACnet Vendor Resolution:**
> "When we identify a BACnet building-automation device, we now resolve its numeric ASHRAE
> vendor ID to a real vendor name — for example, a Johnson Controls field controller shows up
> as 'Johnson Controls' rather than the number 5. Where we also recognize the specific product
> family, that can surface a real CVE advisory the same way any other hardware device does.
> This only covers a curated subset we've individually verified (today, one vendor), so an unrecognized
> device will still show its raw numeric ID — that's expected, not a scanning failure."

### 10.9 Last-Known-Good Current-State Projection (Phase 154)

As of Phase 154, every Hardware Inventory surface (HTML/DOCX report, dashboard `/hardware`
tab, CBOM DEVICE/FIRMWARE hierarchy) shows each device's most recent **successful** observation,
not simply the most recent scan run. If a device's latest probe fails — the device is offline,
the port stopped responding, or the probe errored — that device still appears with its
previous, last-known-good vendor/model/tier data instead of vanishing from the inventory or
flipping to a spurious `Unknown` row. All four surfaces were rewritten together in Phase 154
specifically to keep this behavior consistent across the report writer, the merge/CBOM path,
and both dashboard hardware queries — a device is never present on one surface and missing
from another because of a single failed probe.

**Migration caveat — legacy rows are hidden, never deleted.** Devices last scanned before this
release carry no `probe_status` value (the column did not exist yet, so those rows are `NULL`).
A `NULL` `probe_status` is treated the same as an explicit `failed` probe for the purposes of
"what counts as current state" — those legacy rows will not appear in any Hardware Inventory
surface until the device is scanned at least once more under this release. **Their history rows
are never deleted by this change** — only excluded from the current-state view; the retention
window described in `docs/configuration.md` (`hardware_history_retention_days`) is what
eventually removes old rows, on its own independent 180-day-default clock, not this
projection change. The purge runs when hardware rows are persisted (a full scan, a check-in, or a
sensor result the console ingests) and deletes only old rows of the devices that run probed, so a device that is never probed again
keeps its legacy rows.

**Not yet a report/dashboard column.** The underlying `match_confidence` and `probe_status`
values (see `docs/operators-guide.md` §9.6) that drive this projection are not yet surfaced as
their own report or dashboard columns — that is deferred to a later release. Operators should
not expect to find a `match_confidence` or `probe_status` column on the Hardware Inventory
table today; the values exist in the data model and drive which row is shown, but are not
independently rendered yet.

> **Client Conversation — Last-Known-Good Hardware Data:**
> "If a device shown in the hardware inventory was offline or unreachable during the most
> recent scan, we still show you its last confirmed vendor, model, and remediation tier rather
> than dropping it from the report or the dashboard. That means a temporarily-down device
> won't silently disappear from your inventory — but it also means the data shown for that
> device may be from an earlier scan, not today's. If a device you expect to see is entirely
> missing, it likely predates this release and simply needs one more scan to reappear."

### 10.10 Recent Lifecycle Changes (Phase 156)

As of Phase 156, HTML, PDF, and DOCX reports (and the dashboard `/hardware` and `/compare`
pages — see `docs/operators-guide.md` §9.8) include a **Recent Lifecycle Changes** section
surfacing the drift events Phase 155's reconciliation engine (`docs/operators-guide.md` §9.7) persists to
`hardware_drift_events`.

**Structurally separate from the current-state inventory.** This section is deliberately not a
column added to the Hardware Inventory table described in §10.1–§10.9 above. The inventory table
answers "what does the device look like right now" (a point-in-time snapshot, subject to §10.9's
last-known-good projection); the Recent Lifecycle Changes section answers "what changed since
last scan" — a different question with a different shape (a list of transitions, not a list of
current values). Keeping them structurally separate avoids conflating "current state" with
"history of change" in a single table.

**The four event types**, with their exact display labels:

| Event type | Display label |
|------------|----------------|
| `tier_crossing` | Tier crossing |
| `upstream_mitigated_change` | Bridge mitigation change |
| `cve_delta` | CVE correlation change |
| `eol_state_change` | EOL/EOS state change |

**Direction vocabulary.** Every event carries one of three direction labels — **Improved**,
**Worsened**, or **Changed**. This vocabulary is derived from the CNSA 2.0 tier ordering (`docs/operators-guide.md` §9.2),
not from a severity ranking: a tier crossing from Tier 2 to Tier 1 is "Worsened" because Tier 1
is the most urgent remediation tier (Tier 3 is already PQC-capable), independent of any finding-severity concept used elsewhere in
this report. Event types with no inherent better/worse direction (a bridge mitigation change,
a CVE-delta, an EOL-state change) always render as "Changed."

**No severity, no score contribution.** This section carries no `severity` field at all — it is
not part of the readiness score in any form. Every rendering of this section, in every format,
carries this verbatim caption:

> Advisory — hardware lifecycle changes do not affect the readiness score.

This caption appears unconditionally in the HTML, PDF, and DOCX renderings whenever the section
has at least one event to show — it is never hidden behind a collapsed disclosure or omitted
from any format. This mirrors §10.2's existing advisory-only framing for hardware findings in
general: the Recent Lifecycle Changes section is that same advisory boundary applied to
*changes* in hardware state rather than to hardware state itself.

**A first-ever scan has no lifecycle content by construction.** A device's very first scan has
nothing to diff against, so it produces zero drift events and the section reflects that
correctly — this is expected behavior, not a missing-data defect. See
`docs/operators-guide.md` §9.8 for how the dashboard distinguishes this "no prior scan" state
from the "prior scan exists but nothing changed" state.

> **Client Conversation — Recent Lifecycle Changes:**
> "This section shows you what changed about your hardware devices since the last scan — a tier
> shift, a newly-relevant CVE, a bridge-mitigation status change, or an EOL/EOS status change.
> It's separate from the main hardware inventory table above it, which shows the current state
> of each device. Like every other hardware signal in this report, it's advisory only — it
> doesn't move the readiness score. And if you're looking at a brand-new device's first-ever
> scan, you won't see anything here yet, because there's nothing to compare it against."

### 10.11 EOL/Tier Forecast (Phase 157)

As of Phase 157, HTML, DOCX, and the CLI/markdown executive summary each carry an **EOL/Tier
Forecast** subsection — a forward-looking projection of which fingerprinted devices
are projected to reach end-of-life, with each window broken down by the devices' current CNSA 2.0 tier, based solely on
vendor-published lifecycle dates in the curated EOL/EOS catalog (`hardware_eol.py`).

**Forward-looking, not historical.** This is the complement to §10.10's Recent Lifecycle
Changes section: that section answers "what already changed since last scan," while the
EOL/Tier Forecast answers "what is projected to change from today onward (buckets run from 0-3 months out
to 12+ months), assuming no remediation." The two sections are visually and structurally distinct — the forecast renders
as narrative sentences bucketed by time window (see below), never as a table, so it can never
be visually confused with the drift changes list.

**Renders independently of drift events.** A scan that produces zero drift events (for example,
a device's very first scan) can still show a populated EOL/Tier Forecast, because the forecast
is derived from the current fingerprinted device set and the EOL catalog, not from the
drift-reconciliation engine. Conversely, the forecast is entirely absent (no orphan heading in
any format) when no fingerprinted device carries a known EOL date — see "When the section is
absent" below.

**How to read a bucket sentence.** The forecast groups devices into five time windows relative
to render time: `already passed`, `0-3 months`, `3-6 months`, `6-12 months`, and `12+ months`.
Every non-empty bucket produces one sentence stating the device count in that window and its
CNSA 2.0 tier breakdown (Tier 1 / Tier 2 / Tier 3 / Tier N/A), and every sentence cites the EOL
catalog's `last_verified` date inline — never a bare, unsourced count.

**Why the language is hedged.** Every future-window sentence uses hedged phrasing ("are projected to" /
"is projected to"), and no sentence uses an unqualified "will"; the `already passed` sentence states
that the vendor-published date has passed. The underlying EOL/EOS dates come from a
curated, periodically re-verified vendor catalog (`hardware_eol.py`) — not a live feed —
so, consistent with the forecast's advisory-only framing, it can only ever state a projection
sourced to a dated snapshot, not a guarantee.

**Retention reconciliation — the forecast is forward-only and reads no drift history.** The
EOL/Tier Forecast is derived entirely from each device's *current* end-of-life date and
remediation tier; it never reads a row from `hardware_drift_events`. Because of this, the
`scan.hardware_drift_event_retention_days` retention window (see `docs/configuration.md`) places
**no limit whatsoever** on what the forecast can cover — the two features share no data path,
and no forecast statement ever depends on a period the drift-event retention sweep may have
already purged. This is a reader-facing guarantee, not an internal implementation detail: even
on an engagement running with an aggressively short drift-event retention window, the
forecast is exactly as complete as it would be with unlimited retention.

**When the section is absent.** No device in the report's hardware inventory has a resolved vendor
end-of-life date. That inventory is each device's most recent successful observation on record
(§10.9), not only the devices this run probed. Either the curated catalog has no entry for that
vendor/model, or the devices were not
fingerprinted deeply enough to resolve one. Absence means "no EOL data available", never "no
EOL risk" — an absent forecast section is not evidence that a client's fleet is safe from
upcoming end-of-life exposure. The section is also left out, with a logged warning, if the
hardware rows cannot be read or the forecast cannot be built.

**Advisory only — not a score input.** Every rendering carries an advisory qualifier. HTML and
DOCX print `Advisory only — not included in the readiness score.` (the CLI executive summary
words it `Advisory only — not included in readiness score.`). The forecast reads no
score value at all, is never assigned a severity, and never appears in the findings list — it
renders only precomputed bucket sentences.

**Stale-catalog qualifier.** If the underlying EOL/EOS catalog (`hardware_eol.py`, 365-day
staleness cadence) has not been re-verified within its review window, every rendering of the forecast adds one further qualifier line naming the
catalog's `last_verified` date, so a consultant can immediately see whether the projection is
resting on current data.

**Where it renders:**

| Format | Location |
|--------|----------|
| HTML/PDF | `<h3>EOL/Tier Forecast</h3>` subsection, positioned after (not inside) the Recent Lifecycle Changes section |
| DOCX | Heading level 3 ("EOL/Tier Forecast"), one level below the drift section's level-2 heading; it follows the drift table when the run has drift events, and the Hardware PQC Advisory section otherwise |
| CLI/markdown | `### EOL/Tier Forecast`, a new sibling subsection under Strategic Recommendations, distinct from `### Hardware PQC Advisory` — the CLI report has no separate lifecycle-drift section |

> **Client Conversation — EOL/Tier Forecast:**
> "This section looks ahead, not back — it's a projection of which of your devices are
> expected to hit end-of-life, and which CNSA 2.0 tier each of those devices is in today, based on the vendor's own
> published lifecycle dates. It's separate from the 'what already changed' section above it, and
> like every hardware signal in this report, it's advisory only — it doesn't move your readiness
> score. If the underlying vendor catalog hasn't been re-checked recently, we'll flag that too,
> so you know how fresh the projection is."

### 10.12 Partial Re-Probe Banner (Check-in Scans, Phase 159)

As of Phase 159 (HWLC-13), every rendered report displays a **Partial re-probe** banner whenever
any device or drift row it is showing came from a `--check-in` run (see
`docs/operators-guide.md` §9.9) rather than a full scan. The banner text is locked verbatim
across every report format. The dashboard does not show the banner: a check-in drift event gets a
short "Partial re-probe" badge (the full text is its tooltip), and the `/hardware` device table
carries no check-in marker. The report banner:

> Partial re-probe — check-in scan; not a full assessment.

**What triggers it.** The banner appears whenever any displayed `HardwareDevice` row or
`hardware_drift_events` row carries `is_partial_scan=True` — i.e. it was written by a
`--check-in` run. A report built entirely from full-scan data never shows the banner.

**Where it appears:**

| Format | Location |
|--------|----------|
| HTML/PDF | Hardware PQC Advisory (device) section, and independently the Recent Lifecycle Changes (drift) section — each gated on its own section's data, so either section alone still shows the banner if it has check-in-sourced rows |
| DOCX | Hardware PQC Advisory table and Recent Lifecycle Changes section, same independent per-section gating as HTML/PDF |
| CLI/markdown | Inside the existing `### Hardware PQC Advisory` block of the executive summary — the CLI report has no drift-section rendering to extend (Phase 156 D-12), so the banner appears once, alongside the device advisory |

**How to read it.** The banner means some displayed hardware rows or drift events were written by
a check-in re-probe of already-known devices, not by a discovery pass. A check-in run writes no
report and no score, so every report comes from a full scan. A check-in row appears in that report
only when it is still a device's most recent successful observation, for example because the full
scan did not probe that device or its probe failed. Such a row is therefore **older** than the rest
of the report: the quantum-readiness score and every non-hardware section except Key Reuse (§21,
which reads TLS endpoints from every scan in the database) come from the full scan that wrote the
report.

**`/compare`'s hardware-drift list still includes check-in-sourced events — badged, not
hidden.** By design (D-159-I), a drift event written by a check-in run appears in
`GET /api/hardware/drift` and the `CompareResponse.hardware_drift` block exactly like any
full-scan-sourced drift event, carrying an additive `is_partial_scan: true` field so the
dashboard can badge its provenance rather than filtering it out of the "what changed" history.

**The readiness-score comparison never includes check-in runs at all.** `/trends` and
`/compare`'s score/subscore diffs are structurally immune to check-in data — a check-in run
never writes a scored scan row, so it is never selectable as a comparison endpoint and never
appears in a trend timeline. This is a structural guarantee (regression-tested), not a runtime
filter: there is no scored artifact for a check-in run to be filtered out of in the first place.

> **Client Conversation — Partial Re-Probe Banner:**
> "You'll sometimes see a banner on the hardware section that says 'partial re-probe.' That means
> some of the hardware rows come from a quick, low-cost check-in we ran against devices we'd already
> fingerprinted, rather than from the full scan behind this report, for example because that scan could
> not reach those devices. Your readiness score and your findings come from the full scan.
> Check-ins are a way to keep an eye on drift between full engagements without re-running the
> whole thing."

---

### 10.13 Vendor PQC Status Trends (Phase 161)

As of Phase 161, HTML, DOCX, and the CLI/markdown technical report each carry a **Vendor PQC
Status Trends** section, and the dashboard `/hardware` page shows the same content below Recent
Lifecycle Changes. It surfaces the catalog-level vendor trend events Phase 160's reconciliation
persists to `vendor_pqc_trend_events`.

**Vendor-scoped, not device-scoped.** This is the key distinction from §10.10. Recent Lifecycle
Changes answers "what changed on *this device*"; Vendor PQC Status Trends answers "what changed
about *this vendor's posture across your fleet*" — for example, a vendor going from zero of three
observed models advertising PQC support to one of three. Because a row describes a vendor rather
than an endpoint, it carries **no host, no port, no direction, and no severity**, which is why the
table has four columns where the drift table has five.

**The four columns:**

| Column | Meaning |
|---|---|
| **Vendor** | The vendor whose fleet-wide posture changed. |
| **Change** | The event type. Currently one value, displayed as "PQC status change". |
| **Transition** | The old and new fleet-wide values, rendered `old → new` (`old -> new` in the CLI technical report). An em-dash (—) on either side means that side had no recorded value. |
| **Detected** | When the device observation that confirmed the change was scanned (`detected_at`). The reconciliation engine's own `confirmed_at` time is not shown. |

**Never affects the readiness score.** Every rendering of this section carries the caption
verbatim:

> Advisory — vendor PQC status trends do not affect the readiness score.

This is not merely a convention. The isolation is machine-enforced: `tests/test_cve_score_guard.py`
asserts that the six modules it lists — the CLI, HTML and DOCX renderers, the reconciliation
engine (`hardware_drift.py`), `models_util.py` and the dashboard route — never reference
`SCORE_WEIGHTS` or import the scoring engine, and that no `SCORE_WEIGHTS` key contains vendor-trend
vocabulary. `quirk/reports/writer.py`, which loads the rows for the reports, is not on that list:
it also computes the score, so it imports the scoring engine. The guard strips `#`-comment-only
lines before searching, so a comment line naming `SCORE_WEIGHTS` does not count.

**When the section is absent.** The reports do not scope this section to the current run. They
read the newest 50 rows of `vendor_pqc_trend_events` from the whole database (the table has no
run column), the same feed the dashboard uses. So the HTML, DOCX and CLI report render no heading
and no empty table only when the database holds no vendor trend events at all. A run that recorded
no events of its own still shows the section if an earlier run in the same database recorded
some. Once the `/hardware` page has loaded, the dashboard shows the section card; with no events
it shows a "No vendor PQC status trends recorded" empty state instead of rows, and if the card's
own request fails it shows the error instead. In the reports the section is gated independently
of §10.10 and §10.11, so a scan with zero device drift events and no EOL forecast can still show
populated vendor trends, and vice versa.

**How to explain it to a client:**

> "This part tracks your *vendors*, not your devices. If Cisco starts shipping post-quantum support
> across the models you actually run, that shows up here as a trend, even though nothing about any
> individual box on your network changed. It's context for planning — which vendors are moving and
> which aren't — so it deliberately doesn't move your score."

---

## 11. Dashboard Sidebar Scan-Date Badge (Phase 143)

As of Phase 143, the dashboard sidebar carries a persistent scan-date badge — a small
`role="status"` row rendered directly below the scan selector — showing the recency of the
most recent scan on **every** dashboard view, including the collapsed icon-only sidebar
(it is never gated on scan count or viewport width, unlike the scan selector above it, which
appears only when more than one scan exists, and only in the expanded `lg`+ sidebar).

| State | Rendering |
|-------|-----------|
| At least one completed scan exists | `Last scan: {date} {time}` for the newest session, expanded sidebar. Collapsed (`<lg`) sidebar shows a calendar icon with the same text in a hover tooltip. |
| No scan has ever been run, or the scan list could not be loaded | `No scan yet` placeholder text (plain text in the badge row; it does not use the `EmptyStateCard` component other pages use for empty states). |

The badge sources data from the existing `useScanList()` hook — no new API endpoint was added.
It exists purely to give an operator a quick "is this data current?" answer without navigating
into the scan history page.

> **Client Conversation — Scan-Date Badge:**
> "The date in the sidebar tells you when the newest scan in this QUIRK instance ran (even while
> you are looking at an older scan picked from the scan history) —
> useful when reviewing a report days or weeks after the scan actually ran, or when
> multiple people share the same QUIRK instance."

---

---

## 12. Discovery Liveness Pre-Pass Rows (Phase 145)

As of Phase 145 (DISC-03), a discovery scan can include two new `scan_error_category`
values that do not represent scan failures — they are the byproduct of a cheap
liveness pre-pass that runs ahead of the full port sweep on each nmap-discovery batch it actually
sweeps (a batch, or a whole discovery result, reused from cache on a resumed run gets no pre-pass)
(see `docs/operators-guide.md` §10 for the full mechanism). Both appear as
`CryptoEndpoint` rows with `protocol="ADVISORY"`. They describe normal outcomes, not
failures, but the report pipeline currently handles them like any other row that carries a
scan error: each one becomes an INFO "Informational protocol observation" finding, and each
one counts toward the scan-error rate that lowers the hygiene and modern-TLS subscores. A
sparse range with many unresponsive hosts can therefore score lower than a dense range with
the same services. This is a known defect, not intended behaviour.

| `scan_error_category` | Cardinality | `host` value | `port` | Meaning |
|------------------------|-------------|--------------|--------|---------|
| `liveness_skip` | One row per non-responsive host | The real host address | `0` | The host did not answer the TCP-based liveness probe on any of the sweep's ports and was excluded from the port sweep. This is a normal outcome for a sparse range — not a scan failure — and does not mark the discovery stage as partially failed. |
| `privilege_fallback` | At most one row per scan | `"liveness-prepass"` (a sentinel, not a real host) | `0` | The scanning process could not confirm raw-socket privilege, so nmap's SYN-ping probe may have silently degraded to a slower TCP connect probe. Results remain valid; this row only discloses that the pre-pass ran without the intended privilege level. Absent when the scan ran as root/`sudo`. |

They do not follow the `missing_extra` convention. A `missing_extra` row becomes a
`coverage_gap` advisory that the HTML report lists under Coverage Gaps and keeps out of its
findings tables; a liveness row becomes an ordinary INFO finding (see above).

> **Client Conversation — Liveness Pre-Pass Rows:**
> "Before we sweep a range of addresses for open ports, we run a much cheaper check to
> see which addresses actually respond at all — that saves a lot of time on large,
> sparse ranges where most addresses are unused. Any address that didn't respond shows
> up here as a `liveness_skip` row, which just means 'nothing home,' not a scan
> failure. If you also see a single `privilege_fallback` row, that just means the scan
> process didn't have elevated privileges when it ran, so that pre-check step used a
> slightly slower method — your results are still complete and valid either way."

See §13 below for the aggregate "Hosts undetermined" count that these per-host rows
feed into the executive summary.

## 13. Undetermined-Host Disclosure (Phase 146)

As of Phase 146 (DISC-07), four report surfaces — the CLI markdown executive summary,
the HTML report, the DOCX report, and the end-of-scan terminal summary table — each disclose
one combined **"Hosts undetermined"** count (the markdown and DOCX label it "Hosts undetermined
(unreachable/filtered)"). This is the sum of
two `scan_error_category` values recorded against port-0 `CryptoEndpoint` rows:

- `discovery_exception` — a discovery batch raised an exception during the port sweep
  (Phase 144). This is intentionally a distinct category from the generic `exception`
  value used elsewhere in the scanner for unrelated stage crashes (TLS, SSH, JWT, and so
  on) — those never count toward "hosts undetermined" (CR-01). Each failed batch writes one
  `discovery_exception` row, so it adds one to the count however many addresses it covered.
- `liveness_skip` — a host did not respond to the liveness pre-pass and was excluded
  from the sweep entirely (Phase 145, see §12 above).

All four surfaces read this count (and, where space allows, its `discovery_exception`/
`liveness_skip` breakdown) from one shared field —
`ExecContent.undetermined_hosts_count` / `.undetermined_hosts_breakdown` — computed once
in `quirk/reports/writer.py` and never recomputed per-renderer. In the CLI markdown
executive summary it appears as a bullet in the "Discovery and Coverage" section; in the
HTML report as a `meta-table` row (with the breakdown shown when non-empty); in the DOCX
report as an Executive Summary paragraph; and in the terminal summary table as a "Hosts
undetermined" row directly beneath "Hosts scanned". The dashboard, including its `/print` page
and the Export PDF printed from it, does not show this count.

**This count is not a scan-health signal.** A high `liveness_skip` count is a normal,
expected outcome on a sparse or segmented range — most addresses in a large CIDR often
simply have nothing listening — and is unrelated to whether the discovery stage's
`ScanCheckpoint` recorded a partial failure. Only the `discovery_exception` portion of
the breakdown indicates something the discovery batch loop could not complete; even
then, a non-zero `discovery_exception` count does not by itself mean the overall scan
failed, since a single batch's exception is isolated from the batches around it.

> **Client Conversation — Undetermined Hosts:**
> "This report counts the addresses in the scanned range that never answered our liveness
> check, plus any sweep batch that hit an internal error (a failed batch counts once, however
> many addresses it covered). On a large, mostly-empty range the unanswered addresses are
> usually the biggest contributor, and that's completely expected — it doesn't mean anything
> went wrong with the scan, it just means those addresses have nothing running on them (or are
> filtered from reaching us at all)."

### Dashboard discovery batch sub-line

While a scan is in the discovery stage, the dashboard's job page renders a muted
sub-line beneath the stage progress bar reading "Batch N of M — X hosts checked". It
appears only once the first discovery batch has completed (so there is never a "batch 1
of ?" state) and disappears entirely once the job advances past the discovery stage. See
`docs/operators-guide.md` §11 for the underlying batch-progress mechanism.

---

## 14. OpenAPI Spec-Parsing Error Previews (Phase 172, SAFE-03)

If `--openapi-spec` (used with `--fuzz` or passive OpenAPI analysis) points at a spec URL
that is rejected by scope enforcement or the SSRF guard (or at a local spec file that does not
exist), the raised error includes a short preview of the URL rather than the full raw value.
As of Phase 172, that preview
is a genuine redaction, not a truncation: userinfo (`user:pass@`), the query string, and
the fragment are stripped before the preview is built. Scheme, host, and a truncated
path are kept.

When the spec download itself fails, the error names the exception type, the HTTP status when there is one, and the redacted URL preview.
A spec that downloads but fails to parse gets an error with no URL in it at all. As a general
practice, keep credentials out of spec URLs.

Keeping the host is deliberate: the host in the preview is the value the operator supplied on
the command line or in config, and removing it would make the error message useless for
diagnosing which target the scan was pointed at.

> **Client Conversation — Spec-Parsing Error Previews:**
> "If a scan refuses the OpenAPI spec URL you gave it — say it points outside the scan scope —
> the error message we log shows the host you gave us, so you can tell at a glance which target
> it was, and any username, password, or token embedded in that URL is stripped from that
> message."

---

## 15. Session-Over-Session Trends (Phase 178, IDENT-02)

The `/api/trends` endpoint (`quirk/intelligence/trends.py::compute_trend_report`) compares the
two most recent distinct scan sessions and reports which findings are new, which are resolved,
and — as of Phase 178 — which changed severity without opening or closing. See
`docs/intelligence-schema.md` §TrendReport for the full field table.

**Findings are matched on `(host, port, protocol)`, not on severity.** Before Phase 178 the match
key also included severity, and a filter dropped every row whose severity was `NULL` before the
comparison ever ran. Severity is populated only by some scanners and connectors (for example the
cloud, database and Vault connectors and the JWT, SAML, S/MIME, AD CS, code-signing, broker,
OpenAPI and REST-fuzz scanners), not by the TLS, SSH and HTTP scanners that produce most endpoint
rows — so on a typical scan database the large majority of endpoint rows carry no severity at all, and that filter
emptied both sides of the comparison for those rows: a scan whose rows all lacked severity reported 0 new / 0 resolved
findings regardless of what actually changed. Phase 178 removed the filter and dropped severity
from the key, so the delta now reflects real endpoint-level movement.

**Severity transitions are their own list, not a hidden double-count.** Because severity is no
longer part of the match key, an endpoint whose finding goes from HIGH to MEDIUM between two scans
is no longer reported as "1 resolved + 1 new" (which would misrepresent a partial fix as an
unrelated pair of events). Instead it appears once, in `severity_transitions`, as an entry naming
the endpoint's previous and current severity. Read a `HIGH -> MEDIUM` transition entry as *partial
remediation at that endpoint* — the underlying issue was not fully closed, but its severity
dropped. An endpoint in `severity_transitions` is excluded from the new/resolved sample lists for
that scan — it did not appear or disappear, it changed.

**The high/medium/low bucket counts can legitimately read zero while `new_total`/`resolved_total`
are non-zero.** `new_high`, `new_medium`, `new_low` (and their `resolved_*` counterparts) are
severity-bucketed and are honestly zero when every underlying row has no severity — which is the
normal case for rows from the TLS, SSH and HTTP scanners. `new_total` and `resolved_total` are the
severity-agnostic counts (`len(new_keys)` / `len(resolved_keys)`) and are the signal to read when
the bucket counts are zero: a report showing `new_total: 4` with all-zero severity buckets is the
report honestly telling you 4 endpoints changed, but it does not know their severity — not an
error and not a sign the trend engine is broken.

**A related, bounded gap:** the console's live view and this report can still word one shared
detection condition differently for the same underlying issue (the expired-certificate finding).
That divergence is measured and bounded — not silently reconciled — in
`docs/reviews/178-derivation-path-divergence.md` (D-178-A). It does not affect finding identity or
the trend counts described above; it affects only the wording (title and description) a consultant
sees on each surface.

> **Client Conversation — Trends:**
> "This trend report compares your two most recent scans. New and resolved counts are endpoint-
> based, not severity-based, so they reflect real change even when we haven't recorded a severity
> for every finding. If a finding's severity dropped rather than closed outright — say HIGH to
> MEDIUM — you'll see it listed as a severity transition, which we read as partial progress, not a
> fix-and-reopen."

---

*For scoring implementation details, see `quirk/intelligence/scoring.py`. For finding severity logic, see `quirk/engine/risk_engine.py`. For CBOM classification, see `quirk/cbom/classifier.py`. For the compliance mapping module, see `quirk/compliance/__init__.py`. For QRAMM implementation details, see `quirk/qramm/` and `src/dashboard/src/pages/print.tsx`. For hardware scanning and CBOM device hierarchy, see `quirk/scanner/hardware_*.py` and `quirk/cbom/builder.py`.*

## 16. Remediation Closure State (Phase 180-181)

Phase 180 computes and persists a machine-observed closure state — `open`, `closed`,
`not_observed`, or `resurfaced` — for every tracked remediation item, alongside a per-deadline
burndown aggregation against the Executive Order 14412 dates. Phase 181 renders that state: it now
appears in the HTML report (and the PDF printed from it), the DOCX report, the dashboard, and as CycloneDX VEX
entries in the CBOM. For the full four-state model — what each state means, why an item reads
`not_observed` instead of `closed`, why `resurfaced` is reported separately, and the documented
limits (sensor-origin exclusion, `evidence_only` items, the `unmapped` burndown bucket) — see
`docs/operators-guide.md` §16, which this section does not repeat.

The CLI technical markdown report does not carry closure state. `technical.py` has a burndown
renderer, but `writer.py` never passes it the burndown or the refusal, so that file never shows
the section. This is a known defect.

### Where closure state appears

- The HTML and DOCX reports each carry a **"Remediation Burndown"** section, with a
  byte-identical advisory caption: *"Advisory - remediation burndown does not
  affect the readiness score."* The caption is duplicated once per renderer by design (matching
  this repo's existing vendor-trend precedent). The three renderer copies (HTML, DOCX, and the unused
  CLI markdown renderer) are held equal by a test — it is not a single shared
  string, but the copies cannot drift apart without that test failing.
- The CBOM carries a `vulnerabilities` array — CycloneDX VEX — with one entry per remediation item.
- The dashboard shows closure state on the roadmap items it already displays (the roadmap detail
  panel's closure-state badge), and the Roadmap page carries its own Remediation Burndown table.
  That table does not show a closure refusal; see "When closure was not computed" below.

### Reading the burndown

The burndown is reported **per deadline**, never as one number. Each of the two Executive Order
14412 dates — key establishment (2030-12-31) and digital signatures (2031-12-31) — gets its own
row in the burndown table, with its own counts of `open`, `closed`, `not_observed`, and
`resurfaced` findings against that deadline. A third row, `unmapped` (deadline shown as "No
deadline mapped"), counts findings whose only algorithm evidence could not be matched to either
deadline. Whenever a burndown table is shown, this row is in it, even when its counts are zero. A
refused scan's report shows a refusal statement instead of the table (see below), and the dashboard
shows no table for a scan with no remediation fingerprints.

**There is deliberately no total and no "% remediated."** The burndown counts a finding under every
deadline its endpoint's recorded algorithms resolve to, so the same underlying finding can appear
in both buckets.
Summing across deadlines would double-count it. Read each deadline's figures on their own terms; do
not add them together, and do not look for a single readiness-style burndown scalar, because one
does not exist and will not be added — CLOSE-03 eliminated it deliberately.

**Known gap: TLS and SSH findings do not reach the key-establishment row today.** The burndown reads
only an endpoint's certificate key algorithm, certificate signature field and cipher-suite name. A
TLS cipher-suite name such as `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` (or the OpenSSL form
`ECDHE-RSA-AES128-GCM-SHA256`) resolves to no deadline, and an SSH row stores only the marker `SSH`
there. So a TLS finding counts only under digital signatures (from its certificate key) or under
`unmapped`, an SSH finding counts under `unmapped`, and the key-establishment row under-counts.
This is a known defect.

### Reading the CBOM VEX entries

Each remediation item's closure state maps to a CycloneDX `ImpactAnalysisState` as follows:

| Closure state | VEX `analysis.state` |
|---|---|
| `closed` | `RESOLVED` (serialized in the CBOM JSON as `resolved`) |
| `open` | `EXPLOITABLE` (`exploitable`) |
| `resurfaced` | `EXPLOITABLE` (`exploitable`; only a resurfaced entry carries `analysis.detail`, "Previously closed; re-detected as of scan …", which is what distinguishes it from ordinary `open`) |
| `not_observed` | `IN_TRIAGE` (serialized in the CBOM JSON as `in_triage`) |

**`not_observed` maps to `IN_TRIAGE` — serialized as `in_triage` in the CBOM's JSON —
never to `NOT_AFFECTED` (`not_affected`).** `not_affected` is a CycloneDX state
that asserts the item was assessed and found not to affect the product — that assertion was never
established for a `not_observed` item; the whole point of `not_observed` is that we did not verify
one way or the other this scan. `in_triage` is the honest reading of "we did not verify," and this
matters more in the CBOM than anywhere else in this guide: the CBOM is a machine-readable artifact
a client may feed directly into their own vulnerability-management tooling without a human present
to add the caveat. A wrong mapping here does not just mislead a reader of prose — it plants an
incorrect safety claim (`not_affected`) inside a downstream automated pipeline.

**A refused scan produces no VEX entry at all** — not an `IN_TRIAGE` entry, nothing. Emitting an
entry would imply an assessment was made for items we explicitly declined to compare. The burndown's
`unmapped` bucket does not affect VEX: entries are per remediation item and keyed on the item's
closure state alone, so an item whose findings matched neither deadline still gets an entry for its
state. The refusal itself is stated in the report's burndown section instead — see "When closure was not
computed" below — never silently absorbed into the CBOM as a blank `IN_TRIAGE` row.

**No VEX entry carries a CVE id, a source, ratings, or a host/port.** These are non-CVE remediation
items, not vulnerabilities in the CycloneDX-source sense — the CycloneDX 1.6 schema's
`definitions.vulnerability` has no required fields, so a minimal, honest entry (an `id` that is the
item's slug, a description, and the analysis block above) is fully legal without fabricating any of
that data. The item slug is the correlation key back to the report's roadmap and burndown sections.

### When closure was not computed

If there is no comparable prior scan, or the current scan's scope does not match the prior scan closely enough, closure is
**refused**, not silently skipped. The report states this explicitly and names the differing
axis — for example "Closure not computed: scan scope differs from the prior scan." — rather than
omitting the section. **This must not be read as "nothing closed."** An omitted or all-zero-looking
burndown section would be the false-negative twin of the false-closure risk this whole model exists
to prevent: a consultant reading silence as "no progress" is just as wrong as reading it as
"everything's fine." When you see a refusal statement, the honest response is "we don't have a
comparable answer this run," not "0 closed."

The dashboard does not show the refusal. Its Roadmap page still renders the burndown table for a
refused scan, with every item in the Not Verified column and no refusal statement. Read a refusal
from the exported HTML, PDF or DOCX report, not from the dashboard or the CLI technical markdown.

> **Client Conversation — Remediation Burndown:**
> "This burndown section is per deadline, not a single number — we deliberately don't add a
> 'percent remediated' headline, because the two Executive Order deadlines can both apply to the
> same finding and a total would double-count it. And if you see an item marked `not_observed`,
> that means we didn't verify it this run, not that it's clean — the CBOM reflects that same
> distinction as `IN_TRIAGE`, never as 'not affected,' because we never assert something is safe
> without having actually rechecked it."

---

## 17. Confidence Rating and Its Four Factors (Phase 184.1, SCORE-01)

### What the confidence rating is not

The confidence rating measures how much QUIRK trusts its own assessment of the estate — not
whether the estate's cryptography is good. A HIGH confidence rating paired with a poor readiness
score is not a contradiction; it is the correct reading of a fully-plaintext estate we assessed
completely. We are confident in the assessment, and the assessment is bad news. The readiness
score and the confidence rating are deliberately orthogonal: coverage answers "did we assess it,"
never "is it good." Plaintext HTTP, for example, counts as fully assessed for confidence purposes
and is penalized separately, on the readiness score, via `plaintext_http_count`.

### The four factors

`compute_confidence()` (`quirk/intelligence/confidence.py`) produces a 0-100 `confidence_score`
from four weighted factors:

| Factor | Weight | Numerator | Denominator |
|--------|--------|-----------|-------------|
| `coverage_ratio` | 0.35 | `assessed_crypto_count` — endpoints QUIRK actually assessed | `assessable_endpoint_count` — endpoints that were real scan targets |
| `scan_error_ratio` | 0.30 | endpoints whose probe errored | all endpoints |
| `unknown_ratio` | 0.15 | endpoints classified `UNKNOWN` | all endpoints |
| `tls_enum_coverage_ratio` | 0.20 | TLS cipher/version enumeration actually completed | TLS endpoints found |

**`coverage_ratio` (weight 0.35).** Both the numerator (`assessed_crypto_count`) and denominator
(`assessable_endpoint_count`) are emitted by `build_evidence_summary`
(`quirk/intelligence/evidence.py`), not derived from the fixed-key `protocol_counts` dict —
`protocol_counts` only counts a fixed list of protocol keys (it did not list the six email/STARTTLS
protocols SMTP-STARTTLS, SMTPS, IMAPS, IMAP-STARTTLS, POP3S and POP3-STARTTLS until Phase 188 added
them) and would silently under-count any protocol missing from that list. The rules:

- **`ADVISORY` and `CLOSED` leave the denominator entirely — they are not scanned assets.**
  `ADVISORY` rows are scanner self-reports (a liveness pre-pass notice, a missing-extra notice,
  `broker_scanner.py`'s cleartext/credential advisories), not endpoints QUIRK probed. `CLOSED`
  rows are TIMEOUT/REFUSED/UNREACHABLE probe outcomes, already filtered out of the client-facing
  technical inventory by `quirk/reports/technical.py`. Neither belongs in a ratio meant to
  answer "of the assets we tried to assess, how many did we succeed on."
- **`UNKNOWN` endpoints and endpoints whose probe errored (`scan_error`) leave the numerator but
  stay in the denominator.** They were real scan targets we tried and failed to assess, which is
  exactly what should lower coverage.
- **Plaintext `HTTP` counts as assessed.** We successfully determined the endpoint uses no
  encryption at all — that is a completed assessment, not a gap in one.
- **A mail port that refused the connection or timed out before any TLS was negotiated is not
  counted at all** — neither as assessed nor as an endpoint in the coverage ratio, the same as a
  closed port, and it does not count as plaintext in the data-in-motion subscore. A server that
  accepts the connection and then errors (for example, one that sends nothing) records a scan
  error and is not assessed. A server that answers but does not offer STARTTLS is also not assessed today: the probe records the mail
  client's "STARTTLS extension not supported by server" error as a scan error, so the endpoint
  leaves the numerator like any other errored probe, produces only an INFO "Informational protocol
  observation" finding, and counts against the data-in-motion subscore as an email endpoint with
  no TLS. This is a known defect: the rule was meant to count such hosts as assessed.

**`scan_error_ratio` (weight 0.30).** Numerator: endpoints whose probe raised a scan error, as a
fraction of all endpoints. Points awarded scale with `(1 - scan_error_ratio)` — fewer errors,
more points.

**`unknown_ratio` (weight 0.15).** Numerator: endpoints classified `UNKNOWN`, as a fraction of all
endpoints. Points awarded scale with `(1 - unknown_ratio)`.

**`tls_enum_coverage_ratio` (weight 0.20).** Measures how completely TLS cipher/version
enumeration finished across TLS endpoints. Guarded by the `CR-01` rule below.

### The deliberate double penalty

An endpoint whose probe errored costs the score twice by design: once by leaving
`coverage_ratio`'s numerator (it was not assessed), and again through `scan_error_ratio` (it is
counted as an error). The same double-counting applies to `UNKNOWN` endpoints, once through
`coverage_ratio`'s numerator and once through `unknown_ratio`. This is intentional, not an
oversight — the two factors measure related but distinct things (assessment completeness and
error rate), and "why was my errored endpoint counted twice" is expected to be the first question
this metric generates from a reader who has not seen this section.

### CR-01: the TLS-enumeration guard

`tls_enum_coverage_ratio` defaults to a vacuous `1.0` when a scan has zero TLS endpoints — there
is nothing to enumerate, so completeness is trivially total. To prevent a zero-TLS scan from
earning a phantom +20 points for enumeration it never performed, the CR-01 guard withholds the
entire `tls_enum_coverage_ratio` bonus whenever `tls_count == 0`, regardless of the ratio's
computed value.

### Rating bands

| Score | Rating |
|-------|--------|
| 85 and above | HIGH |
| 65 and above | MEDIUM |
| 40 and above | LOW |
| below 40 | VERY_LOW |

### `NO_DATA`

`confidence_rating` is `NO_DATA` (with `confidence_score: 0`) in two distinct cases, neither of
which awards a partial score:

1. **Zero endpoints.** The scan found nothing to report on at all.
2. **Zero assessable endpoints.** The scan found endpoints (`totals.endpoints > 0`), but every one
   of them was excluded from the coverage denominator — for example, a port sweep that found
   nothing open plus a single `ADVISORY` notice. Awarding up to 35 coverage points for a scan that
   assessed nothing would be the same phantom-points defect the CR-01 guard exists to prevent for
   TLS enumeration, so this case reuses the same `NO_DATA` shape rather than computing a partial
   score from zero real data.

### D-15: absence of the formula-version marker means the report predates Phase 184.1

Every `compute_confidence()` result produced from Phase 184.1 onward carries a
`confidence_formula_version` field, currently `"2.0.0"`. **A report or API response carrying no
`confidence_formula_version` field predates Phase 184.1 and was produced under the older formula**,
in which `coverage_ratio` counted only TLS and SSH endpoints (`protocol_counts["TLS"] +
protocol_counts["SSH"]`) against every endpoint in the scan, including advisories and closed
ports — the exact inversion this phase corrects.

**Where to actually look.** The marker is emitted on exactly three shipped surfaces, and nowhere
else — the absence rule above applies *to those three surfaces only*; a client reading some other
artifact (for example a raw DB row, or a surface this phase does not touch) should not infer a
formula version from its absence there:

1. **`intelligence-{stamp}.json`** (the report bundle's intelligence file, written by
   `quirk/reports/writer.py`) — the field lives at JSON path
   `confidence.confidence_formula_version`.
2. **The executive summary markdown** — in the `## Confidence & Coverage` section, the field
   appears as a literal bullet: `- **confidence_formula_version:** {value}` (emitted by
   `quirk/reports/executive.py`; the bullet is omitted entirely when the value is falsy).
3. **The `/api/scan` JSON response** — the field lives at the same JSON path,
   `confidence.confidence_formula_version`, and is `null`/absent only when the confidence
   computation itself failed (the exception fallback in `quirk/dashboard/api/routes/scan.py`
   explicitly sets it to `None` rather than inventing a version string).

The value is a **scoring-formula version**, deliberately independent of the product version and
of the three separately-drifting `intelligence_version` values (`quirk/config.py`,
`quirk/dashboard/api/routes/jobs.py`, `quirk/reports/writer.py`) — per D-12, reconciling those
three is its own future phase's work, and `confidence_formula_version` must never be "reconciled"
against them; they answer a different question.

Confidence is never persisted: each surface (`reports/writer.py`, `reports/executive.py`,
the `/api/scan` route) calls `compute_confidence()` at render time. The two report writers run once,
when the scan writes its files; the `/api/scan` route recomputes from the endpoints stored for that
scan run on every request. There is no stored confidence value anywhere in the database. This means
the dashboard view of an old scan shows the new-formula number
immediately — no backfill, no migration. Report files already written are not changed. When a client
asks why a confidence rating moved between two report files of the same estate, the answer is
readable from the files themselves: the older one has no `confidence_formula_version` field in
its intelligence JSON or executive summary, the newer one reads `"2.0.0"` in both, and this section names
exactly what changed between them.

---

## 18. Timestamps and Time Zones (Phase 184.3, SCORE-03)

### Every timestamp is UTC, and says so

Every timestamp QU.I.R.K. reports denotes a single, unambiguous instant in UTC. API payloads
(`GET /api/scans` and every other dashboard route that returns a datetime field) carry an
explicit `+00:00` offset — `"2026-09-04T15:28:56.218111+00:00"`, never a bare
`"2026-09-04T15:28:56.218111"` — so a downstream tool parsing that string cannot mistake it for
local time. The scan identifier (`scan_id` in `/api/scans` and `/api/scan/latest`) has the same
shape but is an opaque key, not a datetime field, and is returned without an offset. Before this phase, the offset was missing: a client's own tooling (and, in the
dashboard's case, the browser's own `Date` parser) read a naive ISO string as *local* time,
producing a skew of however many hours the reader's machine sits from UTC. That defect is what
this section, and two source-scan gates, now permanently close: `tests/test_timestamp_serialization_gate.py` (Python serialization) and `src/dashboard/src/components/__tests__/new-date-argument-guard.test.ts` (dashboard date parsing).

Two client-visible surfaces apply that UTC instant differently, deliberately:

- **The interactive dashboard** shows times in *your browser's* local time zone, with the zone
  abbreviation visible next to every full date-and-time value (for example `Sep 4, 2026 11:12 AM EDT`). This is
  the one surface that is not fixed-UTC — it is meant to match the wall clock of the person
  looking at the screen, and the visible zone label is what lets you reconcile a screenshot
  against your own clock without guessing which time zone produced it. Three kinds of dashboard
  display carry no zone label: date-only values, relative ages such as `5 min ago`, and the trend
  chart's axis ticks, which show local month/day and hour:minute.
- **`/print` and the PDF / DOCX / HTML report exports** all show the scan instant in fixed,
  labeled UTC, regardless of which machine or time zone generated the export. The report exports
  write it as `2026-09-04 15:28 UTC`; `/print` writes the same instant in the dashboard's date
  format, `Sep 4, 2026, 3:28 PM UTC`. For the latest scan this means the same scan, exported any
  way, from any machine, states the same instant, although `/print` formats it differently from
  the report files. When a scan is picked in the dashboard's scan selector, `/print` shows that
  run's identifier stamp (the time the run started) instead, which can be minutes earlier than
  the report's `Scan Completed` (the newest endpoint `scanned_at`). `/print` was deliberately
  aligned to fixed UTC in this phase so that a client comparing a live `/print` view against a
  delivered PDF/DOCX/HTML report reads both in the same zone
  — it does not follow the browser-local rule the rest of the interactive dashboard follows.

### `Scan Completed` vs `Generated`

Every report (executive markdown, technical markdown, HTML, and DOCX) states two distinct
instants, each labeled `UTC` and each under a label that cannot be confused with the other:

- **`Scan Completed`** (`Scan completed:` in the markdown reports) is when the evidence was
  actually collected — derived from the scanned endpoints' own `scanned_at` values, not from when
  the document was produced.
- **`Generated`** (`Generated:` in the DOCX cover and the markdown reports; the HTML cover block's
  matching row was itself corrected this phase from an inaccurate `Scan Date` label, which had
  been silently showing the document-build time rather than any scan instant) is when the
  *document* was built.

A gap between these two values is expected and normal — a report is very often produced some time
after the scan it describes ran, whether minutes or days later. If the scan instant cannot be
determined for a particular report (for example, no endpoint carries a `scanned_at` value), every
report path shows the same explicit marker, `Unknown (no scan instant available)`, rather than
silently substituting the document's build time — a report never claims to know when a scan ran if
it does not.

### Calendar dates are not instants

Certificate expiry (`cert_not_after`) and hardware end-of-life (`eol_date`) are calendar DATES,
not instants: they carry no time-of-day and no zone label anywhere they are rendered. They are
computed and displayed in UTC specifically so that the calendar day itself cannot shift depending
on which time zone happens to render it — an expiry date one day either side of midnight UTC
would otherwise appear to move by a day depending on the reader's local offset, which is worse
than useless for a compliance deadline.

---

## 19. The Severity Floor: Band and Score Are Two Different Things (Phase 184.4, SCORE-04/SCORE-05)

### Where the severity floor came from (Phase 184.4, scoring v2)

Before Phase 184.4, a scan could score 89/100 — comfortably inside the 85–100 `EXCELLENT` range —
while still carrying one open CRITICAL finding, such as an expired TLS certificate. Report
generation halted in that situation with:

```
Report generation halted: executive headline 'EXCELLENT' is inconsistent with 1 CRITICAL
finding(s). Review findings before generating the report.
```

The number was correct under scoring v2. The label was the problem: no consultant can defensibly
call an estate with an open expired certificate `EXCELLENT`. Phase 184.4 fixed this by giving the
**band** — not the score — a severity floor: **any open CRITICAL finding caps the band at `FAIR`**,
no matter how high the underlying number is. Under scoring v2 a scan scoring **89/100** with one
open CRITICAL finding (`TLS certificate expired`, port 9443) and one open HIGH finding (`TLS
certificate is self-signed`, port 10443) therefore showed **score: 89**, **band: FAIR**, and
generated successfully, with the cap explained beside the headline.

### What scoring v3 changed: the number is capped too

Scoring v3 (§3.6) moved the same protection onto the number itself. Open CRITICAL and HIGH
findings now set an absolute **ceiling** on the score, and the band is derived from the capped
number: one or more CRITICAL findings limit the score to 34 (`POOR`), five or more to 25, three or
more HIGH findings to 54, and one or two HIGH findings to 69. The ceiling compresses the score
rather than clamping it, so the example above (computed 89, one CRITICAL) now reads **score 30,
band `POOR`**, not 89 and `FAIR`.

The v2 band floor is still in place as a second, independent guarantee: the report's congruence
guard still refuses a headline band that is inconsistent with the open CRITICAL count, and the band
floor still caps `EXCELLENT`/`GOOD`/`MODERATE` at `FAIR` if a CRITICAL-bearing score ever reached
those bands. Because the v3 ceiling already places a CRITICAL-bearing estate in `POOR`, the floor
rarely binds on a v3 score. A scan whose number already lands it in `FAIR` or `POOR` is unaffected
by the floor.

### Why a score can still look high next to a CRITICAL finding on an older report

**"Why is my score still 89 if there's a CRITICAL finding?"** On a report produced under scoring
v2, that was the correct reading: the floor capped the *band* only, and CRITICAL findings reached
the number only through the agility subscore's high-impact ratio, which was diluted by the total
finding count. On a scoring-v3 report this combination cannot occur; check the `Scoring model` row
(§27) to see which model produced a given number. Scores from different scoring versions are not
comparable (§3.6).

### The cap reason: what it says, and where it appears

Whenever the score or band is capped, every report surface shows a short, structured explanation
alongside the headline — not a synthetic scoring driver, not buried in a table, but directly
beside the score/band pair itself. Under scoring v3 it names the ceiling and discloses the
uncapped figure:

```
1 open CRITICAL finding — score limited to 34 (computed 100)
```

The older v2 band-only form reads `Band capped at FAIR: 1 CRITICAL finding(s) open (score 89/100).`
and is produced when only the band floor applies. Both strings (the `rating_cap_reason` field,
internally) are built only from static band names, counts and integers — never from a finding's
title or description — so every report renderer prints the same string verbatim. The two dashboard
surfaces print the reason from the dashboard's own score, which it recomputes from the database and
which can differ from the report's (see §7.1). The cap
reason renders on **all six** report/dashboard surfaces:

1. **CLI executive summary** (markdown) — a `**Cap reason:**` line directly beneath the Rollup
   arithmetic line (`**Rollup:** 150 ÷ 1.5 = **100**, capped to **34 / 100**`; the rollup shows
   what the division actually produces, then the capped figure).
2. **HTML report / PDF export** — an unlabeled italic line directly below the score card, before
   the Score Decomposition table and the Score Drivers list.
3. **DOCX report** — a paragraph beside the Score Breakdown Rollup line.
4. **Scorecard** (the condensed markdown summary) — a `- **Cap reason:**` line beside the score
   headline.
5. **CLI terminal summary table** — a `Cap reason` row, shown only when the score or band is capped.
6. **Dashboard Executive page and print page** — the same string rendered beside the readiness
   headline, next to the confidence badge.

### What the absence of a cap reason means

If a report with a computed score shows **no** cap reason anywhere, that is a positive statement, not missing data: it
means neither a ceiling nor the band floor applied — there is no open CRITICAL or HIGH finding and
a hybrid post-quantum key exchange was observed. A report generated before Phase 184.4 shipped also
shows no cap reason (the field is simply absent from older score data), which renders identically
to "not capped" rather than raising an error. A score that was not computed (§3.6) never carries a
cap reason, even when CRITICAL findings are open.

> **Client Conversation — The Severity Floor:**
> "Your report shows a score limited well below what the rest of the estate would earn. That's not
> a mistake — the number reflects your overall posture across the scoring dimensions, but it is
> deliberately limited whenever an open CRITICAL or HIGH finding exists, like the expired
> certificate we found on port 9443. We do this because a single unresolved critical issue
> shouldn't let an estate read as 'excellent' even if everything else scores well. The 'Cap
> reason' line beside the headline explains exactly why and shows the uncapped figure — once that
> CRITICAL finding is remediated, the score will reflect the underlying posture again on your next
> scan."

## 19.5 Executive Verdict (Phase 194, VERDICT-01)

### What the verdict is

The dashboard's Executive page renders an **Executive Verdict** panel above the readiness
gauges — a plain-language reading of the same server-computed readiness rating that already drives
the score/band headline elsewhere in this document (§19). It exists to answer, in one glance,
"is this environment quantum-ready" without asking a reader to interpret a 0-100 number
themselves.

### The band mapping

The verdict maps the API's six-value `rating` enum to three plain-language outcomes:

| API `rating` | Verdict label | Color |
|---------------|----------------|-------|
| `EXCELLENT`, `GOOD` | QUANTUM-READY | green (safe) |
| `MODERATE`, `FAIR` | PARTIALLY READY | amber (at-risk) |
| `POOR` | NOT QUANTUM-READY | red (vulnerable) |

### The band comes from the API's rating, never a client-side cutoff

Before this phase, the same panel (built on a code-review-sourced spike, never shipped) derived its
band from a client-side `score >= 80` / `score >= 50` cutoff, independently of the server's own
band computation. That path is gone. The verdict now reads the band **exclusively** from the
`rating` field the `/api/scan/latest` payload already carries — the same field §19's severity-floor
cap acts on — so the verdict and the score/band pair shown elsewhere on the page can never disagree.
The dashboard's regression test pins this with a deliberately synthetic payload, `score: 91,
rating: "POOR"`, which renders `NOT QUANTUM-READY`, matching the rating, not the `QUANTUM-READY` a
naive score cutoff would have shown. No server scoring path emits that pairing: §19's floor never
caps a band below `FAIR`, and whenever the scorer returns a number, its rating is that number's own
band. The payload exists only to prove that the verdict ignores the number.

### The cap reason

When `rating_cap_reason` is set (§19's severity floor is active), the verdict panel shows an inline
note directly beneath the band label:

```
Score capped: <reason>
```

This is not an error and not a second, competing signal — it is the same `rating_cap_reason` string
§19 documents, rendered in the verdict panel as well as the score card. Read a capped score as a
caveat on the number, not a contradiction of it: the uncapped figure reflects the whole posture, the
cap reflects the open CRITICAL or HIGH findings (or the missing post-quantum key exchange) holding
the score back from what it would otherwise be.

### The honest-absence state

A scan whose payload carries no `rating` value at
all (the panel's own wording attributes this to data from before v5.21). Rather than guessing a band from the raw score alone, the verdict panel renders:

```
Verdict not available for this scan (pre-v5.21 data).
```

The same card is also shown when the scan assessed no domain at all (rating `NOT_ASSESSED`, §3.6), in which
case the "pre-v5.21" wording does not describe the cause; read it there as "no verdict was computed".
In practice this is the case you will see: `/api/scan/latest` recomputes the rating from the stored
endpoints on every request, so data written before v5.21 also arrives with a rating.

**This is not a poor result — it is an honest statement that no band was computed for this
scan.** Treat it exactly as you would a missing field in any other report section: the absence of a
verdict does not imply "not quantum-ready," it means no scoring domain had assessable evidence (or,
for a payload with no rating, that none was supplied). Re-scanning produces a verdict once the scan
reaches endpoints that at least one domain can assess.

## 19.6 Certificate inventory completeness (Phase 194, DASH-09)

### Only real certificates are listed

The certificates page and the `/print` PDF export list only TLS endpoints that both (a) carry a
certificate subject and (b) completed the TLS handshake without a scan error. A failed handshake
never yields a certificate to inspect — attempting to synthesize or infer one from a failed
connection would fabricate data the scan never actually observed, so the endpoint is excluded from
the certificate table entirely rather than shown with blank or placeholder fields.

### The disclosure line

Whenever any TLS endpoints were excluded for this reason, both the dashboard certificates page and
the `/print` PDF render the same disclosure line above the certificate table:

```
N TLS endpoints failed handshake and are not shown.
```

`N` is the server-authoritative `excluded_cert_count` field on the `/api/scan/latest` payload —
never a client-side re-filter of the certificate list — so a reader can always reconcile the number
of TLS endpoints the scan actually reached against the number of certificates shown in the table.
The line appears identically on both surfaces because both read the same fixed payload; it is
absent entirely when the exclusion count is zero. `N` counts every TLS row of the scan that is not
listed, not only failed handshakes. That includes the extra TLS row the PQC probe writes for each
server where it confirms a hybrid post-quantum key exchange (no certificate, no error), so such a
server adds one to `N` even though its handshake succeeded.

### Reading an empty table alongside a non-zero exclusion count

`No TLS certificates discovered in this scan` can appear **at the same time** as a non-zero
exclusion count in the disclosure line above it. Read that combination correctly: it means TLS
endpoints were reached during the scan, but **none** of them completed a handshake that yielded a
certificate — a real finding about the estate's TLS posture, not an empty or failed scan. An empty
certificate table with **no** disclosure line above it means the opposite: no TLS endpoints were
even attempted, which is the genuinely empty case.

## 20. Unreached Broker Target Advisory (Phase 190, TRIAGE-06)

`connectors.broker_targets` (see [`docs/configuration.md`](configuration.md)) lets an operator
name explicit `host:port` broker endpoints to probe in addition to each broker family's default
ports. When an explicitly-named `host:port` entry never responds to *any* probe across all three
broker drivers, the scan records exactly one row with `protocol="ADVISORY"` and a detail message
naming the unreached target (e.g. `"Configured broker target broker.internal:29099 did not
respond to any probe"`).

**What it means:** you told QU.I.R.K. about a specific broker port and it could not be reached
during this scan — worth checking that the service is actually up, the port is correct, and
there is network reachability from the scan host.

**What it does NOT mean:** a *default-port* broker probe that finds nothing produces no row at
all — that silence is by design (a scanner does not report "checked and found nothing" for every
one of dozens of speculative default ports on every host, or the report would drown in noise).
The unreached-target advisory exists specifically because an operator-named target is a
deliberate assertion ("a broker lives here") that deserves an explicit answer, unlike a
default-port probe which is exploratory.

**Advisory, but not invisible to the score:** the row is `INFO` severity and is not a cryptographic
posture finding. The written report still lists it in its findings tables as an `INFO`
"Informational protocol observation" (the dashboard's findings list does not show it), and its scan
error counts toward the scan-error rate that the hygiene and modern-TLS subscores penalise, so an
unreached target can lower the readiness score slightly.

> **Client Conversation — Unreached Broker Target:**
> "You listed `broker.internal:29099` as a broker endpoint we should check, but our scan
> couldn't get a response from it on any of the broker protocols we tried. It isn't a finding
> about your cryptography — it's telling you the target you named wasn't reachable during this
> scan, which is worth double-checking (is the service running? is the port right? can this scan
> host reach it over the network?)."

## 21. Key Reuse (Phase 191, SPKI-01/SPKI-02)

The TLS scanner now fingerprints the public key of every leaf certificate it parses — a SHA-256 digest of
the certificate's SubjectPublicKeyInfo (SPKI), the same construction used by RFC 7469 HPKP
pinning. A "Key Reuse" section appears in every generated report (CLI technical markdown, HTML,
and DOCX; the HTML and DOCX leave it out only when the scan database cannot be read) and shows
which TLS endpoints share the exact same public key. The section reads every scan in the database,
not only the current one (unlike the exposure map, §23), so its counts and clusters cover the TLS
rows of all stored scans.

**What the section shows:** a coverage line — `"N of M TLS endpoints have SPKI fingerprints."`, where
`M` counts every stored TLS row across all scans, including rows that never carried a certificate
(failed handshakes, and the PQC probe's extra row per confirmed hybrid server) —
followed by either a list of shared-key clusters, ordered biggest-first, or an explicit statement
that no shared keys were found. Each cluster identifies the shared key (certificate subject,
public-key algorithm and size, and a truncated fingerprint) and lists every stored row (`host:port`)
using that key. Because the section spans scans, the same `host:port` appears once for each scan
that saw it, so an endpoint scanned twice with an unchanged key forms a cluster on its own.

**Why it is advisory-only:** the italic caption directly under the "Key Reuse" heading —
`"Advisory - key reuse does not affect the readiness score."` — is not a formality. Key reuse is
never added to the readiness score, never appears in any severity-ranked findings table, and is
covered by a dedicated firewall test (`tests/test_key_reuse_score_guard.py`) that fails the build
if the scoring module is ever imported into the key-reuse code path. This is deliberate: sharing a
public key across endpoints is an operational/architectural fact, not by itself a cryptographic
weakness with a severity — the same key could be shared safely behind a load balancer, or badly
across systems with different blast radii. Scoring it would either double-penalize a single
certificate's existing weaknesses (already scored elsewhere) or invent a severity judgment the
scanner cannot make responsibly.

**How to read the leverage framing:** each cluster is phrased as
`"Re-keying this certificate remediates N endpoints."` — read this as one remediation action
(rotate this one certificate/key) that closes N exposures at once, not as N separate problems to
fix independently. If a cluster lists 12 endpoints, that is one ticket, not twelve. Count the
distinct `host:port` entries rather than trusting N: N counts rows across scans and can count the
same endpoint more than once.

**What the coverage line implies about endpoints scanned before this feature existed:** SPKI
fingerprints are computed at TLS certificate parse time, starting with 5.21.0. There is no
backfill — the raw certificate bytes are not persisted anywhere in the database, so a fingerprint
cannot be reconstructed after the fact for a `crypto_endpoints` row that was written by an older
scan. A row written before this feature shipped keeps `cert_spki_fingerprint` `NULL` for good:
re-scanning the host adds a new, fingerprinted row, and the old row stays in `M`. So if your
coverage line reads `"40 of 120 TLS endpoints have SPKI fingerprints,"` the other 80 are a mix of
pre-5.21 rows (including older rows for hosts you have since re-scanned) and rows with no
certificate (failed handshakes, PQC probe rows). Re-scanning is the only way to fingerprint a
host, but it does not bring the ratio to 100%.

**What "no shared keys detected" does and does not mean:** the zero-reuse sentence —
`"No shared keys detected across N fingerprinted endpoints."` — is a statement about the N
endpoints that currently have a fingerprint, never about all M TLS endpoints in the inventory.
Because unfingerprinted endpoints are excluded from reuse analysis entirely, a report can honestly
say "no shared keys" among a small fingerprinted subset while a much larger unfingerprinted
population remains unexamined. Always read the "no shared keys" statement together with the
coverage line above it, not in isolation.

> **Client Conversation — Key Reuse:**
> "Your report shows one certificate is reused across 12 different endpoints. That's not counted
> against your score — key reuse by itself isn't a severity finding — but it is real remediation
> leverage: rotating that one certificate closes all 12 exposures in a single action instead of
> chasing them one at a time. The coverage line also tells you how many of your TLS endpoints we
> could check for this — anything scanned before this feature existed needs a re-scan before we
> can tell you whether it shares a key with anything else."

## 22. Scan Coverage (Phase 192, OBS-01/OBS-02)

Every generated report (CLI executive and technical markdown, HTML, and DOCX) now carries a "Scan
Coverage" section. In the executive markdown, HTML and DOCX it sits immediately after the
executive-summary metadata and before the readiness assessment; in the technical markdown it comes
before the service inventory. It answers a single question: **which scanner phases actually ran during this scan,
and why did any that didn't run get skipped?**

### What the section is NOT

This section is deliberately distinct from the existing "Confidence & Coverage" section (§17) and
the "Discovery and Coverage" section (§13). Those sections
report **per-endpoint assessment quality** — how many endpoints of a given type were reachable,
liveness-probed, or had enough data for a confident score. Scan Coverage reports **per-phase
execution status** — whether a scanner phase (TLS, SSH, JWT, container, vault, broker, database,
and 18 others) ran at all this scan, independent of how many endpoints it found once it did run.
A phase can run and still contribute low confidence (§17's concern); a phase can also never run at
all, which is what this section discloses.

### Reading the section

The heading is followed by a `{N} ran / {M} skipped` summary line, then one row per phase: ran
rows show the phase's wall-clock duration; skipped rows show the skip reason plus a short,
non-secret detail string (e.g. `connectors.vault_token / VAULT_TOKEN not set`). There are exactly
five skip reasons, each implying a specific operator action:

| Skip reason | What it means | What to do |
|---|---|---|
| `disabled-by-config` | The connector/scanner is turned off in your config. | Enable it (flip the relevant `connectors.enable_*` or scanner toggle) if you want that domain assessed. |
| `missing-extra` | The scanner needs an optional Python package that isn't installed. | Install the optional extra that provides the named package (see `docs/operators-guide.md` §2.2, Optional extras matrix). The extra named in some skip details does not exist: `(extras: vault)` means `[cloud]`, which carries hvac, and `(extras: aws)` names no extra (boto3 is a core dependency). |
| `no-eligible-targets` | The scanner is enabled, but no targets were configured for it. | Add hosts/addresses to the named config key (e.g. `connectors.vault_targets`). |
| `missing-credentials` | The scanner is enabled and has targets, but the credential it needs to authenticate is not set. Today only the Vault phase makes this check, when the phase starts during the scan (`connectors.vault_token` / `VAULT_TOKEN`); a dashboard submit does not check it. | Supply the named config key or environment variable — see the Effective config panel (`docs/operators-guide.md` §3.1.2) to check credential status before submitting a scan; the panel shows each credential as set or not set and never shows a value. |
| `failed` | The phase started and aborted with an error. | Check the error rows / logs for that phase; this is not a configuration gap, it is a runtime failure. |

### A skipped phase never fabricates a zero

The absence of a row for a phase is never itself a signal — every one of the 25 scanner phases
is recorded, ran or skipped, explicitly. If a scan predates this feature (before v5.21), the
section states plainly that coverage was **not recorded** for that scan, rather than rendering an
empty or all-zero table. There is no backfill: coverage recording starts at the scan that produces
it, and the only way to get coverage data for an older target set is to re-scan it. Discovery
and the hardware fingerprinting pass are not among the 25 phases and never get a row, on a fresh
or a resumed scan.

### D-14: a domain section whose phase was skipped states its own skip

For the one report section whose *heading itself* — not merely its rows — normally vanishes when
its backing data is empty (the CLI technical report's "TLS Capabilities" section), a skipped `tls_scanning` phase now
makes that heading state "Not assessed — skipped: {reason}" explicitly, on all three surfaces
(CLI, HTML, DOCX), instead of silently disappearing (the HTML and DOCX have no TLS Capabilities
heading otherwise, and add one only to carry this note). Every other scanner phase feeds an omnibus
findings table that renders unconditionally (an empty-state message in the executive summary,
HTML and DOCX; a header-only table in the CLI technical report) regardless
of which phase(s) produced zero data — for those 24 phases, the Scan Coverage section above is the
sole per-phase disclosure surface.

> **Client Conversation — Scan Coverage:**
> "Your report shows the vault scanner was skipped this run because no Vault token was
> configured. That's not a finding against your posture — it just means we weren't able to check
> that domain this time. Add the token and re-scan, and that domain will show up in your coverage
> going forward."

### `missing-credentials` vs. `disabled-by-config` vs. `missing-extra` — a dashboard scan submitted without credentials (Phase 193)

As of Phase 193, a scan can be submitted from the dashboard's Connectors panel
(`docs/operators-guide.md` §3.1.4) with a connector switched **on** but its credential field left
**blank** — enabling a connector without a credential is allowed, not rejected. For the Vault
connector, whose token has no implicit fallback, that combination produces a `missing-credentials`
row (when `hvac` is installed and a Vault address is set; otherwise the earlier `missing-extra` or
`no-eligible-targets` skip fires first) in this Scan Coverage section, and it reads differently from the other two config-related skip
reasons even though all three sound similar. Other connectors are not gated this way: the database
connectors, for example, deliberately run with no configured credentials and let the client library
read its own defaults (`.pgpass` / `PGPASSWORD` for PostgreSQL). The MySQL connector passes no
password at all and does not ask pymysql to read a defaults file, so it attempts a password-less
login as the configured user (default `root`):

- **`disabled-by-config`** — the operator never turned the connector on at all (`enable_*: false`).
  Nothing was attempted.
- **`missing-extra`** — the connector is on, but the server doesn't have the optional Python
  package installed to run it. The operator can't fix this from the dashboard form; it requires a
  `pip install 'quirk-scanner[<extra>]'` on the machine running the scan.
- **`missing-credentials`** — the connector is on, the code to run it is installed, but no
  credential was available when the Vault phase started (blank dashboard field and no environment-variable
  fallback set). Of these three reasons, this is the one where re-running the *identical* scan with only a credential
  added will change the outcome — nothing else about the target or config needs to change. Today
  only the Vault token is checked this way.

## 23. Exposure Map (Phase 195, MAP-02/MAP-03)

The dashboard carries a new "Exposure Map" tab (`/exposure-map`) rendering a node/edge graph of
**verified-only** quantum-exposure relationships between scanned endpoints. It exists to answer
one question for a consultant preparing a client conversation: "if one of these systems is
compromised, what else is provably connected to it by evidence this scan actually collected" —
never a guess, never an inferred network path.

### What it shows

Nodes are scanned endpoints (`host:port`; the two ends of a hardware crypto-bridge edge are bare
device addresses), plus **certificate-authority hub nodes** (hexagonal,
labelled with the CA's CN) added in v5.25. Edges connect nodes **only** when recorded scan
data proves a concrete relationship between them — there is no topology probing, no `nmap`-style
reachability inference, and no fabricated or assumed path. Every edge that renders carries a
citable evidence string, shown on hover.

### The edge taxonomy

Three edge types ship, each with a distinct color AND line style so a consultant can explain at a
glance *why* a line exists, and so the distinctions survive colorblindness and grayscale printing:

| Edge type | Appearance | What it means |
|-----------|------------|----------------|
| Key-reuse cluster | amber, solid | The two endpoints share the same TLS certificate SPKI SHA-256 fingerprint — the same key material is doing double duty, and compromising one endpoint's key compromises the other's too. Backed by the same derivation `docs/report-interpretation.md` §21 documents for the CLI/HTML/DOCX "Key Reuse" section. |
| Hardware crypto-bridge chain | gray, dashed | A hardware device confirmed (via ARP-evidenced topology, never inferred) to bridge a legacy, non-upgradeable backend behind a PQC-capable front end. Dashed styling (not just color) keeps the distinction legible for colorblind users. |
| Shared certificate authority | red, dotted | Two or more endpoints present certificates issued by the same CA. Drawn as a **hub**: one hexagonal CA node with one edge per dependant, never all-pairs. |

The severity palette is used here purely as a **taxonomy** — three distinguishable relationship
kinds. An exposure edge carries no severity and never feeds any score; a red dotted edge is not
"worse" than an amber one, it is a different *kind* of relationship.

#### Why shared-CA matters, and why it is a hub

A CA's signing key is the highest-value quantum target in an estate. Breaking it lets an attacker
**forge a trusted certificate for every dependant** — without touching those endpoints, and
without any victim seeing an invalid certificate. It is a strictly larger blast radius than key
reuse, and in practice a strictly larger cluster: on the reference chaos-lab estate the largest
key-reuse cluster spans 5 endpoints while the largest shared-CA group spans 10.

The hub shape is deliberate. All-pairs over a 10-member group is 45 edges; over a realistic
enterprise CA it is thousands. A hub is one edge per dependant — linear, legible, and a truer
picture of the relationship, which is *one* CA with *many* dependants rather than a mesh of peers.

A further edge type — **operator-declared reachability** (red, solid) — was specified for this tab
but is **not shipped**: it was deferred to a future release, so the map has the three verified edge
types above only, and there is currently no "declared reachability" legend row or red solid edge
anywhere in this tab.

### Crown jewels (v5.25)

Endpoints named in `assessment.crown_jewels` render with an accent-coloured ring. This is an
**operator declaration, never an inference** — no probe can discover which system a client cares
about, so QU.I.R.K. does not guess. An empty declaration marks nothing, and that is the honest
result rather than a nominated "most important" host. CA hub nodes are never marked, whatever is
declared: a crown jewel is a system the client owns, not an issuer identity.
Only endpoints with at least one edge are drawn, so a declared host with no verified
relationship does not appear on the map at all. See `docs/configuration.md` §Assessment Block.

The most useful reading is often what a crown jewel is **not** connected to. A crown jewel with no
key-reuse edge whose only relationship is a shared-CA edge is a healthy host with an exposure that
is not in the host at all; it is in the authority that vouches for it.

### Scan scoping (v5.25)

The map describes **one scan**. Before v5.25 it aggregated every scan in the database, which on a
24-scan database (measured 2026-09-14 on the multihost chaos-lab estate) rendered 1225 edges across 27 nodes — 32% of them an endpoint joined to *itself*,
95% duplicate rows, and including hosts the displayed scan never touched. The same data scoped to
one scan is 19 edges across 12 nodes. Pass `?scan_id=<ISO timestamp>` to pin the map to a specific
scan; omit it for the latest. The dashboard tab never passes it, so it always shows the latest scan.
Hardware crypto-bridge edges are not scan-scoped: they are built from
each device's most recent successful hardware fingerprint, which can come from an earlier scan. A
database whose endpoint rows carry no `scan_run_id` at all is mapped unscoped, across every row.

Note this differs deliberately from the **report** surface's Key Reuse section (§21), which stays
cross-scan by design (D-03): a report asks "has this key ever been seen reused", while the map
draws "the estate as this scan found it".

### Reading the per-edge evidence

Hovering an edge opens an evidence tooltip labeled "Evidence" naming what was matched — e.g. the
first 12 characters of the shared SPKI fingerprint for a key-reuse edge, the issuing CA for a
shared-CA edge, or the bridging device name for a hardware-bridge edge. Graph edges cannot take
keyboard focus; keyboard and screen-reader users get the same evidence from a visually hidden list
of every edge (type, source, target and evidence). Every rendered edge carries this citation: each
of the three edge builders writes a fixed-text evidence string, the API schema rejects an edge with
an empty one, and the page drops any such edge before drawing. The backend test
(`tests/test_exposure_map_edges.py::test_every_exposure_map_edge_has_evidence`) checks this for
key-reuse and hardware-bridge edges.

### The honest-absence empty state

When a scan produces zero verified edges — the common case until a scan surfaces reused key
material or hardware-bridge evidence — the tab does not render an empty, confusing graph canvas.
It shows:

> **No path data available**
> No verified key-reuse clusters or confirmed hardware crypto-bridge chains were found in this
> scan. Nothing is fabricated or inferred here — check back after a scan surfaces reusable keys or
> hardware bridge evidence.

Read this exactly like any other honest-absence state in this product: it is not a failure or a
weaker result than a populated graph, it is a true statement about what this particular scan's
data did and did not prove. One exception: if the map computation fails, the API returns an empty map
with an `unavailable_reason`, and the tab does not read that field, so it shows this same empty state.

### The score firewall — exposure map data never affects the readiness score (MAP-03, D-10)

**Exposure map data is advisory and does not affect the quantum-readiness score.** This sentence
also appears in-product, under the tab's heading (shown whether or not the map has edges), so the guarantee is visible to the consultant
directly — not just enforced silently in code. The guarantee is machine-enforced, not aspirational:
`tests/test_exposure_map_score_guard.py` asserts that no `SCORE_WEIGHTS` key name contains
`exposure_map`, `reachability` or `crown_jewel`, and, by AST inspection, that the exposure-map
module does not import the scoring module at all. A scan with a rich, alarming-looking exposure
graph and a scan with none produce identical readiness scores, all else equal — the map is a
topology-and-evidence surface for a client conversation, not a second scoring input.

## 24. Report Branding Placement (Phase 200, v5.25 — RPT-01)

When an operator sets a `report:` block in `config.yaml` (see
[Configuration Reference](configuration.md#report-block-phase-200-v525--rpt-01rpt-02rpt-03rpt-04)),
branding text and imagery are operator-supplied labels, not scan results — nothing under this
section reflects anything QU.I.R.K. discovered on the network. Knowing where each piece appears
helps a reader distinguish "who prepared this" from "what was found":

| Surface | What appears | Where |
|---|---|---|
| HTML / PDF | Cover logo (if `branding.logo_path` or the legacy `assessment.logo_path` is set) + a cover identity block (client, engagement, prepared-by, cover date, confidentiality line) | Cover page, plus the client/engagement + confidentiality line in the end-of-document footer (colophon), which as of Phase 222 (5.27.0) also prints in PDFs |
| DOCX | Same cover logo (embedded picture, or the existing `"[ Insert organization logo here ]"` placeholder when no logo resolves or python-docx cannot embed it, e.g. an SVG logo that the HTML does show) + the same identity fields as cover paragraphs | Cover page, plus a header/footer identity line and confidentiality line |
| CLI (executive summary markdown, scorecard markdown, Rich console scan-summary table) | Client / engagement / prepared-by / cover-date / confidentiality identity **text only** | Header block of each surface — **no logo is ever rendered on a CLI surface** |

### QU.I.R.K. colophon logo (Phase 222)

This colophon logo first ships in 5.27.0. Separately from the
operator-supplied branding above, every HTML, PDF and DOCX report and the dashboard `/print` export
ends with a fixed product colophon: "Generated by [QU.I.R.K. logo] Quantum Infrastructure Readiness
Kit". The CLI markdown reports carry no colophon.

| Surface | Logo variant | Why |
|---|---|---|
| HTML / PDF | Paper-on-Ink variant (`quirk-logo-dark.svg`, SVG data URI) | The on-disk report ground is dark |
| DOCX | Ink variant (PNG picture at the end of the document) | White page ground |
| Dashboard Export PDF (`/print`) | Ink variant | White page ground |

The colophon logo is a fixed product mark: it is not configurable, adds no config key or API field,
and is never recoloured to a client palette. The client cover logo (`report.branding.logo_path`) and
its precedence are unchanged. Operator template overrides (`report.template_dir`) show the colophon
logo only if they reference `colophon_logo_b64`.

Every field is independently optional — an unset field simply does not render its line/row, on any
surface. If none of the `report.branding.*` fields are set (by the config or by a report profile), no
identity line or row renders on any surface: the branding output is the same as for a config with no
`report:` block at all (a `report.template_dir` override still changes the HTML).

## 25. Finding Storyline Drawer (Phase 202, v5.25 — STORY-01/STORY-02)

### What it is, and where it opens from

The dashboard's findings table has a `Storyline` column. Clicking (or activating by keyboard) the
button in that column opens a drawer in place — the operator never leaves the findings view. The
drawer narrates the finding's quantum-risk story, using the same narrative catalogs the
CLI/HTML/DOCX report uses (`ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG`, introduced in Phase 99), and
shows the finding's score-lift attribution. It is an interactive dashboard affordance only — it is
**not** part of the PDF/DOCX/HTML report, and a reader should not look for it in a deliverable.

### The theme framing — read this before trusting the number

The number shown in the drawer's attribution panel is **the owning remediation theme's total
lift, conditioned on resolving every constituent finding in that theme** — not this finding's own
contribution. The drawer states this explicitly, verbatim:

> +{N} pts when all {N} findings in this theme are resolved
>
> This is the theme's total lift, not this finding's individual contribution. Resolving this
> finding alone does not yield the full amount.

**No per-finding share is shown, because none exists to show.** Score lifts are not linear in the
number of constituent findings a theme has, so dividing the theme's lift by its finding count would
fabricate a number the scoring engine never computed — and the resulting shares would not sum back
to the theme's real total even if you added them all up. This is the same class of problem Phase
201's score-lift math was built to avoid on the roadmap page, applied to the per-finding drawer.

The drawer also shows a closure sentence — `N of N findings in this theme are verified closed` —
counted from the theme's per-finding closure rows for this scan. The remediation roadmap page does
not show this count. It shows the theme's overall closure state as a badge (Open, Closed, Not
verified this scan, or Resurfaced), which is stored separately from the per-finding rows the drawer
counts, so the drawer's number and the roadmap badge are two different readings.

### Why most findings show no narrative — and why that is correct, not broken

The narrative catalogs (`ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG`) are keyed by
**cryptographic-algorithm keyword** — RSA, ECDSA, DH, DSA, hash-algorithm names, and similar —
matched against a finding's title and description (the report's matcher also reads category and
check ID), and only for CRITICAL, HIGH and MEDIUM findings. They were never keyed by
finding title. That means the highest-volume finding classes in a typical scan — plaintext HTTP,
legacy TLS versions, expired or expiring certificates, self-signed certificates, and certificates
issued by an untrusted CA — carry no algorithm keyword and legitimately show:

> No catalog narrative exists for this finding type yet — the Description and Remediation fields
> above are the available guidance.

**This is faithful consistency with the deliverable, not a gap in the drawer.** The client-facing
report has no narrative for those same finding classes either — the report engine's own
`ALGO_IMPACT_MAP` lookup is the identical keyword match. An honest absence in the drawer means the
dashboard and the report are telling the same story for the same finding, which is exactly what
this feature was built to guarantee (Phase 202's D-05 decision: no fourth narrative generator was
ever written to paper over this). Findings at MEDIUM severity or above whose title or description
names a specific algorithm —
undersized RSA keys, and any non-RSA quantum-vulnerable algorithm (ECDSA, DSA, DH) — are the classes
that reliably do carry narrative text.

One report-side exception to "no narrative for those classes": the matcher is a plain substring
test, so the report's `HTTP on TLS-designated port` finding (plaintext HTTP on a TLS port) matches
the `DES` keyword inside the word "designated" and picks up the DES narrative. The report then lists
an "Authentication exposure" risk for it. The dashboard never emits that title, so the drawer is
unaffected.

The attribution panel (theme, lift, closure) is independent of the narrative and always renders in
full even when the narrative is absent — an absent narrative never hides or blanks the attribution.

### The one-theme rule

A finding can, in the underlying data, belong to more than one remediation theme at once. When that
happens, the drawer shows **the specific, title-based theme** and never the `high-impact-findings`
severity catch-all — and it does not mention that a second theme also exists. Showing two
conditioned lift numbers side by side for the same finding would make the non-additivity point above
substantially harder to convey, which is the whole reason the theme framing exists.

**The one exception:** when the `high-impact-findings` severity catch-all is a finding's **only**
matching theme — for example, a TLS certificate using an undersized RSA key, which is HIGH severity
but is not a constituent of any specific title-based theme — the drawer renders that catch-all theme.
Suppressing it in that case would tell the operator the finding maps to no remediation theme at all,
which is false: it demonstrably has one, with a real lift. An operator who reads the one-theme rule
above and then sees a finding attributed to "Triage high-impact findings" should read that as this
exception, not a contradiction.

### What "Not mapped to a remediation theme" means

A distinct message — `Not mapped to a remediation theme — no score-lift attribution exists for this
finding` — appears when no persisted remediation theme claims the finding in this scan at all (for
example, a certificate issued by an untrusted CA, which is MEDIUM severity and outside every theme's
constituency). This is a genuinely different case from the honest-absence narrative message above:
one says "no story text exists for this algorithm class," the other says "no theme owns this finding
at all, so there is no lift number to show."

## 26. Downloading report deliverables from the dashboard (Phase 209, v5.25 — DELIV-01/DELIV-02)

### The five downloadable formats

The Executive page's header row carries a button group — **HTML, PDF, DOCX, CBOM (JSON), CBOM
(XML)** — beside the existing Export PDF button. Each button downloads a file `write_reports()`
already wrote to the server's configured output directory during the scan itself (see "Only the
newest report set is reachable" below for which scans that covers). **There is no second
rendering path.** Clicking a button does not generate anything new; it retrieves a file that has
existed on disk since the scan completed.

| Format | Contents |
|---|---|
| HTML | The full consulting-grade report as one self-contained HTML file. **Executive Summary:** scan coverage, readiness assessment, score and score decomposition, priority business risks, findings breakdown, score drivers, top findings (risks, drivers and top findings are left out when the scan has none). **Transition Roadmap:** NOW / NEXT / LATER items, then the hardware advisory, lifecycle-change, EOL/Tier forecast, vendor-trend, burndown and key-reuse sections when the scan has data for them. **Technical Appendix:** coverage gaps, all findings, compliance summary, endpoint inventory, algorithm inventory (FIPS 140-3 coverage). |
| PDF | The HTML report printed to PDF: headless Chromium (Playwright) loads the HTML file and prints it, so the PDF carries the same sections, except that the Hardware PQC Advisory section is a collapsed block and prints as its heading only (see §10). No PDF is written when Playwright is unavailable. |
| DOCX | A shorter, editable Word report. It is built from the same scan data and the same shared content model as the HTML, but by its own renderer, not by converting the HTML. It has the executive summary, scan coverage, readiness assessment, score decomposition, priority business risks, top findings, the full findings table, the remediation roadmap, a score breakdown, and the same conditional hardware, lifecycle, forecast, vendor-trend, burndown and key-reuse sections. It has **no** findings breakdown, score drivers, coverage-gaps table, compliance summary, endpoint inventory or algorithm inventory. Requires the server to have the `[docx]` optional extra installed; see the unavailable-reasons table below for what happens when it is not. |
| CBOM (JSON) | The CycloneDX Cryptography Bill of Materials, JSON encoding. |
| CBOM (XML) | The same CBOM, XML encoding. |

HTML and PDF are the same report in two formats. The DOCX shares their score, rating, findings and
roadmap, but leaves out the technical-appendix tables listed above. When a client needs the
compliance summary or the endpoint and algorithm inventories, send the HTML or PDF; send the DOCX
when they need a document they can edit.

### "Export PDF" is not the same thing as these downloads

The "Export PDF" button on
the Executive page reads as "export the report," but it does something different: it
Playwright-prints the dashboard's own Executive summary view (the React `/print` page, a short
dashboard summary) to a PDF. It is not the same artifact as the "PDF" button in the new download
group above, which serves the full consulting-grade renderer output that `write_reports()` produces.

Relabelling or replacing the Export PDF button was explicitly out of scope for the phase that added
these downloads. The two buttons now sit side by side on purpose — placing the real report next to the
dashboard-print button makes the labelling gap visible rather than hiding it, and is meant to make
this deferral easy to rediscover and close in a future phase, not something a future reader has to
puzzle out from scratch. If you want the full report, use one of the five new download buttons, not
Export PDF.

### If these two downloads' numbers differ, which one do you trust? (Phase 210 XSURF-01..04, Phase 211 legacy-TLS/plaintext-HTTP fix)

The two artifacts above remain genuinely different documents (previous subsection). A regression
test asserts that, for one seeded fixture scan, the report pipeline (the `evaluate_endpoints()` →
`build_evidence_summary()` → `compute_readiness_score()` chain whose output `write_reports()`
renders) and the
dashboard pipeline (`GET /api/scan/latest`, which feeds the Executive page and the Export PDF
button) agree on three numbers: the **headline readiness score**, the **CRITICAL finding count** and
the **certificate count**. That is a test of one fixture, not a guarantee that the two pipelines can
never diverge on a real estate. Read the scope note below before quoting a number to a client.

**Regression-gated:** `tests/test_cross_surface_parity.py::test_xsurf04_three_number_cross_surface_equality`
asserts those three numbers separately, with a check that the CRITICAL and certificate counts are
non-zero on both sides so that two pipelines that both report nothing cannot pass vacuously. The plaintext-HTTP and legacy-TLS evidence
counts are pinned for both finding vocabularies in `tests/test_evidence_finding_vocabulary_parity.py`.

**What changed to get here.** Two scoring inputs in `quirk/intelligence/evidence.py` were keyed
off finding **titles** or finding **severity labels**, which the report and dashboard pipelines
populate from two independently-maintained vocabularies by deliberate design. `plaintext_http_count`
now matches findings via a title bridge instead of an exact-string comparison across those two
vocabularies. More significantly for anyone comparing scores across scans: the
"Legacy TLS versions present" Modern TLS contributor is **no longer driven by the count of ALL
LOW-severity findings** — a proxy any newly-added LOW-severity finding class could silently
inflate, whether or not it had anything to do with TLS — **but is now derived from which endpoints
actually accept TLS 1.0/1.1** (`legacy_tls_count`). Before this fix the same scan could score
differently on the two pipelines. If you re-run an older scan and its Modern TLS or Hygiene
subscore differs from what was previously reported for the same estate, that is this contributor
change, not a regression.

**What this gate does not claim.** One title-vocabulary gap is known and deliberately left open:
the finding title `"HTTP on TLS-designated port"` has no dashboard emission site at all, so it
cannot be bridged the way the two fixed counts were (the title bridge records it as an
unbridgeable latent divergence). On an estate where a plaintext-HTTP service happens to run on a
TLS-designated port, the dashboard pipeline counts it as ordinary plaintext HTTP, while the report
counts it under the separate "HTTP on TLS-designated ports" Hygiene contributor. The two contributors
weigh differently, so the headline scores diverge, a Hygiene-category divergence identical in shape
to the two closed ones.

**What this means in practice:** the two pipelines' headline scores agree for the fixtures the
regression tests cover. If you ever see the headline score, a subscore, the CRITICAL count, or the
certificate count differ across the two pipelines for the same scan, check the three known causes
first: a report-side `"HTTP on TLS-designated port"` finding; `intelligence.calibration_overrides`
in the scan's config, which the report applies and the dashboard does not; and, when you are viewing
an older scan, a scoring profile that differs from the newest run's, because the dashboard rescores
every scan with the profile from the newest intelligence file. Any other divergence is a defect to
report, not an expected artifact difference.

### Formats can be unavailable, with a reason

Any of the five formats may be shown disabled, with the reason visible in a tooltip. The three
reasons you may see, quoted verbatim from the UI:

- `No scan has run yet.` — the configured output directory holds no report set yet (no
  `run-stats-*.json` and no `report-*.html`). This is the state a fresh install shows; it is not an
  error. A scan started from the dashboard does not clear it: those scans write their reports to
  `output/jobs/<job-id>/`, which these routes do not read.
- `DOCX requires the optional extra: pip install 'quirk-scanner[docx]'` — the server does not have the
  `[docx]` optional extra installed. Every other format is unaffected. Install `'quirk-scanner[docx]'` on the server.
- `This format failed to render for the latest scan. Check server logs.` — the latest scan's
  report set exists, but this format's file is missing from it: it failed to render or was skipped
  (for example, PDF rendering requires Playwright, which can fail independently of everything else).

A disabled button with a reason is never a silent empty control, and a failed download is never
saved as a file: the page checks the response status first and shows a failure message instead.
The manifest that drives this button group always lists all five formats, each either available or
with one of the reasons above; if the server cannot read its config or output directory, every
format shows `No scan has run yet.`

### The scan-time line

Above the button group, a line discloses which scan's artifacts you are about to download:

- `Report from scan: {date}` — the normal case; `{date}` is the scan's run-stats `ended_utc`.
- `Report artifacts found — scan time unknown` — artifacts exist on disk, but the run-stats file
  that would carry the scan's timestamp is itself missing (for example, after an interrupted or
  crashed run). The report is still real and still downloadable; only its recorded timestamp is
  unknown, and that is disclosed rather than invented.
- `No report artifacts yet — run a scan first.` — every format is unavailable, which
  normally means no artifacts exist at all (the same condition as the `No scan has run yet.`
  per-format reason above).

### Only the newest report set is reachable, and why

These downloads always serve the **newest report set** in the configured output directory (the
directory set by `output.directory` in the config file `QUIRK_CONFIG_PATH` names, default
`./config.yaml`): the newest `run-stats-{stamp}.json` group, or the newest `report-{stamp}.html`
when no run-stats file exists. There is no way to download a
report from an older scan through the dashboard: the download routes take a format and nothing
else. The newest set is not always the most recent scan: scans started from the dashboard write to
`output/jobs/<job-id>/`, which these routes never read. The files `write_reports()` writes are named with the moment the report was *rendered*
(`report-{stamp}.html`, etc.), not the scan's own identifier (`scan_run_id`); on a long scan those
two instants can differ by the scan's full duration. The `run-stats-{stamp}.json` file written in
the same set does record the scan's `started_utc`, which is the value stored as `scan_run_id`, but
the report routes do not use it to look up older scans. See `docs/operators-guide.md` for the
endpoint-level documentation of the latest-only behaviour.

### Auth when a token is configured — a plain browser link will fail

These downloads are served by the same auth-gated API as the dashboard's other data routes (only
`/api/health` and `/api/config` are open). When an API token is configured (`QUIRK_API_TOKEN`, or
`security.api_token` in the config file), a Bearer token or `X-API-Key` header is required; with no
token configured, auth is disabled and the routes pass through. The dashboard's own download buttons
already attach the header for you. If a token is configured and you try to fetch a report artifact
yourself with a bare `curl` command or a plain browser navigation to the URL, you will get a `401`
response instead of a file — and a saved
`401` response body looks exactly like a corrupt or truncated download. See
`docs/operators-guide.md` for the correct authenticated `curl` invocation.

---

## 27. Which scanner produced this score (v5.25 — scan summary identity rows)

The CLI scan summary ends with three identity rows. Two of them are new, and they exist to answer
a question the report could not previously answer at all: **which build of the scanner produced
this number?**

```
Platform version   5.21.0
Scoring model      v3.0
Scanner build      a612e60fd3a2
```

When `report.branding` is set, its identity rows (Client, Engagement, Prepared by, Cover date,
Confidentiality) print after these three.

### Why "Platform version" is not enough

`Platform version` is the released package version. It names **the release, not the code that
ran.** `pyproject.toml` does not bump on every change, so a scanner running months of unreleased
commits still prints the version `pyproject.toml` declares, which is normally the last PyPI release.

That gap is not theoretical. On 2026-09-14 a chaos-lab scan reported a confident **91/100**. The
same evidence scores **15/100** under the scoring model that had been on `main` since earlier that
day — the scan was running a container image built before the change. It exited `0`, wrote eleven
report artifacts, and warned about nothing. `Platform version` read `5.21.0` in both the stale and
the current case, so nothing in the output distinguished them; only the magnitude betrayed it, and
only to a reader who already knew both numbers.

### Scoring model

The scoring model version, read live from the scanner's own `SCORING_VERSION` constant.

**This is the row that matters for comparing scores.** Scores from different models are not
comparable. v3 is materially stricter than v2: every reference estate the project re-scored
dropped under it (a 31-host estate went from 87 to 18, and three smaller reference estates from
95 to 78, 91 to 46 and 85 to 24). If you are comparing a scan against an earlier one, compare this row first. If it differs, the
two numbers do not measure the same thing, and a "score improvement" or "regression" between them
is an artifact of the model change rather than a change in your estate.

### Scanner build

The commit the running scanner was built from, resolved in this order:

1. `$QUIRK_BUILD_SHA`, baked in at image build time — preferred inside a container, where a `.git`
   directory (if any) describes the build *context* rather than the installed code.
2. The repository's `.git`, for an editable or development checkout.
3. `unknown`, when neither is found.

**`unknown` is a deliberate, honest answer, not a defect.** A normal `pip install quirk-scanner`
has no commit to report. The value is never substituted with the package version — doing so would
recreate precisely the ambiguity these rows exist to remove.

The `.git` lookup walks up every parent directory of the installed package. A wheel installed into
a virtualenv that sits inside some other git checkout therefore reports that checkout's commit,
not `unknown`.

To make a container image self-identifying, pass the SHA at build time:

```bash
docker compose -p chaoslab --profile multihost build \
  --build-arg QUIRK_BUILD_SHA="$(git rev-parse HEAD)" mh-prober
```

Without the `--build-arg`, the image still builds and scans normally; its summary simply reports
`Scanner build unknown`.

## 28. Certificates Page Expiry Sorting (Phase 213, v5.25 — UIFIX-01)

The Certificates page's Expiry column header is clickable and sorts the certificate inventory table
by expiry date. The first click sorts ascending (soonest-expiring first); a second click reverses to
descending. Certificates with no recorded expiry (a null value) sort to the end of the table in both
directions, so they never displace an expiring certificate from the top of an ascending sort.

The sort key is the parsed expiry `Date`, not the formatted display string. This matters because a
naive string sort on a rendered date (e.g. `"04 Jan 2027"`) orders lexicographically rather than
chronologically, which looks almost correct and is therefore a worse defect than an obviously broken
sort — a certificate expiring in January 2027 could appear to sort before one expiring in 2026. The
column header also exposes `aria-sort` (`none`, then `ascending`, then `descending`) across clicks for
assistive technology.

## 29. Dashboard Colours Follow the Active Theme (Phase 213, v5.25 — UIFIX-02)

Every dashboard page — including the three Cytoscape-rendered graph pages (Roadmap, CBOM's Graph
tab, and the Exposure Map) — now resolves its colours from the active theme's CSS custom properties
rather than from hardcoded hex or HSL literals baked into the page source (with the exceptions
listed below). Toggling the sidebar
theme control re-colours a page immediately, without a reload, including graphs already on screen:
node fills, edge colours, legend swatches, badges and severity-tier colouring all re-resolve to the
newly active theme.

Some fixed colours are the exception and do not change with the theme: the teal advisory
accent and the improved/worsened drift-direction colours on the Hardware and Compare pages, the
sidebar's vertical accent colour, the brand logo's green, white text on solid-colour badges on
several pages (for example CBOM, Findings and the Migration Roadmap), the black backdrop behind
dialogs and side sheets, the QRAMM scorecard's benchmark-radar fill, and the Hardware page's yellow
caveat banner, which uses one fixed yellow pair for light mode and another for dark mode.

**The exported PDF is deliberately theme-independent.** "Export PDF" runs in a fresh, cookie-less
Playwright context that always renders the print surface in its own fixed light palette, regardless
of whether the live dashboard session that triggered the export was in light or dark mode. A PDF
exported from a dark-theme session and one exported from a light-theme session are equivalent — this
is intentional, not a bug: the printed deliverable is a client-facing artifact and is not expected to
carry the operator's personal theme preference.

## 30. Keyboard Access to Table Regions (Phase 219, 5.27.0 — KBD-01)

Every table on the dashboard that is too wide or too tall for the space it renders in now becomes a
single stop in the page's Tab order. Tab to it, and the arrow keys — ArrowLeft, ArrowRight, ArrowUp,
ArrowDown, PageUp, PageDown, Home, End (where the browser's native handling applies them to the
table's overflow axis) — scroll it in place, the same way a mouse wheel or scrollbar drag would. A
visible focus ring appears around the table region when it receives keyboard focus; it does not
appear when the same region is clicked with a mouse, so sighted keyboard users get an unambiguous
cue without a ring appearing on every mouse interaction.

A table that already fits its space adds no Tab stop at all, and no screen-reader region — there is
nothing to scroll, so there is nothing to announce. A table that does overflow is exposed to a screen
reader as a named region. On the pages built from several tables side by side (CBOM Viewer,
Compare, Data at Rest and Motion; for example Data at Rest's database,
object storage, Kubernetes secrets and vault panels, or Compare's several findings-and-subscore
tables) each region carries its own distinct name, such as "Database encryption findings" or
"Endpoints only in scan B," so a screen-reader user can tell which table they have landed on without
reading its contents first. Every other table uses the generic name "Scrollable table," including
the per-scan coverage tables that rows on the Scan History page expand.

The accepted accessibility exception that previously covered this gap (`scrollable-region-focusable`
in `src/dashboard/tests/a11y/ACCEPTED-VIOLATIONS.md`) was **withdrawn** in Phase 219, not renewed —
the underlying behavior is now fixed at the source, in the shared `Table` component, rather than
accepted as ongoing debt.

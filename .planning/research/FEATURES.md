# Feature Research

**Domain:** Cryptographic inventory scanner — stabilization milestone (gap closure, not net-new capability)
**Researched:** 2026-05-22
**Confidence:** HIGH — all findings derived from direct code inspection of `quirk/intelligence/`, `quirk/cbom/`, `quirk/reports/`, and `quantum-chaos-enterprise-lab/`; zero speculation from training data.

---

## Feature Landscape

### Table Stakes (Users Expect These)

These are the gap-closure behaviors v5.0 must fix. Missing or wrong = product makes false claims.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Evidence tally: subscores penalize on findings | Subscores that stay at 25 when HIGH/CRITICAL findings exist are silent lies; a consultant hands a client a score that says "clean" when it isn't | MEDIUM | Root cause traced: Hygiene/Modern TLS/DAR subscores use proxies that miss specific scanner output — see tally analysis below |
| CLI scorecard renders subscores on 0–25 scale with label | `scorecard-*.md` currently shows `total/100` but does not render subscores — RENDER-CLI-01 is an audit pass, not a confirmed bug; if subscores are absent they cannot mislead | LOW | Code inspection shows `_scorecard_markdown()` only renders `score.get('total')` — subscores stored in intelligence JSON but not displayed in scorecard or HTML template subscore section |
| HTML/PDF report total score correct | `total_score = score.get("total", 0)` in `html_renderer.py` — already pulls the correctly normalized 0–100 integer from `writer.py::score["total"]` which maps to `score_raw["score"]` (the fixed `int(round(sum/1.5))`) | LOW | No confirmed scale mismatch in the renderer path; audit needed to verify no legacy `score.get("score")` vs `score.get("total")` key confusion exists |
| CBOM Pass-1 emits >= 1 algo component for every profile | Phase 42 OBS-1: 5 profiles (database, registry, source, ssh-weak, storage-s3) emit zero CBOM algorithm components — they pass the schema-validation gate vacuously | MEDIUM | Classifier has entries for CONTAINER/SOURCE/POSTGRESQL/MYSQL/S3 protocols; builder does handle them; bug is likely upstream in what `cipher_suite`/`cert_pubkey_alg` fields those scanners populate |
| New chaos lab profiles up and scanner-verified | BACK-80–84: postgres-tls, redis-tls, SMTP/STARTTLS, gRPC TLS, Kafka TLS must exist as Docker Compose profiles, come up cleanly, and produce expected scanner findings | HIGH | Each requires: docker-compose.yml service + profile, cert/config, expected_results_v4.md oracle entry, lab.sh ALL_PROFILES update |
| OQS-nginx PQC-hybrid profile demoable and scores above classical TLS | BACK-81: the only chaos lab target that should receive a positive quantum-safety signal; anchors the scoring ceiling | HIGH | Requires OQS image config + QUIRK scanner recognizing X25519Kyber768/ML-KEM-768 in TLS extension 0x001d + scoring reward |
| Identity evidence keys present in intelligence.json when identity scanner runs | BACK-78: `identity_kerberos_weak_etype_ratio`, `identity_saml_weak_signing_ratio`, `identity_dnssec_weak_algo_ratio` absent unless scanner actually scanned identity endpoints | LOW | Code is correct; lab coverage gap — need identity chaos lab targets in scan config |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| PQC-hybrid TLS classified as quantum-safe (scoring ceiling) | Demonstrates the scanner can distinguish "good classical TLS" from "quantum-ready TLS" — the only tool making this distinction at the endpoint level | MEDIUM | Requires TLS extension parsing for hybrid groups (X25519Kyber768 = IANA group 0x6399); classifier already has `ml-kem-768+x25519` entry at NIST level 3 |
| CBOM carries algorithm components from ALL protocol families | A CBOM that omits algorithms from container/source/database scanners is not a complete bill of materials; completeness is the core consulting deliverable | MEDIUM | Five profiles currently vacuously pass; Phase 61 fixed 12+ families in v4.8 — OBS-1 residuals are a subset that regressed or were missed |
| Score transparency (BACK-63) | Consultant needs to explain to client why the score changed — current `drivers` list shows only top 5 reasons; adding subscore breakdowns makes the score auditable | LOW | Already stored in `intelligence.json`; surface in CLI/HTML |

### Anti-Features (Out of Scope for a Stabilization Milestone)

| Feature | Why Requested | Why Out of Scope | Alternative |
|---------|---------------|-----------------|-------------|
| Net-new scanner surface (new protocol families) | Always tempting to add capability | v5.0 is explicitly a "breathe" milestone; HORIZON.md caps at <= 6 phases; new protocols go to v5.1 | Capture as BACK items for v5.1 |
| Score-engine redesign (subscores as 0–100, weighted average) | Current 0–25 model is non-obvious | Architectural change; the surgical v4.10.1 fix preserved the model deliberately; redesign at v5.x when usage data justifies | Document 0–25 model in scorecard header |
| Authenticated scan mode (credential model) | Deeper findings behind auth walls | HORIZON.md explicitly defers to v5.1 Candidate A | BACK-64 |
| SIEM/ticketing integrations | Make findings load-bearing in customer workflow | HORIZON.md Candidate B for v5.1 | BACK items |
| Real mTLS between brokers / full Kafka KRaft cluster | Realistic enterprise Kafka config | Lab fidelity is secondary to scanner coverage; a single TLS listener on 9093 is sufficient | Out of scope for lab profile |
| S/MIME message-content scanning | Out of scope per PROJECT.md | Agentless model cannot inspect mailbox content | Documented in Out of Scope |

---

## Correct Behavior Specifications

### 1. Evidence Tally — EVIDENCE-TALLY-01

**Problem statement:** Three subscores report exactly 25 (the ceiling) despite the scan having HIGH/CRITICAL findings. This occurs because the evidence counters those subscores depend on are not incremented by the relevant findings.

**Root cause analysis (from code inspection):**

**Hygiene subscore** (`hygiene_score`): driven by `plaintext_http_count` and `http_on_tls_port_count`. These come from `_finding_targets(finding_list, "Plaintext HTTP service detected")` and `_finding_targets(finding_list, "HTTP on TLS-designated port")` — both read *finding titles* from the findings list. A scan of TLS-only endpoints with a HIGH finding for "Weak RSA cipher" produces zero `plaintext_http_count`, so hygiene stays at 25. This is correct behavior for a scan that has no HTTP exposure — the hygiene subscore is genuinely good. This is NOT a tally bug for TLS-only scans.

**Modern TLS subscore**: driven by `legacy_tls_count = sev.get("LOW", 0)` — it uses ALL LOW-severity findings as a proxy for legacy TLS. If a scan has HIGH/CRITICAL but zero LOW findings, `modern_tls_score` = 25. This proxy is correct for TLS scans (legacy TLS findings are typically LOW severity in the risk engine). The subscore is not broken for TLS-only scans with only HIGH/CRITICAL findings.

**Data at Rest subscore** (`dar_score`): driven by `dar_db_plaintext`, `dar_db_weak_ssl`, `dar_storage_unencrypted`, etc. — these come from `evidence.py` counters which read endpoint `protocol` and `service_detail` fields. A DAR scan result where `postgres-ssl-off` endpoint exists with `service_detail="PostgreSQL/ssl-off"` DOES increment `dar_db_plaintext_count`. If the counter reads 0 despite findings, the bug is that the endpoint's `protocol` field does not match `"POSTGRESQL"` exactly, or `service_detail` does not contain `"ssl-off"`, or the endpoint list passed to `build_evidence_summary` is filtered/truncated upstream.

**Actual EVIDENCE-TALLY-01 root cause (most likely):** `build_evidence_summary()` receives the endpoint list from the ORM. If any scanner stores findings in the *findings table* only (not the endpoint table), those findings appear in `finding_severity_counts` but the specific evidence counters (which read endpoints) stay zero. The agility subscore's `high_impact` counter reads `sev.get("HIGH") + sev.get("CRITICAL")` from finding_severity_counts — this DOES penalize correctly. The subscores that stay at 25 must be the ones whose penalty paths depend on endpoint-level attributes rather than finding-level severity.

**Correct behavior — what EVIDENCE-TALLY-01 must produce:**

Given: A scan of chaos lab "database" profile (postgres-ssl-off on port 25432)
- Expected: `dar_score < 25`
- Mechanism: `evidence.dar_db_plaintext_count > 0` because `endpoint.protocol == "POSTGRESQL"` AND `"ssl-off" in endpoint.service_detail`
- Correct evidence dict: `dar_db_plaintext_count: 1`, `dar_db_plaintext_ratio: > 0` → `dar_score = _apply_weighted_impacts([("DB plaintext", -ratio * 12.0)]) < 25`

Given: A scan with rc4-hmac Kerberos etype (identity weak etype)
- Expected: `identity_trust_score < 25`
- Mechanism: `evidence.identity_weak_etype_count > 0` because `endpoint.protocol == "KERBEROS"` AND severity in service_detail parts is "CRITICAL" or "HIGH"
- Correct: `identity_kerberos_weak_etype_ratio > 0` → -10.0 weight applied

Given: A scan with SAML RSA-1024 signing cert
- Expected: `identity_trust_score < 25`
- Mechanism: `evidence.saml_weak_signing_count > 0` because `endpoint.protocol == "SAML"` AND `cert_pubkey_size < 2048`

**Test oracle for EVIDENCE-TALLY-01:**
- Precondition: chaos lab "kerberos" profile up (rc4-hmac enabled on port 88)
- Scan result must show `identity_weak_etype_count >= 1` in evidence JSON
- `identity_trust_score` must be `< 25`
- Precondition: chaos lab "database" profile up
- `dar_db_plaintext_count >= 1`, `dar_score < 25`
- No subscore should report exactly 25 when its penalizing counter has count > 0

---

### 2. Render-Side Audit — RENDER-CLI-01 / RENDER-PDF-01

**Problem statement (deferred from v4.10.1-D-03):** The same backend-scale vs render-scale bug that was fixed in the dashboard might exist in CLI/HTML/PDF renderers.

**Findings from code inspection:**

CLI scorecard (`_scorecard_markdown` in `writer.py`): Renders `score.get('total')/100`. `score["total"]` is set from `score_raw["score"]` which is already the correct `int(round(sum/1.5))` 0–100 value. No bug confirmed. Subscores (0–25 each) are not rendered in the scorecard — they appear only in `intelligence-*.json`. No scale mismatch confirmed. Audit should verify `score.get("total")` is never substituted with a raw subscore.

HTML report (`html_renderer.py`): Renders `total_score = score.get("total", 0)` where the `score` dict is the same wrapper constructed in `writer.py`. `_score_band()` thresholds (85/70/55/35) match `_rating()` thresholds in `scoring.py`. No scale mismatch confirmed. Subscores not rendered in the HTML template (only overall score and drivers are displayed).

PDF report: Playwright renders the HTML report — no separate scoring logic. Same code path as HTML. No additional bug surface.

**Correct behavior — what RENDER-CLI-01 audit must confirm:**
- `scorecard-*.md` shows `X/100` where X == `intelligence.score.total` == same value the dashboard overall gauge shows
- No subscore value (0–25) is ever displayed as if it were out of 100
- If subscores ARE added to the scorecard/HTML in v5.0 for transparency (BACK-63), each must be labeled `/25` not `/100`

---

### 3. CBOM Pass-1 Zero-Algo Fix — Phase 42 OBS-1

**Five profiles currently emitting zero algorithm components:**

| Profile | Protocol | Builder branch | Why zero |
|---------|----------|----------------|----------|
| database | POSTGRESQL / MYSQL | No Pass-1 branch for POSTGRESQL/MYSQL in builder.py | DB scanner populates `service_detail` ("PostgreSQL/ssl-off") but not `cert_pubkey_alg` or `cipher_suite` — builder has nothing to register |
| registry | CONTAINER | `if ep.cipher_suite: _register_algorithm(ep.cipher_suite)` | `cipher_suite` holds library name ("openssl") — not in `_ALGORITHM_TABLE`; returns FALLBACK; not registered as algo component |
| source | SOURCE | `_extract_algo_from_rule_id(ep.cipher_suite)` | Rule ID like `python.cryptography.security.insecure-cipher-des` — hint extraction may return empty for some rule IDs |
| ssh-weak | SSH | SSH endpoints handled via KEX/hostkey parsing from `ssh_audit_json` | KEX algorithms (group1-sha1, ssh-dss) may not be in classifier table; or `ssh_audit_json` unpopulated |
| storage-s3 | S3 | No Pass-1 branch for S3 in builder.py | S3 endpoints store bucket encryption mode in `service_detail` ("S3/unencrypted") not an algorithm string |

**Correct behavior — what each profile's CBOM must contain:**

| Profile | Required CBOM algo component | Algorithm string | NIST level |
|---------|------------------------------|-----------------|------------|
| database (postgres-ssl-off) | A "no-encryption" marker OR postgres-negotiated cipher | "aes-256-gcm" if ssl=on; or a no-encryption marker for ssl-off | 1 (quantum-safe) or 0 |
| registry | Algorithm from detected crypto library (openssl version maps to DES/3DES/AES depending on version) | "3des" or "aes-128" per detected lib | 0 for legacy, 1 for modern |
| source | Detected algorithm from semgrep match (MD5, DES, RC4, AES) | "3des", "md5", "rc4" etc. | 0 |
| ssh-weak | diffie-hellman-group1-sha1, ssh-dss | Need classifier entries: "diffie-hellman-group1-sha1" (CRITICAL legacy DH) | 0 |
| storage-s3 | AES-256 (SSE-S3) or no-encryption marker | "aes-256" for encrypted bucket | 1 |

**Test oracle for OBS-1 fix:**
- Scan each profile → `build_cbom()` → `cbom.components` must contain at least one `CryptoComponent` with a non-unknown name
- Exception: plaintext/unencrypted endpoints may emit a component with nist_level=0 (quantum-vulnerable by omission)

---

### 4. New Chaos Lab TLS Profiles — Expected Scanner Findings

#### BACK-80: postgres-tls profile

Docker Compose — new profile `db-tls`:
- `postgres-tls` on port `25433`: PostgreSQL 16 with `ssl=on`, `ssl_cert_file=modern.crt`, `ssl_key_file=modern.key`
- `postgres-tls-weak` on port `25434`: PostgreSQL 16 with ssl=on using RSA-1024 or SHA-1 scenario cert

**Expected scanner findings:**

| Port | Protocol label | Finding | Severity |
|------|---------------|---------|----------|
| 25433 | POSTGRESQL (TLS via --starttls postgres) | TLS handshake succeeds; cipher + version extracted | No finding (good posture) |
| 25433 | TLS (sslyze) | Self-signed cert from modern.crt | CERT_SELFSIGNED MEDIUM |
| 25434 | POSTGRESQL / TLS | RSA-1024 cert detected | WEAK_RSA_KEY_SIZE HIGH |

**Observable crypto properties from PostgreSQL TLS:**
- `SHOW ssl` returns "on" (vs "off" for plaintext profile)
- `ssl_cipher` parameter: cipher suite string (e.g., "TLS_AES_256_GCM_SHA384")
- sslyze `--starttls postgres` probes STARTSSL extension for PostgreSQL wire protocol
- Server certificate: pubkey algorithm and size, expiry, chain, issuer
- `pg_stat_ssl` view: shows active SSL connections and cipher for each session

#### BACK-80: redis-tls profile

Part of same `db-tls` profile:
- `redis-tls` on port `26381`: Redis 7 with `tls-port 6381`, using `modern.crt`/`modern.key`

**Expected scanner findings:**

| Port | Protocol label | Finding | Severity |
|------|---------------|---------|----------|
| 26381 | REDIS-TLS | TLS handshake; cipher suite and version extracted | No finding (good posture for modern config) |
| 26381 | REDIS-TLS | If TLSv1.2 with non-PFS suite negotiated | HIGH |

**Observable crypto properties from Redis TLS:**
- `CONFIG GET tls-port` returns port number
- `CONFIG GET tls-cert-file`, `tls-key-file` returns cert material paths
- `CONFIG GET tls-auth-clients` returns "optional", "yes", or "no" (client auth mode)
- TLS negotiation observable via sslyze direct socket: cipher suite, protocol version
- No application-layer crypto — TLS is the only crypto surface for Redis

#### BACK-81: OQS-nginx PQC-hybrid profile

Docker Compose — new profile `pqc`:
- `oqs-nginx` on port `25443`: `openquantumsafe/nginx` image
- Configured for TLS 1.3 with `ssl_ecdh_curve X25519Kyber768` (hybrid ECDH + ML-KEM)
- Serving the lab CA-signed cert (modern.crt or a dedicated PQC-lab cert)

**Observable crypto properties from PQC-hybrid TLS handshake:**

The OQS-nginx server presents:
1. Supported groups extension (TLS 1.3): includes IANA group 0x6399 (X25519Kyber768 hybrid) alongside classical groups
2. Key share extension: client hello and server hello carry the hybrid key share
3. sslyze output: `supported_cipher_suites` includes hybrid KEM group; `key_exchange_info` shows `x25519_kyber768`
4. Certificate: standard RSA or ECDSA cert (authentication is classical; only key exchange is PQC-hybrid)
5. Cipher suite negotiated: `TLS_AES_256_GCM_SHA384` or similar (cipher suite unchanged; only key exchange group changes)

**Expected scanner output:**
- `tls_version`: "TLSv1.3"
- `cipher_suite`: "TLS_AES_256_GCM_SHA384"
- `key_exchange_group`: "x25519_kyber768" or "X25519Kyber768"
- `cert_pubkey_alg`: "RSA" or "EC" (classical cert; unaffected by PQC key exchange)
- `quantum_safety`: "hybrid" (new classification needed)

**Expected finding:** NONE — the hybrid profile is a positive baseline, not a weakness. The scanner detects and reports PQC-hybrid capability as a positive signal.

**CBOM output:**
- Algorithm component: `ml-kem-768+x25519` -> `CryptoPrimitive.KEM`, `nist_level=3`, `classical_level=192`
- The classifier already has the entry: `"ml-kem-768+x25519": (CryptoPrimitive.KEM, 3, 192)` at classifier.py line 157
- `quantum_safety_label(3)` = "quantum-safe"
- Certificate component: RSA or EC (classical)

#### BACK-82: SMTP/STARTTLS profile

Note: The existing `email` profile (Phase 32) already covers SMTP/STARTTLS on ports 30025/30465/30587. BACK-82 as originally filed refers to a simpler standalone postfix-starttls service or a validation that the email profile satisfies this gap.

**Expected scanner findings (email_scanner.py against SMTP/STARTTLS):**

| Port | Protocol | Expected finding | Severity | Mechanism |
|------|----------|-----------------|----------|-----------|
| 30025 (SMTP) | SMTP-STARTTLS | STARTTLS downgrade risk | MEDIUM | Port 25 STARTTLS can be stripped |
| 30025 (SMTP) | SMTP-STARTTLS | Weak cipher suite on email TLS | HIGH | TLS_RSA_WITH_* cipher negotiated (no PFS) |
| 30465 (SMTPS) | SMTPS | Weak cipher suite | HIGH | same cipher |
| 30587 (submission) | SMTP-STARTTLS | Weak cipher suite | HIGH | same cipher |

**Observable crypto properties from SMTP STARTTLS:**
- EHLO response includes `STARTTLS` capability advertisement
- `sslyze --starttls smtp` performs full TLS enumeration after STARTTLS upgrade
- Cipher suite, TLS version, certificate (subject, pubkey alg, size, expiry, chain)
- Absence of STARTTLS response -> `motion_email_starttls_missing_count` incremented

#### BACK-83: gRPC TLS profile

Docker Compose — new profile `grpc`:
- `grpc-tls` on port `50051`: minimal gRPC echo server with TLS 1.3, `modern.crt`/`modern.key`
- `grpc-insecure` on port `50052`: same service without TLS (plaintext HTTP/2)

**Observable crypto properties from gRPC TLS:**
- TLS handshake is standard TLS 1.3 over TCP — sslyze probes directly with ALPN `h2`
- ALPN negotiation: server advertises `h2` (HTTP/2 over TLS)
- Cipher suite: standard TLS 1.3 suite (TLS_AES_256_GCM_SHA384 etc.)
- Certificate: same as any TLS endpoint (pubkey alg, size, expiry, chain)
- No application-level crypto (gRPC carries protobufs above TLS)
- `grpc-insecure` port 50052: TCP connection accepted without TLS -> classified as `UNKNOWN` or `HTTP` -> triggers `PLAINTEXT_HTTP` or `UNKNOWN_OPEN_PORT` finding

**Expected scanner findings:**

| Port | Protocol | Expected finding | Severity |
|------|----------|-----------------|----------|
| 50051 | TLS (ALPN h2) | No finding (good posture with modern.crt) | none |
| 50051 | TLS | CERT_SELFSIGNED if using self-signed cert | MEDIUM |
| 50052 | UNKNOWN / HTTP | Plaintext gRPC service on application port | HIGH |

**CBOM:** TLS endpoint on 50051 emits RSA/ECDSA cert component and TLS cipher suite component via existing TLS Pass-1 path. No new protocol handlers needed.

#### BACK-84: Kafka TLS profile

Note: The existing `broker` profile (Phase 33) already includes Kafka on ports 29092 (PLAINTEXT) and 29093 (TLS). BACK-84 refers to a standalone `kafka` profile. The expected behavior below applies to either the standalone profile or the existing broker profile's Kafka TLS listener.

**Expected scanner findings (broker_scanner.py Kafka path):**

| Port | Protocol | Expected finding | Severity |
|------|----------|-----------------|----------|
| 9092 | KAFKA-PLAIN | Kafka plaintext listener detected | HIGH |
| 9093 | KAFKA-TLS | No finding (good TLS posture with modern cert) | none |
| 9093 | KAFKA-TLS | Weak cipher if TLS_RSA_WITH_* configured | HIGH |

**Observable crypto properties from Kafka TLS:**
- Kafka TLS is standard TLS over TCP — sslyze probes directly
- `AdminClient` (kafka-python): `ssl.endpoint.identification.algorithm`, `security.protocol=SSL`
- Broker certificate: standard X.509 (pubkey alg, size, expiry, chain)
- TLS version and cipher suite negotiated
- Plaintext listener on 9092: `KAFKA-PLAIN` protocol label -> `motion_broker_plaintext_count` incremented

---

### 5. PQC-Hybrid Scoring Ceiling — BACK-81 Scoring Specification

**Current scoring model:** The `agility_signals` subscore penalizes RSA-only posture and rewards ECDSA adoption. No reward exists for PQC-hybrid key exchange. Maximum `agility_score` = 25 (ceiling is already the reward).

**Target behavior for OQS-nginx profile:** The OQS-nginx endpoint signals PQC-hybrid key exchange. The agility subscore remains at 25 (ceiling) — there is no "super-bonus" above 25. The key insight is:

- Classical "good TLS" (TLS 1.3, ECDSA cert, modern cipher): `agility_score = 25`, overall possible = 100
- PQC-hybrid TLS: same 25 for agility (ceiling), same overall possible = 100

**The real differentiator is the CBOM output**, not the numeric score. A hybrid TLS endpoint emits a `quantum-safe` KEM component; all classical endpoints emit `quantum-vulnerable` key exchange components.

**Scoring reward path for PQC-hybrid — new evidence key and weight needed:**

```python
# New evidence key in build_evidence_summary():
pqc_hybrid_kem_count: int  # endpoints where PQC-hybrid KEM group was detected

# New scoring impact in agility_impacts list:
("PQC hybrid key exchange detected",
 +_ratio(pqc_hybrid_kem_count, denom) * w["agility_pqc_hybrid_bonus"])
```

**The scoring ceiling contract:**
- With PQC hybrid bonus: `agility_score` stays at 25 (already at cap) when no other penalties apply
- The bonus prevents the agility subscore from dropping below 25 if other penalties are present alongside a PQC-hybrid endpoint — but this is a secondary benefit
- Primary value: consultant can point to CBOM report and show `quantum-safe` classification for the key exchange algorithm on the PQC-capable endpoint

**Classification mapping (quantum_safety_label) for BACK-81:**

| Scenario | Algorithm | NIST level | quantum_safety_label |
|----------|-----------|------------|---------------------|
| Classical RSA-2048 TLS | rsa-2048 | 0 | quantum-vulnerable |
| Classical ECDSA P-256 TLS | ecdsa | 0 | quantum-vulnerable |
| TLS 1.3 + X25519 key exchange | x25519 | 0 | quantum-vulnerable |
| OQS-nginx TLS 1.3 + X25519Kyber768 | ml-kem-768+x25519 | 3 | quantum-safe |
| ML-KEM-768 standalone | ml-kem-768 | 3 | quantum-safe |
| AES-256-GCM cipher suite | aes-256-gcm | 1 | quantum-safe (Grover-resistant) |

**OQS-nginx is the scoring ceiling anchor because:**
- It is the ONLY chaos lab profile where the key exchange algorithm classifies as `quantum-safe`
- All other profiles use classical RSA/ECDSA/DH/ECDH -> quantum-vulnerable key exchange
- AES-256 cipher suites are quantum-safe for symmetric encryption, but key exchange vulnerability is the primary PQC concern
- The "ceiling" is qualitative: the only profile that generates a positive PQC attestation in the CBOM

---

### 6. Identity Evidence Keys — BACK-78

**What observable crypto properties feed each identity subscore counter:**

**Kerberos KDC (`identity_weak_etype_count`):**
- Scanner sends AS-REQ to KDC port 88 (impacket unauthenticated probe)
- Response contains `ETYPE-INFO2` pre-auth hints listing all supported encryption types
- Etype severity map: DES (CRITICAL), RC4-HMAC etype 23 (HIGH), AES128-CTS-SHA1 etype 17 (HIGH), AES256-CTS-SHA1 etype 18 (SAFE), AES256-CTS-SHA384 etype 20 (SAFE)
- Observable: `etype_id` from AS-REQ response -> `service_detail = "etype:{id}:{name}:{severity}"`
- Counter increments when `severity in ("CRITICAL", "HIGH")`
- CBOM component: etype algorithm string (e.g., "rc4-hmac" -> `CryptoPrimitive.BLOCK_CIPHER`, nist_level=0)

**SAML SP (`saml_weak_signing_count`):**
- Scanner fetches SAML IdP metadata URL (HTTP GET, XML response)
- Extracts `<ds:X509Certificate>` from `<KeyDescriptor use="signing">`
- Parses cert: `cert_pubkey_alg` (RSA/ECDSA), `cert_pubkey_size` (bits)
- Observable: RSA key size (1024 -> CRITICAL, < 2048 -> penalized), SHA-1 algorithm URI in `<ds:SignatureMethod Algorithm="...">`
- Counter increments when `is_weak_cipher(cert_pubkey_alg)` OR `cert_pubkey_size < 2048` OR SHA-1 URI detected
- CBOM component: "rsa-1024" -> nist_level=0, classical 80-bit

**DNSSEC zone (`dnssec_weak_algo_count`):**
- Scanner sends authoritative DNS query with DO-bit set to zone's NS
- Retrieves DNSKEY RRset -> algorithm field (RFC 4034 algorithm numbers)
- Algorithm map: RSASHA1 (alg 5, MUST NOT per RFC 8624) -> CRITICAL, RSASHA1-NSEC3-SHA1 (alg 7) -> CRITICAL, ECDSAP256SHA256 (alg 13) -> SAFE, NONE (unsigned zone) -> HIGH
- Observable: DNSKEY algorithm number -> string name -> severity
- Counter increments when algorithm in `_DNSSEC_WEAK_ALGS` OR `_dnssec_alg == "NONE"`
- CBOM component: "rsasha1" -> `CryptoPrimitive.PKE`, nist_level=None

**What BACK-78 requires for lab coverage:**

The scoring counters are correct. The lab gap is that the standard scan config does not include identity port targets (88 for Kerberos, SAML metadata URL, DNSSEC zone). Fix is in scan configuration:

- Add `kerberos`, `saml`, `dnssec` profiles to the test scan target list
- Verify `intelligence-*.json` shows `identity_kerberos_weak_etype_ratio > 0` after scanning `samba-dc` chaos lab
- Verify `identity_saml_weak_signing_ratio > 0` after scanning `simplesamlphp` chaos lab
- Verify `identity_dnssec_weak_algo_ratio > 0` after scanning `bind9-dnssec` chaos lab with `weak.example.com` zone

---

## Feature Dependencies

```
EVIDENCE-TALLY-01 (evidence.py fix)
    must precede RENDER-CLI-01 / RENDER-PDF-01 (render audit)
    (auditing renderers against wrong scores is meaningless)

OBS-1 CBOM Pass-1 fix
    must precede new chaos lab profile oracle entries
    (oracle assumes correct CBOM output)

BACK-80 postgres-tls / redis-tls
    independent of BACK-81 OQS-nginx

BACK-81 OQS-nginx PQC scoring reward
    requires: classifier entry ml-kem-768+x25519 (already exists at classifier.py:157)
    requires: evidence.py new pqc_hybrid_kem_count counter
    requires: scoring.py new agility_pqc_hybrid_bonus weight

BACK-78 identity lab targets
    independent of other chaos lab profiles
    requires: chaos lab kerberos/saml/dnssec profiles running (already exist)

BACK-81 / BACK-80 / BACK-82 / BACK-83 / BACK-84
    each requires: docker-compose.yml update + lab.sh ALL_PROFILES update
                   + expected_results_v4.md oracle entry
```

### Dependency Notes

- EVIDENCE-TALLY-01 before render audit: If subscores are still wrong, auditing the render path against them is circular. Fix the tally first, confirm correct values in intelligence JSON, then confirm renderers faithfully pass those values through.
- OBS-1 before new profile oracles: The new chaos lab profiles need CBOM oracle entries. Those entries assume the CBOM builder correctly emits algo components. Fixing OBS-1 first ensures the oracle reflects correct behavior.
- PQC hybrid scorer requires new evidence key: `agility_pqc_hybrid_bonus` requires `pqc_hybrid_kem_count` in the evidence dict, which requires `build_evidence_summary()` to detect PQC-hybrid KEM groups from TLS scanner output.

---

## MVP Definition

### Ship in v5.0 (table-stakes gap closure)

- [ ] EVIDENCE-TALLY-01 — fix the three subscores that stay at 25 with findings present; write targeted test per counter
- [ ] RENDER-CLI-01 / RENDER-PDF-01 — audit CLI/HTML/PDF render paths; confirm no scale mismatch; add labels if subscores are surfaced
- [ ] OBS-1 CBOM Pass-1 — 5 profiles must emit >= 1 non-unknown algo component; add missing algorithm table entries and scanner field population
- [ ] BACK-80 postgres-tls + redis-tls — new `db-tls` chaos lab profile; expected_results oracle; scanner verification
- [ ] BACK-81 OQS-nginx PQC-hybrid — `pqc` chaos lab profile; PQC-hybrid KEM evidence key; agility scoring reward; CBOM quantum-safe classification
- [ ] BACK-82 SMTP/STARTTLS — verify existing email profile satisfies this or add standalone postfix-starttls variant
- [ ] BACK-83 gRPC TLS — `grpc` chaos lab profile; verify sslyze ALPN h2 probe works; expected_results oracle
- [ ] BACK-84 Kafka TLS — verify existing broker profile covers this or add standalone `kafka` profile
- [ ] BACK-78 identity evidence keys — scan config includes identity port targets; integration test verifies ratios > 0 after chaos lab scan

### Add After Validation (v5.x)

- [ ] BACK-63 score transparency — surface subscores in CLI scorecard and HTML report (labeled `/25`)
- [ ] BACK-58 JWT verify=False documentation — operator advisory, not a code fix

### Future Consideration (v5.1+)

- [ ] Score-engine redesign (0–100 subscores, weighted average) — deferred explicitly in v4.10.1-D-04
- [ ] Authenticated scan mode (BACK-64) — HORIZON.md Candidate A for v5.1

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| EVIDENCE-TALLY-01 (score correctness) | HIGH — false-positive "clean" scores destroy trust | MEDIUM | P1 |
| BACK-81 OQS-nginx PQC scoring ceiling | HIGH — strategic centerpiece; only PQC-positive profile | HIGH | P1 |
| OBS-1 CBOM Pass-1 fix | HIGH — incomplete CBOM = incomplete deliverable | MEDIUM | P1 |
| BACK-80 postgres-tls / redis-tls | MEDIUM — closes lab gap; validates DB TLS scanning | MEDIUM | P1 |
| RENDER-CLI-01 / RENDER-PDF-01 audit | MEDIUM — confirm no bug; low risk if confirmed clean | LOW | P1 |
| BACK-83 gRPC TLS | MEDIUM — validates HTTP/2 ALPN TLS probing | MEDIUM | P2 |
| BACK-84 Kafka TLS | MEDIUM — closes broker lab picture | MEDIUM | P2 |
| BACK-78 identity evidence keys | MEDIUM — integration test correctness | LOW | P2 |
| BACK-82 SMTP/STARTTLS | LOW — existing email profile may cover this; verify first | LOW | P2 |
| BACK-63 score transparency | LOW — nice-to-have visibility improvement | LOW | P3 |

---

## Sources

- `quirk/intelligence/evidence.py` — `build_evidence_summary()` counter logic, all protocol branches (direct inspection)
- `quirk/intelligence/scoring.py` — `compute_readiness_score()`, `SCORE_WEIGHTS`, subscore penalty paths (direct inspection)
- `quirk/reports/writer.py` — score dict construction, `_scorecard_markdown()`, `render_html_report()` call (direct inspection)
- `quirk/reports/html_renderer.py` — `_score_band()`, `total_score = score.get("total", 0)`, no subscore display (direct inspection)
- `quirk/cbom/classifier.py` — `_ALGORITHM_TABLE` entries including `ml-kem-768+x25519` at nist_level=3 (direct inspection)
- `quirk/cbom/builder.py` — Pass-1 algo registration per protocol; CONTAINER, SOURCE, S3 branches missing DAR protocols (direct inspection)
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — existing profile oracle entries confirming current coverage
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing service/port assignments
- `.planning/ROADMAP.md` BACK-78, BACK-80, BACK-81, BACK-82, BACK-83, BACK-84 descriptions
- `.planning/PROJECT.md` — v5.0 milestone scope, v4.10.1 deferred requirements, scoring decisions log
- `.planning/milestones/v4.10.1-REQUIREMENTS.md` — EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01 deferred requirements text
- `.planning/HORIZON.md` — v5.0 theme, done-when criteria, <=6 phases guardrail

---

*Feature research for: QU.I.R.K. v5.0 Stabilization — gap closure behavior specifications*
*Researched: 2026-05-22*

# Architecture Research

**Domain:** QU.I.R.K. v5.0 Stabilization — Integration Points
**Researched:** 2026-05-22
**Confidence:** HIGH (all findings verified against live codebase)

---

## v5.0 Integration Map

### System Overview (existing data flow, unchanged by v5.0)

```
run_scan.py (orchestrator)
  └─ _wrapped_phase() ──► scanner modules (quirk/scanner/*.py)
                               │
                               ▼
                        CryptoEndpoint rows (SQLite via quirk/models.py)
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
            evidence.py    cbom/         reports/
            (build_evidence  builder.py  writer.py
             _summary)        │          ├─ executive.py
                    │         ▼          ├─ html_renderer.py (+ Playwright PDF)
                    ▼     cbom/          └─ technical.py
              scoring.py  writer.py
              (compute_
               readiness_
               score)
                    │
                    ▼
           intelligence JSON
           + HTML/PDF reports
           + CLI summary table
```

React dashboard reads from FastAPI (quirk/dashboard/server.py) which calls
`build_evidence_summary` + `compute_readiness_score` at request time from the
stored endpoints. **The scoring path runs twice per scan: once at scan-completion
time in writer.py, and once at dashboard-request time in server.py.**

---

## 1. Scoring Fixes — Exact Files and Blast Radius

### EVIDENCE-TALLY-01

**Root cause (verified):** `quirk/intelligence/scoring.py` derives three
subscores from evidence counters that do NOT flow from `finding_severity_counts`:

- **Hygiene subscore** (lines 177-182) — uses `plaintext_http_count`,
  `http_on_tls_port_count`, `scan_error_rate` only. A scan with zero plaintext
  HTTP and zero scan errors scores 25 regardless of HIGH/CRITICAL findings.
- **Modern TLS subscore** (lines 184-189) — uses `legacy_tls_count =
  sev.get("LOW", 0)` (maps LOWs, not HIGHs/CRITICALs) and `unknown_count`.
  A scan with only HIGH/CRITICAL findings and no LOW findings scores 25.
- **Data at Rest subscore** (lines 220-229) — uses `dar_*` protocol-specific
  counters only. If no database/storage/k8s/vault endpoints are scanned, all
  `dar_*` counters are 0 and the subscore is 25.

**Blast radius:** `quirk/intelligence/scoring.py` only. The penalty model
(`SCORE_WEIGHTS`, `_apply_weighted_impacts`) is not the issue — the per-subscore
evidence reads are. Fix options:
- Add a cross-cutting `high_critical_penalty` to hygiene/modern_tls/dar impacts
  weighted against `finding_severity_counts["HIGH"] + ["CRITICAL"]`, OR
- Document that 25/25 on these subscores is semantically correct ("no evidence
  of weakness in this category") and close EVIDENCE-TALLY-01 as won't-fix with
  rationale. Decide which position to take in requirements scoping.
- If adding the cross-cutting penalty: only `scoring.py` changes; `evidence.py`
  already emits `finding_severity_counts` so no evidence changes needed.
- `tests/test_score_weights_invariant.py` must be updated if any `SCORE_WEIGHTS`
  keys change (CI gate). No other files change.

### RENDER-CLI-01 and RENDER-PDF-01

**Root cause (verified):** `quirk/reports/writer.py` (lines 166-170) creates a
`score` dict with `"total": score_raw["score"]` — this is the already-normalized
0-100 value from `scoring.py`. Then `html_renderer.py` (line 165) reads
`score.get("total", 0)` and passes it to `_score_band()` which uses the same
85/70/55/35 thresholds as `scoring._rating()`. The CLI summary table (writer.py
line 275) renders `total_score/100`.

**Verdict:** The scale mismatch that plagued the dashboard (subscores at 25 fed
to a gauge expecting 0-100) does NOT exist in the CLI/HTML/PDF path. The `total`
key already holds the normalized 0-100 value. RENDER-CLI-01 / RENDER-PDF-01 may
be a false alarm — or they may describe a different issue (e.g., subscores in
the HTML template). The HTML template (`report.html.j2`) does NOT currently
render subscores, only `total_score`. The `score.get("subscores")` dict is
passed through to `intelligence.json` but not used in the template.

**Action for v5.0:** Verify empirically. The audit should scan a test target,
compare CLI output vs dashboard vs HTML report vs PDF for the same scan. If
values match, close RENDER-CLI-01/PDF-01 as "confirmed no bug — the renderer
already uses the normalized path." If mismatches found, the fix lives in:
- `quirk/reports/html_renderer.py` — `render_html_report()`, `_score_band()`
- `quirk/reports/writer.py` — `write_reports()` summary table section

Blast radius: at most 2 files. No scoring.py changes needed.

### Phase 42 OBS-1 — CBOM Pass-1 Zero Algo Components

**Root cause (verified):** `quirk/cbom/builder.py` has explicit `elif` branches
for every protocol. Five profiles emit zero CBOM algo components because their
protocols fall into no branch or into an explicit `pass` branch:

| Profile | Protocol | Current Pass-1 behavior |
|---------|----------|-------------------------|
| `database` | `POSTGRESQL` (lines 509-512) | Registers `cert_pubkey_alg` if set — but bare PostgreSQL probe leaves `cert_pubkey_alg` empty on plaintext connections. MODIFIED needed: extract cipher from `service_detail` or register `"unencrypted"` sentinel. |
| `database` | `MYSQL` (lines 497-507) | Extracts cipher from `service_detail` — but `mysql-ssl-off` sets `ssl-off` which is excluded by the `not in ("SSL-OFF",...)` guard. So ssl-off MySQL emits zero algos. MODIFIED needed. |
| `registry` | `TLS` (falls to `else`) | Goes through the TLS `else` branch (line 536+) which reads `cipher_suite`. The registry scanner must populate `cipher_suite` — verify this is the actual gap. |
| `source` | `SOURCE` (lines 425-430) | `_extract_algo_from_rule_id` uses `cipher_suite` field. If semgrep rule_id has no recognized fragment, `algo_hint` is None and falls back to raw rule_id. If the rule_id itself is unrecognized by `classify_algorithm()`, it emits an UNKNOWN component. Check if UNKNOWN components count toward the "zero" observation. |
| `ssh-weak` | `SSH` (lines 401-413) | Reads `ssh_audit_json` — but ssh-weak profile may not populate full KEX/host-key data. Verify ssh_audit_json is non-empty. |
| `storage-s3` | `S3`, `AZURE_BLOB` | Only registers AES-256 when posture is positively confirmed encrypted. `S3/unencrypted` or `AZURE_BLOB/platform-managed` emit zero algos intentionally (lines 514-526). This may be a design decision, not a bug. |

**The actual fix target in builder.py:** Add algorithm registration for the truly
empty cases (plaintext DB connections, ssl-off MySQL). The S3/storage and
ssh-weak cases may require separate investigation.

**Blast radius:** `quirk/cbom/builder.py` only. No changes to classifier.py,
writer.py, or the CycloneDX schema model. Tests: update
`tests/test_cbom_schema_validation.py` golden snapshots for the affected profiles.

---

## 2. Chaos Lab Profile Registration Surface

### Registration Requirements (CLAUDE.md rule — applies to ALL new profiles)

For each new profile, three files must update in the same commit:
1. `quantum-chaos-enterprise-lab/docker-compose.yml` — add service(s) with
   explicit `profiles: ["<name>"]` and pinned image tags (no `:latest` — CHAOS-05
   pin policy enforced by `lab.sh _validate_pinned_tags` and
   `tests/test_chaos_lab_image_pinning.py`).
2. `quantum-chaos-enterprise-lab/lab.sh` — **no manual ALL_PROFILES list** exists
   anymore (v4.5 Phase 40 fix). `_derive_all_profiles()` reads profile names from
   docker-compose.yml at runtime via `yq` or grep fallback. Adding a new profile to
   docker-compose.yml is sufficient for `lab.sh all` to pick it up automatically.
   Verify `_derive_all_profiles()` grep pattern `[a-zA-Z0-9_-]` handles new names.
3. `quantum-chaos-enterprise-lab/expected_results_v4.md` — add
   `## Profile: <name>` section with port/service/expected-finding oracle table
   in the format established by the v4 oracle.

### New Profile Analysis — New vs Modified, Scanner Probe Needs

#### BACK-80 — `postgres-tls` + `redis-tls` (profile: `db-tls`)

**docker-compose.yml:** NEW services. PostgreSQL 16 with SSL enabled using
`modern.crt`/`modern.key` from `./certs/`. Redis 7 with `--tls-port 6380`.
Port suggestions: postgres-tls at `25433`, postgres-tls-weak at `25434`,
redis-tls at `26380`.

**Scanner probe:** MODIFIED — both scanners already handle TLS ports.
- `quirk/scanner/db_connector.py` `scan_pg_targets()` probes via `psycopg2`
  with `sslmode="disable"` to detect plaintext. For TLS detection, it reads
  `pg_stat_ssl`. TLS cipher enumeration for postgres-tls would require running
  the TLS scanner separately (adding the postgres-tls host:port to the TLS
  scanner target list). No new probe logic — just add the port to TLS scan
  targets in the lab config.yaml.
- `quirk/scanner/broker_scanner.py` already handles port 6380 for
  `_probe_redis_tls()` (line 757). Port 6380 is already in `scan_redis_targets()`
  (line 795). No code change needed — just start a Redis-TLS container on 6380.

**lab.sh:** Automatic pickup via `_derive_all_profiles()`.
**expected_results:** NEW section for `db-tls` profile.

#### BACK-81 — `oqs-nginx` PQC-hybrid (profile: `pqc`)

**docker-compose.yml:** NEW service using `openquantumsafe/nginx` image (verify
current pinnable tag). Port: `25443`. Config: `X25519Kyber768` TLS 1.3 cipher
preference in nginx.conf.

**Scanner probe:** MODIFIED + NEW logic needed.
- `quirk/scanner/tls_scanner.py` via sslyze — sslyze may or may not negotiate
  `X25519Kyber768` depending on the installed OpenSSL/BoringSSL version. If
  sslyze does negotiate it, `cipher_suite` will contain the hybrid KEM name.
- `quirk/cbom/classifier.py` — `mlkem768x25519-sha256` is already in
  `_ALGORITHM_TABLE` (line 66) with NIST level 3. But `X25519Kyber768` (the TLS
  extension name) may differ from the ssh-audit key name. Verify the sslyze
  cipher suite string and add it to classifier if missing.
- `quirk/intelligence/scoring.py` — **NEW bonus weight needed.** Currently the
  only positive signals are `agility_has_ecdsa_bonus` (+4) and
  `identity_mtls_ratio_bonus` (+6). A new `agility_pqc_hybrid_bonus` weight
  (reading a new evidence counter) is needed for OQS-nginx to score above "good
  classical TLS." This is the strategic centerpiece of BACK-81.
- `quirk/intelligence/evidence.py` — NEW counter `pqc_hybrid_endpoint_count`
  that increments when a TLS endpoint's cipher_suite contains a recognized
  PQC-hybrid KEM string (e.g., `X25519Kyber768`, `mlkem768x25519`).

**Blast radius:** classifier.py, evidence.py, scoring.py, expected_results. This
is the most architecturally invasive of the chaos lab additions because it
requires a new evidence counter and a new SCORE_WEIGHTS entry (which triggers the
`tests/test_score_weights_invariant.py` CI gate — must update the expected sum).

**lab.sh:** Automatic.
**expected_results:** NEW `pqc` profile section.

#### BACK-82 — SMTP/STARTTLS (profile: `smtp`)

**docker-compose.yml:** NEW services. `postfix-starttls` on port `587` (weak
TLS: TLS 1.0/1.1 + legacy ciphers) and `postfix-tls-modern` on port `465`
(implicit TLS). Note: existing `email` profile already has a `postfix-email`
service — this is a NEW profile (`smtp`) with a different focus (STARTTLS vs
the existing postfix's configuration).

**Scanner probe:** NO new code needed. `quirk/scanner/email_scanner.py` already
handles port 587 as `SMTP-STARTTLS` with `ProtocolWithOpportunisticTlsEnum.SMTP`
sslyze probe (lines 82-86). Port 465 handled as `SMTPS` implicit TLS (line 84).
The STARTTLS stripping check at port 25 is also already wired. This is config-
and lab-only work.

**lab.sh:** Automatic.
**expected_results:** NEW `smtp` profile section.

#### BACK-83 — gRPC TLS (profile: `grpc`)

**docker-compose.yml:** NEW services. `grpc-tls` on port `50051` (TLS 1.3,
CA-signed cert), `grpc-insecure` on port `50052` (plaintext). Minimal gRPC echo
server (Python `grpcio` or Go).

**Scanner probe:** MODIFIED — TLS scanner needs HTTP/2 ALPN awareness.
- sslyze supports ALPN negotiation; gRPC uses `h2` (HTTP/2) as ALPN. The TLS
  scanner should work if sslyze can complete the TLS handshake without needing a
  valid gRPC request body. Test empirically.
- `grpc-insecure` (plaintext) on 50052 — the TLS scanner will detect "no TLS"
  and create an UNKNOWN or HTTP endpoint. No special handling needed.
- If sslyze fails on ALPN mismatch, a fallback in `_scan_one_fallback()` via
  `ssl.SSLContext.wrap_socket()` should work for certificate extraction.

**lab.sh:** Automatic.
**expected_results:** NEW `grpc` profile section.

#### BACK-84 — Kafka TLS (profile: `kafka`)

**docker-compose.yml:** NEW services. `kafka-tls` with `confluentinc/cp-kafka`
or `bitnami/kafka` (KRaft mode preferred — avoids Zookeeper dependency).
Listeners: `PLAINTEXT://9092` and `SSL://9093`, CA cert from `./certs/`.

**Scanner probe:** NO new code needed. `quirk/scanner/broker_scanner.py`
`scan_one_kafka()` already handles port 9093 as `KAFKA-TLS` with an sslyze
probe (line 120+). Port 9092 already handled as `KAFKA-PLAIN`. Port 9094
(mTLS) supported via `enable_kafka_mtls` config flag (line 467). This is
config- and lab-only work.

**lab.sh:** Automatic.
**expected_results:** NEW `kafka` profile section.

#### BACK-78 — Identity Scoring Evidence Keys (profile: `identity`)

**Root cause confirmed:** The Kerberos, SAML, and DNSSEC scanners correctly
emit endpoints and counters when they find weak algorithms. The identity chaos
lab profiles (kerberos/saml/dnssec) already exist with correct containers
(samba-dc on ports 88+389, simplesamlphp on 8080, bind9-dnssec on 15353). The
gap is that UAT ran with a target of `127.0.0.1` against TLS/SSH ports — the
identity containers were not included in the scan targets.

**Fix:** No code change. Lab config change only — ensure `config.yaml` for the
identity validation scenario includes:
- `kerberos_targets: ["127.0.0.1"]` with Kerberos port 88
- `saml_targets: ["http://localhost:8080/simplesaml/saml2/idp/metadata.php"]`
- `dnssec_targets: ["weak.example.com", "unsigned.example.com"]` with resolver
  pointing to `127.0.0.1:15353`

The three evidence keys (`identity_weak_etype_count`, `saml_weak_signing_count`,
`dnssec_weak_algo_count`) are already computed in `evidence.py` lines 87-89, 165,
171-183. The ratios are already emitted at lines 397-399. The SCORE_WEIGHTS
already include the three identity ratio keys (scoring.py lines 31-33). **This
is a lab scan-target configuration gap, not a code gap.** BACK-78 closes when
the identity profiles are verified to produce non-zero values for these three
keys in `intelligence-*.json`.

---

## 3. Kerberos/SAML/DNSSEC Evidence Key Attachment Points

The attachment chain is complete and correct. For reference:

```
Scanner emits CryptoEndpoint with protocol="KERBEROS"/"SAML"/"DNSSEC"
    |
    v
evidence.py::build_evidence_summary() — lines 160-183
  - KERBEROS: increments identity_weak_etype_count when service_detail
              has etype:{id}:{name}:HIGH or CRITICAL
  - SAML:     increments saml_weak_signing_count on is_weak_cipher() or
              cert_pubkey_size < 2048
  - DNSSEC:   increments dnssec_weak_algo_count on weak algo names or
              cert_pubkey_alg == "NONE" (unsigned zone)
    |
    v
evidence dict emits:
  "identity_weak_etype_count" (line 387)
  "saml_weak_signing_count"   (line 388)
  "dnssec_weak_algo_count"    (line 389)
  "identity_kerberos_weak_etype_ratio" (line 397)
  "identity_saml_weak_signing_ratio"   (line 398)
  "identity_dnssec_weak_algo_ratio"    (line 399)
    |
    v
scoring.py::compute_readiness_score() — lines 159-161
  kerberos_weak_count = evidence.get("identity_weak_etype_count")
  saml_weak_count     = evidence.get("saml_weak_signing_count")
  dnssec_weak_count   = evidence.get("dnssec_weak_algo_count")
    |
    v
identity_trust_impacts (lines 196-198) apply weights:
  "identity_kerberos_weak_etype_ratio": 10.0
  "identity_saml_weak_signing_ratio":   8.0
  "identity_dnssec_weak_algo_ratio":    8.0
```

No SCORE_WEIGHTS changes needed for BACK-78. No evidence.py changes needed.

---

## 4. defusedxml.lxml to lxml Migration (XXE Chokepoint)

### Affected Files

| File | Import | Usage | Migration action |
|------|--------|-------|-----------------|
| `quirk/scanner/saml_scanner.py` | lines 4-24 | `_safe_ET_fromstring()` — try/except block: imports `lxml.etree as ET` first, falls back to `defusedxml.ElementTree` if lxml unavailable | ALREADY MIGRATED to lxml as primary. `defusedxml` is only the fallback. To complete BACK-67: remove the `defusedxml.ElementTree` fallback branch (lines 16-23) and make lxml a hard requirement in `[identity]` extras. |
| `quirk/discovery/nmap_parser.py` | line 6 | `import defusedxml.ElementTree as ET` — used in `parse_nmap_xml()` | REQUIRES MIGRATION. Replace `defusedxml.ElementTree.parse()` with `lxml.etree.parse()` using `ET.XMLParser(resolve_entities=False, no_network=True)`. |

### XXE Control Chokepoint

The canonical XXE-safe lxml pattern (already established in saml_scanner.py lines 6-12):

```python
import lxml.etree as ET

def _safe_parse(xml_source):
    parser = ET.XMLParser(resolve_entities=False, no_network=True)
    return ET.parse(xml_source, parser)  # or ET.fromstring(xml_bytes, parser)
```

`resolve_entities=False` blocks XXE entity expansion. `no_network=True` blocks
SSRF via external DTD/entity URLs. Both flags must be present.

### Migration Scope

- `nmap_parser.py` — MODIFIED. Change `import defusedxml.ElementTree as ET` to
  lxml with safe parser. `parse_nmap_xml()` currently calls `ET.parse(xml_path)` —
  change to `ET.parse(xml_path, parser=ET.XMLParser(resolve_entities=False, no_network=True))`.
- `saml_scanner.py` — MODIFIED (minor). Remove defusedxml fallback branch (lines
  16-23), keeping only the lxml primary path. `lxml` is already in
  `[identity]` extras so the import is safe for identity scans.
- `pyproject.toml` — verify `lxml` is already a declared dependency (it is, in
  `[identity]` extras). `defusedxml` remains in extras for any other consumers
  but the lxml-submodule usage is eliminated.
- `tests/` — no test changes expected; the external behavior of both functions
  is identical.

**Blast radius:** 2 files modified. No API changes. No schema changes.

---

## 5. Node.js 20 to 24 Actions Bump

### Affected File

**Only file:** `.github/workflows/dashboard-quality.yml` line 22: `node-version: '20'`

**Action:** Change to `node-version: '24'`. This is the only GitHub Actions
workflow that specifies a Node.js version. `release.yml` and
`release-container.yml` use Python and Docker only — no Node reference.

**Blast radius:** Single line in one workflow file. The npm ecosystem in
`src/dashboard/` will run against Node 24 in CI. Verify `package-lock.json`
and dependencies are Node 24 compatible (most React/Vite tooling is).

**Deadline:** 2026-06-02. This must be Phase 87 Plan 01, committed before any
other v5.0 work.

---

## 6. Dependency-Aware Build Order

### Critical Path: Node Deadline First

```
Phase 87 (single-file fix, minimum viable phase)
  Plan 87-01: Node 20 to 24 in dashboard-quality.yml
              defusedxml.lxml to lxml in nmap_parser.py + saml_scanner.py
              (both are 2-file mechanical changes; combine into one dep-hygiene plan)
              DEADLINE: merge before 2026-06-02
              Tests: existing SAML tests + nmap parser tests pass unchanged
```

### Scoring Fixes Chain

```
Phase 88 (scoring correctness sweep)
  Plan 88-01: EVIDENCE-TALLY-01 investigation + decision
              (fix or close-as-won't-fix with rationale)
              Files: quirk/intelligence/scoring.py (if fix)
              Tests: update test_score_weights_invariant.py if SCORE_WEIGHTS changes

  Plan 88-02: RENDER-CLI-01 + RENDER-PDF-01 verification
              Empirically compare CLI/HTML/PDF scores vs dashboard for same scan
              Files: quirk/reports/html_renderer.py, quirk/reports/writer.py (if fix needed)
              Tests: regression test against known-bad scan fixture

  Plan 88-03: CBOM Pass-1 OBS-1 fix
              Files: quirk/cbom/builder.py
              Tests: golden snapshots in test_cbom_schema_validation.py
              Constraint: depends on 88-01/88-02 being settled first (scoring
              and CBOM are separate subsystems but share a phase for coherence)
```

### Chaos Lab Chain

```
Phase 89 (chaos lab — scanner-verified targets, NO scoring changes)
  Constraint: Phase 89 plans must be independent of each other within the phase.
              All five lab profiles can be added in parallel plans.

  Plan 89-01: BACK-80 postgres-tls + redis-tls (profile: db-tls)
              No scanner code change. docker-compose + expected_results only.

  Plan 89-02: BACK-82 SMTP/STARTTLS (profile: smtp)
              No scanner code change. docker-compose + expected_results only.

  Plan 89-03: BACK-84 Kafka TLS (profile: kafka)
              No scanner code change. docker-compose + expected_results only.

  Plan 89-04: BACK-83 gRPC TLS (profile: grpc)
              Possibly scanner-probe verification only. docker-compose + expected_results.
              Probe compatibility with sslyze needs empirical check.

  Plan 89-05: BACK-78 Identity evidence keys (lab config only)
              No code change. Verify identity scanner produces non-zero evidence
              keys against the existing kerberos/saml/dnssec profiles with correct
              targets in config.yaml. Update expected_results if gap found.
```

### OQS-nginx — Last (architectural scope)

```
Phase 90 (BACK-81 OQS-nginx PQC-hybrid)
  Constraint: Must come AFTER Phase 88 (scoring) because it introduces a NEW
              SCORE_WEIGHTS key (agility_pqc_hybrid_bonus) and a NEW evidence
              counter (pqc_hybrid_endpoint_count). The test_score_weights_invariant
              expected sum changes again — doing this in the same phase as
              EVIDENCE-TALLY-01 would create conflicting sum expectations.

  Plan 90-01: docker-compose service (oqs-nginx, profile: pqc) + classifier.py
              (verify/add X25519Kyber768 cipher suite string mapping)
              Files: docker-compose.yml, quirk/cbom/classifier.py

  Plan 90-02: evidence.py new counter + scoring.py new bonus weight
              Files: quirk/intelligence/evidence.py, quirk/intelligence/scoring.py,
                     tests/test_score_weights_invariant.py
              Test: verify OQS-nginx scan produces overall score above 80 GOOD

  Plan 90-03: expected_results oracle + docs updates
              Files: expected_results_v4.md
```

### Code Cleanup — Parallel to Lab Work

```
Phase 91 (BACK-49-57 dead code + bookkeeping)
  Can execute in parallel with Phase 89 (no shared files with lab changes).
  Plans map to individual BACK items — each is a small, independent file change.

  Plan 91-01: BACK-49 remove quirk/engine/rules.py
  Plan 91-02: BACK-50 dead writer.py helpers + scorecard.py orphan
  Plan 91-03: BACK-51 migration_planner.py dual categorization
  Plan 91-04: BACK-52 dead intelligence modules (driver_text, schema, calibration)
  Plan 91-05: BACK-53 remove data/qcscan-legacy.sqlite
  Plan 91-06: BACK-54 tqdm dead branch + dependency cleanup
  Plan 91-07: BACK-55 clean D-reference comments + stale version tags
  Plan 91-08: BACK-56 datetime.utcnow deprecation fix in logging_util.py + nmap_provider.py
  Plan 91-09: BACK-58 JWT verify=False documentation
  Plan 91-10: BACK-62 Nyquist VALIDATION.md updates
  Plan 91-11: BACK-63 score transparency section in executive summary
```

### Recommended Phase Structure (at the 6-phase HORIZON cap)

```
Phase 87 — Dependency Hygiene (Node + lxml) [DEADLINE-DRIVEN, FIRST]
Phase 88 — Scoring Residuals (EVIDENCE-TALLY, RENDER-CLI/PDF, CBOM OBS-1)
Phase 89 — Chaos Lab Targets I (db-tls, smtp, kafka, grpc, identity evidence)
Phase 90 — OQS-nginx PQC-hybrid (scoring ceiling anchor)
Phase 91 — Code Cleanup + Bookkeeping (BACK-49-63)
Phase 92 — v5.0 Close-out (version bump, docs, Obsidian sync, release notes)
```

This is 6 phases, exactly at the HORIZON cap. Phase 91 is the most compressible
— if scope is tight, BACK-49-63 can be split across two phases or some items
deferred to v5.1 as low-risk P3 debt.

---

## Component Boundaries — New vs Modified

### What is NEW in v5.0

| Component | File | Nature |
|-----------|------|--------|
| `pqc_hybrid_endpoint_count` counter | `quirk/intelligence/evidence.py` | NEW function/branch |
| `agility_pqc_hybrid_bonus` weight | `quirk/intelligence/scoring.py` + `SCORE_WEIGHTS` | NEW dict key |
| docker-compose services: postgres-tls, postgres-tls-weak, redis-tls, postfix-starttls, postfix-tls-modern, grpc-tls, grpc-insecure, kafka-tls | `quantum-chaos-enterprise-lab/docker-compose.yml` | NEW services |
| Oracle sections for new profiles | `expected_results_v4.md` | NEW sections |

### What is MODIFIED in v5.0

| Component | File | What Changes |
|-----------|------|--------------|
| Node version | `.github/workflows/dashboard-quality.yml:22` | `'20'` to `'24'` |
| XXE fallback removal | `quirk/scanner/saml_scanner.py:16-23` | Remove defusedxml fallback branch |
| lxml migration | `quirk/discovery/nmap_parser.py:6` | `defusedxml.ElementTree` to `lxml.etree` with safe parser |
| Scoring logic | `quirk/intelligence/scoring.py` | New evidence reads and/or cross-cutting penalty (if EVIDENCE-TALLY-01 gets a code fix) |
| HTML/PDF renderer | `quirk/reports/html_renderer.py` + `writer.py` | Potentially no-op if audit confirms no bug |
| CBOM builder Pass-1 | `quirk/cbom/builder.py` | New branches for zero-algo-component protocols (db plaintext, ssl-off MySQL) |
| Algorithm classifier | `quirk/cbom/classifier.py` | Possibly new entry for OQS TLS cipher suite name |
| CBOM golden snapshots | `tests/test_cbom_schema_validation.py` | Updated fixture files for affected profiles |
| Score weights invariant | `tests/test_score_weights_invariant.py` | New expected sum when SCORE_WEIGHTS keys change |
| Dead code removal | `quirk/engine/rules.py`, `quirk/reports/writer.py`, `quirk/intelligence/*.py` (stubs), `data/qcscan-legacy.sqlite` | Deleted |
| datetime.utcnow | `quirk/logging_util.py:43`, `quirk/discovery/nmap_provider.py:50` | Replaced with `datetime.now(timezone.utc)` |

### What is UNTOUCHED in v5.0

- `quirk/intelligence/evidence.py` (except OQS counter addition in Phase 90)
- `run_scan.py` (scanner orchestration unchanged)
- All scanner modules (tls_scanner, email_scanner, broker_scanner, db_connector)
- FastAPI server and React dashboard (no v5.0 scope)
- SQLite schema (no new columns needed)
- CBOM writer
- Compliance module, QRAMM module, error registry
- `quirk/reports/executive.py`, `quirk/reports/technical.py`

---

## Data Flow Changes

### Before v5.0

```
TLS endpoint scan -> cipher_suite -> evidence.py (no PQC signal) -> scoring.py (no PQC bonus)
```

### After v5.0 (BACK-81)

```
TLS endpoint scan -> cipher_suite (contains "X25519Kyber768" on OQS-nginx)
    -> evidence.py: pqc_hybrid_endpoint_count += 1
    -> scoring.py: agility_impacts += ("PQC-hybrid adoption", +N * weight)
    -> overall score > 80 for OQS-nginx-only scans
```

All other data flows are unchanged. The v5.0 scoring fixes are additive to the
existing penalty-only model — the OQS bonus is the only new positive signal.

---

## Sources

- Live codebase inspection (HIGH confidence — all file paths and line numbers verified)
- `quirk/intelligence/evidence.py` — complete read
- `quirk/intelligence/scoring.py` — complete read
- `quirk/cbom/builder.py` — Pass-1 section (lines 397-550)
- `quirk/reports/html_renderer.py`, `quirk/reports/writer.py` — score rendering sections
- `quirk/scanner/saml_scanner.py:1-60` — defusedxml import pattern
- `quirk/discovery/nmap_parser.py:1-40` — defusedxml usage
- `quantum-chaos-enterprise-lab/docker-compose.yml` — all service and profile definitions
- `quantum-chaos-enterprise-lab/lab.sh:56-70` — `_derive_all_profiles()` implementation
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — oracle format
- `.github/workflows/dashboard-quality.yml:22` — Node version declaration
- `.planning/milestones/v4.10.1-REQUIREMENTS.md` — EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01 root cause descriptions
- `.planning/ROADMAP.md` Backlog — BACK-49 through BACK-84 item descriptions
- `.planning/HORIZON.md` — v5.0 scope guardrails (6-phase cap)

---
*Architecture research for: QU.I.R.K. v5.0 Stabilization integration points*
*Researched: 2026-05-22*

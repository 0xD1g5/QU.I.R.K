---
audit: comprehensive-codebase-2026-05-08
ledger_status: active
generated: 2026-05-09
total_findings: 169
closed: 0
open: 148
deferred: 0
wont_fix: 0
---

# Audit Findings Ledger — 2026-05-08

**Purpose:** Durable, mark-off-able tracking of every finding from the 2026-05-08 audit across the v4.8 milestone and into v4.9 triage.

**Lifecycle:**
- `[ ] open` — finding present in code, no decision yet
- `[ ] mapped` — closed-by a v4.8 phase; flips to `[x]` when that phase ships
- `[x] closed` — fix shipped, verified by phase verification
- `[ ] deferred-v4.9` — explicit decision to push to next milestone
- `[ ] wont-fix` — explicit decision not to address (with reason)

**How to use:**
1. During Wave A phase execution, executor flips matching rows to `[x]` after verification.
2. After Wave A complete, triage all remaining `open` rows — assign deferred-v4.9 / wont-fix / new-phase.
3. v4.9 milestone planning consumes this ledger as input.

---

## Summary

| Severity | Total | Mapped | Open | Closed | Deferred | Won't-fix |
|---|---:|---:|---:|---:|---:|---:|
| BLOCKER | 44 | 21 | 23 | 0 | 0 | 0 |
| WARNING | 96 | 0 | 96 | 0 | 0 | 0 |
| INFO | 29 | 0 | 29 | 0 | 0 | 0 |
| **TOTAL** | **169** | **21** | **148** | **0** | **0** | **0** |

---

## Findings by Subsystem

### Scanners — Protocol

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| scanners-protocol/CR-01 | BLOCKER | JWT scanner disables TLS verification on JWKS fetch (MITM) | Phase 57 (HARDEN-SCAN-01) | [x] closed |
| scanners-protocol/CR-02 | BLOCKER | Argument injection into semgrep via repo_path | Phase 57 (HARDEN-SCAN-02) | [x] closed |
| scanners-protocol/CR-03 | BLOCKER | Argument injection into syft via image_ref | Phase 57 (HARDEN-SCAN-03) | [x] closed |
| scanners-protocol/CR-04 | BLOCKER | SSRF in SAML metadata fetcher — no scheme/host validation | Phase 57 (HARDEN-SCAN-04) | [x] closed |
| scanners-protocol/CR-05 | BLOCKER | Hardcoded guest:guest credentials sent to arbitrary hosts | Phase 57 (HARDEN-SCAN-05) | [x] closed |
| scanners-protocol/CR-06 | BLOCKER | verify=False on RabbitMQ mgmt API + ssl_cert_reqs=none Redis | Phase 57 (HARDEN-SCAN-06) | [x] closed |
| scanners-protocol/CR-07 | BLOCKER | Nested ThreadPoolExecutor + sslyze internal pool resource leak | — | [ ] open |
| scanners-protocol/CR-08 | BLOCKER | fingerprint._tcp_connect socket leak on SSH banner branch | — | [ ] open |
| scanners-protocol/WR-01 | WARNING | coverage.calculate_coverage can return >100% | — | [ ] open |
| scanners-protocol/WR-02 | WARNING | quantum_readiness_score non-monotonic; severity case-sensitive | — | [ ] open |
| scanners-protocol/WR-03 | WARNING | Bare except Exception swallowing subprocess errors silently | — | [ ] open |
| scanners-protocol/WR-04 | WARNING | nmap_provider default port CSV is incomplete and wrong | — | [ ] open |
| scanners-protocol/WR-05 | WARNING | nmap_provider.run_nmap_discovery accepts unvalidated extra_args | — | [ ] open |
| scanners-protocol/WR-06 | WARNING | nmap_parser uses stdlib ET — XXE / billion-laughs surface | — | [ ] open |
| scanners-protocol/WR-07 | WARNING | dnssec _parse_dnskeys unbounded subscript on key_bytes | — | [ ] open |
| scanners-protocol/WR-08 | WARNING | kerberos _probe_kdc_udp silently swallows all decode errors | — | [ ] open |
| scanners-protocol/WR-09 | WARNING | kerberos _build_as_req uses non-cryptographic RNG for nonce | — | [ ] open |
| scanners-protocol/WR-10 | WARNING | saml _classify_target parses JSON of arbitrary bytes; no size cap | — | [ ] open |
| scanners-protocol/WR-11 | WARNING | Inconsistent extras messaging across optional-dep scanners | — | [ ] open |
| scanners-protocol/WR-12 | WARNING | email/broker ThreadPool workers hardcoded to 50 | — | [ ] open |
| scanners-protocol/WR-13 | WARNING | discovery/tls_scanner.py is dead-code duplicate | — | [ ] open |
| scanners-protocol/WR-14 | WARNING | target_expander dedup; no CIDR bound; type confusion | — | [ ] open |
| scanners-protocol/IN-01 | INFO | tls_capabilities downgrade SSLContext warrants comment | — | [ ] open |
| scanners-protocol/IN-02 | INFO | DNSSEC_ALG_MAP missing reserved algorithms 9, 11 | — | [ ] open |
| scanners-protocol/IN-03 | INFO | SHA1_INDICATORS substring match too loose | — | [ ] open |
| scanners-protocol/IN-04 | INFO | fingerprint _http_probe_plain sends Host: localhost | — | [ ] open |
| scanners-protocol/IN-05 | INFO | _is_pfs / _is_weak duplicated across email/broker/tls | — | [ ] open |
| scanners-protocol/IN-06 | INFO | kerberos _derive_realm IPv4 detection is fragile | — | [ ] open |

### Scanners — Cloud + Engine

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| scanners-cloud/CR-01 | BLOCKER | migration_planner.py is a stub — does not implement scoring | — | [ ] open |
| scanners-cloud/CR-02 | BLOCKER | GCP Cloud SQL stuffs severity into cert_pubkey_alg field | — | [ ] open |
| scanners-cloud/CR-03 | BLOCKER | K8s scan_k8s_targets calls _scan_aks_encryption with None cred | — | [ ] open |
| scanners-cloud/CR-04 | BLOCKER | Vault scan_error leaks raw exception text incl token fragments | Phase 59 (LEAK-01) | [ ] mapped |
| scanners-cloud/CR-05 | BLOCKER | GCP scan_gcp_targets exception message includes raw cred text | Phase 59 (LEAK-02) | [ ] mapped |
| scanners-cloud/CR-06 | BLOCKER | Cache TTL boundary inverted on ttl_hours <= 0 | — | [ ] open |
| scanners-cloud/CR-07 | BLOCKER | TokenBucket starvation when tokens > capacity requested | — | [ ] open |
| scanners-cloud/CR-08 | BLOCKER | TokenBucket sleep + busy-wait can starve under contention | — | [ ] open |
| scanners-cloud/CR-09 | BLOCKER | K8s scan_k8s_targets empty-list edge case violates K8S-03 | — | [ ] open |
| scanners-cloud/CR-10 | BLOCKER | Azure Blob key_source microsoft.storage conflated with absent | — | [ ] open |
| scanners-cloud/WR-01 | WARNING | AWS _scan_acm may pass empty ARN to describe_certificate | — | [ ] open |
| scanners-cloud/WR-02 | WARNING | AWS _scan_kms does not skip disabled or pending-deletion keys | — | [ ] open |
| scanners-cloud/WR-03 | WARNING | Azure _scan_keyvault_keys swallows key_size — always None | — | [ ] open |
| scanners-cloud/WR-04 | WARNING | GCP _scan_kms triple-nested while with no pagination cap | — | [ ] open |
| scanners-cloud/WR-05 | WARNING | GCP _scan_kms skips UNSPECIFIED/UNKNOWN keys inconsistently | — | [ ] open |
| scanners-cloud/WR-06 | WARNING | K8s _emit_inaccessible_finding does not strip : from cluster_name | — | [ ] open |
| scanners-cloud/WR-07 | WARNING | DB connector psycopg2.connect password defaults to empty string | — | [ ] open |
| scanners-cloud/WR-08 | WARNING | DB connector exception message does not strip target host | — | [ ] open |
| scanners-cloud/WR-09 | WARNING | vault_connector reads VAULT_TOKEN from env after token=None | — | [ ] open |
| scanners-cloud/WR-10 | WARNING | risk_engine.py is misnamed / actual scorer not in this review | — | [ ] open |
| scanners-cloud/WR-11 | WARNING | profiles.py mutates enable_email/enable_broker w/o user override | — | [ ] open |
| scanners-cloud/WR-12 | WARNING | profiles.py standard profile re-applies defaults equal to baseline | — | [ ] open |
| scanners-cloud/WR-13 | WARNING | AWS _scan_s3_encryption executor.map drops _classify exceptions | — | [ ] open |
| scanners-cloud/WR-14 | WARNING | AWS _scan_eks_encryption reads enc_cfg[0] on multi-entry list | — | [ ] open |
| scanners-cloud/WR-15 | WARNING | Cache _read_json does not handle malformed JSON | — | [ ] open |
| scanners-cloud/WR-16 | WARNING | cache.scope_hash does not include connector enable flags | — | [ ] open |
| scanners-cloud/WR-17 | WARNING | K8s _enumerate_secret_types Counter may include None | — | [ ] open |
| scanners-cloud/WR-18 | WARNING | Vault _scan_pki_mounts PEM split heuristic fragile | — | [ ] open |
| scanners-cloud/WR-19 | WARNING | AWS module-level ThreadPoolExecutor import inside function | — | [ ] open |
| scanners-cloud/WR-20 | WARNING | K8s key_name from unencrypted path included in dat_scan_json | — | [ ] open |
| scanners-cloud/WR-21 | WARNING | profiles.py tail truncated mid-function — verify EOF | — | [ ] open |
| scanners-cloud/WR-22 | WARNING | GCP _scan_cloud_sql description not surfaced via service_detail | — | [ ] open |
| scanners-cloud/WR-23 | WARNING | evaluate_endpoints _postprocess_findings mutates during iteration | — | [ ] open |
| scanners-cloud/WR-24 | WARNING | _dedupe_findings 4-tuple ordering causes unstable golden outputs | — | [ ] open |

### QRAMM + Compliance

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| qramm-compliance/BL-01 | BLOCKER | Profile multiplier not clamped server-side | Phase 60 (SCORE-01) | [ ] mapped |
| qramm-compliance/BL-02 | BLOCKER | Maturity threshold gap mis-classifies scores in [1.4,1.5) etc. | Phase 60 (SCORE-02) | [ ] mapped |
| qramm-compliance/BL-03 | BLOCKER | last_verified lexicographic string comparison is fragile | — | [ ] open |
| qramm-compliance/BL-04 | BLOCKER | int(years_raw) accepts negative/zero years | — | [ ] open |
| qramm-compliance/WR-01 | WARNING | Evidence bridge date-string equality vulnerable to TZ drift | — | [ ] open |
| qramm-compliance/WR-02 | WARNING | compute_practice_score accepts out-of-range answers | — | [ ] open |
| qramm-compliance/WR-03 | WARNING | evidence_bridge synchronize_session=fetch suboptimal; no idempotency | — | [ ] open |
| qramm-compliance/WR-04 | WARNING | Practice 1.1 Discovery score ignores endpoint count entirely | — | [ ] open |
| qramm-compliance/WR-05 | WARNING | vuln_pct unbounded division — zero algos scores 4 (Advanced) | — | [ ] open |
| qramm-compliance/WR-06 | WARNING | Maturity label >=4.0 unreachable at multiplier=1.0 (FP noise) | — | [ ] open |
| qramm-compliance/WR-07 | WARNING | evidence_bridge does not handle db.commit failure | — | [ ] open |
| qramm-compliance/WR-08 | WARNING | attach_context swallows AttributeError; user context dropped | — | [ ] open |
| qramm-compliance/WR-09 | WARNING | migration_advisor substring matching produces false positives | — | [ ] open |
| qramm-compliance/WR-10 | WARNING | _walk_json_for_alg_strings skips non-_ALG_KEYS strings | — | [ ] open |
| qramm-compliance/WR-11 | WARNING | compliance_map.py weight 0.0 ambiguous vs not-yet-covered | — | [ ] open |
| qramm-compliance/WR-12 | WARNING | model_meta.py lacks is_qramm_model_stale helper | — | [ ] open |
| qramm-compliance/WR-13 | WARNING | TODO Phase 50 comment left in production module header | — | [ ] open |

### CBOM + Intelligence + Reports

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| cbom-intel-reports/CR-01 | BLOCKER | CBOM Pass-1 emits zero algo components for 12 protocol families | Phase 61 (CBOM-COVER-01) | [ ] mapped |
| cbom-intel-reports/CR-02 | BLOCKER | VAULT protocol falls through to TLS branch in Pass-1/2/3 | Phase 61 (CBOM-COVER-02) | [ ] mapped |
| cbom-intel-reports/CR-03 | BLOCKER | SOURCE algo hint maps DES->3DES and collapses AES variants | — | [ ] open |
| cbom-intel-reports/CR-04 | BLOCKER | Confidence returns 100% TLS-enum coverage when no TLS scanned | Phase 60 (SCORE-03) | [ ] mapped |
| cbom-intel-reports/CR-05 | BLOCKER | Trend 1-second session window cannot disambiguate two scans | — | [ ] open |
| cbom-intel-reports/CR-06 | BLOCKER | Score subscores can sum >100; agility_score added unbounded | Phase 60 (SCORE-04) | [ ] mapped |
| cbom-intel-reports/CR-07 | BLOCKER | Markdown injection / table-break in technical.py finding rows | Phase 61 (REPORT-SAN-01) | [ ] mapped |
| cbom-intel-reports/WR-01 | WARNING | PDF render uses blanket except Exception — masks programmer errors | — | [ ] open |
| cbom-intel-reports/WR-02 | WARNING | PDF render does not clean up Playwright resources on exception | — | [ ] open |
| cbom-intel-reports/WR-03 | WARNING | motion_broker_weak_tls_count predicate uses inconsistent uppercase | — | [ ] open |
| cbom-intel-reports/WR-04 | WARNING | ECDSA detection in evidence.py mismatches cert_pubkey_alg conventions | — | [ ] open |
| cbom-intel-reports/WR-05 | WARNING | _apply_weighted_impacts uses fixed score_cap=25.0 | Phase 60 (SCORE-04) | [ ] mapped |
| cbom-intel-reports/WR-06 | WARNING | SCORE_WEIGHTS sum is 261, not normalized | — | [ ] open |
| cbom-intel-reports/WR-07 | WARNING | Roadmap _why string-format produces double-period artifacts | — | [ ] open |
| cbom-intel-reports/WR-08 | WARNING | Roadmap mutation-after-yield merge rule undocumented | — | [ ] open |
| cbom-intel-reports/WR-09 | WARNING | executive _build_interpretation accesses score['score'] w/o guard | — | [ ] open |
| cbom-intel-reports/WR-10 | WARNING | evidence.py SAML weak detection equality on uppercased SHA1 fragile | — | [ ] open |
| cbom-intel-reports/WR-11 | WARNING | evidence.py motion email weak-cipher predicate diverges from broker | — | [ ] open |
| cbom-intel-reports/WR-12 | WARNING | _decompose_cipher_suite returns wrong KEX for RSA non-PFS in TLS1.2 | — | [ ] open |
| cbom-intel-reports/WR-13 | WARNING | confidence.py weight overrides bypass clamp and validation | — | [ ] open |
| cbom-intel-reports/WR-14 | WARNING | writer.py PDF graceful degradation prints no warning to user | — | [ ] open |
| cbom-intel-reports/IN-01 | INFO | Hardcoded PLATFORM_VERSION = 4.4.0 duplicated across modules | — | [ ] open |
| cbom-intel-reports/IN-02 | INFO | _extract_ssh_algorithms swallows JSONDecodeError silently | — | [ ] open |
| cbom-intel-reports/IN-03 | INFO | Trend analysis fetches all endpoints into memory per session | — | [ ] open |
| cbom-intel-reports/IN-04 | INFO | evidence.py _PROTOCOL_KEYS missing CONTAINER/SOURCE/AWS/etc. | — | [ ] open |
| cbom-intel-reports/IN-05 | INFO | Roadmap baseline governance item only when len < min_items | — | [ ] open |
| cbom-intel-reports/IN-06 | INFO | executive truncates Migration Paths at 10 with no indicator | — | [ ] open |
| cbom-intel-reports/IN-07 | INFO | html_renderer roadmap_section timeframe comparison dead branch | — | [ ] open |
| cbom-intel-reports/IN-08 | INFO | writer hosts_count set falsy hosts collapse to single "" | — | [ ] open |
| cbom-intel-reports/IN-09 | INFO | Schema dataclass IntelligenceReport defined but unused | — | [ ] open |

### Dashboard API + CLI + Core

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| api-cli-core/CR-01 | BLOCKER | Path traversal in quirk init --output | Phase 58 (HARDEN-API-02) | [ ] mapped |
| api-cli-core/CR-02 | BLOCKER | SSRF / port binding in routes/pdf.py via QUIRK_SERVE_PORT | Phase 58 (HARDEN-API-03) | [ ] mapped |
| api-cli-core/CR-03 | BLOCKER | Missing authentication on every dashboard route | Phase 58 (HARDEN-API-01) | [ ] mapped |
| api-cli-core/CR-04 | BLOCKER | QRAMMProfile.session_id is nullable and has no DB-level FK | — | [ ] open |
| api-cli-core/CR-05 | BLOCKER | delete_session does not clear qramm_sessions.profile_id link | — | [ ] open |
| api-cli-core/CR-06 | BLOCKER | Bare except: pass in classifier call drops findings silently | — | [ ] open |
| api-cli-core/CR-07 | BLOCKER | SQL injection guard on column names lacks col_type DDL fragment | — | [ ] open |
| api-cli-core/CR-08 | BLOCKER | init_db ALTER TABLE migrations are not transactional | — | [ ] open |
| api-cli-core/CR-09 | BLOCKER | parse_target_tokens reflective DoS via deep @file recursion | Phase 58 (HARDEN-API-04) | [ ] mapped |
| api-cli-core/WR-01 | WARNING | _check_dashboard / _check_network always return True | — | [ ] open |
| api-cli-core/WR-02 | WARNING | _check_db opens DB at default path regardless of QUIRK_DB_PATH | — | [ ] open |
| api-cli-core/WR-03 | WARNING | _default_db_path mtime-newest-wins is non-deterministic | — | [ ] open |
| api-cli-core/WR-04 | WARNING | get_latest_scan ?scan_id= time-window slice off-by-microsecond | — | [ ] open |
| api-cli-core/WR-05 | WARNING | list_scans groups by string-formatted timestamp — TZ-fragile | — | [ ] open |
| api-cli-core/WR-06 | WARNING | compute_overall_score multiplier validated client-side only | — | [ ] open |
| api-cli-core/WR-07 | WARNING | routes/qramm read_session returns score=None on JSON corruption | — | [ ] open |
| api-cli-core/WR-08 | WARNING | _derive_dar_findings swallows json.loads errors with bare except | — | [ ] open |
| api-cli-core/WR-09 | WARNING | _compute_multiplier rounds before clamp — boundary fragile | — | [ ] open |
| api-cli-core/WR-10 | WARNING | interactive _prompt_int infinite loop on EOF | — | [ ] open |
| api-cli-core/WR-11 | WARNING | interactive exposure default silently used when input not 1/2/3 | — | [ ] open |
| api-cli-core/WR-12 | WARNING | setattr enable_nmap injects undeclared dataclass attribute | — | [ ] open |
| api-cli-core/WR-13 | WARNING | validate.py artifact list missing intelligence-{stamp}.json | — | [ ] open |
| api-cli-core/WR-14 | WARNING | qramm_cmd env override has no try/except on malformed input | — | [ ] open |
| api-cli-core/WR-15 | WARNING | routes/scan reads QUIRK_OUTPUT_DIR from env into Path read | — | [ ] open |
| api-cli-core/WR-16 | WARNING | parse_target_tokens does not validate hostnames | — | [ ] open |
| api-cli-core/WR-17 | WARNING | routes/qramm list_questions fragile on QRAMM_QUESTIONS schema drift | — | [ ] open |
| api-cli-core/IN-01 | INFO | Dict[str, Any] type erasure on QRAMM endpoints | — | [ ] open |
| api-cli-core/IN-02 | INFO | _FACES banner has \- ambiguous escape (comment misleading) | — | [ ] open |
| api-cli-core/IN-03 | INFO | interactive timezone fallback to UTC string vs IANA name | — | [ ] open |
| api-cli-core/IN-04 | INFO | Magic numbers for QRAMM clamp 0.8 / 1.5 / 0.10 / 0.20 | — | [ ] open |
| api-cli-core/IN-05 | INFO | app.py closure captures via default argument missing | — | [ ] open |
| api-cli-core/IN-06 | INFO | db.py _ensure_*_columns helpers collapse to one helper | — | [ ] open |
| api-cli-core/IN-07 | INFO | targets.py projected_probe_count materializes /8 host list | — | [ ] open |

### React Frontend

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| react-frontend/BR-01 | BLOCKER | Debounced draft persister drops fields on rapid multi-field edits | Phase 62 (HOOK-01) | [x] closed |
| react-frontend/BR-02 | BLOCKER | Confirm-auto-fill flow never persists confirmed_at to server | Phase 62 (HOOK-02) | [x] closed |
| react-frontend/BR-03 | BLOCKER | useScanData error setters lack cancellation guard | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/BR-04 | BLOCKER | useScanData does not clear stale data when scan switches | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/BR-05 | BLOCKER | /print data-ready sentinel never reset — stale on re-fetch | Phase 62 (HOOK-04) | [x] closed |
| react-frontend/BR-06 | BLOCKER | System theme not reactive — prefers-color-scheme read once | Phase 62 (HOOK-04) | [x] closed |
| react-frontend/WR-01 | WARNING | useQRAMMSession setError/setSession run without cancellation guard | Phase 62 (HOOK-01) | [x] closed |
| react-frontend/WR-02 | WARNING | useScanList silently swallows non-OK responses | — | [ ] open |
| react-frontend/WR-03 | WARNING | Pending QRAMM debounce timers leak on provider unmount | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/WR-04 | WARNING | theme-provider casts localStorage value to Theme without validation | — | [ ] open |
| react-frontend/WR-05 | WARNING | executive PDF download setTimeout revoke leaks across unmount | — | [ ] open |
| react-frontend/WR-06 | WARNING | executive reads body.detail without coercion check | — | [ ] open |
| react-frontend/WR-07 | WARNING | print data-ready set even when QRAMM has errored | — | [ ] open |
| react-frontend/WR-08 | WARNING | qramm-profile submitError swallows actual error message | — | [ ] open |
| react-frontend/WR-09 | WARNING | certificates Subject CN regex breaks on RFC2253-escaped commas | — | [ ] open |
| react-frontend/WR-10 | WARNING | cbom Cytoscape registration uses cast without proper typing | — | [ ] open |
| react-frontend/WR-11 | WARNING | ScorecardTab Maturity Distribution width math hardcodes /4 | — | [ ] open |
| react-frontend/WR-12 | WARNING | ScorecardTab maturity bar applies badge text/border classes | — | [ ] open |
| react-frontend/WR-13 | WARNING | ComplianceMapTab re-fetches on every ctx.scoreResult change | — | [ ] open |
| react-frontend/WR-14 | WARNING | qramm-assessment handleNewAssessment does not abort debounced persists | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/IN-01 | INFO | qramm-assessment comment says 5-tab but renders 6 tabs | — | [ ] open |
| react-frontend/IN-02 | INFO | cbom/roadmap try/catch swallows extension registration error | — | [ ] open |
| react-frontend/IN-03 | INFO | findings/identity recreate columns array on every render | — | [ ] open |
| react-frontend/IN-04 | INFO | useQRAMMSession seededRef not reset on New Assessment flow | — | [ ] open |
| react-frontend/IN-05 | INFO | cbom compByAlg lookups use [0] for representative — drops variance | — | [ ] open |
| react-frontend/IN-06 | INFO | print createElement style injection works but non-standard React | — | [ ] open |
| react-frontend/IN-07 | INFO | useScanData does not propagate actual fetch URL into errors | — | [ ] open |

---

## Cross-Cutting Patterns

Findings rolled up into a single phase fix.

- **Pattern A — Credential leakage via exception stringification:** scanners-cloud/CR-04, scanners-cloud/CR-05, scanners-cloud/WR-08, scanners-cloud/WR-09, api-cli-core/WR-08, api-cli-core/WR-15 → Phase 59 (LEAK-01..03). Top-15 blockers (CR-04, CR-05) are mapped above; remaining warnings flagged here for Phase 59 opportunistic close.
- **Pattern B — Untrusted input flowing to subprocess / HTTP:** scanners-protocol/CR-02, CR-03, CR-04, WR-05, WR-06, WR-10 → Phase 57 (HARDEN-SCAN-02..04). Top-15 blockers mapped above; warnings are sub-instances candidate for Phase 57 close.
- **Pattern C — Cancellation guard inconsistency in React hooks:** react-frontend/BR-01..BR-06 (mapped), plus react-frontend/WR-01, WR-03, WR-14 → Phase 62 (HOOK-01..04) opportunistic close.
- **Pattern D — Migration safety:** api-cli-core/CR-07, api-cli-core/CR-08, scanners-cloud/WR-15, scanners-cloud/CR-06 → flag as `open` (not mapped; candidate for v4.9 or Phase 67 RESUME).
- **Pattern E — Score arithmetic correctness:** cbom-intel-reports/CR-04, CR-06, WR-05, WR-06, qramm-compliance/BL-01, BL-02, WR-05, WR-06 → Phase 60 (SCORE-01..04). Top-15 + WR-05 mapped; remainder candidate for Phase 60 opportunistic close.

---

## Initial Triage Recommendations

For findings NOT mapped to a Wave A phase, suggest a default disposition based on the finding text. **These are recommendations only — no triage decisions are recorded as final dispositions in this ledger.**

- **Likely defer-v4.9 (dead/misnamed code):**
  - scanners-protocol/WR-13 — `quirk/discovery/tls_scanner.py` dead duplicate (delete)
  - cbom-intel-reports/IN-09 — `quirk/intelligence/schema.py` unused dataclasses
  - scanners-cloud/CR-01 — `migration_planner.py` 16-line stub
  - scanners-cloud/WR-10 — `risk_engine.py` rename / scoping
  - qramm-compliance/WR-09 — migration_advisor false-positives
  - AUDIT-SUMMARY explicitly suggests v5.2 chaos lab + tech debt sweep for dead-code cleanup.

- **Likely close-during-Wave-A (opportunistic in-phase fixes):**
  - All Pattern A warnings (Phase 59)
  - All Pattern B warnings (Phase 57)
  - Pattern C remaining warnings (Phase 62)
  - Pattern E remaining warnings (Phase 60)
  - Subsystem INFO findings adjacent to BLOCKER fixes already in scope

- **Likely won't-fix (audit text flagged low-value or addressed-by-design):**
  - cbom-intel-reports/IN-05 — Roadmap baseline governance item (probably intentional, undocumented)
  - cbom-intel-reports/IN-08 — writer hosts_count edge case (defensive-but-misleading)
  - api-cli-core/IN-05 — closure capture pattern (correct as-is)
  - react-frontend/IN-04 — useQRAMMSession seededRef (no action required per audit text)

These are recommendations for the human triage pass.

---

_Generated: 2026-05-09 from `.planning/audit-2026-05-08/` REVIEW.md files._

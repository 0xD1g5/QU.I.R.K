# Requirements: v4.9 Audit Depth

**Milestone goal:** Systematically close the 121 remaining open findings from the 2026-05-08 audit (92 WARNINGs + 29 INFOs + 13 deferred BLOCKERs), hardening correctness, resource management, input validation, and code quality across all six scanner subsystems.

**Audit ledger:** `.planning/audit-2026-05-08/AUDIT-TASKS.md` — authoritative source of truth; rows flip to `[x] closed` as phases verify fixes.

**Previous milestone requirements:** See `.planning/milestones/v4.8-REQUIREMENTS.md`

---

## v1 Requirements

### BLOCK — Deferred BLOCKERs

- [ ] **BLOCK-01**: TLS scanner ThreadPool and socket resources are correctly cleaned up on all exception paths during sslyze invocation (closes scanners-protocol/CR-07, CR-08)
- [ ] **BLOCK-02**: GCP Cloud SQL connector writes SSL enforcement status to the severity/description fields, not to cert_pubkey_alg (closes scanners-cloud/CR-02)
- [ ] **BLOCK-03**: K8s connector guards against None azure_cred before invoking _scan_aks_encryption; empty target list returns K8S-03-conformant empty result (closes scanners-cloud/CR-03, CR-09)
- [ ] **BLOCK-04**: Azure Blob connector distinguishes platform-managed key (Microsoft.Storage) from absent key_source state in both severity and description output (closes scanners-cloud/CR-10)
- [ ] **BLOCK-05**: Cache._is_fresh treats ttl_hours ≤ 0 as "never fresh" (cache disabled) per documented operator semantics (closes scanners-cloud/CR-06)
- [ ] **BLOCK-06**: TokenBucket.acquire raises on n > capacity instead of looping forever; contention starvation eliminated via fair queue or equivalent guard (closes scanners-cloud/CR-07, CR-08)
- [ ] **BLOCK-07**: QRAMMProfile.session_id has a DB-level FK constraint; delete_session nulls the reverse profile_id pointer to prevent dangling references (closes api-cli-core/CR-04, CR-05)
- [ ] **BLOCK-08**: Bare except in classifier invocation replaced with specific logged exception; DDL col_type string validated before interpolation into ALTER TABLE (closes api-cli-core/CR-06, CR-07)

### PROTO — Scanner-Protocol WARNINGs

- [ ] **PROTO-01**: coverage.calculate_coverage return value clamped to [0.0, 1.0]; quantum_readiness_score severity comparison is case-insensitive (closes scanners-protocol/WR-01, WR-02)
- [ ] **PROTO-02**: Bare except swallowing subprocess errors replaced with specific exception handling and stderr logging (closes scanners-protocol/WR-03)
- [ ] **PROTO-03**: nmap_provider default port CSV corrected; extra_args validated against character allowlist; nmap XML output parsed via defusedxml to eliminate XXE surface (closes scanners-protocol/WR-04, WR-05, WR-06)
- [ ] **PROTO-04**: DNSSEC _parse_dnskeys key_bytes subscript bounded; Kerberos decode errors logged not silently swallowed; Kerberos nonce uses cryptographic RNG; SAML _classify_target JSON parse has byte size cap (closes scanners-protocol/WR-07, WR-08, WR-09, WR-10)
- [ ] **PROTO-05**: Optional-dep extras messaging consistent across email/broker/container/source scanners; email/broker ThreadPool max_workers configurable via ScanCfg; discovery/tls_scanner.py dead duplicate deleted; target_expander dedup stable, CIDR expansion bounded, type confusion resolved (closes scanners-protocol/WR-11, WR-12, WR-13, WR-14)

### CLOUD — Cloud Scanner WARNINGs

- [ ] **CLOUD-01**: AWS ACM empty ARN guarded before describe_certificate; KMS skips disabled and pending-deletion keys; S3 executor.map propagates _classify exceptions; EKS enc_cfg reads from entire list not index 0 (closes scanners-cloud/WR-01, WR-02, WR-13, WR-14)
- [ ] **CLOUD-02**: Azure KeyVault key_size populated correctly; K8s cluster_name colon-stripped before finding emission; K8s Counter excludes None values; K8s key_name omitted for unencrypted path in dat_scan_json (closes scanners-cloud/WR-03, WR-06, WR-17, WR-20)
- [ ] **CLOUD-03**: GCP KMS pagination loop has cap; UNSPECIFIED/UNKNOWN key handling consistent; GCP Cloud SQL description surfaced in service_detail (closes scanners-cloud/WR-04, WR-05, WR-22)
- [ ] **CLOUD-04**: Cache _read_json handles malformed JSON gracefully; scope_hash includes connector enable flags; profiles.py file verified complete and not truncated (closes scanners-cloud/WR-15, WR-16, WR-21)
- [ ] **CLOUD-05**: risk_engine.py naming/scoping resolved; profiles.py email/broker mutation guarded; profiles.py standard profile re-apply corrected; vault_connector VAULT_TOKEN env order safe; DB connector password empty-string default guarded; DB connector exception message stripped; AWS ThreadPoolExecutor import moved to module level; Vault _scan_pki_mounts PEM split hardened; evaluate_endpoints _postprocess_findings safe under iteration; _dedupe_findings ordering stable (closes scanners-cloud/WR-07..WR-12, WR-18, WR-19, WR-23, WR-24)

### INTEL — CBOM + Intelligence + Reports WARNINGs

- [ ] **INTEL-01**: PDF render blanket except narrowed to expected exceptions; Playwright resources cleaned up in finally block; PDF graceful degradation prints user-visible warning (closes cbom-intel-reports/WR-01, WR-02, WR-14)
- [ ] **INTEL-02**: motion_broker_weak_tls_count predicate uppercase consistent; ECDSA detection matches cert_pubkey_alg conventions; SAML weak detection handles mixed-case SHA-1; email/broker weak-cipher predicates unified (closes cbom-intel-reports/WR-03, WR-04, WR-10, WR-11)
- [ ] **INTEL-03**: SCORE_WEIGHTS documented/normalized; roadmap _why double-period artifact removed; roadmap mutation-after-yield documented; executive _build_interpretation guards score['score'] access; cipher KEX returns correct label for RSA non-PFS in TLS 1.2; confidence weight overrides pass through clamp and validation (closes cbom-intel-reports/WR-06, WR-07, WR-08, WR-09, WR-12, WR-13)

### QWARN — QRAMM + Compliance WARNINGs

- [ ] **QWARN-01**: compute_practice_score rejects out-of-range answers; Practice 1.1 Discovery score incorporates endpoint count; vuln_pct denominator guarded against zero; Maturity label ≥ 4.0 reachable or documented as intentional (closes qramm-compliance/WR-02, WR-04, WR-05, WR-06)
- [ ] **QWARN-02**: Evidence bridge date comparison is TZ-safe; synchronize_session idempotent; db.commit failures handled and logged; attach_context AttributeError logged not swallowed (closes qramm-compliance/WR-01, WR-03, WR-07, WR-08)
- [ ] **QWARN-03**: migration_advisor substring matching false positives reduced; _walk_json_for_alg_strings covers all ALG_KEYS strings; compliance weight 0.0 vs not-yet-covered disambiguated; model_meta.py adds is_qramm_model_stale helper; stale TODO Phase 50 comment removed (closes qramm-compliance/WR-09, WR-10, WR-11, WR-12, WR-13)

### APCL — API + CLI + Core WARNINGs

- [ ] **APCL-01**: quirk doctor _check_dashboard and _check_network return meaningful status; _check_db uses QUIRK_DB_PATH; _default_db_path uses deterministic selection (closes api-cli-core/WR-01, WR-02, WR-03)
- [ ] **APCL-02**: get_latest_scan ?scan_id= time-window is microsecond-safe; list_scans groups by parsed timestamp not formatted string; compute_overall_score multiplier validated server-side (closes api-cli-core/WR-04, WR-05, WR-06)
- [ ] **APCL-03**: routes/qramm read_session returns structured error on JSON corruption; _derive_dar_findings bare except replaced with logged exception; routes/qramm list_questions handles QRAMM_QUESTIONS schema drift gracefully (closes api-cli-core/WR-07, WR-08, WR-17)
- [ ] **APCL-04**: interactive _prompt_int handles EOF without infinite loop; exposure default validated not silently applied; setattr nmap injection replaced with ConnectorsCfg field; validate.py artifact list includes intelligence-{stamp}.json; qramm_cmd env override has try/except; routes/scan QUIRK_OUTPUT_DIR input validated; parse_target_tokens validates hostname format (closes api-cli-core/WR-10, WR-11, WR-12, WR-13, WR-14, WR-15, WR-16)

### REACT — React Frontend WARNINGs

- [ ] **REACT-01**: useScanList surfaces non-OK API responses as user-visible errors; executive body.detail coercion checked before access; print data-ready sentinel not set when QRAMM has errored; QRAMM submitError exposes actual error message (closes react-frontend/WR-02, WR-06, WR-07, WR-08)
- [ ] **REACT-02**: localStorage Theme value validated before cast; executive PDF download setTimeout revoke on unmount; ComplianceMapTab re-fetches on targeted dependency change only (closes react-frontend/WR-04, WR-05, WR-13)
- [ ] **REACT-03**: Certificate Subject CN regex handles RFC2253-escaped commas; CBOM Cytoscape registration cast replaced with proper typing; ScorecardTab Maturity Distribution width math and badge classes corrected (closes react-frontend/WR-09, WR-10, WR-11, WR-12)

### INFO — Code Quality

- [ ] **INFO-01**: Scanner-protocol INFOs: tls SSLContext downgrade commented; DNSSEC_ALG_MAP reserved algorithms 9 and 11 added; SHA1_INDICATORS made precise; fingerprint Host header corrected; _is_pfs/_is_weak deduplicated; Kerberos realm IPv4 detection hardened (closes scanners-protocol/IN-01..IN-06)
- [ ] **INFO-02**: CBOM/intelligence INFOs: PLATFORM_VERSION centralized; _extract_ssh_algorithms JSONDecodeError logged; trend analysis session fetch batched or paginated; evidence _PROTOCOL_KEYS completed; roadmap baseline governance logic documented; executive Migration Paths truncation indicator added; html_renderer dead timeframe branch removed; writer hosts_count falsy-hosts handled; IntelligenceReport dataclass used or removed (closes cbom-intel-reports/IN-01..IN-09)
- [ ] **INFO-03**: API/CLI INFOs: QRAMM endpoint types tightened from Dict[str, Any]; _FACES banner escape corrected; interactive TZ fallback uses IANA name; QRAMM magic numbers extracted to named constants; app.py closure capture corrected; db.py _ensure_*_columns helpers collapsed; targets.py CIDR host-list materialisation bounded (closes api-cli-core/IN-01..IN-07)
- [ ] **INFO-04**: React frontend INFOs: qramm-assessment tab count comment corrected; cbom extension registration error logged; findings/identity columns array memoized; useQRAMMSession seededRef reset on New Assessment; cbom compByAlg variance tracked; print createElement replaced with standard React pattern; useScanData propagates fetch URL into errors (closes react-frontend/IN-01..IN-07)

### LEDGER — Audit Closure

- [ ] **LEDGER-01**: AUDIT-TASKS.md has zero bare-open `[ ] open` rows — all 169 findings carry an explicit `[x] closed`, `[ ] deferred-*`, or `[ ] wont-fix` disposition with rationale

---

## Future Requirements

These items were considered but deferred beyond v4.9:

| Requirement | Reason |
|-------------|--------|
| HTML/PDF injection hardening (markdown in rendering pipeline) | Separate attack surface shape from v4.8 REPORT-SAN-01 (markdown-only); deferred per v4.8 D-06 |
| migration_planner.py deletion | Dead code; wont-fix per audit (scanners-cloud/CR-01); removal in v5.2 tech-debt sweep |
| CBOM FIPS 140-3 CMVP attestation (certified flag) | Deferred from Phase 52 D-01; requires CMVP attestation data feed |
| S/MIME message-content scanning | Agentless model cannot inspect mailbox content |
| Windows AD CS live connector | Complex Kerberos/NTLM auth; stub deferred to v2 |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| New scanner surfaces (additional protocols, cloud providers) | v4.9 is correctness-only; new coverage in future milestone |
| Dashboard feature additions | Operating model features shipped in v4.8; v4.9 is fix-only |
| SaaS platform work | Future milestone |
| v5.x dead-code sweep (migration_planner, risk_engine rename) | Explicitly deferred to v5.2 per audit disposition |

---

## Traceability

| Requirement | Phase |
|-------------|-------|
| (populated by roadmapper) | — |

---

*Last updated: 2026-05-14 — v4.9 Audit Depth requirements defined*

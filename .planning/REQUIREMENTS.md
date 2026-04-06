# Requirements: QU.I.R.K. — v4.1 Foundation Polish

**Defined:** 2026-04-06
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours.

## v4.1 Requirements

Requirements for the Foundation Polish milestone. Each maps to a roadmap phase.
No new user-visible features — exclusively closes P0/P1 correctness and trust gaps.

### CLI Correctness

- [ ] **CLI-01**: User's generated config has correct field names after `quirk init` (no startup crashes on first run) — BACK-40
- [ ] **CLI-02**: User can run `quirk scan` to initiate a scan from the CLI — BACK-41
- [ ] **CLI-03**: User's generated config contains no `[owner]` placeholder after `quirk init` — BACK-47
- [ ] **CLI-04**: User sees consistent version number (4.x) across CLI output, reports, and CBOM stamps — BACK-48

### Interactive Mode

- [ ] **INTER-01**: Interactive mode detects local timezone automatically without prompting — BACK-27
- [ ] **INTER-02**: Interactive mode does not prompt for SNI (hardcoded True for FQDN targets) — BACK-28
- [ ] **INTER-03**: Interactive mode does not prompt for Windows ADCS (non-functional feature removed) — BACK-29
- [ ] **INTER-04**: Interactive mode correctly labels AWS and Azure as implemented connectors with credential requirement warnings — BACK-38
- [ ] **INTER-05**: User can enable JWT, container, and source scanners from interactive mode — BACK-32
- [ ] **INTER-06**: Interactive mode offers scan profile selection (quick/standard/deep) instead of raw timeout/concurrency fields — BACK-30
- [ ] **INTER-07**: Interactive mode uses a consulting-grade TLS port default list (LDAPS 636/3269, IMAPS 993, POP3S 995, SMTPS 465, K8s 6443, Docker TLS 2376, DB ports 5432/3306/1433, Vault 8200) without prompting — BACK-33
- [ ] **INTER-08**: Interactive mode presents prompts in targets-first order (targets → options → output → metadata) — BACK-36
- [ ] **INTER-09**: `enable_windows_adcs` dead field removed from interactive mode and generated configs — BACK-39
- [ ] **INTER-10**: Interactive mode presents a single coherent data classification prompt (consolidates overlapping `data_classification` and `data_types` prompts) — BACK-31

### Scoring Correctness

- [ ] **SCORE-01**: Calibration profile (`lenient/balanced/strict`) is applied to weight multipliers in `compute_readiness_score()` — BACK-43
- [ ] **SCORE-02**: `validate.py` checks for artifacts that `write_reports()` actually produces (no permanent validation failure on every scan) — BACK-44
- [ ] **SCORE-03**: `migration_advisor.py` finding pattern strings match `risk_engine.py` finding titles so legacy TLS migration recommendations surface correctly — BACK-46
- [ ] **SCORE-04**: Dashboard passes the scan-time profile kwarg to `compute_readiness_score()` so dashboard and CLI report scores match — BACK-60

### Code Hygiene

- [ ] **HYGN-01**: Legacy `quirk/connectors/` stub directory (`aws_stub.py`, `azure_stub.py`, `windows_adcs_stub.py`) removed from codebase — BACK-37
- [ ] **HYGN-02**: `cfg.scan` `timeout_seconds` and `concurrency` mutations in `run_scan.py` wrapped in `try/finally` for safe config restore on exception — BACK-45
- [ ] **HYGN-03**: Orphaned `quirk/reports/scorecard.py` deleted (never called in production) — BACK-61
- [ ] **HYGN-04**: All 11 Nyquist VALIDATION.md files (9 stale + 2 missing) updated to reflect actual phase completion status — BACK-62

## Future Requirements

Deferred to v4.2+ scanner expansion milestones.

### Identity Crypto (v4.2)

- Kerberos etype enumeration (AS-REQ probe, RC4/AES detection)
- SAML/OAuth metadata scanning (signing cert key type, algorithm declarations)
- DNSSEC algorithm audit (DNSKEY/DS records via dnspython)
- Identity chaos lab (Samba DC + Keycloak/SimpleSAMLphp)

### Data at Rest (v4.3)

- Database encryption detection (PostgreSQL, MySQL, RDS)
- S3/Blob/GCS storage encryption audit
- Kubernetes secrets-at-rest inspection (etcd EncryptionConfiguration)
- HashiCorp Vault live connector (transit keys, PKI mounts, auth methods)

### Data in Motion (v4.4)

- Email protocol scanning (SMTP/STARTTLS, IMAP, POP3 → sslyze handoff)
- Message broker TLS detection (Kafka, RabbitMQ, Redis, AMQP)

### API Depth (v4.5)

- OpenAPI/Swagger spec analysis (securitySchemes, unauthenticated endpoints)
- Bearer token interception and algorithm analysis
- Active REST API crypto posture probing

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dashboard UI enhancements (config panel, multi-scan nav, heatmap, themes) | Deferred to dedicated dashboard/UX milestone |
| Narrative report onboarding guide | Deferred to documentation milestone |
| Trend analysis across scan sessions | Natural companion to multi-scan navigation; deferred |
| Scheduled/continuous scanning | Significant operational mode change; v5.x |
| BACK-34 (SSH port prompt), BACK-35 (tls_enum_mode surface) | P2/P3; deferred to v4.1 capacity overflow or v4.2 |
| Windows ADCS scanner implementation | Full implementation deferred; stub removal is in scope |
| GCS cloud connector (new provider) | Considered for v4.3 Data at Rest; not in v4.1 |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 12 | Pending |
| CLI-02 | Phase 12 | Pending |
| CLI-03 | Phase 12 | Pending |
| CLI-04 | Phase 12 | Pending |
| INTER-01 | Phase 13 | Pending |
| INTER-02 | Phase 13 | Pending |
| INTER-03 | Phase 13 | Pending |
| INTER-04 | Phase 13 | Pending |
| INTER-05 | Phase 13 | Pending |
| INTER-06 | Phase 13 | Pending |
| INTER-07 | Phase 13 | Pending |
| INTER-08 | Phase 13 | Pending |
| INTER-09 | Phase 13 | Pending |
| INTER-10 | Phase 13 | Pending |
| SCORE-01 | Phase 14 | Pending |
| SCORE-02 | Phase 14 | Pending |
| SCORE-03 | Phase 14 | Pending |
| SCORE-04 | Phase 14 | Pending |
| HYGN-01 | Phase 15 | Pending |
| HYGN-02 | Phase 15 | Pending |
| HYGN-03 | Phase 15 | Pending |
| HYGN-04 | Phase 15 | Pending |

**Coverage:**
- v4.1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 — traceability table populated after roadmap creation*

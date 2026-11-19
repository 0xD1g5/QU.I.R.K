# Requirements: QU.I.R.K. — v5.29 Surface Agreement

**Defined:** 2026-11-15
**Core Value:** A consulting-grade cryptographic inventory whose findings a consultant can hand to a
client without qualification. That includes every number the tool shows being correct on every
surface that shows it.

**Milestone goal:** for any scan, every surface (dashboard, report, history/trends/compare, CBOM,
notify) shows the same findings, counts and score, and connector targets cannot get past the trust
gate.

**Operator scoping decisions (2026-11-15 kickoff, after the PM review of `.planning/LEDGER.md`):**
- Scope: four themed phases plus a security trust-gate phase (Phases 236–240).
- `A0527:PUBREPO-LAB-KEYS` is deferred to v5.30 and re-rated P0 -> P1 (recorded in the ledger).
- Research was skipped: every item is a reproduced or code-read defect with a ledger row, most with
  a todo naming file:line and a candidate fix. Per-phase research still runs in `/gsd-plan-phase`.
- The milestone-boundary version-drift audit was clean (all surfaces read 5.28.2).

**Public-repo note:** ROADMAP.md, PROJECT.md, STATE.md and LEDGER.md are tracked in a public repo.
Phase 239's public wording stays generic ("connector target trust-gate hardening"). Its detail lives
in the two `999.136`-owned todos; nothing from `.planning/security-embargo/` may be copied into a
tracked file.

---

## v5.29 Requirements

### Score agreement (XSURF)

- [x] **XSURF-09**: Legacy TLS gets the same severity on the dashboard and in the report for the same
  endpoint. Source: `261015-xsurf-legacy-tls-severity-diverges-dashboard-vs-report`.
- [x] **XSURF-10**: "Weak cipher suites enabled" has a report counterpart with the same severity as the
  dashboard. Source: `261015-xsurf-weak-cipher-suites-dashboard-high-has-no-report-counterpart`.
- [x] **XSURF-11**: An undersized ECDSA key gets the same severity on the dashboard and in the report.
  Source: `261015-xsurf-undersized-ecdsa-report-high-dashboard-medium`.
- [x] **XSURF-12**: Container crypto-library EOL findings appear on the dashboard as well as in the
  report. Source: `261015-xsurf-container-library-eol-findings-are-report-only`.
- [x] **XSURF-13**: The severity-divergence gate and the Slack/Trends drift check read derived
  severities, so a new dashboard/report divergence fails CI. Source:
  `261015-xsurf-dashboard-and-report-pipelines-still-diverge-gate-blind` (P1; WR-01, WR-02).
- [x] **XSURF-14**: For the same run, the dashboard headline score equals the job report's score on a
  core-lab scan. Source: `261108-headline-score-divergence`.

### Count truth (COUNT)

- [x] **COUNT-01**: Scan History's High/Medium/Low counts include every finding, TLS-derived ones too.
  Source: `261110-scan-history-trends-compare-count-endpoint-severities` (P1).
- [x] **COUNT-02**: Trends' new-finding counts include TLS-derived findings. Source: same row.
- [x] **COUNT-03**: Compare lists the added and removed findings between two scans that differ.
  Source: same row.
- [x] **COUNT-04**: The Executive Skipped badge lists every skipped connector, including those after a
  connector row with no error category. Source: `261109-executive-skipped-badge-drops-null-category-entries`
  (P1, v5.28.2 audit F1).
- [x] **COUNT-05**: Export PDF shows the skip reasons whenever skips lowered the score. Source:
  `261109-dashboard-export-pdf-omits-coverage-skip-reasons` (v5.28.2 audit F2).
- [x] **COUNT-06**: An in-progress scan is marked as running and is not published as the latest scan.
  Source: `261110-running-scan-published-as-latest`.
- [x] **COUNT-07**: Trends and notify show a full JWT/SAML/DNSSEC connector outage. Source:
  `261107-trends-hide-full-connector-outage` (B-WR-07).

### Identity and certificate findings (IDENT, DETECT)

- [x] **IDENT-05**: JWKS keys using `alg: none`, RSA-1024 or HS256 produce a finding on the dashboard
  and in the report, and lower the score. Source: `261110-jwks-weak-alg-no-finding-no-score` (P1).
- [x] **IDENT-06**: The Identity page shows JWT results whenever JWT scanning ran. Source:
  `261110-jwt-weakness-absent-from-identity-page`.
- [x] **IDENT-07**: A SAML URL that answers with something other than SAML metadata reads as skipped
  or failed with a named reason, not `ran`; the JWT connector is measured for the same defect and
  fixed if affected. Source: `261108-saml-non-metadata-answer-reads-ran` (P1, disclosed S8b).
- [x] **DETECT-06**: An mTLS-required endpoint is reported as MTLS_REQUIRED when the handshake is TLS
  1.3 and the rejection comes at the HTTP layer (regression; UAT-4-11 PASS 2026-04-17). Source:
  `261110-reg-mtls-required-undetected-under-tls13`.
- [x] **DETECT-07**: A SHA-1-signed TLS certificate produces a finding. Source:
  `261110-sha1-cert-signature-no-finding`.

### Trust gate (TRUST)

- [x] **TRUST-01**: A scalar `*_targets` value for any connector loads as a one-element list, with the
  field set enumerated from `ConnectorsCfg` at run time, so the trust gate checks exactly what the
  scanner scans. Source: `261023-detect-scalar-connector-targets-bypass-trust-gate` (P1, owner 999.136).
- [x] **TRUST-02**: LDAP-based connectors never follow a referral to a host the trust gate has not
  checked; every `ldap3.Server`/`Connection` in `quirk/` is checked by a run-time source scan. Source:
  `261023-detect-ldap-referrals-and-zone-id-literals-in-other-connectors` (P1, owner 999.136).
- [x] **TRUST-03**: The trust gate fails closed on an IP literal that is not ASCII. Source: same row.

### Scan confidence (SCORE)

- [ ] **SCORE-11**: A scan whose probe error rate is above 50% reports confidence below 60
  (regression; UAT-8-02 PASS 2026-08-27). Source: `261110-reg-confidence-ignores-high-scan-error-rate`.

### Release (REL)

- [ ] **REL-13**: 5.29.0 is tagged and published to PyPI and GitHub Releases, and UAT-1-02 passes on
  the published wheel.
- [ ] **REL-14**: The CHANGELOG and README known-defect wording for every item fixed in this milestone
  is removed in 5.29.0 (the 5.28.0 score-divergence disclosure is withdrawn only for what is fixed).
- [ ] **REL-15**: Every date-gated catalog is green at release time, each re-verified against its
  `source_url` (hw_cve trips 2026-11-29; pqc_deadlines and snmp_meta 2026-12-02). No bare date bumps.

## Future Requirements (v5.30 candidates)

- Connector, source/container, operator-guidance and packaging clusters: `999.126`, `999.127`,
  `999.128`, `999.129`.
- Chaos-lab fixtures diverge from their oracles: `261111-chaos-lab-fixtures-diverge-from-oracles` and
  its members; `A0527:PUBREPO-LAB-KEYS` (deferred, P1).
- Azure Key Vault endpoints, Windows `install.ps1` sensor config, the Semgrep `p/cryptography` ruleset.
- The remaining `261015-xsurf-*` rows not listed above (four are DEFERRED by operator decision at the
  Phase 228 close).

## Out of Scope

| Item | Reason |
|------|--------|
| Net-new scanner surfaces | PM sequencing rule: drain known defects first |
| `A0527:PUBREPO-LAB-KEYS` | Deferred by operator 2026-11-15; belongs with the lab-fixtures cluster |
| Score-model changes beyond the divergence fixes | v5.28 moved to scoring 4.0; v5.29 makes surfaces agree, it does not re-weight |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| XSURF-09 | Phase 236 | Complete |
| XSURF-10 | Phase 236 | Complete |
| XSURF-11 | Phase 236 | Complete |
| XSURF-12 | Phase 236 | Complete |
| XSURF-13 | Phase 236 | Complete |
| XSURF-14 | Phase 236 | Complete |
| COUNT-01 | Phase 237 | Complete |
| COUNT-02 | Phase 237 | Complete |
| COUNT-03 | Phase 237 | Complete |
| COUNT-04 | Phase 237 | Complete |
| COUNT-05 | Phase 237 | Complete |
| COUNT-06 | Phase 237 | Complete |
| COUNT-07 | Phase 237 | Complete |
| IDENT-05 | Phase 238 | Complete |
| IDENT-06 | Phase 238 | Complete |
| IDENT-07 | Phase 238 | Complete |
| DETECT-06 | Phase 238 | Complete |
| DETECT-07 | Phase 238 | Complete |
| TRUST-01 | Phase 239 | Complete |
| TRUST-02 | Phase 239 | Complete |
| TRUST-03 | Phase 239 | Complete |
| SCORE-11 | Phase 240 | Pending |
| REL-13 | Phase 240 | Pending |
| REL-14 | Phase 240 | Pending |
| REL-15 | Phase 240 | Pending |

---
*Requirements defined: 2026-11-15*

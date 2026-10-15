# Requirements: QU.I.R.K. — v5.28 Score & Finding Truth

**Defined:** 2026-10-15
**Core Value:** A consulting-grade cryptographic inventory whose findings a consultant can hand to a
client without qualification. That includes every number the tool shows being correct on every
surface that shows it.

**Milestone goal:** Every number and finding QU.I.R.K. shows a client is correct and agrees across
surfaces. The readiness score stops rewarding scan depth, findings that should fire do fire, and
QRAMM's scoring surfaces work.

**Sequencing constraint:** the P2b work (SCORE-08, SCORE-09) is instrument-first: no fix shape is
chosen before the third measurement instrument exists. It must not share a phase with a release tag
(212 §8: re-scoring inside a tag freezes an unmeasured number), and this milestone has no release
phase.

---

## Boundary verifications — read these before planning

Checked against live source and the backlog at the milestone boundary (2026-10-15), not against
HORIZON prose:

1. **P2b is still open and still numeric.**
   `tests/test_score_properties.py::test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints`
   is `xfail(strict=True)` and registered as `known_open_defect` in `tests/skip_registry.py:130`.
   `assessable_endpoint_count` (`quirk/intelligence/evidence.py:161`, incremented at `:257`) grows with scan depth
   and is the endpoint denominator (the `999.120` IDEA file cites `:154`/`:250`, which have drifted). Phase 212's decision record (`.planning/milestones/v5.25-phases/212-*`)
   recommended none of its three candidates.
2. **Each defect below has a pending todo with a source-cited reproduction.** The todo is the
   evidence. A requirement here closes its todo, and the todo moves to `todos/completed/` with the
   closing commit cited.
3. **QRAMM Cause A is an open product decision**, recorded in
   `.planning/todos/pending/261002-qramm-compliance-map-scores-never-populate.md`. The operator
   deferred it to the QRAMM phase discuss (2026-10-15). Cause B (no refetch) is a bug whatever the
   Cause A answer is.
4. **117 of the 118 `doc224` todos have no owner field.**
   `tests/test_backlog_reconciliation_gate.py::test_no_pending_todo_points_at_a_closed_owner` cannot
   police a todo with no owner, so the pool is invisible to every gate.
5. **W15 predates the milestone.** `quirk/dashboard/api/app.py` mounts only `/assets` (`:161-167`)
   plus five root files (`:48`). The built CSS requests `/fonts/JetBrainsMono[wght].ttf`, which
   falls through to the SPA catch-all and returns `index.html`, even though the font files are built into `quirk/dashboard/static/fonts/`. Only the route is missing.

---

## v5.28 Requirements

### Score-depth dilution (SCORE)

- [ ] **SCORE-08**: A third measurement instrument for scan-depth dilution exists and is recorded
      before any fix is chosen. It is independent of the two Phase 212 used, and it measures, on the
      calibration ladder, how much the readiness score moves when only healthy endpoints are added.
      Effort is decided by its result, not assumed (`999.120`, spike).
- [ ] **SCORE-09**: Observing more healthy endpoints no longer raises the readiness score:
      `test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints` passes without `xfail`
      and its skip-registry row is removed. All five calibration-ladder rungs are re-measured after
      the change and recorded beside the pre-change values, and the CLI report and dashboard agree
      on the new score for the same scan.

### Cross-surface score parity (XSURF)

- [ ] **XSURF-05**: A certificate expiring within 30 days gets the same severity on the dashboard
      and in the report, so the headline score matches on both surfaces (todo
      `261013-doc224-cert-expiry-severity-diverges-dashboard-vs-report`).
- [ ] **XSURF-06**: Dashboard-only certificate/TLS findings on S/MIME, AD CS, Vault and database
      rows no longer move the dashboard's headline score, ceiling or lift badges away from the report
      (todo `261013-doc224-dashboard-only-findings-diverge-headline-and-lifts`).
- [ ] **XSURF-07**: Trend timeline, multi-sensor merge and per-segment scores apply the CRITICAL/HIGH
      consequence ceilings, the same as the headline score (todo
      `261013-doc224-trend-and-merge-scores-skip-consequence-ceilings`).
- [ ] **XSURF-08**: A mail port that refused the connection is not counted as plaintext, so closed
      mail ports stop lowering the Data in Motion subscore on a default scan (todo
      `261013-doc224-email-refused-ports-counted-as-plaintext`).

### Finding and state correctness (FIND)

- [ ] **FIND-11**: Remediation closure states follow the documented model end to end. A detected
      finding is written `open` (not read as `not_observed`), a closure lands on the scan that
      observed it closed (not the prior scan), and plaintext HTTP can close (todo
      `261013-doc224-closure-states-open-never-written-closed-on-prior-scan`).
- [ ] **FIND-12**: Drift notifications compare the two newest scan runs, never a scan with itself
      (todo `261013-doc224-notifier-session-key-ignores-scan-run-id`).
- [ ] **FIND-13**: `sensor merge` and `/api/merge/latest` keep every endpoint from each sensor's
      latest push, not one row per sensor (todo `261013-doc224-sensor-merge-keeps-one-endpoint-per-sensor`).

### Findings that never fire (DETECT)

- [ ] **DETECT-01**: `--inventory-code-signing` finds code-signing-EKU certificates among those the
      TLS phase captured in a real scan, proven by a test that runs the real TLS capture rather than
      an injected fixture (todo `261013-doc224-codesign-tls-eku-path-dead-in-real-scans`).
- [ ] **DETECT-02**: Kerberos etype enumeration runs against a KDC that requires pre-authentication
      with the pinned impacket (todo `261013-doc224-kerberos-preauth-required-read-as-no-preauth`).
- [ ] **DETECT-03**: `--auth-*` credentials reach the JWKS target, and the redaction applies only to
      logged output, proven by a wire-level test asserting the received headers (`999.125` item 1).
- [ ] **DETECT-04**: `--auth-basic` sends a correctly base64-encoded `Authorization: Basic` header,
      and its help text and `docs/configuration.md` row match (`999.125` item 2).
- [ ] **DETECT-05**: A bearer token declaring `alg: none` produces a CRITICAL finding in a scan, with
      its score treatment decided and recorded in the phase (`999.125` item 3).

### QRAMM (QRAMM)

- [ ] **QRAMM-17**: After a successful Calculate Score, the compliance map tab refetches and shows
      the new rows without a remount, and the existing no-refetch-loop test stays green (todo `261002`
      Cause B).
- [ ] **QRAMM-18**: A dimension with no answers shows as "Not assessed" on the scorecard and is not
      counted as level 1 in the Maturity Distribution (todo `261002` scorecard flaw).
- [ ] **QRAMM-19**: The compliance map's treatment of manually assessed SGRM, DPE and ITR is decided
      by the operator in the phase discuss (shown and marked self-assessed, or excluded with a clearer
      explanation) and implemented on every surface that reads those rows, including the print/PDF
      QRAMM page (todo `261002` Cause A).
- [ ] **QRAMM-20**: `quirk qramm --help`, `quirk doctor --help` and `quirk cve --help` print their
      own usage and exit 0 without running anything, an unknown action is an error, and
      `cve status --format` is listed (todo `261012-doc224-doctor-qramm-cve-do-not-implement-help`).

### Post-launch visible fixes (POLISH)

- [ ] **POLISH-01**: The dashboard serves its bundled JetBrains Mono font: `/fonts/*` returns the
      font file, not `index.html`, and a test probes it (audit W15).
- [ ] **POLISH-02**: Every runtime `quirk-scanner[extra]` install hint is shell-safe when pasted into
      zsh, and the guard test covers every hint form, not only bare `quirk[` (todo
      `261015-install-hints-unquoted-and-guard-scope`, WR-01..03).
- [ ] **POLISH-03**: The HTML/PDF report header no longer renders the old electric-blue `QU.I.R.K.`
      wordmark; it follows `BRAND-GUIDELINES.md` (todo `261003-brand-identity-non-dashboard-residue`,
      report-header leg).
- [ ] **POLISH-04**: Every README link resolves on the PyPI project page (todo
      `261014-readme-relative-links-dont-resolve-on-pypi`).

### Todo ownership (OWN)

- [x] **OWN-01**: Every pending `doc224` todo names a live owner (a v5.28 requirement or a HORIZON
      backlog row) or is closed with evidence, and the todo -> owner gate fails on a `doc224` todo
      with no owner. This includes the four high-priority todos outside this milestone's fixes: Azure
      Key Vault keys, the Semgrep `p/cryptography` 404, the CMVP-refresh error hints, and the Windows
      `install.ps1` sensor identity.

## Future Requirements

Deferred from this milestone with an owner:

- **`999.124`** sensor payload signature verification (P2, M, half-day spike). Better placed beside
  the next sensor work.
- **`999.121`** GUI-first gaps (bare `quirk` opens the dashboard; 11 CLI-only subcommands without an
  API route). Raised at the PM review as the operator asked; not scoped.
- **`999.123`** reference docs generated from source (the DOC-04 4.0% residual).
- **`999.118`** a11y design calls, **`999.119`** CI/lab hygiene, **`999.122`** GHCR/Homebrew,
  `999.104`, `999.107`, `999.110`, `999.105`, `999.112`: owned by HORIZON ledger rows.
- **CBOM minimum-elements guidance** (CISA/NIST, due about 2026-12-19 under EO 14412): watch item,
  not scope.

## Out of Scope

| Feature | Reason |
|---------|--------|
| A release tag inside this milestone | P2b rescales every ladder rung; a tag must not freeze an unmeasured number (212 §8). The next release follows a milestone that has re-measured the ladder |
| Fixing the four high-priority `doc224` todos outside this scope | Operator accepted them as owner-assignment only (OWN-01) at the 2026-10-15 kickoff |
| Rewriting reference docs by hand | `999.123` owns the durable fix (generate from source) |
| New scanner families or connectors | This is a correctness milestone; net-new detection waits for the next capability cycle |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCORE-08 | Phase 233 | Pending |
| SCORE-09 | Phase 234 | Pending |
| XSURF-05 | Phase 228 | Pending |
| XSURF-06 | Phase 228 | Pending |
| XSURF-07 | Phase 228 | Pending |
| XSURF-08 | Phase 228 | Pending |
| FIND-11 | Phase 229 | Pending |
| FIND-12 | Phase 229 | Pending |
| FIND-13 | Phase 229 | Pending |
| DETECT-01 | Phase 230 | Pending |
| DETECT-02 | Phase 230 | Pending |
| DETECT-03 | Phase 230 | Pending |
| DETECT-04 | Phase 230 | Pending |
| DETECT-05 | Phase 230 | Pending |
| QRAMM-17 | Phase 231 | Pending |
| QRAMM-18 | Phase 231 | Pending |
| QRAMM-19 | Phase 231 | Pending |
| QRAMM-20 | Phase 231 | Pending |
| POLISH-01 | Phase 232 | Pending |
| POLISH-02 | Phase 232 | Pending |
| POLISH-03 | Phase 232 | Pending |
| POLISH-04 | Phase 232 | Pending |
| OWN-01 | Phase 227 | Complete |

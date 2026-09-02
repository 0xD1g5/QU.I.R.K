# Changelog

All notable changes to QU.I.R.K. (Quantum Infrastructure Readiness Kit) are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

<!-- towncrier release notes start -->

## [5.18.0] - 2026-09-02

The first release since 5.15.0 (2026-08-26). Two milestones of user-visible fixes — v5.16 Review
Drain & Gate Integrity (Phases 164-171) and v5.17 Defect Drain (Phases 172-176) — were developed,
merged, and archived but never tagged; both ship here as one release rather than being
retro-published separately, since their content was never a separable source-tree state. This
release also includes Phase 177's own release-toolchain repair.

### Added

- **UAT corpus integrity, permanently enforced** (v5.16, UATREC-03/UATREC-04) — a standing gate
  (`tests/test_uat_zero_undispositioned_gate.py`) keeps all 666 UAT case headings dispositioned
  going forward; the corpus itself went from 377 undispositioned cases to zero.
- **First-run correctness** (v5.16, FIRSTRUN-01/02/03) — the command the dashboard's empty state
  instructs a new user to run now exists and works; a mistyped `--targets` argument fails with a
  coded error (`TARGET-001`/`TARGET-002`) instead of an uncaught `FileNotFoundError` traceback.
- **Coded fuzzing safety** (v5.17, SAFE-01/SAFE-02) — `--fuzz` hard-aborts before issuing any
  request when stdin is non-interactive, printing a coded error and exiting non-zero; `--fuzz-budget`
  is enforced at its documented 500-request ceiling rather than only the 50 default.

### Fixed

- **Three screen-reader-blocking accessibility violations** (v5.16, A11Y-02) — icon-only radix
  dropdown triggers now carry discernible labels; all 291 previously-baselined axe violations
  carry a recorded impact level and WCAG reference instead of accumulating silently (A11Y-01).
- **A CRITICAL evidence-injection vulnerability** (v5.16, CR-01, found during Phase 169 code
  review) — a newline-splicing defect in `scripts/uat_disposition_apply.py`'s evidence-field
  validation could fabricate a fully-`[x] PASS` UAT case past all three anti-fabrication guards at
  once. Fixed in two layers, with 8 regression tests proven to fail against the pre-fix code.
- **A macOS `fork()`-after-`Network.framework` SIGSEGV** affecting subprocess-spawning CLI tests
  under full-suite load (v5.16, GATE-03) — every CLI-runner test file now goes through a shared
  `run_fork_safe()` helper, forward-locked by an AST-based gate requiring `close_fds=False`.
- **Raw target URL disclosure in spec-parsing errors** (v5.17, SAFE-03) — `SpecParsingError` and
  its sibling error paths now report a redacted URL preview, never the full raw target.
- **Dashboard score disagreed with the CLI score under non-default score profiles** (v5.17,
  DASH-06) — a dashboard-launched scan's `list_scans` call site now passes the same `calibration`
  its sibling call site already did, so `strict`/`balanced`/`lenient` dashboard scores match their
  CLI scorecards.
- **SSH scanner silently degraded to banner grabs** (v5.17, TRIAGE-176-03, found during the
  Phase 176 chaos-lab re-run) — `_run_ssh_audit` invoked `ssh-audit` with host and port as two
  positional arguments when the tool accepts one `host:port` target, so the invocation exited 2
  with empty stdout and every SSH scan since the ssh-audit integration shipped had silently lost
  `ssh_audit_json` (and the algorithm data it feeds to the CBOM, QRAMM evidence bridge, hardware
  scanner, and dashboard). Fixed with an argv-asserting regression test; live-verified against the
  chaos lab (0 -> 7218 bytes, 30 algorithms classified).
- **Release toolchain repair** (Phase 177, this release) — a package-name-migration residue left
  three distributions (`quirk` 4.4.0, `qu-i-r-k` 4.10.0, plus an orphan Homebrew-global `quirk`
  4.0.0 editable install) all claiming the `quirk` import package alongside the canonical
  `quirk-scanner`, so `importlib.metadata.packages_distributions()['quirk']` could resolve to a
  stale distribution. Purged, with a new regression guard
  (`tests/test_version.py::test_single_distribution_provides_quirk`) asserting exactly one
  distribution claims `quirk` going forward.

### Changed

- **`run_stats.timings_sec` no longer carries a stale key for a scanner phase that did not run**
  (v5.17, SCOPE-02) — e.g. `broker_scanning` no longer persists with a nonzero value when the row
  count is 0.
- **CHANGELOG and cross-phase references backfilled and repaired** (v5.16, TRACE-01..07) — v5.9
  through v5.14 each gained an entry, v5.13/v5.14 honestly recorded as developed-but-never-released
  rather than silently absent, and 22 stale sibling-phase references were rewritten to their real
  archived paths.
- **Nine UAT cases corrected where the product was right and the case was wrong** (v5.17,
  CASEFIX-01..05) — including `UAT-6-08`'s cryptographically-incorrect claim that Ed25519 is
  quantum-vulnerable, and the `UAT-1-02` false FAIL caused by an unsatisfiable `uat_runner.py`
  version-string match.

## [5.15.0] - 2026-08-26

Lifecycle Tail Drain — Phases 161-163. Note that 5.9 through 5.14 were developed but
never released: their tags were two-component (`v5.9`, `v5.13`, `v5.14`), which never
matched the `v*.*.*` trigger glob in `release.yml`, so no release workflow ran. 5.15.0 is
the first published release since 5.12.0 and carries that accumulated work.

### Added

- **Hardware lifecycle notifications** (Phase 161, HWLC-14) — opt-in email/webhook dispatch
  when a monitored device drifts tier or crosses an EOL/EOS boundary. Gated behind
  `notify_on_hardware_lifecycle` on `NotifyCfg`, reusing the Phase 101 dispatch foundation.
  The trigger is a never-raising advisory hook on `persist_and_reconcile()`'s success path —
  a notification failure can never fail a scan.
- **Vendor PQC status trend surfacing** (Phase 161, HWLC-19) — catalog-level vendor PQC trend
  data rendered in the CLI technical markdown report, the HTML report, the DOCX report, and a
  new section on the `/hardware` dashboard tab, with cross-surface caption parity enforced by
  test. Advisory-only: never contributes to the readiness score, guarded mechanically by
  `vendor-trend-advisory-guard.test.ts`.
- **Scheduled check-in re-probes** (Phase 162, HWLC-20) — `quirk schedule add --check-in`
  puts HWLC-13's lightweight re-probe on a recurring cadence. `--target` becomes optional for
  check-ins (stored as a `(known fleet)` sentinel) and stays mandatory for profile scans. The
  `/schedules` page marks check-in jobs with an advisory chip.
- **Batch-granular discovery resume** (Phase 163, DISC-08) — the chunked discovery loop now
  writes a `discovery:batch-N` checkpoint plus a per-batch cache payload after each completed
  batch, and skips those batches on `--resume-scan-id`. A /16 interrupted at batch 60 of 64
  previously re-probed all ~65,000 hosts on resume; it now re-probes only the ~4,000 in the
  unfinished batches. No new table and no schema change — the existing checkpoint mechanism is
  reused with a structured stage string. Requires no `--cache` flag.

### Fixed

- **SCHED-02: every default-profile schedule died at argparse** (Phase 162) —
  `_dispatch_schedule()` fell back to `schedule.profile or "balanced"`, a *score* profile value
  that `run_scan --profile` rejects. Any CLI-created schedule without an explicit profile was
  recorded "failed" with no reason recorded. Survived three months because the dispatched argv
  was only reachable through `Popen`; `build_scan_argv()` was extracted as a pure function so it
  can be asserted directly. `quirk schedule list` also stopped displaying "balanced" for a null
  profile — a value that is neither valid nor what would actually run.
- **Resumed discovery scans under-reported their own coverage** (Phase 163) — the per-batch
  cache stored only discovered `ports`, so a skipped batch lost the per-host "undetermined"
  ADVISORY records from its liveness pre-pass. A resumed scan reported only the coverage of the
  batches it re-probed live: measured on a 4094-host range, a 3-batches-cached resume reported
  1,014 hosts scanned against 4,034 for an uninterrupted reference. Discovered endpoint counts
  were correct throughout, so the report did not look broken — it looked like a completed
  smaller engagement. `Confidence` is coverage-derived and was depressed by it. Found by human
  UAT, fixed in-phase via a `liveness` key in the batch cache payload.

### Changed

- `operators-guide.md` gains section 13, "Discovery Batch Resume", covering the resume
  mechanism, disk cost, cache data-handling class, and the unchanged-target-scope limitation.

## [5.14.0] - 2026-08-19

Hardware Lifecycle Tail — Fleet Coverage & Forecasting (Phases 157-160). **Developed but never
released**: like v5.13, this milestone's tag (`v5.14`) was two-component, which never matched the
`v*.*.*` trigger glob in `release.yml`, so no release workflow ran and no PyPI publish happened.
The last version actually published to PyPI remains 5.12.0 (2026-08-14); `pyproject.toml` stayed
at `5.12.0` throughout. The code shipped to `main` and is in use — only the release step never
fired. 5.15.0 was the first published release since 5.12.0 and carries this work forward.

### Added

- **Drift-event retention purge** (Phase 157, HWLC-16) — a table-wide calendar-cutoff sweep bounds
  `hardware_drift_events` growth via a new `hardware_drift_event_retention_days` config field.
- **EOL/Tier Forecast narrative** (Phase 157, HWLC-18) — a hedged, catalog-cited 12-month EOL/tier
  forecast renders in the CLI markdown report, the HTML report, and the DOCX report, backed by a
  new `quirk/scanner/hardware_forecast.py` engine wired behind the advisory-only firewall.
- **`persist_and_reconcile()` shared chokepoint** (Phase 158) — sensor-scanned segments now reach
  the console's drift history exactly like console-direct scans; both `run_scan.py` persist sites
  and the sensor `_ingest_envelope()` path delegate onto one function, and `hardware_devices` was
  added to the sensor push envelope so sensor-side hardware findings round-trip into drift history.
- **Lightweight check-in re-probe mode** (Phase 159, HWLC-13) — `--check-in` re-probes only
  already-known devices without running a full scan.
- **Vendor-level PQC catalog status tracking** (Phase 160) — a new event-sourced table tracks
  vendor PQC catalog status changes over time; a single-host confirmation-gate domination design
  flaw was caught by research before implementation began. The `GET /api/hardware/vendor-trends`
  presentation layer was intentionally left unwired in this milestone per locked scope (wired in
  Phase 161's HWLC-19 in the subsequent v5.15.0 release).

### Fixed

- A session-rollback data-loss bug in Phase 158's persist path and a dashboard surface silently
  dropping a backend-serialized field in Phase 159 were both caught and closed via this
  milestone's code-review → fix → re-review cycle on every phase.

## [5.13.0] - 2026-08-15

Continuous Hardware Lifecycle Monitoring (Phases 154-156). **Developed but never released**: its
tag (`v5.13`) was two-component, which never matched the `v*.*.*` trigger glob in `release.yml`,
so pushing it matched nothing and fired no release workflow — no run, no failure, no signal.
`v5.13` was never even pushed to origin. The last version actually published to PyPI remains
5.12.0 (2026-08-14); `pyproject.toml` stayed at `5.12.0` throughout this milestone, so even the
tag string is wrong. The code shipped to `main` and is in use — only the release step never fired.

### Added

- **Stable hardware identity across re-IP/DHCP** (Phase 154, HWLC-01/HWLC-02) — a secondary SSH
  host-key-fingerprint match key lets a device survive a DHCP lease change or re-IP; honest
  `probe_status` classification (success vs. failed) distinguishes a confirmed re-probe from a
  timeout, and failed re-probes no longer erase last-known-good device state. A new
  `hardware_history_retention_days` config field (default 180) bounds history growth, purged
  inside the same persist transaction.
- **Two-scan drift-reconciliation engine** (Phase 155) — `hardware_drift.py` compares consecutive
  scans of the same device and surfaces CNSA 2.0 tier crossings, PQC/bridge-mitigation shifts,
  EOL/EOS proximity, and CVE deltas as four distinct, N-of-M-confirmed event types, backed by a new
  `hardware_drift_events` table and visible on the `/hardware` and `/compare` dashboard tabs and in
  HTML/DOCX reports as structurally separate advisory content.
- **Opt-in recurring OT/ICS re-probing** — recurring Modbus/BACnet re-probing requires explicit
  opt-in plus a hardcoded 168-hour cadence floor, closed by an independent `/gsd-secure-phase`
  review (19/19 threats, 0 high-severity findings).

## [5.12.0] - 2026-08-14

Release & Verification Integrity (Phases 148-153). The real, published `v5.12.0` release —
PyPI + Windows operator zip + GitHub Release — closing the release-pipeline debt that had
accumulated since v5.9's silent tag-glob failure.

### Added

- **Release dry-run + tag-hygiene guards** (Phase 148, RELEASE-01/02/03/04) — `release.yml`
  gained a `workflow_dispatch` dry-run trigger and tag-ref guards; a scheduled tag-hygiene
  workflow with a seeded historical baseline (`.github/tag-hygiene-baseline.txt`) detects
  malformed version tags going forward; a Windows release asset gap from v5.11.0 was closed.
- **Suite-wide skip/xfail visibility** (Phase 149, SUITE-01) — the AST walker used to audit the
  test suite was extended to detect `skip`/`xfail` decorators, surfacing previously invisible
  disabled coverage.
- **Gating Linux full-suite CI job** (Phase 150, SUITE-02/03) — a green, gating full-suite CI job
  on Linux, plus idempotent per-profile chaos-lab certificate generation so cert expiry no longer
  silently rots CI.
- **Phase-completion artifact gate** (Phase 151, ARTIFACT-01/02/03/04) —
  `scripts/verify_phase_gates.py` plus a `.githooks/pre-commit` wrapper enforce that
  VERIFICATION.md/VALIDATION.md/UAT-SERIES.md artifacts exist before a phase can close, and a
  `check_destructive_archive()` guard prevents an unchecked `phases.clear` from silently deleting
  live phase directories (closing the incident that lost ~39 of ~58 v5.11 phase artifact files).
- **Segmented-network chaos lab profile** (Phase 152, DISC-09/10/11) — a new gateway profile plus
  a live-fire smoke test; the interactive nmap-discovery-first prompt now defaults to Y; the
  Phase 144 nmap timing artifact was empirically confirmed to not reproduce.
- **Actual tag cut** (Phase 153, RELEASE-01) — the real `v5.12.0` tag proving the repaired
  pipeline end-to-end.

## [5.11.0] - 2026-08-11

Discovery at Scale + Backlog Drain (Phases 144-147). Made large (>1024-host) range scans reachable
end-to-end from the dashboard's nmap-discovery path.

### Added

- **Chunked discovery core** (Phase 144, DISC-01/02) — lazy host-expansion and chunking helpers in
  `target_expander.py`, a sequential per-batch nmap discovery loop with per-batch failure
  isolation, and a `discovery` `ScanCheckpoint` stage for resumability.
- **TCP-SYN/ACK liveness pre-pass** (Phase 145, DISC-03/04) — `run_nmap_liveness_check()` with
  explicit privilege-fallback detection, wired into the discovery batch loop ahead of full probing.
- **Batch progress, scaled timeouts, and undetermined-host disclosure** (Phase 146,
  DISC-05/06/07) — `scan_jobs` gained discovery batch-progress columns rendered live on the
  scan-job page; discovery timeouts scale with batch size; hosts that could not be determined
  live/dead are now disclosed across markdown/HTML/DOCX report surfaces instead of silently
  dropped.
- **Backlog drain — lifecycle & ledger tail** (Phase 147) — OT/ICS fingerprinting now runs ahead
  of the SSH-stage if/else so it is no longer skipped; a curated BACnet vendor-ID + model-family
  resolution catalog was added and wired into the hardware scanner; the default CORS allowlist
  became port-aware.

4 phases, 16 plans, 11/11 requirements, audit `passed`.

## [5.10.0] - 2026-08-03

Hardware Lifecycle Depth (Phases 139-143). Closed out the Hardware Compatibility & Lifecycle
Remediation arc opened in v5.7/v5.8.

### Added

- **SNMPv3 auth+priv support** (Phase 139) — a `SnmpV3Credential`-driven v3→v2c→none probe ladder
  wired into the fingerprint waterfall, with SNMPv3 version/protocol fields projected through the
  report writer, dashboard route, and CBOM Pass 4.
- **SNMP-confirmed bridge mitigation** (Phase 140, BRIDGE-01..05) — a bounded ARP-table walk probe
  (v2c + v3) confirms an upstream TLS terminator mitigating a quantum-vulnerable on-device cipher,
  surfaced as a Bridge Status badge on the `/hardware` dashboard tab and in HTML/DOCX reports.
- **OT/ICS Modbus/BACnet fingerprinting** (Phase 141, OTICS-01..06) — Modbus/TCP FC43/14 and
  BACnet/IP Who-Is/I-Am + ReadProperty fingerprint probes, gated behind `--enable-modbus` /
  `--enable-bacnet` CLI flags and a new `otics` chaos-lab profile with fragile Modbus/BACnet
  simulators. Required two post-ship gap-closure rounds after a live checkpoint caught a deeper
  orchestration bug the plan-checker had missed.
- **Advisory-only firmware CVE correlation** (Phase 142, CVE-01..04) — a curated
  `quirk/scanner/hw_cve.py` correlation module plus a `quirk cve status` CLI command; per-device
  CVE annotations render in HTML/PDF/DOCX reports and as CBOM `quirk:hw-cve-*` properties.
- **Dashboard & security tail** (Phase 143, TAIL-01..04) — a `ScanDateBadge` in the sidebar, a
  `target_trust.py` allowlist matcher (`SecurityCfg.trusted_targets`) wired into CLI and dashboard
  entry points, and Windows sensor exe self-test signing wired pre-zip.

36 plans, 23/23 requirements satisfied, tech_debt disposition (0 blockers, 4 tracked non-blocking
items).

## [5.9.0] - 2026-07-30

Documentation Audit & Living Docs System (Phases 135-138 + 138.1/138.2).

### Added

- **Full documentation audit against v5.4-v5.8** (Phase 135-138) — README, getting-started,
  architecture, operators-guide, and report-interpretation refreshed; a net-new
  `docs/admin-guide.md` added (ADMIN-01/02/03); the chaos-lab `hwcompat` profile documented; a
  permanent doc-hygiene checklist embedded in `CLAUDE.md`.
- **Hardware Inventory report section** (Phase 137, OPS-04) — `docs/report-interpretation.md`
  gained a §10 Hardware Inventory section documenting the DEVICE/FIRMWARE component hierarchy.

### Fixed

- **CORE-04 tier-inversion** (Phase 138.1) — corrected an inverted CNSA 2.0 tier semantics
  description in `architecture.md`.
- **LIVE-03 vault re-sync** (Phase 138.2) — the Obsidian vault guide copies were re-synced after
  drifting from their `docs/` source during the audit.
- **Six write-review corrections in `architecture.md`** (Phase 135, WR-01..06) — fabricated
  migration function names, an inverted crypto-bridge trust-model description, a stale module
  path, an outdated dashboard route count (9→19), an outdated backend route module count
  (4→10, missing the `HardwareFinding` DTO), and a hardcoded platform-version string were all
  corrected to match the shipped codebase.

16/16 requirements satisfied, tech_debt disposition (deferred human-UAT only, no content gaps).

## [5.8.0] - 2026-06-16

### Added

- **SNMP hardware fingerprinting** (Phase 133) — pysnmp 7 HLAPI 3-OID probe (sysDescr / sysName / sysObjectID) with sysdescrparser dual-path parsing (structured MIB + regex fallback) to extract vendor, model, and hardware family from raw SNMP responses. Signal cascade ordering: SSH banner → HTTP management interface → SNMP (last resort, requires read-only community string). New `[hw]` extras group (`pysnmp`, `sysdescrparser`); **not included in `[all]`** — opt-in required (`pip install 'quirk-scanner[hw]'`). Cisco IOS chaos-lab profile added on port 20223.
- **CBOM DEVICE/FIRMWARE component hierarchy** (Phase 134) — hardware endpoints promoted to a CycloneDX `ComponentType.DEVICE` parent component with a `ComponentType.FIRMWARE` child; separates the hardware platform from its firmware crypto posture in the CBOM graph. Dashboard "Hardware Inventory" section added to the CBOM tab. Hardware inventory is advisory-only and does not contribute to the quantum-readiness score.

## [5.7.0] - 2026-06-14

### Added

- **Hardening + Hardware Compatibility milestone** (Phases 123–129) — SSRF cluster hardening across all outbound HTTP surfaces, scoring correctness fixes (clamp/aggregation alignment), and full audit drain of the 2026-05-27 codebase audit findings.
- **Hardware fingerprinting via SSH/HTTP banner** — SSH host-key banner and HTTP management-interface response classify network hardware vendor, model, and CNSA 2.0 remediation tier (quantum-safe / PQC-migration-required / quantum-vulnerable). Crypto-bridge detection identifies hardware devices where an upstream TLS terminator mitigates a quantum-vulnerable on-device cipher suite.

## [5.6.0] - 2026-06-12

### Added

- **Public launch** (Phase 119–120) — QU.I.R.K. is now an open-source public repository on GitHub with branch protection on `main` and `windows-sensor-smoke` enforced as a required CI status check. A full git-history secret scan (gitleaks, 0 findings across 2652+ commits) preceded the visibility flip; Actions SHA-pinning (all 30 uses:) and SECURITY_CHECKLIST canonicalization completed the posture sweep (Phase 120).
- **Windows production build — frozen sensor binary** (Phase 117) — production PyInstaller `--onedir` build of the QUIRK sensor on `windows-latest` CI; `quirk.exe --version` and `quirk.exe --help` confirmed on a runner with no Python installed; data-file and hidden-import set locked from the WINPKG-01 spike.
- **Windows packaging + Scheduled Task installer** (Phase 118) — zip + PowerShell `install.ps1` / `uninstall.ps1` pair; registers a Windows Scheduled Task for periodic sensor cadence; frozen sensor passes Phase 113 per-sensor Bearer-token wire contract in E2E CI; Windows zip published as a GitHub Release asset alongside PyPI/GHCR/Homebrew. (Unsigned — Authenticode deferred.)
- **Port-scope discovery control** (Phase 121) — dashboard scan-new form offers four port-scope options (Common TLS / Top 1000 / All ports / Custom); nmap discovery decoupled from the hardcoded 6-port TLS list; wide-scope jobs hard-fail without nmap rather than silently using 6 ports; custom port specs cap at 2048 expanded ports with strict nmap-style parse/validation; `GET /api/jobs/{id}/result-summary` returns an explicit zero-endpoints completion signal so stale data is never displayed.

### Fixed

- **Phase 122 tech-debt sweep** (11 audit items from 2026-05-27 codebase audit):
  - CR-01: Phantom +20 TLS-enum confidence bonus guarded on `tls_count > 0` — zero-TLS scans no longer receive unearned coverage credit (commit c60d1bd).
  - CE-01: AKS scanner now emits an advisory finding (K8S-03 invariant) instead of silently returning `[]` when valid credentials yield an empty cluster list (commit c20245e).
  - CE-02: `safe_str` base64 redaction regex tightened with a negative lookbehind + first-char guard; ARNs and resource IDs no longer over-redacted (commit ef6aeab).
  - CE-03: Vault PKI SHA-1 reason field always populated when detected, even on dual-weakness (RSA+SHA-1) certificates (commit ef6aeab).
  - CE-05: Engine safe-mode concurrency default aligned to 200 baseline — was erroneously 100 (a 2× divergence) (commit ef6aeab).
  - QC-01: Explicit `int()` cast on QRAMM `suggested_answer` — eliminates silent SQLite float→integer coercion (commit b14cdd9).
  - QC-04: `compute_overall_score` itself now clamped at 4.0 — prior BL-01 fix was router-only (commit b14cdd9).
  - QC-05: Compliance staleness gate moved to production code path (`check_compliance_staleness()` in `quirk/compliance/__init__.py`); malformed `last_verified` dates raise `RuntimeError` instead of silently continuing (commit 8539f99).
  - WR-01: `md_cell` now strips DEL (0x7f) and C1 control range (0x80–0x9f); previously kept by `c >= "\\x20"` guard (commit eba210a).
  - WR-06: `html_renderer` no-`exec_content` fallback reads canonical `score["score"]` key, not the non-existent `"total"` key (commit eba210a).
  - Stub-label: AWS and Azure connector prompts in `quirk/interactive.py` confirmed production-grade (stub labeling already absent from prior phase work).

### Misc

- Windows distribution is unsigned — Authenticode code-signing deferred to a future spike (needs certificate + CI secret handling).
- Phase 120 git-history rewrite: 12 sensitive path categories stripped from history; 989 → 901 tracked files, 6260 → 2952 commits after empty-commit pruning.

## [5.5.0] - 2026-05-27

### Added

- **Per-sensor authentication & revocation** (Phase 113) — distributed-mode sensors now enroll with opaque Bearer tokens individually issued and individually revocable via `quirk revoke-sensor`; new `revoked_at` migration on the sensors table; console rejects requests from revoked tokens.
- **Failure-isolated auto-merge** (Phase 114) — when one sensor fails mid-scan, the console merges the remaining successful results into a CBOM and final score rather than discarding the batch; operators guide §8.9 documents the partial-merge contract.
- **Weak-TLS chaos-lab target** (Phase 115) — added intentionally-weak TLS profile to widen scanner regression surface; live-UAT stabilization sweep cleared 4 follow-up items.

### Fixed

- Phase 114 inverted revoked-filter caught in code review pre-ship.
- Phase 115 cron crash on absent schedule resolved.
- Phase 116 over-broad hard-gate narrowed.

### Misc

- Windows packaging spike (Phase 116) — onedir frozen sensor build confirmed GO via live windows-latest CI run.

## [5.4.0] - 2026-05-26

### Added

- **Distributed on-prem scanner** (Phases 106–112) — sensor / console architecture: scan-per-segment on isolated sensors, push findings to a central console, merge into one CBOM + final score (Option A merge: keep newest-per-fingerprint, never rewrite `scanned_at`).
- **`enroll` + `--sensor-id` CLI surface** for sensor-to-console pairing.
- **`crypto.internal` hostname-alias** pattern for same-subnet docker compose validation (compose forbids same-subnet networks; alias works around).
- **Sensor SSRF mitigation** corrected to allow internal console targets while still blocking external SSRF paths.

### Fixed

- Discarded CBOM artifact on partial-success scans (caught by code review, not unit verification).
- `_run_local_scan --output` path resolution (caught by live E2E).

## [5.3.0] - 2026-05-25

### Added

- **Notification fan-out** (Phase 101) — webhook + email + Slack dispatch on schedule completion or finding severity threshold.
- **SIEM CEF dispatch** (Phase 102) — Common Event Format export for Splunk / QRadar / ArcSight ingestion.
- **Jira / ServiceNow ticketing** (Phase 103) — automatic ticket creation on high-severity findings with secret-scrubbing applied to ticket bodies.
- **Dashboard token auth** (Phase 105) — bearer-token gate on dashboard API to prevent unauthenticated query of stored scans.

### Fixed

- Fingerprint formula corrected to `SHA256(host:port::title)` for finding deduplication.
- Shared SSRF-safe / secret-scrubbing layer (Phase 101 anchor) unifies outbound HTTP across notification / SIEM / ticketing surfaces.

## [5.2.0] - 2026-05-24

### Added

- **Consulting-grade reporting** (Phases 97–100) — one shared content model drives CLI markdown, HTML, PDF, and new DOCX renderers; eliminates render-divergence across surfaces.
- **DOCX renderer** (`quirk/reports/docx_renderer.py`) — client-deliverable Word format with consultant-editable narrative blocks.
- **Code-signing endpoint evaluation** — LDAP+TLS-EKU based codesign certificate posture wired into agility scoring.

### Fixed

- CLI score sourcing aligned with executive narrative content (logged backlog item v5.2-TD-1 closed in v5.3).

## [5.1.0] - 2026-05-22

### Added

- **Authenticated scanning** (Phases 93–96) — ephemeral credentials for JWT API + cloud connector scans; no long-lived secret storage in scheduled scan rows.
- **Query-param API-key CLI flag** + JWT-scanner URL credential consumption (Phase 93 D-1, full delivery in 93 not 94).
- **Code-signing posture** (Phase 95) — LDAP+TLS-EKU only; fuzzing non-TTY hard-abort guard; schemathesis excluded from `[all]` extra.
- **Agility subscore** absorbs codesign signals; no separate 7th subscore.

### Fixed

- SCORE_WEIGHTS walks 283 → 293 → 299 → 303 across the v5.1 milestone.


## [5.0.0] - 2026-05-22

### Added

- Added four weak-TLS chaos-lab profiles (postgres-tls port 39432, redis-tls ports 39380/39379, kafka-tls ports 39093/39092, grpc-tls port 39443) with intentional RSA-2048 / RSA-KX ciphers, plus a Go gRPC multi-stage Docker build with empirically-confirmed sslyze ALPN-h2 compatibility (LAB-03 SMTP STARTTLS closed as already covered by the email profile). (v5.0-89)
- Added OQS-nginx PQC-hybrid chaos-lab profile (port 39444) serving TLS 1.3 with X25519MLKEM768 hybrid KEM and ML-DSA-65 certificate (digest-pinned openquantumsafe/nginx image, sha256:6ca18ac6); live openssl s_client probe detects X25519MLKEM768 group negotiation; agility scoring gains an agility_pqc_hybrid_bonus weight of +8.0 that anchors the scoring ceiling for post-quantum readiness. (v5.0-90)

### Fixed

- Added six-subscore N/25 decomposition block to CLI markdown, executive markdown, and HTML/PDF report surfaces so reviewers can see per-category scores alongside the overall readiness number; CBOM builder now emits affirmative coverage-note properties for five formerly-zero-algorithm profiles (database, registry, source, ssh-weak, storage-s3) closing Phase 42 OBS-1; forward-locking orthogonality and render-parity tests lock the single scoring engine as invariant. (v5.0-88)

### Misc

- v5.0-87, v5.0-91


## [4.10.1] - 2026-05-22

### Fixed

- Overall readiness no longer caps at 100 on real scans. The previous aggregator summed six 0–25 subscores and clamped at 100, masking real posture issues. Overall readiness is now `int(round(sum_of_subscores / 1.5))`; dashboard subscore radials now render against `maxValue=25` so a perfect category shows green and a depleted category shows red.

  **Before / After (canonical example):**

  | Subscores | Sum | Overall (before) | Rating (before) | Overall (after) | Rating (after) |
  |-----------|-----|-----------------|-----------------|-----------------|----------------|
  | 25+25+23+3+25+19 | 120 | **100** | EXCELLENT | **80** | GOOD |

  Old stored scores will display lower after upgrade. The underlying per-category penalty math is unchanged — only the aggregation and dashboard scale are corrected. To refresh a stored score, re-render or re-scan. (v4.10.1)


## 4.4.0 - 2026-04-29

**Milestone:** v4.4 Data in Motion — full release notes: [docs/release-notes/4.4.0.md](docs/release-notes/4.4.0.md)

### Added

- **Email protocol scanning** (Phase 32, EMAIL-01..12): SMTP/SMTPS, submission, IMAP/IMAPS,
  POP3/POP3S TLS posture with STARTTLS-stripping detection on port 25, weak-cipher
  detection on email TLS endpoints, and a new `email` Docker chaos lab profile (Postfix +
  Dovecot with intentionally weak TLS).
- **Message broker TLS scanning** (Phase 33, KAFKA-01..04, RABBIT-01..05, REDIS-01..03,
  BROKER-LAB-01/02): Kafka (9092/9093/9094), RabbitMQ AMQPS (5671) + management API (15672),
  Redis TLS (6380), Azure Service Bus AMQPS (5671), AWS SQS HTTPS (443). Plaintext-listener
  HIGH findings for all three local broker types. New `broker` Docker chaos lab profile
  (Kafka + RabbitMQ + Redis with weak TLS configs).
- **Data-in-motion intelligence** (Phase 34, MOTION-01..04): six new `motion_*` evidence
  counters in the intelligence summary, three new `motion_*_ratio` scoring weights with
  profile multipliers (strict / balanced / lenient), and a `data_in_motion` 6th subscore
  alongside `tls`, `ssh`, `api`, `identity`, and `data_at_rest`. Legacy scans without
  motion keys preserve full credit (D-12 backward compatibility).
- **Motion CBOM integration** (Phase 35, CBOM-01..04): email and broker TLS endpoints
  generate Pass-1 algorithm components with quantum-safety classification; plaintext-only
  endpoints (`KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`, `SMTP-STARTTLS`) are excluded from
  Pass-2/Pass-3 to prevent hollow certificate entries. AMQPS/Azure-ServiceBus passes
  through the default-TLS branch unchanged.
- **Dashboard Motion tab** (Phase 36, DASH-01..05): new `/motion` React route with email
  and broker surface sections, a "Data in Motion" line on the executive summary card, and
  a `motion_findings` field on `/api/scan/latest`.
- **`[motion]` meta-extra** (Phase 37, INFRA-02): `pip install quirk[motion]` is now the
  single happy path; pulls in `quirk[email]`, `quirk[broker]`, and `quirk[kafka]` flat
  sub-extras. Each remains independently installable.
- **INFRA-03 Nyquist coverage** (Phase 37): new `tests/test_infra03_nyquist_coverage.py`
  module with 18 explicit tests — 6 scanner entry points × happy / refused / plaintext-only.
- **Version-regression lock** (Phase 37, INFRA-01): new `tests/test_version.py` asserting
  `quirk.__version__`, CBOM `PLATFORM_VERSION`, report `PLATFORM_VERSION`,
  `INTELLIGENCE_VERSION`, and `IntelligenceCfg.intelligence_version` all read 4.4.0.

### Changed

- **Version bumped to 4.4.0** across `quirk/__init__.py`, `pyproject.toml`,
  `quirk/cbom/builder.py` (CBOM tool metadata), `quirk/reports/writer.py` (report header),
  and `quirk/config.py` `intelligence_version` default.
- **`pyproject.toml [project.optional-dependencies]`** restructured: `motion` is now a
  meta-extra over `email` (no non-core deps), `broker` (`redis>=5.0`), and `kafka`
  (`kafka-python>=2.0`).

### Fixed

- Stale `PLATFORM_VERSION = "4.2.0"` and `INTELLIGENCE_VERSION = "4.2.0"` in
  `quirk/reports/writer.py` (carried over since v4.2) now reflect the current 4.4.0 platform
  version.
- Stale version-regression assertions in `tests/test_packaging.py`,
  `tests/test_v41_gap_closure.py`, and `tests/test_cli_correctness.py::test_version_consistency`
  bumped from 4.1.0/4.2.0 to 4.4.0 (Plan 37-04 sweep).
- Five legacy `quirk scan` CLI references in `docs/UAT-SERIES.md` (lines 1526, 3866, 4772,
  4833, 4835) replaced with the modern `quirk --config` invocation.

### Documentation

- This CHANGELOG, sourced from each phase's SUMMARY.md.
- `docs/release-notes/4.4.0.md` standalone narrative.
- `docs/UAT-SERIES.md` updated with v4.4 test cases (per Phase 37 close-out).
- Per-phase `VALIDATION.md` files for phases 32, 33, 34, 35, and 37 all read
  `nyquist_compliant: true` and `wave_0_complete: true`. Phase 36's flip is deferred
  pending an unrelated SAML scan-window regression (ISSUE-3 from Phase 24).

---

*Earlier milestones: see `.planning/milestones/v4.3-ROADMAP.md`, `v4.2-ROADMAP.md`,
`v4.1-ROADMAP.md`, `v3.9-ROADMAP.md` for the full historical record. v4.4 is the first
milestone with a top-level CHANGELOG.md.*

---
phase: 32-email-scanner
plan: "06"
subsystem: email-scanner
tags: [email-scanner, chaos-lab, expected-results, documentation, validation, regression-baseline, quirk]

dependency_graph:
  requires:
    - 32-03-email-scanner-module
    - 32-04-risk-engine-findings
    - 32-05-chaos-lab
  provides:
    - "labs/email/expected_results.md (regression baseline for scanner-vs-lab validation)"
  affects:
    - 32-07-uat-and-docs
    - 34-motion-intelligence
    - 35-cbom-integration

tech-stack:
  added: []
  patterns:
    - "expected_results.md captured from live chaos-lab + scanner invocation, not authored from theory (consulting deliverable contract)"
    - "Direct scan_one_email() invocation with host_port arguments — bypasses the EMAIL_PORTS standard-port hardcode for lab-only validation without privileged port forwarding"

key-files:
  created:
    - labs/email/expected_results.md
  modified:
    - run_scan.py

key-decisions:
  - "Captured the live scanner output via direct scan_one_email() invocation against lab ports 30xxx rather than fighting the scanner's hardcoded EMAIL_PORTS standard-port table. This is the documented reproducible path for lab-only validation; full pipeline run via run_scan.py requires privileged-port forwarding (sudo socat) on macOS"
  - "Documented the port-mapping mismatch as a known followup item rather than refactoring EMAIL_PORTS to be parameterizable — that is a Plan 32-04 architectural change (Rule 4 territory) and not in scope for EMAIL-12"
  - "Captured Dovecot's TLS 1.3 default behavior (no weak-cipher findings on 30143/30993/30110/30995) as expected, with explicit guidance for forcing TLS 1.2 to exercise the weak path manually — matches Plan 32-05 documented limitation"

requirements-completed: [EMAIL-12]

metrics:
  duration: "~30 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 32 Plan 06: Email Lab Expected Results Summary

**One-liner:** Captured the live scanner output against the booted Phase 32 chaos lab (Postfix+Dovecot) and froze it as `labs/email/expected_results.md` — 7 endpoints, 4 findings (1 MEDIUM STARTTLS-downgrade + 3 HIGH weak-cipher), with documented caveats for Dovecot TLS 1.3 default, sslyze requirement, and the lab/scanner port-mapping mismatch.

## What Was Built

### `labs/email/expected_results.md` — 228 lines

**Sections:**

| Section                    | Content                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| Lab Setup                  | docker compose --profile email up + healthy-state check                                                |
| Port Map                   | 7-row host_port → container_port table                                                                 |
| Expected Scan Output       | 7-row table: TLS version, cipher, cert subject, pubkey, PFS — captured live                            |
| Expected Findings          | 4-row finding table (MEDIUM STARTTLS-downgrade + 3× HIGH weak-cipher) + generic self-signed cert note  |
| Caveats                    | Dovecot 2.3.16 TLS 1.3 default; OpenSSL 3.x TLS-1.0/1.1 limit; port 25 cloud egress; D-11 layering; sslyze required; port mapping |
| Reproducing                | Full-pipeline invocation + lab-only direct-invocation Python snippet                                    |
| Tear-Down                  | docker compose down                                                                                     |

### Captured live data

Per-port scanner output (sslyze 6.3.1 + Python 3.14):

| Host port | Protocol         | TLS version | Cipher suite                       | Cert subject               | Pubkey   | PFS    |
| --------- | ---------------- | ----------- | ---------------------------------- | -------------------------- | -------- | ------ |
| 30025     | SMTP-STARTTLS    | TLSv1.2     | TLS_RSA_WITH_ARIA_256_GCM_SHA384   | CN=postfix.chaos.local     | RSA-2048 | False  |
| 30465     | SMTPS            | TLSv1.2     | TLS_RSA_WITH_ARIA_256_GCM_SHA384   | CN=postfix.chaos.local     | RSA-2048 | False  |
| 30587     | SMTP-STARTTLS    | TLSv1.2     | TLS_RSA_WITH_ARIA_256_GCM_SHA384   | CN=postfix.chaos.local     | RSA-2048 | False  |
| 30143     | IMAP-STARTTLS    | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256       | CN=dovecot.chaos.local     | RSA-2048 | False* |
| 30993     | IMAPS            | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256       | CN=dovecot.chaos.local     | RSA-2048 | False* |
| 30110     | POP3-STARTTLS    | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256       | CN=dovecot.chaos.local     | RSA-2048 | False* |
| 30995     | POP3S            | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256       | CN=dovecot.chaos.local     | RSA-2048 | False* |

\* PFS=False reported by sslyze on TLS 1.3 endpoints (lab cipher allowlist is RSA-only),
but the risk-engine does NOT emit a non-PFS finding under TLS 1.3 (D-12).

### Findings produced by `evaluate_email_endpoints()`

After rewriting host ports → standard ports (so EMAIL-08's `port == 25` gate fires):

| Severity | Title                                     | Port | Source   |
| -------- | ----------------------------------------- | ---- | -------- |
| MEDIUM   | STARTTLS downgrade risk on SMTP           | 25   | EMAIL-08 |
| HIGH     | Weak cipher suite on email TLS endpoint   | 25   | EMAIL-09 |
| HIGH     | Weak cipher suite on email TLS endpoint   | 465  | EMAIL-09 |
| HIGH     | Weak cipher suite on email TLS endpoint   | 587  | EMAIL-09 |

**Severity counts:** HIGH=3, MEDIUM=1, total=4. Plan minimums met (≥1 STARTTLS-downgrade
MEDIUM ✓, ≥1 weak-cipher HIGH ✓). D-11 layering verified — port 25 emits both findings.

## Task Commits

1. `0c6a8c3` — `fix(32-06): correct logger.info call signature in email scan block`
2. `7542120` — `docs(32-06): add labs/email/expected_results.md from live chaos-lab capture`

## Acceptance Criteria — All Met

| Criterion                                                         | Result            |
| ----------------------------------------------------------------- | ----------------- |
| `test -f labs/email/expected_results.md`                          | PASS              |
| `wc -l ≥ 60`                                                      | 228               |
| `grep -c "STARTTLS downgrade risk"`                               | 2 (≥1)            |
| `grep -c "Weak cipher suite"`                                     | 3 (≥1)            |
| `grep -c "RSA-2048\|RSA 2048"`                                    | 8 (≥1)            |
| `grep -c "TLSv1.2"`                                               | 6 (≥1)            |
| `grep -c "30025\|30465\|30587\|30143\|30993\|30110\|30995"`       | 30 (≥7)           |
| `grep -c "OpenSSL\|TLS 1.0/1.1"`                                  | 4 (≥1)            |
| `grep -c "<captured>"`                                            | 0                 |
| Lab booted via `docker compose --profile email up -d --build`     | PASS — both healthy|
| Lab torn down at end of plan                                       | PASS              |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `logger.info()` call in run_scan.py used stdlib-style positional format args**

- **Found during:** Task 1, first attempt to run `python3 run_scan.py --config ... --profile standard`.
- **Issue:** Plan 32-04 added at line 703-704:
  ```python
  logger.info("Email scan: %d endpoints from %d hosts",
              len(email_endpoints), len(email_hosts))
  ```
  But QUIRK's `Logger.info(self, msg: str)` only accepts a single argument. Runtime
  raised `TypeError: Logger.info() takes 2 positional arguments but 4 were given`,
  aborting the email-scan block.
- **Fix:** Single-line f-string replacement.
- **Files modified:** run_scan.py
- **Verification:** Subsequent invocations did not crash on this line (run_scan still
  has unrelated long-running behavior on this lab — see deviation #2).
- **Committed in:** `0c6a8c3`

**2. [Rule 3 — Blocking] Live scanner output captured via direct invocation, not full `run_scan.py` pipeline**

- **Found during:** Task 1, after fixing deviation #1, the `run_scan.py` invocation
  hung > 5 minutes during the discovery/TLS-scan phase against `127.0.0.1`.
- **Issue:** Two compounding factors:
  - macOS without sudo cannot bind privileged ports (1–1023), so the scanner cannot
    reach the lab's services through standard ports (25/465/587/143/993/110/995). The
    lab uses non-privileged forwards 30025…30995, but the scanner's `EMAIL_PORTS`
    table is hardcoded to standard ports.
  - `run_scan.py` performs full TLS/SSH/discovery sweeps against the configured target
    range; even with a tightened cidr, fingerprint/cipher enumeration on the unrelated
    chaos services running in the same compose network produced long delays.
- **Fix:** Captured scanner output via a one-off probe script
  (`/tmp/email-lab-probe.py`) that calls `scan_one_email()` directly with host-port
  arguments (30025, 30465, …). This is the documented reproducible path now codified
  in `expected_results.md` "Reproducing" section.
- **Why this is correct, not a workaround:** the captured data IS what the scanner
  produces against the lab — endpoints, TLS versions, ciphers, certs, and finding
  emission via `evaluate_email_endpoints` are all real outputs from the production
  scanner code paths. The only thing bypassed is the discovery/fingerprint pre-pass,
  which is irrelevant to the EMAIL-12 contract (the contract is about the scanner-
  vs-lab agreement, not about discovery latency).
- **Files modified:** none (probe script is ephemeral, not committed).
- **Verification:** All 4 expected findings emit; D-11 layering verified.
- **Committed in:** N/A (capture is recorded in expected_results.md commit `7542120`).

**3. [Rule 3 — Blocking] sslyze installed mid-plan**

- **Found during:** Task 1, first probe-script run reported `SSLYZE_AVAILABLE = False`,
  and the stdlib fallback returned `SSLV3_ALERT_HANDSHAKE_FAILURE` for all 3 Postfix
  ports (Python 3.10+'s default `ssl.create_default_context()` excludes RSA-kex
  ciphers from its client hello, which the lab's RSA-only cipher allowlist rejects).
- **Issue:** The .venv at `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.venv`
  did not have sslyze installed. Without sslyze the Postfix endpoints record
  `scan_error` instead of cipher data, and zero findings emit — failing the plan's
  Success Criterion #5 minimums.
- **Fix:** `pip install sslyze` into the project .venv (sslyze 6.3.1 + nassl 5.4.0 +
  tls-parser 2.0.2). Re-ran probe — all 7 endpoints captured cipher + cert data,
  4 findings emitted.
- **Why install vs. document-as-not-applicable:** the plan's success criteria
  explicitly require ≥1 weak-cipher HIGH finding. The stdlib-fallback path
  cannot meet that criterion against this lab's posture (Python won't even offer
  the weak ciphers in client_hello, so the scanner can't observe what the server
  actually supports). sslyze is the production-required dependency for the
  email-scanner motion path; this is the same situation as the existing tls_scanner
  pipeline.
- **Documented in expected_results.md** under "sslyze required for full enumeration"
  caveat — explicit guidance that consulting/CI runs must have sslyze installed.

---

**Total deviations:** 3 (1 auto-fixed bug + 2 blocking-issue resolutions). No
architectural decisions; no checkpoints reached. All deviations addressed inline
without scope change.

## Issues Encountered

Beyond the deviations above:

- **Logger bug `0c6a8c3`** is a regression that escaped Plan 32-04's tests because
  the test fixtures stub the logger (or run with `logger=None`). The wiring tests
  do not exercise the live `logger.info()` call inside the `cfg.connectors.enable_email`
  branch with a real `Logger` instance. Phase 32 Plan 07 (UAT/docs) should add a
  smoke test that imports `quirk.logging_util.Logger` and runs run_scan with a real
  logger to catch this class of regression.

- **Architectural followup (deferred):** the scanner's `EMAIL_PORTS` table is
  hardcoded to standard ports, which forces consultants on macOS to use sudo
  socat for `run_scan.py` end-to-end runs against the chaos lab. A future plan
  should consider parameterizing `EMAIL_PORTS` (e.g., via cfg.connectors.email_ports
  override) so the lab is exercisable end-to-end without privileged forwarding.
  Tracked in expected_results.md "Port mapping (lab vs. scanner)" caveat.

## TDD Gate Compliance

This plan is `type: execute` (not `type: tdd`). Task 1 was a checkpoint:human-verify
that captured live scan data; Task 2 was a docs-write. No RED→GREEN cycle expected
or required. The data captured by Task 1 directly drove Task 2's content.

## Threat Surface

No new threat surface introduced. The plan's `<threat_model>` (T-32-18) addresses
documentation accuracy — `expected_results.md` enumerates ALL findings produced
by the captured run; deviations during future regression checks are explicit
signals (added/missing finding ↔ scanner or lab change).

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. Lab
posture remains exactly as Plan 32-05 documented.

## Known Stubs

None. The expected_results.md is fully populated from live data; no `<captured>`
or TODO placeholders remain. The "lab port vs scanner standard-port" mismatch is
called out as a known caveat, not a stub.

## Next Phase Readiness

- **Plan 32-07 (UAT/docs):** can reference `labs/email/expected_results.md` as the
  ground truth for the email scanner's behavior against the chaos lab. UAT
  scenarios can compare a fresh scan against this document.
- **Phase 34 (motion intelligence):** can iterate the documented endpoint list
  (3 SMTP + 4 IMAP/POP3) and finding titles for motion-tab population.
- **Phase 35 (CBOM integration):** can use the captured cipher list
  (`TLS_RSA_WITH_ARIA_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`) and
  cert posture (RSA-2048 self-signed) for Pass-1 algorithm registration tests.

## Self-Check

- `labs/email/expected_results.md` exists: FOUND (228 lines)
- Commit `7542120` (expected_results.md) exists in git log: FOUND
- Commit `0c6a8c3` (logger fix) exists in git log: FOUND
- All plan acceptance grep checks pass: CONFIRMED (228 lines, ≥1 STARTTLS, ≥1 Weak cipher, ≥1 RSA-2048, ≥1 TLSv1.2, ≥7 port refs, ≥1 OpenSSL caveat, 0 placeholders)
- Lab torn down: CONFIRMED (postfix-email + dovecot-email containers removed via `docker compose --profile email down`)
- `python3 -c "..."` post-verify snippet from plan: PASSES (file contains STARTTLS, Weak cipher, RSA-2048)

## Self-Check: PASSED

---
*Phase: 32-email-scanner*
*Completed: 2026-04-27*

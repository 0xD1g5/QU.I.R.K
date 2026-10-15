---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-R05; docs/report-interpretation.md §17 "An endpoint reached but whose crypto handshake never completed also counts as assessed — for example, an SMTP-STARTTLS host that advertised the port but never offered STARTTLS ... usually a HIGH-severity finding"
priority: medium
area: quirk/scanner/email_scanner.py (stdlib fallback), quirk/intelligence/evidence.py (coverage D-04), quirk/engine/findings_evaluator.py
status: pending
resolves_phase: null
owner: "999.131"
---

# An SMTP host that does not offer STARTTLS is recorded as a scan error, not as an assessed endpoint

Confidence rule D-04 (Phase 184.1) says a reached-but-no-crypto email endpoint, such as an SMTP
server that never offers STARTTLS, counts as assessed and is "usually a HIGH-severity finding". The
real scanner does neither:

- sslyze cannot complete a STARTTLS scan against such a server, so `_scan_one_sslyze_email`
  returns None (`quirk/scanner/email_scanner.py:160-163`) and the stdlib fallback runs.
- The fallback calls `smtp.starttls(...)` (`email_scanner.py:306`), which raises
  `SMTPNotSupportedError`; the generic handler stores it as `ep.scan_error`
  (`email_scanner.py:471-473`).
- `build_evidence_summary` drops any row with `scan_error` from `assessed_crypto_count`
  (`quirk/intelligence/evidence.py:251`), so confidence coverage goes down.
- `evaluate_endpoints` routes the row to the generic scan-error branch and emits only an INFO
  "Informational protocol observation" (`quirk/engine/findings_evaluator.py:485-534`).
  `evaluate_email_endpoints` emits its STARTTLS finding only when TLS was negotiated
  (`findings_evaluator.py:818`). No HIGH finding exists for "STARTTLS not offered".
- The row does tick `motion_email_starttls_missing_count` (`evidence.py:479-484`), so the
  data-in-motion subscore is penalised.

Probe (isolated HOME, local fake SMTP server whose EHLO omits STARTTLS, through
`_scan_one_fallback_email`): `scan_error: SMTPNotSupportedError: STARTTLS extension not supported by
server.`, `assessed_crypto_count 0 / assessable_endpoint_count 1`, findings `[('INFO',
'Informational protocol observation')]`, `motion_email_starttls_missing_count 1`. Conversely a
STARTTLS row that timed out (no `scan_error`, only `tls_blocker_reason="TIMEOUT"`) counts as
assessed (1/1). The D-04 regression fixture
(`tests/test_evidence_coverage_regression.py:62-64`) builds the row without `scan_error`, so it
cannot see this.

- [ ] Treat "STARTTLS not offered" as an assessment result in the fallback (no `scan_error`; set a
      blocker reason or a dedicated flag) and emit a severity finding for plaintext-only mail.
- [ ] Decide whether timeout/refused STARTTLS rows should count as assessed.
- [ ] Add a scanner-level test that runs the fallback against a no-STARTTLS server.
- [ ] Revert the §17 doc narrowing in docs/report-interpretation.md once fixed.

## Feasibility & Effort

- **CONFIRMED** path by reading `email_scanner.py:160-163,302-316,446-473`, `evidence.py:251,479-484`,
  `findings_evaluator.py:485-534,818`, and by the probe above.
- **LIKELY** effort **S-M**: a branch in three `_fallback_*_starttls` helpers plus one finding rule and
  tests. Moves scores on estates with plaintext-only mail, so check whether it needs a
  `SCORING_VERSION` note (`quirk/intelligence/scoring.py:29`).
- **UNKNOWN**: severity for "no STARTTLS" (HIGH as the design says, or MEDIUM). No spike needed.

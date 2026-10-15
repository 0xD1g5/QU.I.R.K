---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-LAB; ledger rows DCL-CHAOSLAB-0332 and DCL-CHAOSLAB-0348 (docs/chaos-lab.md smime and adcs "Expected findings")
priority: medium
area: quirk/engine/findings_evaluator.py, quirk/dashboard/api/routes/scan.py (_derive_findings, _derive_identity_findings), quantum-chaos-enterprise-lab/expected_results_v4.md (smime, adcs sections)
status: pending
resolves_phase: null
owner: "999.132"
---

# S/MIME and AD CS weaknesses are rated but never listed as findings anywhere

> **Phase 228 update (2026-10-15): the dashboard half of this todo is true again.** For a short while the dashboard
> listed SMIME and ADCS rows under a TLS-certificate title: `findings_for_endpoint` ran its certificate checks on every
> row, and the S/MIME and AD CS scanners set `cert_pubkey_alg` / `cert_pubkey_size`
> (`smime_scanner.py:276-288`, `adcs_scanner.py:383-393`), so an RSA-1024 S/MIME key produced HIGH "TLS certificate uses
> undersized RSA key" (this was the GC3-LAB3 correction that used to sit here). That dashboard-only emission is gone.
> Phase 228 commit `2cd1b90d` (near-expiry MEDIUM plus TLS-only gating, D-05) and `6df84979` (the shared dashboard
> scoring-findings helper) gate the dashboard's TLS and certificate checks on `runs_tls_certificate_checks(ep)`, the same
> predicate the report uses. Neither surface now lists an S/MIME or AD CS weakness as a finding, which makes this todo's
> title accurate again. **Surfacing them as findings on BOTH surfaces remains this todo's job (999.132).** The owner stays
> "999.132".
>
> Protocols that lost a dashboard finding under D-05 (D-06, from the scanner-source enumeration in
> `228-RESEARCH.md`): SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS, POP3-STARTTLS, POP3S, KAFKA-TLS, AMQPS,
> AMQPS/Azure-ServiceBus, HTTPS/AWS-SQS, REDIS-TLS, CODE_SIGNING, SMIME, ADCS (CA row), VAULT, AWS, AZURE, AZURE_BLOB,
> GCP, CLOUD_SQL, JWT and OPENAPI. Email, broker and code-signing rows are still covered on the dashboard, now by the
> report's own evaluators (D-20, `evaluate_protocol_service_endpoints`), not by the TLS certificate checks. SMIME, ADCS and
> the cloud, vault and API labels have no such evaluator, so they are the open part of this todo.

The S/MIME and AD CS scanners put a severity on each endpoint row they emit
(`quirk/scanner/smime_scanner.py:285 severity=severity`, `quirk/scanner/adcs_scanner.py:391 severity="HIGH"`,
`quirk/scanner/adcs_scanner.py:453 severity=severity`). The CBOM builder reads those rows
(`quirk/cbom/builder.py:700`, `:710`) and the score counts them (`quirk/intelligence/scoring.py:100-106`).
Nothing turns them into a finding:

- CLI: the findings stage (`run_scan.py:4077-4104`) calls `evaluate_endpoints`, the email, broker and code-signing
  evaluators, and `evaluate_identity_endpoints(saml_endpoints)`. None has an SMIME or ADCS branch. An in-process
  `evaluate_endpoints(cfg, [SMIME HIGH row, ADCS HIGH row])` returned 0 findings.
- Dashboard: `_derive_findings`, `_derive_identity_findings` (KERBEROS/SAML/DNSSEC only, `scan.py:430-464`) and
  `_derive_dar_findings` returned 0 / 0 / 0 for the same two rows. `grep -rl 'SMIME\|smime_scan_json'` over
  `quirk/dashboard`, `quirk/reports` and `src/dashboard/src` finds nothing.

So the `smime` lab profile's alice/bob weak certs and the `adcs` profile's weak CA and ESC1 template lower the
score, but no operator-facing list names them. The v4 oracle says "Findings appear in the Identity tab
(`source="smime"`)" (`expected_results_v4.md` smime section) and the same for adcs; no code supports that.

`docs/chaos-lab.md` (GC3) says the dashboard lists key-bearing SMIME/ADCS rows via its certificate checks; Phase 228 removed
that, so neither surface lists them and that note needs the same correction when this todo is worked. If a dedicated evaluator is added, update the §3 "Reading the finding
columns" note and the smime/adcs sections.

- [ ] Decide whether S/MIME and AD CS rows should be findings (the score already treats them as weaknesses).
- [ ] If yes, add an SMIME/ADCS branch to the shared identity evaluator so the CLI and dashboard both list them.
- [ ] Correct the oracle's "Findings appear in the Identity tab" sentences either way, and the `docs/chaos-lab.md` note above.

## Feasibility & Effort

**CONFIRMED** gap (source read plus the two in-process probes above). Effort **S-M**: the shared evaluator
pattern already exists (`evaluate_identity_endpoints`, `quirk/engine/findings_evaluator.py:1142`, used by both
`run_scan.py:4102` and the dashboard route), so a new branch keyed on `protocol in {"SMIME", "ADCS"}` with the
row's own severity is small; most of the effort is titles, tests and the parity fixture. Unknown: whether ADCS
coverage-gap LOW rows should become findings or stay disclosure-only. No spike needed.

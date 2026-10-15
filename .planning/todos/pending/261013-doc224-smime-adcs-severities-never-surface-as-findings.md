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

> **Correction (GC3-LAB3, 2026-10-13): the dashboard half of this todo is false.** The GC2 probe below used SMIME and
> ADCS rows with no certificate fields, which never reach the dashboard's certificate checks. `_derive_findings`
> (`quirk/dashboard/api/routes/scan.py:339-367`) runs `findings_for_endpoint` (`:120-337`) on every row except
> KERBEROS/SAML/DNSSEC, and the S/MIME scanner and the AD CS CA path set `cert_pubkey_alg` / `cert_pubkey_size`
> (`smime_scanner.py:276-288`, `adcs_scanner.py:383-393`). Re-probed with scanner-shaped rows: an SMIME or ADCS CA row
> with an RSA-1024 key yields HIGH "TLS certificate uses undersized RSA key" on the dashboard Findings page (the
> `smime` lab profile's alice and bob are RSA-1024), and an SMIME ECDSA key yields MEDIUM "Quantum-vulnerable algorithm".
> Only the AD CS ESC template and coverage-gap rows (no key fields) are absent from both surfaces. The CLI half stands:
> no CLI evaluator lists SMIME or ADCS rows (only the generic scan_error INFO). So the real defect is narrower and
> different: **the CLI never lists these weaknesses, and the dashboard lists them under a TLS-certificate title rather
> than an S/MIME- or AD CS-specific one, and misses the ESC rows.** `docs/chaos-lab.md` was corrected in GC3 (ledger
> rows DCL-CHAOSLAB-0803/0804/0807/0813/0819/0821-0823). Read the checklist below with that correction.

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

`docs/chaos-lab.md` (GC3) now says which surface lists which row: the dashboard lists key-bearing SMIME/ADCS rows via
its certificate checks; the CLI lists none. If a dedicated evaluator is added, update the §3 "Reading the finding
columns" note and the smime/adcs sections.

- [ ] Decide whether S/MIME and AD CS rows should be findings (the score already treats them as weaknesses).
- [ ] If yes, add an SMIME/ADCS branch to the shared identity evaluator so the CLI and dashboard both list them.
- [ ] Correct the oracle's "Findings appear in the Identity tab" sentences either way.

## Feasibility & Effort

**CONFIRMED** gap (source read plus the two in-process probes above). Effort **S-M**: the shared evaluator
pattern already exists (`evaluate_identity_endpoints`, `quirk/engine/findings_evaluator.py:1142`, used by both
`run_scan.py:4102` and the dashboard route), so a new branch keyed on `protocol in {"SMIME", "ADCS"}` with the
row's own severity is small; most of the effort is titles, tests and the parity fixture. Unknown: whether ADCS
coverage-gap LOW rows should become findings or stay disclosure-only. No spike needed.

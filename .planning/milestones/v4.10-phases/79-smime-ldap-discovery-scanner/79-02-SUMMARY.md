---
phase: 79-smime-ldap-discovery-scanner
plan: 02
status: complete
commit: bbd1d81
requirements: [SMIME-01, SMIME-02, SMIME-05, SMIME-06]
files_added:
  - quirk/scanner/smime_scanner.py
files_modified:
  - quirk/models.py
  - quirk/cbom/builder.py
  - quirk/config.py
  - run_scan.py
---

# Phase 79 Plan 02: SMIME Scanner Module + CBOM Wiring — Summary

S/MIME LDAP discovery scanner module landed with CBOM Pass-1 emission,
Pass-2/3 skip-list extension, and full orchestrator wiring. The scanner
produces `protocol="SMIME"` IdentityFindings consumable by the existing
React Identity tab, CBOM, and the Plan 79-03 scoring/evidence pipeline.

## Files

| File | Action | LOC delta |
|------|--------|-----------|
| `quirk/scanner/smime_scanner.py` | **NEW** | +291 |
| `quirk/models.py` | modified (+1) | smime_scan_json ORM column |
| `quirk/cbom/builder.py` | modified (+12 / -2) | Pass-1 emit branch + Pass-2/3 tuple appends |
| `quirk/config.py` | modified (+12) | enable_smime + smime_targets + smime_search_base + smime_timeout |
| `run_scan.py` | modified (+27 / -3) | smime phase dispatch + resume + endpoint aggregation |

**Total:** 1 file added, 4 files modified, 339 insertions / 4 deletions.

## Scanner module — public surface

- `scan_smime_targets(targets, timeout=10, logger=None, session_start=None, *, search_base=None) -> list[CryptoEndpoint]`
- `_realm_to_base_dn(realm) -> str` (verified: `"QUIRK.LAB"` → `"DC=quirk,DC=lab"`)
- `_parse_smime_cert(cert_bytes) -> dict | None` (DER-first, PEM fallback)
- `_classify_severity(parsed) -> (sev, reasons)`

LDAP enumeration uses `ldap3.extend.standard.paged_search` with
`paged_size=500`, retrieves `userCertificate` + `userSMIMECertificate`
via `entry['raw_attributes']` (no `;binary` suffix — confirms D-79-R4).
Multi-cert-per-user supported. SAFE certs (`carol`) produce no finding.
Expired certs emit `|expired=true` sentinel in `service_detail` for
evidence.py to read.

## CBOM edit sites

| Pass | Anchor | Line(s) | Edit |
|------|--------|---------|------|
| Pass-1 | after SAML branch | 449–462 | `elif ep.protocol == "SMIME":` registers `cert_pubkey_alg` |
| Pass-2 | cert-component skip tuple | 528 | append `"SMIME"` |
| Pass-3 | protocol-component skip tuple | 610–614 | append `"SMIME"` |

`grep -cE '"SMIME"' quirk/cbom/builder.py` returns **3** (one per site).

## Orchestrator wiring

`run_scan.py` `_run_smime_phase()` block is inserted **immediately after
the Kerberos block** (lines ~1391+ post-edit). It reads
`cfg.connectors.enable_smime`, `cfg.connectors.smime_targets`,
`cfg.connectors.smime_search_base`, `cfg.connectors.smime_timeout`, then
calls `scan_smime_targets(...)` via `_wrapped_phase(...)` so partial
failures route into `error_endpoints`.

Three downstream sites updated symmetrically:
1. `_dar_protocols` tuple now includes `"SMIME"` (resume detection).
2. Resume branch extracts `smime_endpoints` from `_resumed_endpoints`.
3. `_dar_eps` (DB flush) and final endpoint aggregation list both
   include `smime_endpoints`.

No CLI flag was added — symmetric with SAML/Kerberos, which are
config-driven only. The chaos lab validation command in
`expected_results_v4.md` uses `quirk scan` with `enable_smime: true`
and `smime_targets: [...]` in the YAML config (Plan 79-01 contract).

## Config surface (additive)

```python
# quirk/config.py ScanConnectorsConfig
enable_smime: bool = False
smime_targets: list = field(default_factory=list)
smime_search_base: Optional[str] = None
smime_timeout: int = 10
```

## Verification

- `python -m compileall quirk/` exits 0.
- `python -m pytest tests/test_cbom*.py -q --deselect tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles` →
  same 26 pre-existing failures both before and after (confirmed via
  `git stash` diff). **Zero regressions.**
- Pre-existing CBOM failures: `RSA-kex`/`ssh-dss` UNKNOWN classifier
  (broker, email, ssh-weak profiles) and CycloneDX 1.6 schema
  validation regressions — both untouched by this plan.
- `python -m pytest tests/test_scan_error_gate.py -q` → 9 passed.
- **Mock-based smoke test** with `unittest.mock` stubbing
  `_bind_and_search`: 3 generated DER certs (alice RSA-1024/SHA256,
  bob RSA-1024/SHA256, carol RSA-2048/SHA256) produced **2 HIGH
  findings** (alice + bob), carol filtered SAFE. All findings carry
  `protocol="SMIME"` and populated `smime_scan_json`. Independent
  classifier checks for SHA-1 / expired-only / weak+expired / SAFE
  paths all pass.

## Deviations from plan

1. **CLI flag (`--smime-target` / `--smime-base`) NOT added.** Plan
   Task 3 said "add if existing CLI exposes per-scanner target flags;
   otherwise rely purely on config-file driven targets." Grep
   confirmed SAML and Kerberos are config-driven only — no
   `--saml-target` / `--kerberos-target` CLI flags exist. Following
   the symmetric pattern, SMIME is also config-driven via
   `enable_smime: true` + `smime_targets: [...]`. Plan 79-01's
   expected_results_v4.md doc may need a tweak to reflect this in
   Plan 79-04 finalization, but that's outside Plan 79-02's scope.

2. **No PEM-fallback unit-test coverage in smoke harness.** The
   `_parse_smime_cert` PEM-fallback branch is exercised at runtime
   (if DER parse raises, PEM is attempted) but the synthetic smoke
   test only feeds DER bytes. Full coverage will land in Plan 79-04
   (`tests/test_smime_scanner.py`).

3. **`signature_hash_algorithm.name` Capture** added under
   `cert_sig_alg` field on the emitted `CryptoEndpoint`. The plan
   sketch did not explicitly list this field, but capturing the
   signing-algorithm name surfaces it for downstream classification
   without parsing JSON. Additive — no contract change.

## Plan 79-03 boundary respected

`quirk/intelligence/scoring.py` and `quirk/intelligence/evidence.py`
were **not modified** in this commit. Wave-parallel safety preserved.

## Self-Check: PASSED

- `quirk/scanner/smime_scanner.py` exists (291 lines, exports
  `scan_smime_targets`). ✓
- `quirk/cbom/builder.py` Pass-1 branch contains
  `elif ep.protocol == "SMIME":`. ✓
- Both Pass-2 and Pass-3 tuples contain `"SMIME"` literal. ✓
- Commit `bbd1d81` exists in git log. ✓
- Plan 79-03's files (`scoring.py`, `evidence.py`) unmodified in this
  commit. ✓
- `tests/test_score_weights_invariant.py` unmodified (Phase 83 owns). ✓

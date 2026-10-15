---
type: todo
created: 2026-10-13
source: Phase 224 evidence audit 3 (DCL-OPS-A-1229, docs/operators-guide.md "Code-signing inventory"); fixed in round A3FIX
priority: high
area: quirk/scanner/codesign_scanner.py (scan_codesign_from_tls_endpoints), quirk/scanner/tls_scanner.py (tls_capabilities_json), tests/test_codesign_*.py
status: pending
resolves_phase: 230
---

# The code-signing TLS-EKU source never fires in a real scan; fixture-injected tests hide it

`--inventory-code-signing` runs two sources (`run_scan.py:3762-3786`). The second,
`scan_codesign_from_tls_endpoints`, is meant to find CodeSigning-EKU certificates among the certificates the TLS
phase already captured. It reads only `tls_capabilities_json["eku_oids"]` and skips every endpoint without that
key (`quirk/scanner/codesign_scanner.py:449-459`).

Nothing in a real scan writes `eku_oids`:
- The only writer of `tls_capabilities_json` is `quirk/scanner/tls_scanner.py:352-360` (sslyze path). It writes
  `source`, `sslyze_version`, `accepted_by_version`, `chain_depth`, `chain_verified`, `elliptic_curves`.
- The stdlib fallback path (`tls_scanner.py:381-512`) never sets `tls_capabilities_json` at all.
- `grep -rn eku_oids quirk/ run_scan.py` finds only the reader in `codesign_scanner.py`.
- The TLS scanner does not parse the leaf's ExtendedKeyUsage extension anywhere.

Every test that exercises this source injects the key by hand, so the suite is green while the path is dead:
`tests/test_codesign_scanner.py:174,187`, `tests/test_codesign_expiry_classification.py:41`,
`tests/test_codesign_cbom.py:231`, `tests/test_codesign_column_rename.py:137`.

Live probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/a3fix-codesign-tls-eku-live-probe.py`):
a loopback TLS server whose self-signed leaf carries EKU `1.3.6.1.5.5.7.3.1` + `1.3.6.1.5.5.7.3.3`.
`tls_scanner.scan_one` (sslyze) -> caps keys without `eku_oids` -> 0 CODE_SIGNING endpoints; the fallback path ->
`tls_capabilities_json` None -> 0. Control: the same endpoint with `eku_oids` injected -> 1 CODE_SIGNING (MEDIUM).

The operators-guide now says this source finds nothing in a real scan.

- [ ] In both TLS parse sites, read the leaf's `ExtendedKeyUsage` and record its dotted OIDs (as `eku_oids` in the
      caps JSON, or a dedicated column), or remove the TLS source and its docs.
- [ ] Replace the fixture-injection tests with one that runs the real TLS scan against a loopback server presenting a
      CodeSigning-EKU leaf (the probe above is a ready template) and asserts a CODE_SIGNING endpoint.
- [ ] Update `docs/operators-guide.md` ("Code-signing inventory" and the scanner table row) and `docs/configuration.md` (`enable_codesign` row, "In-process TLS EKU check", `--inventory-code-signing` row) when fixed.

## Feasibility & Effort

- **CONFIRMED** defect: reader at `quirk/scanner/codesign_scanner.py:454` (`caps.get("eku_oids")`); sole caps writer
  `quirk/scanner/tls_scanner.py:352-360` has no EKU key; fallback `tls_scanner.py:449-477` sets cert fields but not caps.
- **LIKELY** effort **S-M**: `cryptography`'s `cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)` is
  available at both parse sites (fallback already holds `cert` at `tls_scanner.py:455`; the sslyze path parses the leaf
  near `:242`). Writing into the caps JSON on the fallback path means creating that blob there, which other readers
  (`quirk/engine/findings_evaluator.py:307`, `quirk/intelligence/scope_signature.py:281`) must tolerate; check them.
- **UNKNOWN**: whether the scope-signature evidence field treats a non-null `tls_capabilities_json` as "deep TLS ran"
  (`scope_signature.py:257`); populating it on the fallback path could change closure evidence. Check before choosing
  the caps blob over a new column. No spike needed beyond that read.

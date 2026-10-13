---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-LAB3; ledger rows DCL-CHAOSLAB-0383, 0831, 0834-0836 (docs/chaos-lab.md §3.30 oqs-nginx)
priority: medium
area: quirk/scanner/tls_scanner.py (_scan_one_fallback, _pubkey_info), quantum-chaos-enterprise-lab/docker-compose.yml (oqs-nginx comment)
status: pending
resolves_phase: null
---

# The TLS scanner turns an ML-DSA certificate into a scan error and records no key, signature or expiry

A post-quantum server certificate is exactly what a quantum-readiness scanner should inventory, and today it cannot.
Reproduced on loopback with `openssl s_server -tls1_3 -groups X25519MLKEM768` serving a self-signed ML-DSA-65
certificate (the `oqs-nginx` lab profile's shape) and Python `ssl` linked to OpenSSL 4.0.3:

- `tls_scanner.scan_one` completes the handshake and stores `cert_subject` / `cert_issuer`, then
  `cert.signature_hash_algorithm` raises `UnsupportedAlgorithm: Signature algorithm OID: 2.16.840.1.101.3.4.3.18 not
  recognized` (`quirk/scanner/tls_scanner.py:460`). The row ends with `scan_error='TLS_ERROR: ...'`,
  `cert_pubkey_alg=None`, `cert_pubkey_size=None`, `cert_sig_alg=None`, and no `cert_not_after`
  (the expiry lines `:475-476` are never reached).
- Even past that line, `_pubkey_info` (`:45-55`) maps any key that is not RSA, EC, Ed25519 or Ed448 to
  `("Unknown", None)`.
- The CLI then lists the row as INFO "Informational protocol observation" (`findings_evaluator.py` generic scan_error
  branch). The PQC probe separately records only the negotiated group (`X25519MLKEM768`).

A second, smaller defect: the compose comment above `oqs-nginx` says a live scan needs `--allow-internal-targets`
(`quantum-chaos-enterprise-lab/docker-compose.yml`, "Requires --allow-internal-targets for live QUIRK scan"). Neither
the TLS scanner, the PQC probe, the target expander nor the fingerprinter reads that flag
(`grep -c allow_internal` on all four is 0), so the comment is stale. `docs/chaos-lab.md` §3.30 now says so.

- [ ] Guard `signature_hash_algorithm` (ML-DSA has no separate hash) and record the signature OID name instead.
- [ ] Extend `_pubkey_info` for ML-DSA / SLH-DSA (OID-based when `cryptography` has no key class), with a size.
- [ ] Keep the expiry and SPKI fingerprint when only the algorithm is unrecognised.
- [ ] Fix the compose comment; then update `docs/chaos-lab.md` §3.30 (rows 0383, 0834-0836) and §5's 39444 row.

## Feasibility & Effort

- **CONFIRMED** by the loopback probe above (`gc3-lab3-oqs-tls-scanner-probe`) and a read of
  `quirk/scanner/tls_scanner.py:454-476` (subject/issuer set at `:457-458` before the raising call at `:460`) and
  `:45-55` (`_pubkey_info`'s four classes).
- **Effort M.** The guard is small; the PQC key-type mapping needs a decision on names shared with
  `quirk/cbom/classifier.py` and with the scoring buckets tracked by
  `261013-doc224-undetermined-key-type-penalises-dsa-and-ml-dsa.md` (do those together). The sslyze path
  (`_scan_one_sslyze`, `:133`) needs the same check; not probed here.
- **Unknown:** whether the installed `cryptography` (46.0.6 here) exposes an ML-DSA public-key class; if not, parse the
  SPKI OID directly. No spike needed beyond that check.

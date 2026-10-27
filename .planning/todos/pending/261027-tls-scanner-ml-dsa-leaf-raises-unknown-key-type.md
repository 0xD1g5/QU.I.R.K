---
type: todo
created: 2026-10-27
source: Phase 234 (D-20; decision record §10)
priority: low
area: quirk/scanner/tls_scanner.py (_pubkey_info), quirk/intelligence/evidence.py (cert_key_type_counts.PQC)
status: pending
resolves_phase: null
owner: "999.139"
---

# The TLS scanner cannot read an ML-DSA leaf certificate's key, so the PQC certificate bucket never fires on real scans

**Owner:** 999.139

Scoring 4.0 (Phase 234, O-4) added a `cert_key_type_counts.PQC` bucket that earns a single agility credit for an
ML-DSA, SLH-DSA or composite certificate key. On a real scan it stays dormant: for an ML-DSA leaf, `cryptography`
raises "Unknown key type" when the scanner loads the public key, in `quirk/scanner/tls_scanner.py::_pubkey_info`
(defined at `:45`, called at `:257` and `:482`). The key type therefore never reaches evidence as a PQC name.

The ML-DSA SubjectPublicKeyInfo algorithm OIDs are (RFC 9881):

- `2.16.840.1.101.3.4.3.17` ML-DSA-44
- `2.16.840.1.101.3.4.3.18` ML-DSA-65
- `2.16.840.1.101.3.4.3.19` ML-DSA-87

The bucket itself is unit- and mutation-tested (record §11, M6;
`tests/test_intelligence_evidence.py::test_pqc_cert_key_bucket_counts_ml_dsa_and_slh_dsa`), so only the
scanner side is missing.

## Proposed fix shape

When `cryptography` cannot load the key, read the SPKI algorithm OID from the certificate's DER
(`cert.public_key_algorithm_oid` where available, or a minimal ASN.1 parse of `tbsCertificate.subjectPublicKeyInfo`)
and map the three OIDs above to `ML-DSA-44/65/87` with the parameter-set size, so the existing evidence prefix
match puts the row in the PQC bucket. Add the SLH-DSA OIDs in the same table if a test certificate is available.
Needs an ML-DSA test certificate (OpenSSL 3.5+ can generate one) for a scanner-level test.

## Feasibility & Effort

**CONFIRMED** by the record's D-20 finding. Effort **M**: the OID table is small; the test certificate and a
scanner-level fixture are the work.

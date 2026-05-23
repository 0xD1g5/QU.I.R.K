---
phase: 95-code-signing-certificate-inventory
reviewed: 2026-05-23T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - quirk/scanner/codesign_scanner.py
  - quirk/cbom/builder.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
  - run_scan.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 95: Code Review Report

**Reviewed:** 2026-05-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 95 adds code-signing certificate inventory via two passive sources (LDAP
`userCertificate` filtered to the CodeSigning EKU, and an in-process TLS-EKU
check on already-captured endpoints), with CBOM dedup, evidence counting, and a
scoring agility signal.

The LDAP path is well-defended: anonymous bind only, hardcoded
`(userCertificate=*)` filter (no DN/filter interpolation), `safe_str()` routing
on all logged DNs/exceptions, paged `paged_size=500`, ldap3-only (no impacket),
and DER-then-PEM parse wrapped in try/except so malformed certs cannot crash.
`SCORE_WEIGHTS` verified at sum 299.0 / count 40. Protocol casing is the exact
`CODE_SIGNING` literal across all four consumers. `run_scan` wiring is correct:
`_run_codesign_phase` runs after `tls_endpoints` is populated, and the flag-off
path returns `[]` before importing the scanner module.

The headline defect is in the CSIGN-03 cross-source dedup: it is **dead in
production**. The scanner never populates the `cert_subject` / `cert_not_after`
ORM columns on emitted `CODE_SIGNING` endpoints, so the surrogate-key match in
the builder can never fire against real scanner output. The passing test that
"proves" the contract injects those fields via a MagicMock that does not reflect
the scanner's actual output shape — false confidence.

## Critical Issues

### CR-01: CSIGN-03 cross-source dedup never fires in production (TLS-wins reconciliation is dead)

**File:** `quirk/cbom/builder.py:783` (consumer) / `quirk/scanner/codesign_scanner.py:368-380, 450-462` (producer)

**Issue:** The builder's cross-source reconciliation depends on
`_codesign_surrogate_key(ep)` returning `(cert_subject, cert_pubkey_alg,
cert_not_after)` — all three read from ORM columns on the CODE_SIGNING endpoint
(`builder.py:404-408`). But **neither scanner path sets `cert_subject` or
`cert_not_after`** on the emitted CODE_SIGNING endpoint:

- `scan_codesign_from_ldap` (lines 368-380) sets only `cert_pubkey_alg`,
  `cert_pubkey_size`, `cert_sig_alg`, `service_detail`, `severity`,
  `smime_scan_json`. Subject/not_after live inside `service_detail` and the
  JSON blob, not the columns.
- `scan_codesign_from_tls_endpoints` (lines 450-462) likewise sets only
  `cert_pubkey_alg`/`size`/`sig_alg`. Subject/not_after are embedded in the
  `surrogate=...` string in `service_detail`, not the columns.

Verified empirically: a real `scan_codesign_from_tls_endpoints` endpoint reports
`cert_subject = None` and `cert_not_after = None`. Therefore
`_codesign_surrogate_key()` returns `None` for every real CODE_SIGNING endpoint,
the `surrogate in _tls_surrogate_index` branch at `builder.py:783` is never
taken, and the "TLS-derived component wins, code-signing annotates" behaviour
(ROADMAP Success Criterion 3 / CSIGN-03) does not happen. A cert seen via both
TLS and code-signing produces **two** cert components, not one.

The test `tests/test_codesign_cbom.py::test_cbom_tls_plus_codesign_no_dup` masks
this: its `_make_codesign_ep` MagicMock sets `ep.cert_subject` and
`ep.cert_not_after` directly (lines 44, 48), a shape the scanner never emits.
The test passes against a fiction.

**Fix:** Populate the surrogate-key columns on emitted CODE_SIGNING endpoints so
the builder can reconcile, then re-point the test fixture at real scanner output.
In `scan_codesign_from_tls_endpoints`:
```python
code_ep = CryptoEndpoint(
    host=ep.host,
    port=ep.port,
    protocol=CODE_SIGNING,
    cert_pubkey_alg=getattr(ep, "cert_pubkey_alg", None),
    cert_pubkey_size=getattr(ep, "cert_pubkey_size", None),
    cert_sig_alg=getattr(ep, "cert_sig_alg", None),
    cert_subject=cert_subject or None,          # ADD — feeds surrogate key
    cert_not_after=not_after,                   # ADD — feeds surrogate key
    service_detail=detail,
    ...
)
```
And in `scan_codesign_from_ldap`, set `cert_subject` from the parsed cert subject
(parse it in `_parse_codesign_cert` and surface it) and `cert_not_after` from the
parsed `not_after` datetime. Then change `_make_codesign_ep` / `_make_tls_ep` to
build endpoints through the real scanner emit path (or assert the columns are
actually set) so the regression is caught.

Note the type mismatch this also exposes: TLS-source `cert_not_after` is a
`datetime` while the LDAP-source value, if added naively from `parsed["not_after"]`,
is an ISO string. `_tls_surrogate_key` / `_codesign_surrogate_key` both
`str(...)` the value, so a datetime renders as `2028-06-01 00:00:00+00:00` while
an ISO string renders as `2028-06-01T00:00:00Z` — these will not match. Normalise
both sides to a single canonical string before keying.

## Warnings

### WR-01: Dead first loop in Pass-2b builds and immediately discards `_tls_surrogate_index`

**File:** `quirk/cbom/builder.py:740-748`

**Issue:** The first loop iterates `cert_components`, computes `subj`, comments
"we cannot recover cert_pubkey_alg ... so instead we'll re-scan endpoints," and
never stores anything. Line 749 then reassigns `_tls_surrogate_index = {}`,
throwing away the loop's only side effect. `subj` is computed and unused. This is
pure dead code that obscures the real index-building loop below it.

**Fix:** Delete lines 740-748 entirely; keep the authoritative endpoint-based
build starting at line 749.
```python
    # Build surrogate-key index from TLS-derived cert components (authoritative).
    _tls_surrogate_index: dict[tuple[str, str, str], Component] = {}
    for ep in endpoints:
        ...
```

### WR-02: Convoluted, error-prone protocol filter in surrogate-index build

**File:** `quirk/cbom/builder.py:751-759`

**Issue:** The guard `if ep.protocol not in ("TLS",) and ep.protocol in (...big list...)` is
a double negative that only works because every non-TLS cert-emitting protocol
must be enumerated in the second tuple. Any protocol that emits a Pass-2 cert
component but is omitted from that list would silently be treated as a TLS
surrogate source and could poison the index. The intent is simply "only TLS
endpoints," which the very next line (`if ep.protocol == "CODE_SIGNING": continue`)
half-restates.

**Fix:** Replace the whole guard with the direct intent:
```python
    for ep in endpoints:
        if ep.protocol != "TLS":
            continue
        key = _tls_surrogate_key(ep)
        ...
```
(If non-TLS protocols are ever meant to contribute surrogate keys, enumerate
*those* explicitly rather than enumerating the exclusions.)

### WR-03: `"weak"` substring match in evidence counter is subject/DN-sensitive (false positives)

**File:** `quirk/intelligence/evidence.py:333-335`

**Issue:** `codesign_weak_algo_count` increments when `"weak" in _cs_detail`
(lowercased `service_detail`). For LDAP-source endpoints the detail begins with
`safe_str(user_dn)` (`codesign_scanner.py:355`), and for TLS-source endpoints it
embeds `cert_subject` inside the `surrogate=` token (`codesign_scanner.py:436-438`).
Any DN or subject containing the literal substring "weak" (e.g.
`CN=weak-signing-lab`, `OU=Weakly Trusted`) will increment the weak counter even
for a SAFE certificate, inflating the agility penalty. The sentinel and the
free-text fields share the same delimited string with no token boundary.

**Fix:** Match a delimited token, not a bare substring:
```python
_cs_tokens = str(getattr(ep, "service_detail", "") or "").split("|")
if "weak" in _cs_tokens:
    codesign_weak_algo_count += 1
```
This matches the scanner's `|weak` sentinel (`codesign_scanner.py:359, 439`) exactly
and is immune to subject/DN content.

### WR-04: `expired` computed but never propagated; `not_after`/expiry never reach the endpoint or evidence

**File:** `quirk/scanner/codesign_scanner.py:116-117, 362-377`

**Issue:** `_parse_codesign_cert` computes `not_after` and `expired`, and they are
copied into `scan_dict` (the JSON blob), but the emitted `CryptoEndpoint` for the
LDAP path sets neither `cert_not_after` nor any expiry sentinel. Consequently:
(a) the evidence `certificate_observations.expired_count` / `expiring_count`
logic (which keys on `ep.cert_not_after` being a `datetime`, evidence.py:167-174)
never counts code-signing cert expiry; (b) an expired-but-strong-algo
code-signing cert produces no finding at all (severity is `None` when no weak
algo, so the endpoint is dropped at lines 349-351). Expiry of code-signing certs
is silently invisible. Combined with CR-01, the missing `cert_not_after` column
also breaks the surrogate key.

**Fix:** Set `cert_not_after` on the emitted endpoint (parse it as a datetime and
pass it through), which simultaneously fixes the surrogate-key gap in CR-01 and
lets the existing evidence expiry counters work for CODE_SIGNING.

## Info

### IN-01: SAFE code-signing certs are dropped, defeating inventory intent

**File:** `quirk/scanner/codesign_scanner.py:349-351`

**Issue:** `scan_codesign_from_ldap` emits an endpoint only for *non-SAFE*
(weak-algo) certs; SAFE certs `continue` with no endpoint. The feature is named
"code-signing certificate **inventory**," and CSIGN-01 describes discovering
certificates, but a healthy code-signing cert leaves no inventory record (no CBOM
component, no protocol_count). If the goal is inventory + risk flagging, SAFE
certs should still be inventoried. If by-design risk-only, document it; either
way the `protocol_counts["CODE_SIGNING"]` metric will only ever reflect weak
certs, which is misleading.

**Fix:** Emit an endpoint for every EKU-matching cert and let `severity=None`
distinguish SAFE; or explicitly document the risk-only scope in the module
docstring and the evidence comment.

### IN-02: Ed25519 / Ed448 code-signing certs classified UNKNOWN, never weak-flagged

**File:** `quirk/scanner/codesign_scanner.py:100-109, 138-167`

**Issue:** `_parse_codesign_cert` only recognises `RSAPublicKey` and
`EllipticCurvePublicKey`; Ed25519/Ed448 fall to `key_alg="UNKNOWN", key_bits=None`.
`_classify_codesign_severity` then cannot flag them (no RSA/EC branch matches),
and SHA-1 detection relies on `signature_hash_algorithm.name`, which is `None`
for EdDSA certs (the `try/except` yields `""`). These are quantum-vulnerable like
all classical signatures but are silently treated as having no weak indicator.
Acceptable for v1 if documented, but worth noting since code-signing is exactly
where Ed25519 appears.

**Fix:** Recognise Ed25519/Ed448 explicitly (even if only to record key_alg) so
the inventory is accurate; defer any weak-classification decision to product.

### IN-03: `_dar_protocols` resume tuple mixes label conventions (pre-existing, confirm not regressed)

**File:** `run_scan.py:1515-1527`

**Issue:** The resume protocol tuple uses `"AZURE-BLOB"`, `"K8S"`, `"GCS"`
(hyphenated/short) while evidence.py keys on `AZURE_BLOB`, `KUBERNETES`. The new
`CODE_SIGNING` entry is correctly the exact uppercase literal and matches the
emitter, so Phase 95 itself is consistent. Flagged only to confirm the new entry
did not adopt the inconsistent neighbours' convention — it did not. No change
required for Phase 95; the AZURE-BLOB/K8S/GCS divergence is pre-existing and out
of scope.

---

_Reviewed: 2026-05-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

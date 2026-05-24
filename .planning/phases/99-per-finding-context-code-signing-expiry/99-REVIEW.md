---
phase: 99-per-finding-context-code-signing-expiry
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - quirk/reports/content_model.py
  - quirk/engine/findings_evaluator.py
  - quirk/scanner/codesign_scanner.py
  - run_scan.py
  - quirk/reports/technical.py
  - quirk/reports/templates/report.html.j2
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 99: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 99 adds per-finding `quantum_risk` context, a centralized `REMEDIATION_CATALOG`,
conditional `NIST_IR_8547_DEPRECATION` appending, codesign certificate expiry
classification, and `evaluate_codesign_endpoints()`. Overall the implementation is
solid: timezone handling is correct on both scanner paths, the `_ALGO_KEYWORDS`
reorder correctly guards against the DES-substring false-match, and XSS discipline
(`| sanitize`) is applied to all new scanner-derived fields in the HTML template.

One clear deviation from the locked UI-SPEC contract was found (column ordering in
the HTML All Findings table). Two quality-level issues concern: (a) the weak-crypto
codesign path silently producing generic `FALLBACK_QUANTUM_RISK` text instead of
algorithm-specific context for EC/SHA-1 cases, and (b) codesign findings bypassing
`_dedupe_findings` — the same pre-existing pattern as email/broker findings, but
worth documenting for the codesign path.

---

## Warnings

### WR-01: HTML "All Findings" Quantum Risk column placed before Recommendation, contradicting UI-SPEC contract

**File:** `quirk/reports/templates/report.html.j2:359`
**Issue:** The locked UI-SPEC (`99-UI-SPEC.md` §Interaction Contract) specifies
the Quantum Risk column as "the 7th column, **after** Recommendation." The
implementation places it as the 6th column, **before** Recommendation:

```html
<!-- Current (line 359) -->
<th>Description</th><th>Quantum Risk</th><th>Recommendation</th>

<!-- UI-SPEC mandates -->
<th>Description</th><th>Recommendation</th><th>Quantum Risk</th>
```

The `<td>` data row (line 369) and the CLI markdown header (technical.py line 121)
place Quantum Risk before Recommendation, so they are internally consistent with each
other but both violate the UI-SPEC ordering. Auditors or clients who reference the
column numbering in reports will find column 6 (Quantum Risk) where the contract
promised column 7.

**Fix:** Swap `<th>Quantum Risk</th>` and `<th>Recommendation</th>` in the All Findings
`<thead>` row, and move the corresponding `<td>` for quantum_risk after the
recommendation `<td>`. Apply the same swap to the `technical.py` pipe-table header and
row loop to maintain render parity. The CLI markdown header and HTML header should
both read: `| ... | Description | Recommendation | Quantum Risk |`.

---

### WR-02: Weak-crypto codesign findings (weak-ec-key / weak-signing-alg) always render FALLBACK_QUANTUM_RISK instead of algorithm-specific context

**File:** `quirk/engine/findings_evaluator.py:1057-1073`
**Issue:** The weak-crypto branch in `evaluate_codesign_endpoints` builds a finding
with a title like `"Code-signing certificate uses weak algorithm: {cert_subject}"` and
a description that contains the opaque reason strings (e.g., `"weak-ec-key"`,
`"weak-signing-alg"`). These strings do NOT contain any keyword from `_ALGO_KEYWORDS`
that would trigger a specific catalog match:

- `"weak-ec-key"` — does not contain `"ECDSA"` or `"ECC"` (it contains `"ec"` lowercase
  but `_classify_finding` upper-cases before matching; `"EC"` IS a substring of `"weak-ec-key"`
  but `"ECC"` is not, and `"ECDSA"` is not).
- `"weak-signing-alg"` — does not contain `"SHA1"`, `"SHA-1"`, or any hash keyword.

Wait: `"EC"` is not in `_ALGO_KEYWORDS` — the map has `"ECC"` and `"ECDSA"`. So
`weak-ec-key` produces no keyword hit. The result: these findings receive
`FALLBACK_QUANTUM_RISK` ("This cryptographic weakness reduces the security margin
against quantum-capable adversaries. Migrate to NIST-approved post-quantum algorithms
per NIST IR 8547.") instead of the specific ECC or SHA-1 quantum risk sentences from
`ALGO_IMPACT_MAP`. This partially contradicts D-06 ("no finding should reach the
report without a quantum-risk 'so what'") — the fallback is technically present, but
it is generic boilerplate rather than the weakness-specific text that D-06 requires.

Additionally, because `quantum_vulnerable=True` AND no catalog hit, `NIST_IR_8547_DEPRECATION`
is appended to the custom recommendation string (D-05 path), which is redundant given the
fallback `quantum_risk` field already references NIST IR 8547.

**Fix (two options):**

Option A — pass `check_id` on the weak-crypto branch to force the correct catalog key.
For a pure RSA-key finding, `check_id="RSA"` would select `ALGO_IMPACT_MAP["RSA"][2]`.
For a pure EC/ECDSA finding, `check_id="ECDSA"`. For SHA-1, `check_id="SHA-1"`. This
requires inspecting `reasons` to pick the right key:

```python
# Determine dominant reason for check_id hint
_reason_to_check_id = {
    "weak-rsa-key": "RSA",
    "weak-ec-key": "ECDSA",
    "weak-signing-alg": "SHA-1",
}
dominant_check_id = next(
    (_reason_to_check_id[r] for r in reasons if r in _reason_to_check_id),
    ""
)
findings.append(_build_finding(
    ...
    check_id=dominant_check_id,
))
```

Option B — explicitly set `quantum_risk` on the finding dict after `_build_finding`
returns, keyed by inspecting `reasons`. Less elegant than the catalog-wins path but
surgical.

---

### WR-03: codesign_findings bypasses _dedupe_findings — potential duplicate findings from LDAP + TLS overlap

**File:** `run_scan.py:2127-2129`
**Issue:** `evaluate_codesign_endpoints` is called on `codesign_endpoints`, which may
contain entries from both `scan_codesign_from_ldap` and `scan_codesign_from_tls_endpoints`
for the same certificate. When a certificate is discoverable via both paths (a code-signing
cert served on a TLS endpoint AND present in LDAP), two separate `CryptoEndpoint` records
are created — one by each scanner. Both will produce findings with similar (but not
identical) titles because the cert subject (`cert_subject`) is included in the title.
If both endpoints resolve to the same `cert_subject` string, the title will be identical,
but the host/port will differ (LDAP host vs TLS host), so they will NOT dedup via the
`(host, port, title, recommendation)` key.

More critically, the resulting `findings` list is passed directly to renderers without
running through `_dedupe_findings` — the same pre-existing gap as email/broker findings.
A certificate that is both LDAP-sourced (host=ldap.example.com:389) and TLS-EKU-sourced
(host=app.example.com:443) produces two separate findings for the same certificate, with
distinct hostnames, so dedup cannot collapse them even if both were run through
`_dedupe_findings`.

This is pre-existing behavior consistent with the email/broker pattern, but the
code-signing scenario is more likely to produce genuine duplicates than email/broker
(where STARTTLS and weak-cipher findings come from distinct protocols on different
endpoints). Since `scan_codesign_from_tls_endpoints` is always called (scanning already-captured
TLS endpoints), any TLS endpoint that also has an LDAP entry will produce two findings for
one certificate.

**Fix:** After building `codesign_findings`, run them through `_dedupe_findings` before
merging:

```python
from quirk.engine.findings_evaluator import _dedupe_findings

codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)
if codesign_findings:
    codesign_findings = _dedupe_findings(codesign_findings)
    findings = (findings or []) + codesign_findings
```

Alternatively, dedup the combined list once at the end of the findings-assembly block.

**Resolution (2026-05-24):** Downgraded to known limitation. Both `email_findings` and
`broker_findings` in `run_scan.py` follow the identical append-without-dedupe pattern
(lines 2117–2124). Applying `_dedupe_findings` only to codesign would introduce an
asymmetric divergence from the project's established per-scanner finding-merge convention.
Since the `(host, port, title, recommendation)` dedup key cannot collapse LDAP-path and
TLS-EKU-path findings for the same certificate anyway (different hosts), adding a
`_dedupe_findings` call here provides no practical benefit and no consistency gain.
This is a known limitation of the per-scanner append pattern across email, broker, and
codesign — tracked for a future unified dedup pass (single `_dedupe_findings` call on the
combined findings list at the end of the findings-assembly block).

---

## Info

### IN-01: REMEDIATION_CATALOG uses parenthesized string concatenation, type annotation is Dict[str, str] but values are str — minor clarity issue

**File:** `quirk/reports/content_model.py:228-303`
**Issue:** The `REMEDIATION_CATALOG` values are defined using implicit string concatenation
across parentheses (e.g., `"Replace RSA keys..." "...Prioritize certificates"`). This is
valid Python and produces correct `str` values, but it differs from how `ALGO_IMPACT_MAP`
uses explicit tuple construction. The type annotation `Dict[str, str]` is correct.
No functional issue; flagged for consistency with the codebase pattern.

**Fix:** No change required — this is consistent with `_NARRATIVE_LEADS` in the same file
which also uses parenthesized multi-line string literals.

---

### IN-02: `_classify_finding` searches `check_id` field but `proto_finding` in `_build_finding` omits `category` — minor missing field

**File:** `quirk/engine/findings_evaluator.py:111-117`
**Issue:** The `proto_finding` dict constructed inside `_build_finding` for the
`_classify_finding` call includes `severity`, `title`, `description`, and `check_id`,
but omits `category`. The `_classify_finding` function builds `search_text` from
`title + description + category + check_id`. Since `proto_finding` has no `category`
key, `str(finding.get("category", ""))` returns `""`, which is harmless — the category
field is not used for any existing finding type. Future findings that rely on
`category` for keyword matching would silently miss.

**Fix:** Add `"category": ""` to `proto_finding` for explicitness, or document the
intentional omission:

```python
proto_finding: Dict[str, Any] = {
    "severity": severity,
    "title": title,
    "description": description.strip(),
    "category": "",   # category not available at construction time
    "check_id": check_id,
}
```

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

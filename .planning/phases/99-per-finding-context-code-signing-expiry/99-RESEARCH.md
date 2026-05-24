# Phase 99: Per-Finding Context + Code-Signing Expiry - Research

**Researched:** 2026-05-24
**Domain:** Python report enrichment — content_model, findings_evaluator, codesign_scanner, renderer trio
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Extend the existing `ALGO_IMPACT_MAP` (crypto-class → risk label/impact sentence) in `quirk/reports/content_model.py` as the single source of per-finding quantum-risk context. Do NOT build a parallel finding-type catalog for risk text — reuse the crypto-class keying already proven for the exec summary's top-risks (Phase 98 D-02).
- **D-02:** Attach the "so what" to each finding as a **dedicated field** (`quantum_risk`) rather than folding it into the existing `description`. Keep technical detail (`description`) and risk framing (`quantum_risk`) separate so the renderer can present them distinctly.
- **D-03:** Render the new quantum-risk field across **all three** report surfaces — CLI markdown (`technical.py` findings table), HTML (`html_renderer.py` findings section), and PDF. This honors the EXEC-04 same-story-across-formats contract.
- **D-04:** Introduce a **centralized remediation catalog** keyed by finding type / crypto-class (mirroring the `ALGO_IMPACT_MAP` pattern) as the single source of remediation text. `_build_finding` call sites reference the catalog instead of carrying ad-hoc inline strings. Goal: auditable, consistent, specific-to-the-weakness remediation.
- **D-05:** Remediation copy must be specific to the detected weakness — NOT generic PQC boilerplate. Re-examine the auto-appended `NIST_IR_8547_DEPRECATION` sentence in `_build_finding` (applied to every `quantum_vulnerable=True` finding) so the boilerplate does not crowd out or duplicate the weakness-specific guidance.
- **D-06:** Enrich **all finding-producing paths**, not just those flowing through `_build_finding`. Findings from codesign, email, and broker scanners (and any DB-sourced findings) must not render with empty or thin context / remediation. No finding should reach the report without a quantum-risk "so what" and a specific remediation.
- **D-07:** Add expiry classification to `_classify_codesign_severity` in `quirk/scanner/codesign_scanner.py`. Severity mapping: expired → HIGH; within 90 days of `not_after` → MEDIUM (approaching expiry).
- **D-08:** Expiry is an **independent reason** that can stack with existing weak-crypto reasons. A SAFE-crypto-but-expired cert must now emit a finding (it previously returned `None` and was silently dropped).
- **D-09:** Apply expiry classification to **both** codesign source paths — `scan_codesign_from_ldap` and `scan_codesign_from_tls_endpoints`. The TLS path must read `cert_not_after` reliably; confirmed available (see §Architecture Patterns — Critical Pre-Existing Gap).
- **D-10:** Lock all new author-facing copy in a UI-SPEC Copywriting Contract first, before planning — DONE (99-UI-SPEC.md is locked and canonical).

### Claude's Discretion
- Exact field name for the quantum-risk "so what" (`quantum_risk` confirmed in UI-SPEC §Field Name Contract).
- Catalog data structure (dict-of-tuples vs dataclass) — follow the `ALGO_IMPACT_MAP` analog and `PATTERNS.md`.
- How the new field threads through `_dedupe_findings` keying.
- Markdown/HTML/PDF column-vs-block presentation of the risk text, within the locked copy.

### Deferred Ideas (OUT OF SCOPE)
- DOCX editable export (FMT-03), PDF branding/layout (FMT-01/02) — separate formatting phases in v5.2.
- Net-new scanner detection — out of scope; this phase is report-content only.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CTX-01 | Each finding carries a plain-language quantum-risk "so what" explanation (why it matters for PQC) | Addressed via `ALGO_IMPACT_MAP` extension in `content_model.py` + new `quantum_risk` field on every finding dict; lookup performed in `_build_finding` and post-enrichment pass for out-of-chokepoint paths |
| CTX-02 | Each finding carries actionable remediation guidance specific to the detected weakness | Addressed via a new `REMEDIATION_CATALOG` keyed by crypto-class in `content_model.py`; `_build_finding` sources from it; `NIST_IR_8547_DEPRECATION` append conditioned on catalog miss |
| CTX-03 | Code-signing certificate expiry (not_after / expired) is surfaced as a finding [WR-05 carry-over from v5.1] | Addressed via expiry classification in `_classify_codesign_severity` + new `evaluate_codesign_endpoints()` function in `findings_evaluator.py` called from `run_scan.py`; `cert_not_after` confirmed available on both LDAP and TLS paths |
</phase_requirements>

---

## Summary

Phase 99 is a pure enrichment phase: no new scanner detection, no new Python packages. The work falls into three coordinated tracks: (1) extending the content model with per-finding quantum-risk text and a weakness-specific remediation catalog, (2) wiring that content through all three rendering surfaces, and (3) promoting code-signing certificate expiry from a silently-dropped scanner field to a first-class report finding.

**Critical architectural discovery:** `CODE_SIGNING` protocol endpoints currently produce no findings at all. `evaluate_endpoints()` in `findings_evaluator.py` has branches for TLS, SSH, HTTP, CONTAINER, and UNKNOWN, but no `CODE_SIGNING` branch. The scanner emits `CryptoEndpoint` objects with `severity` pre-set and `evidence.py` counts them for scoring — but the report findings list never sees them. Phase 99 must introduce an `evaluate_codesign_endpoints()` function (mirroring the existing `evaluate_email_endpoints()` / `evaluate_broker_endpoints()` pattern) and call it in `run_scan.py`. Without this, CTX-03 cannot be fulfilled and D-06's "no finding renders thin" acceptance bar is impossible to meet for the codesign path.

The copy for all new fields is fully locked in `99-UI-SPEC.md` (Copywriting Contract). The planner must use those verbatim strings and must NOT deviate from the locked field name `quantum_risk`, the ALGO_IMPACT_MAP tuple extension to 3 elements, or the NIST_IR_8547_DEPRECATION conditioned-removal policy (remove when catalog match exists; retain only on catalog miss).

**Primary recommendation:** Implement in four plans: (A) extend `content_model.py` (ALGO_IMPACT_MAP + REMEDIATION_CATALOG), (B) wire `_build_finding` + add `evaluate_codesign_endpoints()` in `findings_evaluator.py` / `run_scan.py`, (C) update the renderer trio, (D) write tests and update the chaos lab expected-results oracle.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-finding quantum-risk text (`quantum_risk`) | Backend (content model) | — | Static lookup against `ALGO_IMPACT_MAP` extension; no renderer logic |
| Per-finding remediation (catalog-sourced) | Backend (findings evaluator) | — | `_build_finding` chokepoint; catalog in content model |
| NIST_IR_8547_DEPRECATION conditional removal | Backend (findings evaluator) | — | `_build_finding` must condition append on catalog hit/miss |
| Code-signing expiry classification | Scanner (`codesign_scanner.py`) | — | `_classify_codesign_severity` — scanner decides severity/reasons |
| Code-signing findings emission | Backend (findings evaluator) | Run-scan wiring | New `evaluate_codesign_endpoints()` + `run_scan.py` call |
| Rendering quantum_risk (CLI markdown) | Report layer (`technical.py`) | — | Extend pipe-table to 7 columns |
| Rendering quantum_risk (HTML) | Report layer (template) | `html_renderer.py` | Two separate presentation modes (Top Findings vs All Findings) |
| Rendering quantum_risk (PDF) | Derived from HTML | — | Playwright renders HTML automatically; no separate CSS |
| React dashboard | — | — | No changes; dashboard does not render per-finding table |

---

## Standard Stack

### Core (no new packages — enrichment only)

| Module | Current State | Phase 99 Change |
|--------|--------------|-----------------|
| `quirk/reports/content_model.py` | `ALGO_IMPACT_MAP`: `Dict[str, tuple[str, str]]` — 2-element tuples | Extend to `tuple[str, str, str]` (add `quantum_risk_sentence`); add `REMEDIATION_CATALOG: Dict[str, str]` with same key set |
| `quirk/engine/findings_evaluator.py` | `_build_finding` appends `NIST_IR_8547_DEPRECATION` unconditionally on `quantum_vulnerable=True` | Inject `quantum_risk` field via catalog lookup; condition NIST boilerplate on catalog miss; add `evaluate_codesign_endpoints()` |
| `quirk/scanner/codesign_scanner.py` | `_classify_codesign_severity` returns `(None, [])` for SAFE certs (drops them) | Add expiry check: expired → `("HIGH", ["expired"])`, ≤90d → `("MEDIUM", ["approaching-expiry"])` |
| `quirk/reports/technical.py` | 6-column pipe-table: `Severity\|Host\|Port\|Title\|Description\|Recommendation` | Add `Quantum Risk` column (column 6, before Recommendation) |
| `quirk/reports/templates/report.html.j2` | "All Findings" 6-column table; "Top Findings" 4-column table | Add `<th>Quantum Risk</th>` + `<td>` rendering in All Findings; add `.quantum-risk-block` sub-element inside Top Findings Description `<td>` |
| `run_scan.py` | Calls `evaluate_email_endpoints()` and `evaluate_broker_endpoints()` post-evaluate_endpoints | Add `codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)` call |

**No new pip dependencies.** [VERIFIED: codebase grep]

---

## Architecture Patterns

### System Architecture Diagram

```
codesign_scanner.py
  _parse_codesign_cert() → {not_after, expired, key_alg, key_bits, sig_hash, ...}
  _classify_codesign_severity(parsed)
    [Phase 99 add]: + expiry check → (severity, reasons)
    Returns (None, []) for SAFE/not-expiring → SAFE certs now kept when expired/approaching
  scan_codesign_from_ldap() → [CryptoEndpoint(protocol=CODE_SIGNING, cert_not_after=..., severity=...)]
  scan_codesign_from_tls_endpoints() → [CryptoEndpoint(protocol=CODE_SIGNING, cert_not_after=..., severity=...)]

run_scan.py (risk_engine phase)
  evaluate_endpoints(cfg, endpoints) → findings (TLS/SSH/HTTP/CONTAINER...)
    [No CODE_SIGNING branch — findings from codesign were NEVER in reports before]
  [Phase 99 add] evaluate_codesign_endpoints(codesign_endpoints) → codesign_findings
  findings = findings + email_findings + broker_findings + codesign_findings

findings_evaluator.py
  evaluate_codesign_endpoints(endpoints) [NEW]
    for each CODE_SIGNING endpoint with severity is not None:
      _build_finding(title, description, recommendation, quantum_risk) from catalogs
  _build_finding(...)
    [Phase 99]: lookup REMEDIATION_CATALOG[crypto_class] → rec
    [Phase 99]: lookup ALGO_IMPACT_MAP[crypto_class][2] → quantum_risk field
    [Phase 99]: append NIST_IR_8547_DEPRECATION only if no catalog match

content_model.py
  ALGO_IMPACT_MAP[crypto_class] = (risk_label, impact_sentence, quantum_risk_sentence) [3-tuple]
  REMEDIATION_CATALOG[crypto_class] = "weakness-specific remediation text"
  [new keys] "CODESIGN_EXPIRY", "CODESIGN_APPROACHING_EXPIRY"
  _classify_finding(finding) → crypto_class key [unchanged]

writer.py → write_reports()
  → build_tech_markdown(cfg, endpoints, findings) → technical-findings-*.md
  → render_html_report(path, ..., findings, ...) → report-*.html
  → render_pdf_report(html, pdf) → report-*.pdf [auto-derived]

technical.py
  | Severity | Host | Port | Title | Description | Quantum Risk | Recommendation |
  f.get('quantum_risk', fallback)[:120]

report.html.j2
  All Findings: <th>Quantum Risk</th> as 7th column; <td> with .quantum-risk-label + prose
  Top Findings: .quantum-risk-block sub-div inside Description <td>
```

### Recommended Project Structure

No new files or directories required. All changes are edits to existing modules:

```
quirk/
├── reports/
│   ├── content_model.py      # ALGO_IMPACT_MAP → 3-tuple; new REMEDIATION_CATALOG
│   └── technical.py          # Add Quantum Risk column to pipe-table
├── engine/
│   └── findings_evaluator.py # _build_finding: quantum_risk + conditional NIST; new evaluate_codesign_endpoints()
├── scanner/
│   └── codesign_scanner.py   # _classify_codesign_severity: add expiry branch
└── reports/templates/
    └── report.html.j2         # Two findings table additions + CSS classes
run_scan.py                    # Call evaluate_codesign_endpoints(), extend findings list
tests/
├── test_content_model_phase99.py          # New: quantum_risk lookup + REMEDIATION_CATALOG
├── test_codesign_expiry_classification.py # New: expiry severity branches
├── test_codesign_findings_evaluator.py    # New: evaluate_codesign_endpoints()
├── test_quantum_risk_render_parity.py     # New: quantum_risk in all 3 surfaces
└── (extend existing tests)
```

### Pattern 1: ALGO_IMPACT_MAP Extension (D-01)

**What:** Extend the existing 2-tuple to a 3-tuple by appending `quantum_risk_sentence`. All existing callers that unpack `(risk_label, impact_sentence) = ALGO_IMPACT_MAP[key]` break — they must be updated to `(risk_label, impact_sentence, _) = ALGO_IMPACT_MAP[key]` or switched to index access.

**Existing callers to update:** [VERIFIED: codebase grep]
- `content_model.py:_build_top_risks()` line ~360: `risk_label, impact_sentence = ALGO_IMPACT_MAP[crypto_class]`
- `tests/test_exec_content_model.py` line ~115: `_, expected_sentence = ALGO_IMPACT_MAP["RSA"]`

**New 3-tuple structure (locked strings from 99-UI-SPEC.md §Copywriting Contract):**
```python
# Source: 99-UI-SPEC.md §Copywriting Contract (locked — use verbatim)
ALGO_IMPACT_MAP: Dict[str, tuple[str, str, str]] = {
    "RSA": (
        "Harvest-now-decrypt-later exposure",
        "adversaries may already be archiving encrypted traffic for future decryption.",
        "RSA key material is vulnerable to Shor's algorithm — a sufficiently powerful "
        "quantum computer can factor the modulus and recover the private key, breaking "
        "both confidentiality and non-repudiation.",
    ),
    # ... (all entries in 99-UI-SPEC.md — CODESIGN_EXPIRY and CODESIGN_APPROACHING_EXPIRY added)
}
```

**New keys to add** (these do not exist in the current map):
- `"CODESIGN_EXPIRY"` — for expired code-signing certs
- `"CODESIGN_APPROACHING_EXPIRY"` — for ≤90-day expiry

### Pattern 2: REMEDIATION_CATALOG (D-04)

**What:** New module-level dict in `content_model.py` with the same key set as `ALGO_IMPACT_MAP`. Provides weakness-specific remediation strings.

```python
# Source: 99-UI-SPEC.md §Per-Finding Remediation Catalog (locked — use verbatim)
REMEDIATION_CATALOG: Dict[str, str] = {
    "RSA": "Replace RSA keys with NIST PQC standard algorithms...",
    # ... full set in 99-UI-SPEC.md
    "CODESIGN_EXPIRY": "Renew the expired code-signing certificate immediately...",
    "CODESIGN_APPROACHING_EXPIRY": "Renew this code-signing certificate before the not_after date...",
}
```

### Pattern 3: `_build_finding` Enrichment (D-02, D-04, D-05)

**What:** Add `quantum_risk` field to the returned dict; source it from `ALGO_IMPACT_MAP` (3rd element) via `_classify_finding`. Source `recommendation` override from `REMEDIATION_CATALOG` when a catalog key matches. Condition `NIST_IR_8547_DEPRECATION` append on catalog miss only.

**Constraint:** `_build_finding` currently receives `recommendation` as a caller-provided string. Two approaches are valid:
1. `_build_finding` calls `_classify_finding` on the constructed finding to look up catalog/quantum_risk (self-referential — finding not yet complete when _classify_finding runs, but title/description/check_id are available).
2. Callers continue to pass `recommendation`; `_build_finding` only augments with `quantum_risk` and conditionally overrides/appends NIST boilerplate.

**Recommended approach (Claude's Discretion):** Keep the caller-provided `recommendation` as-is; `_build_finding` constructs the finding dict, then calls `_classify_finding(finding)` to get the crypto-class key, then: (a) sets `finding["quantum_risk"]` from `ALGO_IMPACT_MAP[key][2]` if key found, else uses the fallback string; (b) replaces the recommendation with `REMEDIATION_CATALOG[key]` if key found (D-04 centralized catalog wins over the caller-provided string for known crypto-class findings); (c) appends `NIST_IR_8547_DEPRECATION` only if `quantum_vulnerable=True` AND key not in `REMEDIATION_CATALOG`.

**Dedup key:** `quantum_risk` must NOT be added to the `_dedupe_findings` dedup key tuple `(host, port, title, recommendation)`. This is consistent with the existing treatment of `recommendation` in the stable sort (not in dedup key per Phase 72 design). [VERIFIED: findings_evaluator.py L303-312]

### Pattern 4: `_classify_codesign_severity` Expiry Extension (D-07, D-08)

**Current behavior** [VERIFIED: codesign_scanner.py L145-174]:
```python
def _classify_codesign_severity(parsed: dict) -> tuple[str | None, list[str]]:
    reasons: list[str] = []
    if is_weak_cipher(parsed.get("sig_hash") or ""):
        reasons.append("weak-signing-alg")
    # ... RSA<2048, EC<256 checks
    if reasons:
        return "HIGH", reasons
    return None, reasons  # SAFE — no finding emitted
```

**Phase 99 extension** (expiry is independent — D-08):
```python
def _classify_codesign_severity(parsed: dict) -> tuple[str | None, list[str]]:
    reasons: list[str] = []
    # [existing weak-crypto checks unchanged]
    if is_weak_cipher(parsed.get("sig_hash") or ""):
        reasons.append("weak-signing-alg")
    # ...

    # [Phase 99 D-07/D-08] Expiry classification — independent of weak-crypto
    # parsed["expired"] is a bool; parsed["not_after_dt"] is a datetime (LDAP path)
    # For TLS path, the caller (scan_codesign_from_tls_endpoints) must pass
    # "expired" and "not_after_dt" in pseudo_parsed from ep.cert_not_after
    not_after_dt = parsed.get("not_after_dt")
    expired_flag = parsed.get("expired", False)
    if expired_flag:
        reasons.append("expired")
    elif not_after_dt is not None:
        now = datetime.now(timezone.utc)
        if not_after_dt.tzinfo is None:
            not_after_dt = not_after_dt.replace(tzinfo=timezone.utc)
        days_remaining = (not_after_dt - now).days
        if 0 <= days_remaining <= 90:
            reasons.append("approaching-expiry")

    if reasons:
        # severity: any "expired" or weak-crypto → HIGH; approaching-expiry alone → MEDIUM
        if "expired" in reasons or any(r in reasons for r in ("weak-signing-alg", "weak-rsa-key", "weak-ec-key")):
            return "HIGH", reasons
        return "MEDIUM", reasons
    return None, reasons
```

**CRITICAL — TLS path gap:** `scan_codesign_from_tls_endpoints` builds `pseudo_parsed` from TLS endpoint metadata but currently does NOT include `"expired"` or `"not_after_dt"`. The TLS path passes:
```python
pseudo_parsed = {
    "sig_hash": getattr(ep, "cert_sig_alg", None) or "",
    "key_alg": (getattr(ep, "cert_pubkey_alg", None) or "").upper(),
    "key_bits": getattr(ep, "cert_pubkey_size", None),
}
```
Phase 99 must extend `pseudo_parsed` to include:
```python
pseudo_parsed["not_after_dt"] = getattr(ep, "cert_not_after", None)
# compute expired inline since we have the datetime
_na = pseudo_parsed["not_after_dt"]
if _na is not None:
    _na_aware = _na if _na.tzinfo else _na.replace(tzinfo=timezone.utc)
    pseudo_parsed["expired"] = _na_aware < datetime.now(timezone.utc)
else:
    pseudo_parsed["expired"] = False
```
`cert_not_after` is confirmed populated on both paths [VERIFIED: codesign_scanner.py L386, L473; tls_scanner.py L226, L438].

### Pattern 5: `evaluate_codesign_endpoints()` — New Function (D-06, CTX-03)

**What:** New function in `findings_evaluator.py` mirroring `evaluate_email_endpoints` / `evaluate_broker_endpoints`. Takes `codesign_endpoints: List[CryptoEndpoint]` and emits `List[Dict[str, Any]]`.

**Trigger:** Only called when endpoint `severity` is not `None` (i.e., the scanner already classified a finding). The scanner SAFE path (`severity=None`) emits no endpoints to this evaluator.

**Finding title/description/recommendation** from locked copy in 99-UI-SPEC.md §Code-Signing Expiry Findings. Two finding types:
- Weak-crypto findings (existing HIGH path): `title` encodes the key algorithm + weakness; description from `smime_scan_json["reasons"]`.
- Expiry findings (new): title/description/recommendation from the locked copy, with `{subject}`, `{not_after_date}`, `{days_remaining}` interpolated from the endpoint's fields.

**`_build_finding` call site:** The new `evaluate_codesign_endpoints` will call `_build_finding`, which (after Phase 99's Plan A) will automatically attach `quantum_risk` from the catalog. The codesign-expiry crypto-class keys (`CODESIGN_EXPIRY`, `CODESIGN_APPROACHING_EXPIRY`) must exist in both `ALGO_IMPACT_MAP` and `REMEDIATION_CATALOG` so the lookup succeeds.

**`run_scan.py` wiring:** Add after the broker findings block:
```python
codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)
if codesign_findings:
    findings = (findings or []) + codesign_findings
```
Import: add `evaluate_codesign_endpoints` to the existing import from `quirk.engine.findings_evaluator` at line 37.

### Pattern 6: Renderer Trio (D-03)

**CLI markdown (`technical.py` L113-122):**

Current:
```python
lines.append("| Severity | Host | Port | Title | Description | Recommendation |")
lines.append("|---|---|---:|---|---|---|")
for f in findings:
    ...
    lines.append(f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(rec)} |")
```

Phase 99 (column 6 = Quantum Risk, between Description and Recommendation):
```python
lines.append("| Severity | Host | Port | Title | Description | Quantum Risk | Recommendation |")
lines.append("|---|---|---:|---|---|---|---|")
FALLBACK_QR = "This cryptographic weakness reduces the security margin..."  # from 99-UI-SPEC.md
for f in findings:
    qr = (f.get("quantum_risk") or FALLBACK_QR)[:120]
    lines.append(f"| {sev} | {md_cell(host)} | {port} | {md_cell(title)} | {md_cell(desc)} | {md_cell(qr)} | {md_cell(rec)} |")
```

**HTML template (`report.html.j2`):**

"All Findings" table (currently 6 columns: Severity, Title, Host, Port, Description, Recommendation):
- Add `<th>Quantum Risk</th>` as 7th header (before or after Recommendation — executor discretion per CONTEXT.md Claude's Discretion).
- Add `<td>` with `.quantum-risk-label` + `{{ f.get('quantum_risk', fallback)[:200] | sanitize }}`.
- New CSS classes in existing `<style>` block: `.quantum-risk-block` and `.quantum-risk-label` (exact CSS from 99-UI-SPEC.md §HTML/CSS Additions Contract).

"Top Findings" table (currently 4 columns): add `.quantum-risk-block` sub-div INSIDE Description `<td>` (not a new column — per 99-UI-SPEC.md §Interaction Contract).

**PDF:** Derived from HTML via Playwright. No additional work (confirmed by 99-UI-SPEC.md §Scope Clarification §PDF).

### Anti-Patterns to Avoid

- **Fragmenting dedup clusters:** Adding `quantum_risk` to the `_dedupe_findings` key tuple would cause identical findings with different risk text (e.g., after a catalog update) to appear as separate findings. Always exclude free-text enrichment fields from the dedup key.
- **Parallel quantum-risk catalog:** Building a separate finding-type keyed map for risk text instead of extending `ALGO_IMPACT_MAP` violates D-01 and creates two sources of truth.
- **Forgetting the TLS-path `pseudo_parsed` gap:** `scan_codesign_from_tls_endpoints` builds `pseudo_parsed` without `expired` / `not_after_dt`. Without adding those fields, the TLS path will never emit expiry findings even after `_classify_codesign_severity` is extended.
- **Forgetting `evaluate_codesign_endpoints()` in run_scan.py:** The scanner emits endpoints; findings are generated by the evaluator. Without adding `codesign_findings = evaluate_codesign_endpoints(codesign_endpoints)` in `run_scan.py`, CODE_SIGNING endpoints continue to produce no report findings.
- **ALGO_IMPACT_MAP tuple unpack breakage:** `_build_top_risks()` in `content_model.py` unpacks `risk_label, impact_sentence = ALGO_IMPACT_MAP[crypto_class]` — this breaks when the tuple becomes a 3-element tuple. Must update to 3-value unpack or `[0]`/`[1]` indexing.
- **Test tuple assertion:** `tests/test_exec_content_model.py` asserts `_, expected_sentence = ALGO_IMPACT_MAP["RSA"]` — 2-value unpack breaks on 3-tuple. Must update.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-finding quantum-risk text | Separate keyword-to-text lookup in renderer | Extend `ALGO_IMPACT_MAP` + call `_classify_finding()` already in content_model.py | `_classify_finding()` already maps any finding to a crypto-class key via title/description/category/check_id keyword scan |
| Crypto-class detection | New keyword-matching logic in `_build_finding` | Reuse `_classify_finding(finding)` which searches title + description + category + check_id | Avoids duplicating the 14-keyword ordered scan already in content_model.py |
| datetime / timezone arithmetic for expiry | Custom time comparison code | Use `datetime.now(timezone.utc)` + `timedelta(days=90)` + `(not_after_dt - now).days` | The pattern already exists in `findings_evaluator.py` L543-579 (TLS cert expiry) |
| HTML escaping in template | Inline Python escaping | Jinja2 `| sanitize` filter (already registered via `env.filters["sanitize"] = sanitize_scanner_text`) | Used throughout `report.html.j2`; consistent with existing security pattern |

---

## Runtime State Inventory

> Not applicable — this is a code enrichment phase; no rename/refactor/migration of stored data.

---

## Common Pitfalls

### Pitfall 1: ALGO_IMPACT_MAP Tuple Unpack Breakage
**What goes wrong:** Extending tuples from 2 to 3 elements breaks every existing 2-value unpack of `ALGO_IMPACT_MAP` entries.
**Why it happens:** Python tuple unpacking requires exact count match.
**How to avoid:** Search for all `= ALGO_IMPACT_MAP[` usages before committing. Current known usages: `content_model.py:_build_top_risks()` L~360 (`risk_label, impact_sentence = ...`) and `tests/test_exec_content_model.py` L~115 (`_, expected_sentence = ...`). Both must be updated in the same commit as the map extension.
**Warning signs:** `ValueError: too many values to unpack` in `_build_top_risks` or test failures in `test_exec_content_model.py`.

### Pitfall 2: TLS Path pseudo_parsed Missing expiry Fields
**What goes wrong:** After `_classify_codesign_severity` is extended with expiry logic, the TLS EKU path still silently skips expiry classification because `pseudo_parsed` lacks `"expired"` and `"not_after_dt"`.
**Why it happens:** `scan_codesign_from_tls_endpoints` was written before expiry was in scope; it builds `pseudo_parsed` from only 3 fields.
**How to avoid:** Add expiry derivation to `pseudo_parsed` construction in `scan_codesign_from_tls_endpoints` in the same plan as the `_classify_codesign_severity` change. Test with a `CryptoEndpoint` fixture that has an `expired` cert_not_after value.
**Warning signs:** Expiry findings appear from the LDAP path but not the TLS-EKU path in integration tests.

### Pitfall 3: evaluate_codesign_endpoints Missing from run_scan.py
**What goes wrong:** `evaluate_codesign_endpoints` is added to `findings_evaluator.py` but not imported or called in `run_scan.py`. CODE_SIGNING endpoints continue producing no findings.
**Why it happens:** Pattern established by email/broker evaluators (added to imports + called at risk_engine phase) must be replicated manually.
**How to avoid:** Update `run_scan.py` import at L37 to include `evaluate_codesign_endpoints`. Add call in the risk_engine phase block immediately after broker findings.
**Warning signs:** Test scanning a host with a known CODE_SIGNING endpoint; no expiry or weak-algo findings appear in the output.

### Pitfall 4: Stale Safe-Cert Branch in scan_codesign_from_ldap
**What goes wrong:** The LDAP path has an early-continue when `severity is None` (L358: `if severity is None: continue`). After the expiry extension, an expired SAFE-crypto cert will have `severity = "HIGH"` and should NOT continue. But the early-continue check uses the result of `_classify_codesign_severity`, which now returns non-None for expired certs — so this is automatically correct IF the severity call result is checked properly.
**Why it happens:** Not a real pitfall if implemented correctly — just requires awareness that the SAFE-cert early exit `if severity is None: continue` naturally gates on the new expiry classification too.
**Warning signs:** Expired SAFE-crypto certs silently dropped — check that `_classify_codesign_severity` returns `("HIGH", ["expired"])` for them, not `(None, [])`.

### Pitfall 5: NIST_IR_8547_DEPRECATION Still Appended to Catalog-Sourced Findings
**What goes wrong:** D-05 requires removing the generic boilerplate when catalog-sourced remediation is used. If the condition on `quantum_vulnerable=True` is left unchanged, findings with a catalog match get both the catalog-specific guidance AND the generic NIST boilerplate.
**Why it happens:** `_build_finding` currently appends `NIST_IR_8547_DEPRECATION` to ALL `quantum_vulnerable=True` findings unconditionally.
**How to avoid:** Change the append logic to: `if quantum_vulnerable and crypto_class not in REMEDIATION_CATALOG: rec += " " + NIST_IR_8547_DEPRECATION`. The boilerplate remains as the final safety net for novel/unknown findings.
**Warning signs:** Catalog-sourced recommendation ends with `"Per NIST IR 8547, RSA and ECC are deprecated after 2030..."` — this means D-05 was not implemented. Test in `test_build_finding_catalog_sourced_no_boilerplate`.

---

## Code Examples

### ALGO_IMPACT_MAP 3-tuple extension
```python
# Source: content_model.py (existing structure) + 99-UI-SPEC.md §Copywriting Contract
ALGO_IMPACT_MAP: Dict[str, tuple[str, str, str]] = {
    "RSA": (
        "Harvest-now-decrypt-later exposure",                         # risk_label [existing]
        "adversaries may already be archiving encrypted traffic...",   # impact_sentence [existing]
        "RSA key material is vulnerable to Shor's algorithm...",       # quantum_risk [new]
    ),
    # CODESIGN_EXPIRY added — these keys do not exist in the current map:
    "CODESIGN_EXPIRY": (
        "Code-signing trust chain failure",
        "expired certificate cannot authenticate software artifacts.",
        "An expired code-signing certificate breaks the trust chain...",  # from UI-SPEC
    ),
    "CODESIGN_APPROACHING_EXPIRY": (
        "Code-signing certificate approaching expiry",
        "imminent expiry creates operational risk for software verification.",
        "A code-signing certificate expiring within 90 days creates operational risk...",
    ),
}
```

### _build_finding with quantum_risk injection
```python
# Source: findings_evaluator.py (existing _build_finding pattern + Phase 99 additions)
def _build_finding(
    *,
    severity: str,
    host: str,
    port: int,
    title: str,
    description: str,
    recommendation: str,
    quantum_vulnerable: bool = False,
) -> Dict[str, Any]:
    # [existing validation unchanged]
    finding = {
        "severity": severity, "host": host, "port": port,
        "title": title, "description": description.strip(),
        # [Phase 99]: compliance, quantum_risk added below
    }
    # [Phase 99 D-01/D-04/D-05] Catalog + quantum-risk injection
    from quirk.reports.content_model import (
        ALGO_IMPACT_MAP, REMEDIATION_CATALOG, _classify_finding
    )
    crypto_class = _classify_finding(finding)
    if crypto_class and crypto_class in ALGO_IMPACT_MAP:
        finding["quantum_risk"] = ALGO_IMPACT_MAP[crypto_class][2]
    else:
        finding["quantum_risk"] = REMEDIATION_FALLBACK_QUANTUM_RISK  # from UI-SPEC default fallback
    rec = recommendation.strip()
    if crypto_class and crypto_class in REMEDIATION_CATALOG:
        rec = REMEDIATION_CATALOG[crypto_class]
    elif quantum_vulnerable:
        rec = f"{rec} {NIST_IR_8547_DEPRECATION}"
    finding["recommendation"] = rec
    finding["compliance"] = COMPLIANCE_MAP.get(_normalize_for_compliance(title), [])
    return finding
```
Note: The import of `_classify_finding` inside `_build_finding` must be careful of the circular import path (`findings_evaluator` imports from `quirk.compliance`; `content_model` imports nothing from `findings_evaluator`). The safe direction is `findings_evaluator` importing from `content_model`. [VERIFIED: content_model.py has no import from findings_evaluator]

### evaluate_codesign_endpoints skeleton
```python
# Source: findings_evaluator.py (mirrors evaluate_email_endpoints pattern)
def evaluate_codesign_endpoints(endpoints) -> List[Dict[str, Any]]:
    """Phase 99 CTX-03: emit codesign-specific findings.

    Only called for endpoints already classified by _classify_codesign_severity
    (protocol=CODE_SIGNING, severity is not None). The scanner's SAFE path emits
    no endpoints so no filtering needed here.
    """
    findings: List[Dict[str, Any]] = []
    for e in endpoints:
        host = getattr(e, "host", "")
        port = int(getattr(e, "port", 0) or 0)
        severity = getattr(e, "severity", None) or "HIGH"
        cert_subject = getattr(e, "cert_subject", "") or ""
        cert_not_after = getattr(e, "cert_not_after", None)
        # Parse reasons from smime_scan_json
        reasons = []
        try:
            import json
            scan_json = getattr(e, "smime_scan_json", None)
            if scan_json:
                reasons = json.loads(scan_json).get("reasons", [])
        except Exception:
            pass

        not_after_date = cert_not_after.date() if cert_not_after else "unknown"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        na_naive = cert_not_after if (cert_not_after and cert_not_after.tzinfo is None) else (
            cert_not_after.astimezone(timezone.utc).replace(tzinfo=None) if cert_not_after else None
        )
        days_remaining = (na_naive - now).days if na_naive else None

        if "expired" in reasons:
            findings.append(_build_finding(
                severity="HIGH", host=host, port=port,
                title=f"Code-signing certificate expired: {cert_subject}",
                description=f"The code-signing certificate for '{cert_subject}' expired on "
                            f"{not_after_date}. Software signed by this certificate can no "
                            f"longer be verified as authentic, creating a supply-chain trust failure.",
                recommendation="Renew the expired code-signing certificate immediately...",
                # _build_finding will inject quantum_risk via CODESIGN_EXPIRY key lookup
            ))
        elif "approaching-expiry" in reasons:
            findings.append(_build_finding(
                severity="MEDIUM", host=host, port=port,
                title=f"Code-signing certificate expiring within 90 days: {cert_subject}",
                description=f"The code-signing certificate for '{cert_subject}' expires on "
                            f"{not_after_date} ({days_remaining} days remaining)...",
                recommendation="Renew this code-signing certificate before the not_after date...",
            ))
        else:
            # Weak-crypto path (existing HIGH severity reasons: weak-signing-alg, weak-rsa-key, weak-ec-key)
            reason_str = ", ".join(reasons) if reasons else "weak algorithm"
            findings.append(_build_finding(
                severity=severity, host=host, port=port,
                title=f"Code-signing certificate uses weak algorithm: {cert_subject}",
                description=f"The code-signing certificate for '{cert_subject}' uses {reason_str}.",
                recommendation="Replace the weak code-signing certificate with a strong algorithm...",
                quantum_vulnerable=True,
            ))
    return findings
```
Note: The exact locked copy for titles/descriptions/recommendations comes from `99-UI-SPEC.md §Code-Signing Expiry Findings` (planner must reference UI-SPEC verbatim strings).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-finding context in description (ad-hoc) | `quantum_risk` as a dedicated field | Phase 99 | Renderers can present risk framing distinctly from technical description |
| Generic `NIST_IR_8547_DEPRECATION` boilerplate on all quantum-vulnerable findings | Weakness-specific catalog; NIST boilerplate only on catalog miss | Phase 99 | Eliminates repeated generic noise; every finding gets targeted guidance |
| CODE_SIGNING endpoints → scoring signal only (no report findings) | CODE_SIGNING endpoints → `evaluate_codesign_endpoints()` → findings | Phase 99 | Expiry and weak-algo codesign issues now appear in the findings table |
| Codesign expiry: computed but never propagated to a finding (WR-05) | Expiry → HIGH (expired) or MEDIUM (≤90 days) finding | Phase 99 | Closes WR-05 carry-over from v5.1 |

**Deprecated/outdated after Phase 99:**
- Unconditional `NIST_IR_8547_DEPRECATION` append for ALL `quantum_vulnerable=True` findings — replaced by conditional (catalog miss only).
- `ALGO_IMPACT_MAP` as a `Dict[str, tuple[str, str]]` — becomes `Dict[str, tuple[str, str, str]]`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_classify_finding()` in `content_model.py` will successfully match codesign expiry finding titles (they contain no crypto-class keyword by default — titles like "Code-signing certificate expired: CN=..." contain no RSA/ECC/SHA keywords) | Architecture Patterns Pattern 3 | `quantum_risk` lookup via `_classify_finding` returns `None` for expiry findings; must use hardcoded key lookup or add "CODESIGN_EXPIRY" to `_ALGO_KEYWORDS` |

**Note on A1:** This is the most important assumption. `_classify_finding` scans `title + description + category + check_id` for keywords in `_ALGO_KEYWORDS`. The current keyword list contains RSA, ECC, SHA1, etc. — not "CODESIGN_EXPIRY". For expiry findings built in `evaluate_codesign_endpoints`, there are two valid approaches: (a) add "CODESIGN" or "CODE_SIGNING" to `_ALGO_KEYWORDS` and map it to a new `CODESIGN_EXPIRY` key in `ALGO_IMPACT_MAP`, or (b) `evaluate_codesign_endpoints` passes a pre-computed `check_id="CODESIGN_EXPIRY"` field to allow `_classify_finding` to match. Approach (b) is cleaner — `_build_finding` should accept an optional `check_id` param and store it in the returned dict. This is Claude's Discretion.

---

## Open Questions

1. **`_classify_finding` matching for codesign expiry findings**
   - What we know: `_classify_finding` matches on keywords in `title + description + category + check_id`. "CODESIGN_EXPIRY" is not a current keyword.
   - What's unclear: Whether to add `check_id` as a new param to `_build_finding` or add a "CODE_SIGNING" keyword to `_ALGO_KEYWORDS`.
   - Recommendation: Add optional `check_id: str = ""` parameter to `_build_finding`; store it in the returned dict; pass `check_id="CODESIGN_EXPIRY"` or `check_id="CODESIGN_APPROACHING_EXPIRY"` from `evaluate_codesign_endpoints`. This allows `_classify_finding` to match via the `check_id` field. Add the two new keys to `_ALGO_KEYWORDS`.

2. **Existing weak-algo codesign finding titles**
   - What we know: Currently no codesign findings exist in any report (the CODE_SIGNING evaluate gap). There are no existing locked copy strings for weak-algo codesign finding titles (only expiry titles are in `99-UI-SPEC.md §Code-Signing Expiry Findings`).
   - What's unclear: The exact title/description for weak-algo codesign findings (RSA-1024, EC-192, SHA-1) — these are the existing HIGH path findings that Phase 95 intended to emit but which never made it to the report.
   - Recommendation: Derive title/description from the `reasons` list in `smime_scan_json`. E.g., `"Code-signing certificate uses weak algorithm: {subject}"` with a description enumerating the reasons. The planner must author these strings or recognize they are `[ASSUMED]` and verify with the user.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All modules | ✓ | 3.14.x (confirmed by pytest cache) | — |
| pytest | Test suite | ✓ | 8.4.2 / 9.0.2 | — |
| cryptography | codesign_scanner.py | ✓ | installed (confirmed by import) | — |
| Playwright | PDF rendering | conditional | if installed | Graceful degradation — `render_pdf_report` returns False if missing |

No missing dependencies for this phase.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_codesign_expiry_classification.py tests/test_content_model_phase99.py -x -q` |
| Full suite command | `python -m pytest tests/ -m "not slow" -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CTX-01 | `_build_finding` returns dict with `quantum_risk` field for known crypto-class | unit | `pytest tests/test_content_model_phase99.py::test_quantum_risk_field_populated -x` | ❌ Wave 0 |
| CTX-01 | `quantum_risk` uses fallback string when no crypto-class match | unit | `pytest tests/test_content_model_phase99.py::test_quantum_risk_fallback -x` | ❌ Wave 0 |
| CTX-01 | `quantum_risk` absent from `_dedupe_findings` key (no cluster fragmentation) | unit | `pytest tests/test_content_model_phase99.py::test_quantum_risk_excluded_from_dedup_key -x` | ❌ Wave 0 |
| CTX-01 | `Quantum Risk` column present in CLI markdown table | unit | `pytest tests/test_quantum_risk_render_parity.py::test_markdown_has_quantum_risk_column -x` | ❌ Wave 0 |
| CTX-01 | `Quantum Risk` column present in HTML All Findings table | unit | `pytest tests/test_quantum_risk_render_parity.py::test_html_all_findings_has_quantum_risk -x` | ❌ Wave 0 |
| CTX-01 | `.quantum-risk-block` present in HTML Top Findings Description cell | unit | `pytest tests/test_quantum_risk_render_parity.py::test_html_top_findings_risk_block -x` | ❌ Wave 0 |
| CTX-02 | Catalog-sourced remediation used when crypto-class matches | unit | `pytest tests/test_content_model_phase99.py::test_catalog_remediation_overwrites_caller -x` | ❌ Wave 0 |
| CTX-02 | NIST_IR_8547_DEPRECATION NOT appended when catalog match exists | unit | `pytest tests/test_content_model_phase99.py::test_nist_boilerplate_absent_on_catalog_hit -x` | ❌ Wave 0 |
| CTX-02 | NIST_IR_8547_DEPRECATION retained when no catalog match | unit | `pytest tests/test_risk_engine.py::TestBuildFinding::test_quantum_vulnerable_appends_deprecation_phrase` | ✅ (must update assertion) |
| CTX-03 | Expired cert → HIGH finding with "expired" reason | unit | `pytest tests/test_codesign_expiry_classification.py::test_expired_cert_emits_high -x` | ❌ Wave 0 |
| CTX-03 | ≤90-day cert → MEDIUM finding with "approaching-expiry" reason | unit | `pytest tests/test_codesign_expiry_classification.py::test_approaching_expiry_emits_medium -x` | ❌ Wave 0 |
| CTX-03 | SAFE-crypto-but-expired cert emits a finding (not silently dropped) | unit | `pytest tests/test_codesign_expiry_classification.py::test_safe_crypto_expired_not_dropped -x` | ❌ Wave 0 |
| CTX-03 | Expiry stacks with weak-crypto: both reasons in output | unit | `pytest tests/test_codesign_expiry_classification.py::test_expiry_stacks_with_weak_crypto -x` | ❌ Wave 0 |
| CTX-03 | TLS path: `pseudo_parsed` includes expired/not_after_dt fields | unit | `pytest tests/test_codesign_expiry_classification.py::test_tls_path_expiry_fields -x` | ❌ Wave 0 |
| CTX-03 | `evaluate_codesign_endpoints` emits dict findings (not endpoints) | unit | `pytest tests/test_codesign_findings_evaluator.py::test_evaluate_codesign_emits_dicts -x` | ❌ Wave 0 |
| CTX-03 | `evaluate_codesign_endpoints` result wired into run_scan.py findings list | integration | `pytest tests/test_run_scan_codesign_wiring.py` (extend existing) | ✅ (extend) |
| D-01 | ALGO_IMPACT_MAP 3-tuple: `_build_top_risks` unpacks correctly | unit | `pytest tests/test_exec_content_model.py -x` | ✅ (must update unpack) |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_codesign_expiry_classification.py tests/test_content_model_phase99.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -m "not slow" -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_content_model_phase99.py` — covers CTX-01/02 (quantum_risk field, REMEDIATION_CATALOG, NIST conditional)
- [ ] `tests/test_codesign_expiry_classification.py` — covers CTX-03 severity branches, TLS path, stacking
- [ ] `tests/test_codesign_findings_evaluator.py` — covers `evaluate_codesign_endpoints()` finding shape
- [ ] `tests/test_quantum_risk_render_parity.py` — covers CLI markdown column + HTML template additions
- [ ] Update `tests/test_exec_content_model.py` — 2-tuple unpack at `_, expected_sentence = ALGO_IMPACT_MAP["RSA"]` breaks on 3-tuple
- [ ] Update `tests/test_risk_engine.py` — `test_quantum_vulnerable_appends_deprecation_phrase` must add condition check (boilerplate only on catalog miss)
- [ ] Framework install: already present

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `sanitize_scanner_text` filter already applied to all finding fields in HTML template; `md_cell` escape in markdown; Phase 99 adds no new input sources |
| V6 Cryptography | no | — |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via injected finding text in HTML report | Tampering / Spoofing | `{{ ... \| sanitize }}` Jinja2 filter already applied to all scanner-derived strings in report.html.j2; `quantum_risk` field must be wrapped in the same filter |
| Markdown injection in CLI pipe-table | Tampering | `md_cell()` escapes pipe characters and special markdown in all finding cells; `quantum_risk` must be passed through `md_cell()` |
| cert_not_after naive/aware datetime comparison error | Tampering (incorrect expiry result) | Explicit tzinfo normalization before comparison (mirror the existing pattern at findings_evaluator.py L543-546) |

---

## Sources

### Primary (HIGH confidence)

All findings are from direct codebase inspection. No external documentation required for this phase — the work is purely internal enrichment.

- `quirk/reports/content_model.py` — ALGO_IMPACT_MAP structure, `_classify_finding` keyword list, tuple unpack callers confirmed [VERIFIED: codebase grep]
- `quirk/engine/findings_evaluator.py` — `_build_finding` signature, `NIST_IR_8547_DEPRECATION` append logic, `_dedupe_findings` key, CODE_SIGNING protocol gap [VERIFIED: codebase grep]
- `quirk/scanner/codesign_scanner.py` — `_classify_codesign_severity` current behavior, `not_after`/`expired` availability on LDAP path, `cert_not_after` on TLS path, `pseudo_parsed` gap [VERIFIED: codebase grep]
- `quirk/reports/technical.py` — pipe-table column order (6 columns confirmed) [VERIFIED: codebase grep]
- `quirk/reports/templates/report.html.j2` — "All Findings" 6-column structure, "Top Findings" 4-column structure, existing CSS variable palette [VERIFIED: grep]
- `run_scan.py` — evaluate_email_endpoints/evaluate_broker_endpoints wiring pattern; codesign_endpoints assembled but no evaluate call [VERIFIED: codebase grep]
- `quirk/scanner/tls_scanner.py` — `cert_not_after` populated at L226 and L438 [VERIFIED: codebase grep]
- `.planning/phases/99-per-finding-context-code-signing-expiry/99-UI-SPEC.md` — locked copywriting contract [VERIFIED: full read]
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — codesign lab fixture documents `CODE-SIGN/weak-algorithm` HIGH finding; no expiry fixture (lab uses 100-year validity certs; expiry tested by unit mocks) [VERIFIED: codebase grep]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules read directly; no external libraries involved
- Architecture: HIGH — code paths traced end-to-end through run_scan.py → findings_evaluator → writer → renderers
- Pitfalls: HIGH — all pitfalls grounded in concrete line-number evidence from codebase
- CTX-03 gap finding: HIGH — confirmed no `CODE_SIGNING` branch in `evaluate_endpoints`; confirmed `codesign_findings` not assembled in run_scan.py

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (stable codebase; no external dependencies)

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 99 |
|-----------|-------------------|
| Follow PEP 8 for all Python changes | All new code (evaluate_codesign_endpoints, catalog dicts, _classify_codesign_severity extension) must be PEP 8 compliant |
| Keep diffs minimal — avoid unnecessary refactors | Do not refactor existing `_build_finding` call sites beyond what D-04/D-05 require; only add catalog lookup + quantum_risk injection |
| After changes, run `python -m compileall` and relevant tests | Each plan must include a `python -m compileall quirk/` check + relevant test run as a verification step |
| If detection logic changes, update `labs/*/expected_results.md` accordingly | CTX-03 changes `_classify_codesign_severity` detection logic — the chaos lab expected_results_v4.md §ldaps section must be updated to document the new expiry finding path (even though the lab fixture uses a 100-year cert and the expiry path is exercised by unit mocks, the oracle must describe both paths) |
| Any chaos lab profile/port/service change requires lab.sh update | Phase 99 adds no new profiles; no lab.sh update required |

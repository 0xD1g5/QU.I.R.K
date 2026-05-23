# Phase 95: Code-Signing Certificate Inventory - Research

**Researched:** 2026-05-23
**Domain:** LDAP certificate discovery, EKU inspection, CBOM fingerprint dedup, scoring agility signals
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **v5.1-D-07:** Code-signing scope = Option A (LDAP `userCertificate` + TLS EKU check only). Sigstore/npm/Authenticode deferred to v5.2.
- **v5.1-D-04:** No 7th subscore — signals fold into existing `agility_signals`. SCORE_WEIGHTS sum 293.0 → 299.0 (Phase 95 increment).
- **Protocol label:** `CODE_SIGNING` (UPPERCASE — all CBOM/evidence/resume consumers key on exact string match, per Phase 94 casing lesson).
- **CLI gate:** `--inventory-code-signing` flag; no implicit activation.
- **LDAP source:** Reuse `smime_scanner.py`'s anonymous LDAP `userCertificate` connection pattern, filtered to CodeSigning EKU.
- **TLS source:** In-process EKU check on already-captured TLS endpoints — no new network fetch.
- **New module:** `quirk/scanner/codesign_scanner.py` — reuse smime LDAP helpers and adcs EKU-parsing helpers.
- **Finding category:** `CODE-SIGN/weak-algorithm`; severity HIGH for RSA<2048, EC<256, SHA-1.
- **Dedup:** SHA-256 fingerprint key; TLS-derived component wins; code-signing annotates existing component.
- **Chaos lab:** Reuse `ldaps` profile — add code-signing cert fixture. No new profile.
- **Score delta:** +6.0 → 299.0. BOTH sum AND count invariant in `tests/test_score_weights_invariant.py` must update.
- **No impacket:** ldap3 only (`quirk[adcs]` safe-for-`[all]` constraint holds).

### Claude's Discretion

- Exact evidence counter key name(s) for the code-signing agility signal.
- Precise agility weight split for the +6.0 increment.
- Helper structure within `codesign_scanner.py`.
- Report layout for code-signing findings.

### Deferred Ideas (OUT OF SCOPE)

- Sigstore / npm / Authenticode code-signing verification → v5.2.
- Active fetching of certs solely for EKU inspection → out of scope (passive only).
- A dedicated `codesign` chaos-lab profile → not now; reuse `ldaps`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CSIGN-01 | User can inventory code-signing certificates via LDAP `userCertificate` and EKU checks on already-captured TLS certs | LDAP pattern fully verified in smime_scanner.py; EKU OID confirmed as `ExtendedKeyUsageOID.CODE_SIGNING` = `1.3.6.1.5.5.7.3.3`; TLS cert EKU read pattern confirmed |
| CSIGN-02 | Code-signing certs with weak algorithms (RSA<2048, EC<256, SHA-1) raise HIGH finding | `is_weak_cipher()` in weak_crypto.py covers SHA-1 family; RSA/EC thresholds use same inline logic as smime_scanner.py and adcs_scanner.py |
| CSIGN-03 | Code-signing CBOM components deduped by SHA-256 fingerprint against existing TLS-derived components | `cert.fingerprint(hashes.SHA256())` confirmed on `cryptography` 46.0.6; TLS cert bom_ref keyed by `host:port` — fingerprint-based reconciliation must happen in `build_cbom()` Pass-1 or as a pre-pass |
| SCORE-01 (partial) | New signals contribute to `agility_signals` subscore — no 7th pillar | 2 new `SCORE_WEIGHTS` entries at +6.0 total; current sum 293.0/count 39; target 299.0/41 (or 299.0/40 with a single +6.0 entry at discretion) |
| LAB-01 (partial) | Chaos lab gains code-signing cert fixture coverage with `expected_results_*.md` oracle updates | `ldaps` profile confirmed at port 636 (`bitnamilegacy/openldap:2.6.10-debian-12-r4`); fixture requires DER cert with CodeSigning EKU added to `userCertificate` attribute; CLAUDE.md triple-update rule applies |
</phase_requirements>

---

## Summary

Phase 95 adds a passive code-signing certificate inventory scanner that discovers certs from two sources: (1) LDAP `userCertificate` attributes on existing LDAP targets (filtered to CodeSigning EKU), and (2) already-captured TLS cert objects checked in-process for the CodeSigning EKU — no new network fetches. The implementation is a `codesign_scanner.py` module that reuses virtually all helpers from `smime_scanner.py` (LDAP bind/search/parse pattern) and `adcs_scanner.py` (EKU parsing pattern). The new protocol label is `CODE_SIGNING` (uppercase, per Phase 94 casing lesson).

CBOM deduplication is the most novel aspect of this phase. The `cryptography` library exposes `cert.fingerprint(hashes.SHA256())` directly, verified at version 46.0.6. SHA-256 fingerprints must be embedded in `service_detail` (or a dedicated field) by the scanner so that `build_cbom()` can compare CODE_SIGNING endpoints against existing TLS-derived cert components. When the same cert is found via both TLS capture and code-signing LDAP, the TLS component wins and the code-signing scanner annotates it rather than emitting a duplicate. The CBOM pass must assert stable component counts — tested by an automated unit test.

Scoring advances SCORE_WEIGHTS +6.0 from 293.0 to 299.0 by adding agility signal(s) for code-signing weak-algorithm findings. The invariant test in `tests/test_score_weights_invariant.py` pins both sum and count; both must be updated in the same commit. The chaos lab reuses the existing `ldaps` profile at port 636 — a new DER cert fixture carrying the CodeSigning EKU is added to the LDAP user tree, and the `expected_results_v4.md` oracle plus `README.md` are updated in the same commit per CLAUDE.md.

**Primary recommendation:** Implement `codesign_scanner.py` as a near-copy of `smime_scanner.py` with EKU filter added, wire a `--inventory-code-signing` CLI gate in run_scan.py following the exact `_run_smime_phase()` / `_wrapped_phase()` pattern, add `CODE_SIGNING` to the builder and evidence layers following the SMIME/ADCS precedent, and dedup fingerprints via a SHA-256 lookup dict built during CBOM Pass-1 from TLS endpoints.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LDAP userCertificate discovery | Scanner (`codesign_scanner.py`) | Config (`ConnectorsCfg`) | Same tier as SMIME/ADCS; LDAP is a remote identity data source |
| TLS EKU in-process check | Scanner (`codesign_scanner.py`) | — | Operates on already-in-memory CryptoEndpoint list passed from run_scan.py |
| Weak-algorithm classification | Utility (`weak_crypto.py`) | Scanner (`codesign_scanner.py`) | Centralised predicate; scanner calls it inline for EC<256 gap |
| CodeSigning EKU detection | Scanner helper (inline, mirrors adcs_scanner.py) | — | EKU OID is a one-liner via `ExtendedKeyUsageOID.CODE_SIGNING` |
| SHA-256 fingerprint dedup | CBOM builder (`builder.py`) | Scanner (embeds fingerprint in service_detail) | Builder owns dedup logic; scanner must emit fingerprint for lookup |
| Scoring agility signal | Scoring (`scoring.py`) | Evidence (`evidence.py`) | Evidence counts events; scoring weights them |
| Chaos lab fixture | Lab (`quantum-chaos-enterprise-lab/`) | — | LDAP fixture lives in lab directory; triple-update per CLAUDE.md |

---

## Standard Stack

### Core (all already installed — no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | 46.0.6 [VERIFIED: project venv] | X.509 parsing, EKU OID lookup, SHA-256 fingerprint computation | Already used by smime_scanner, adcs_scanner, tls_scanner |
| `ldap3` | existing project dep [ASSUMED: version not pinned here] | LDAP anonymous bind + paged search | Already used by smime_scanner and adcs_scanner; no impacket |

No new package installations required for this phase. [VERIFIED: codebase inspection]

**Installation:** None needed.

---

## Package Legitimacy Audit

No new packages are introduced in this phase. Both `cryptography` and `ldap3` are existing project dependencies already in use by smime_scanner.py and adcs_scanner.py. [VERIFIED: codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
CLI --inventory-code-signing
  │
  ▼
run_scan.py  _run_codesign_phase()
  │   ├─► codesign_scanner.scan_codesign_from_ldap(cfg.connectors.codesign_targets)
  │   │       └─► ldap3 paged_search("userCertificate=*") on target hosts
  │   │           filter: cert has EKU 1.3.6.1.5.5.7.3.3
  │   │           compute: SHA-256 fingerprint → embed in service_detail
  │   │           classify: weak-algo (RSA<2048 / EC<256 / SHA-1) → HIGH
  │   │           emit: CryptoEndpoint(protocol="CODE_SIGNING")
  │   │
  │   └─► codesign_scanner.scan_codesign_from_tls_endpoints(tls_endpoints)
  │           filter existing TLS CryptoEndpoint list for certs with EKU 1.3.6.1.5.5.7.3.3
  │           (reads DER bytes from already-captured cert chain — no new network I/O)
  │           compute: SHA-256 fingerprint → embed in service_detail
  │           classify: weak-algo → HIGH if weak
  │           emit: CryptoEndpoint(protocol="CODE_SIGNING")
  │
  ▼
codesign_endpoints list → flows into:
  ├─► build_cbom()
  │     Pass-1: register algorithm component (CODE_SIGNING branch)
  │     Fingerprint dedup pass: build {sha256_hex: bom_ref} from TLS cert components
  │       - if CODE_SIGNING endpoint fingerprint matches TLS component → annotate existing, skip new
  │       - else → emit new CRYPTOGRAPHIC_ASSET/CERTIFICATE component
  │     Pass-2: skip CODE_SIGNING (no separate X.509 cert component — already handled in dedup pass)
  │     Pass-3: skip CODE_SIGNING (no ProtocolProperties — not a transport protocol)
  │
  └─► evidence.py build_evidence_summary()
        proto == "CODE_SIGNING" branch:
          codesign_weak_algo_count += 1 if service_detail has "weak"
        returns agility_codesign_weak_algo_count in dict
  │
  └─► scoring.py compute_readiness_score()
        agility_codesign_weak_algo_ratio weight (+6.0)
        agility_impacts.append(...)
```

### Recommended Project Structure

```
quirk/scanner/
├── codesign_scanner.py    # NEW — LDAP userCertificate + TLS EKU check

tests/
├── test_codesign_scanner.py   # NEW — unit tests, mirrors test_smime_scanner.py
├── fixtures/codesign/         # NEW — DER cert fixtures with CodeSigning EKU

quantum-chaos-enterprise-lab/
├── docker-compose.yml     # ADD codesign user with userCertificate to ldaps service
├── expected_results_v4.md # ADD code-signing section under ldaps profile
├── README.md              # ADD code-signing fixture description
```

### Pattern 1: LDAP userCertificate Discovery (mirrors smime_scanner.py)

**What:** Anonymous bind + paged search on LDAP targets, filter `userCertificate` entries carrying CodeSigning EKU.
**When to use:** When `--inventory-code-signing` is set and `cfg.connectors.codesign_targets` is non-empty.

```python
# Source: quirk/scanner/smime_scanner.py (VERIFIED: read 2026-05-23)
# Pattern to adapt: _bind_and_search() + loop over raw_attributes["userCertificate"]
# Key difference: filter on EKU OID 1.3.6.1.5.5.7.3.3 after cert parse

from cryptography.x509 import ExtendedKeyUsage
from cryptography.x509.oid import ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes

EKU_CODE_SIGNING = ExtendedKeyUsageOID.CODE_SIGNING  # OID 1.3.6.1.5.5.7.3.3

def _has_codesigning_eku(cert) -> bool:
    try:
        eku_ext = cert.extensions.get_extension_for_class(ExtendedKeyUsage)
        return EKU_CODE_SIGNING in eku_ext.value
    except Exception:
        return False

def _cert_fingerprint_sha256(cert) -> str:
    return cert.fingerprint(hashes.SHA256()).hex()
```

### Pattern 2: EC<256 Weak Key Classification (gap in weak_crypto.py)

**What:** `weak_crypto.is_weak_cipher()` covers SHA-1 family and named weak ciphers. EC<256 requires inline logic matching the RSA<2048 pattern in smime_scanner.py and adcs_scanner.py.
**When to use:** In `_classify_codesign_severity()` inside codesign_scanner.py.

```python
# Source: quirk/scanner/smime_scanner.py:113-115 (VERIFIED: read 2026-05-23)
# Same pattern for EC<256 (not covered by is_weak_cipher):
key_alg = (parsed.get("key_alg") or "").upper()
key_bits = parsed.get("key_bits")
if key_alg == "RSA" and isinstance(key_bits, int) and key_bits < 2048:
    reasons.append("weak-rsa-key")
if key_alg == "ECDSA" and isinstance(key_bits, int) and key_bits < 256:
    reasons.append("weak-ec-key")
```

### Pattern 3: CBOM builder — new protocol branch (mirrors SMIME/ADCS)

**What:** Add `elif ep.protocol == "CODE_SIGNING":` in Pass-1 to register algorithm component. Add `"CODE_SIGNING"` to both the Pass-2 skip tuple and the Pass-3 skip tuple.
**When to use:** In `build_cbom()` in `quirk/cbom/builder.py`.

```python
# Source: quirk/cbom/builder.py:508-525 (VERIFIED: read 2026-05-23)
# Existing SMIME branch for reference:
elif ep.protocol == "SMIME":
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)

# Pass-2 skip tuple (line 620-624) — add "CODE_SIGNING":
if ep.protocol in (
    "SSH", "BEARER_TOKEN", "JWT", "CONTAINER", "SOURCE", "KERBEROS",
    "SAML", "DNSSEC", "SMIME", "ADCS", "CODE_SIGNING",  # ADD CODE_SIGNING
    *DAR_SKIP_PROTOCOLS, *MOTION_PLAINTEXT_PROTOCOLS,
):
    continue

# Pass-3 skip tuple (line 705-710) — add "CODE_SIGNING":
elif ep.protocol in (
    "JWT", "BEARER_TOKEN", "CONTAINER", "SOURCE", "AWS", "AZURE",
    "DNSSEC", "SAML", "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING",  # ADD
    *DAR_SKIP_PROTOCOLS, *MOTION_PLAINTEXT_PROTOCOLS,
):
    continue
```

### Pattern 4: SHA-256 Fingerprint Dedup in build_cbom()

**What:** CSIGN-03 requires that a cert seen via both TLS capture and code-signing LDAP appear only once in the CBOM. TLS cert components are currently keyed by `host:port` in Pass-2. The dedup must happen by fingerprint.
**Design decision (at Claude's discretion):** The scanner embeds the SHA-256 hex fingerprint in `service_detail` as `fingerprint=<hex>` so the builder can extract it without reparsing the cert. The builder builds a `{fp_hex: bom_ref}` dict during Pass-2 from TLS cert components, then checks CODE_SIGNING endpoints against it in a separate pass.

```python
# Fingerprint extraction helper in builder.py or codesign_scanner.py:
def _extract_fingerprint_from_service_detail(service_detail: str | None) -> str | None:
    if not service_detail:
        return None
    for part in service_detail.split("|"):
        if part.startswith("fingerprint="):
            return part[len("fingerprint="):]
    return None
```

**Important caveat:** TLS scanner (`tls_scanner.py`) does NOT currently embed SHA-256 fingerprints in any field. The TLS-side dedup requires either:
- Option A (simpler): build_cbom() re-derives fingerprints from cert_subject+serial combo stored as service_detail — but TLS scanner does NOT store serial in service_detail either.
- Option B (recommended): The dedup in CSIGN-03 applies only to CODE_SIGNING endpoints among themselves (dedup two CODE_SIGNING endpoints that found the same cert via LDAP and TLS-EKU paths). TLS-derived cert components are already unique by host:port bom_ref. The annotation approach adds a `quirk:code-signing-eku` property to the existing bom_ref component.

**Resolution:** The CONTEXT.md says "TLS-derived component WINS; code-signing adds an EKU/usage annotation." This only requires CODE_SIGNING endpoints to not emit a _duplicate cert component_ for a cert already in Pass-2 output. The dedup can be implemented as: CODE_SIGNING endpoints skip Pass-2 (they are already in the Pass-2 skip tuple), and a post-Pass-2 step looks for matching cert components by fingerprint if the fingerprint is stored in service_detail. For the test to assert "stable CBOM component count," both scanner paths must emit fingerprints in service_detail that the builder can compare.

### Pattern 5: Evidence counter + scoring key

**What:** Add `codesign_weak_algo_count` counter in `evidence.py` and a corresponding weight in `scoring.py`. Follow Phase 94 pattern exactly.
**When to use:** In `build_evidence_summary()` and `compute_readiness_score()`.

```python
# Source: quirk/intelligence/evidence.py:305-322 (VERIFIED: read 2026-05-23)
# Phase 94 bearer-token pattern to mirror:
elif proto == "BEARER_TOKEN":
    _bt_alg = str(getattr(ep, "cert_pubkey_alg", "") or "")
    if _bt_alg and _bt_alg.lower() != "none":
        bearer_token_weak_alg_count += 1

# Phase 95 analog:
elif proto == "CODE_SIGNING":
    _cs_detail = str(getattr(ep, "service_detail", "") or "").lower()
    if "weak" in _cs_detail:
        codesign_weak_algo_count += 1
```

```python
# Source: quirk/intelligence/scoring.py:59-60 (VERIFIED: read 2026-05-23)
# Phase 94 weights pattern:
"agility_weak_jwt_alg_ratio": 6.0,      # Phase 94 SCORE-01
"agility_openapi_plaintext_ratio": 4.0, # Phase 94 SCORE-01

# Phase 95 analog (weight split at Claude's discretion — total must be +6.0):
"agility_codesign_weak_algo_ratio": 6.0,  # Phase 95 SCORE-01
```

### Pattern 6: run_scan.py wiring (mirrors _run_smime_phase)

**What:** Add `--inventory-code-signing` CLI flag in the argparse block, wire a `_run_codesign_phase()` function in the DAR/identity scan block, add `codesign_endpoints` to the final `endpoints` assembly, and add `"CODE_SIGNING"` to `_dar_protocols` for resume logic.

```python
# Source: run_scan.py:1691-1711 (VERIFIED: read 2026-05-23)
# SMIME phase pattern to mirror exactly:
def _run_codesign_phase():
    if not (getattr(args, "inventory_code_signing", False)
            and getattr(cfg.connectors, "codesign_targets", None)):
        return []
    from quirk.scanner.codesign_scanner import scan_codesign_from_ldap
    eps = scan_codesign_from_ldap(
        targets=cfg.connectors.codesign_targets,
        timeout=getattr(cfg.connectors, "codesign_timeout", 10),
        logger=logger,
        session_start=session_start,
        search_base=getattr(cfg.connectors, "codesign_search_base", None),
    )
    logger.info("CODE_SIGNING scan: %d endpoints from %d targets",
                len(eps), len(cfg.connectors.codesign_targets))
    return eps
codesign_endpoints = _wrapped_phase(
    run_stats, "codesign_scanning", "codesign_scanner",
    _run_codesign_phase, error_endpoints, logger,
)
```

### Anti-Patterns to Avoid

- **Protocol label in any case other than `CODE_SIGNING`:** `code_signing`, `codesign`, `Code-Signing` — any variant will silently break CBOM Pass-1/2/3 skip tuples, evidence counters, and scoring. Phase 94 casing lesson: consumers key on exact uppercase string match.
- **Adding EC<256 to `_WEAK_CIPHER_TOKENS`:** The string `"ECDSA-256"` would incorrectly flag `AES-256` variants via substring match. Keep EC<256 as an inline key-size check, not a token.
- **Importing `impacket` in codesign_scanner.py:** Breaks `[all]` install. ldap3 only.
- **Computing fingerprint from cert_subject+serial only:** SHA-256 fingerprint uses the full DER-encoded cert. Use `cert.fingerprint(hashes.SHA256())`.
- **Updating only sum in test_score_weights_invariant.py:** Both `test_score_weights_sum_invariant` and `test_score_weights_count_invariant` must be updated. Phase 94 lesson: forgetting the count assertion causes CI failure.
- **Chaos lab: updating only expected_results_v4.md:** CLAUDE.md requires `lab.sh` + `README.md` + `expected_results_*.md` in the same change. The `ldaps` profile is derived dynamically from docker-compose.yml by `_derive_all_profiles()` — it is already in `all`; only the seed data and oracle need updating.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LDAP anonymous bind + paged search | Custom socket/SASL code | `ldap3.Connection.extend.standard.paged_search` | Already verified in smime_scanner.py |
| X.509 DER parsing | Manual ASN.1 decode | `load_der_x509_certificate()` + fallback `load_pem_x509_certificate()` | Exact pattern in smime_scanner.py:58-100 |
| EKU OID check | Hardcoded string compare | `cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)` + `ExtendedKeyUsageOID.CODE_SIGNING` | Cryptography library handles OID representation, ASN.1 variants |
| SHA-256 cert fingerprint | Manual hash of fields | `cert.fingerprint(hashes.SHA256()).hex()` | Confirmed working on cryptography 46.0.6 |
| SHA-1 / weak-cipher detection | New token list | `is_weak_cipher(sig_hash)` from `quirk/util/weak_crypto.py` | Single source of truth per D-02; SHA1/SHA-1 in `_WEAK_CIPHER_TOKENS` |
| EC key size extraction | bitstring parse | `isinstance(pub, ec.EllipticCurvePublicKey); pub.key_size` | Same as RSA path in smime_scanner.py:76-81 |

---

## Common Pitfalls

### Pitfall 1: Protocol casing — `CODE_SIGNING` vs any variant

**What goes wrong:** Every consumer of `ep.protocol` — `evidence.py` `_PROTOCOL_KEYS`, `scoring.py` agility block, `builder.py` Pass-1/2/3 branches, `run_scan.py` `_dar_protocols` tuple, resume logic — does an exact uppercase string comparison. A single lowercase character silently bypasses all scoring, CBOM, and resume handling.
**Why it happens:** Phase 94 introduced BEARER_TOKEN and the casing lesson was documented in CONTEXT.md. Developers may follow smime naming patterns (lowercase `smime` in some variable names) and forget the protocol field is uppercase.
**How to avoid:** Use the constant `CODE_SIGNING = "CODE_SIGNING"` at module top of codesign_scanner.py and reference it everywhere instead of the string literal.
**Warning signs:** Protocol appears in proto_counts summary as zero despite scan running; score not changing; test_evidence_summary passing but score not updating.

### Pitfall 2: SCORE_WEIGHTS dual invariant — sum AND count

**What goes wrong:** Updating only the sum assertion in `test_score_weights_sum_invariant` leaves `test_score_weights_count_invariant` failing at CI.
**Why it happens:** Two separate test functions; developers update the first one they see.
**How to avoid:** The count must change from 39 to 40 (one new `agility_codesign_weak_algo_ratio` entry at +6.0) or 39→41 (two entries summing to +6.0). Both tests must match the actual dict length and sum simultaneously.
**Warning signs:** CI passes sum test but fails count test; or vice versa.

### Pitfall 3: CBOM dedup — TLS fingerprints not pre-computed

**What goes wrong:** TLS scanner does NOT store SHA-256 fingerprints. A dedup lookup comparing CODE_SIGNING fingerprints against TLS cert objects requires either re-parsing TLS cert bytes (not stored in CryptoEndpoint) or using a different dedup signal.
**Why it happens:** The CONTEXT says "dedup by SHA-256 fingerprint" but TLS certs are stored as parsed metadata (subject, issuer, not_after) — not as raw DER in the CryptoEndpoint model.
**How to avoid:** The practical dedup path is: codesign_scanner embeds the fingerprint in `service_detail` as `fingerprint=<hex>`; builder compares CODE_SIGNING fingerprints among themselves and also against fingerprints of cert components that TLS Pass-2 would emit. For TLS cert objects seen with EKU via the in-process path, the dedup is by fingerprint embedded in service_detail vs other CODE_SIGNING endpoints only. The test for "stable CBOM component count" can use two CODE_SIGNING endpoints with the same fingerprint; TLS cert components (keyed by host:port in Pass-2) are a separate component class and the annotation is a CycloneDX Property added to the bom_ref component.
**Warning signs:** Unit test for dedup produces N+1 components when same cert seen twice; or property annotation not appearing on TLS cert component.

### Pitfall 4: `userCertificate` vs `userSMIMECertificate` attribute name

**What goes wrong:** smime_scanner.py queries BOTH `userCertificate` and `userSMIMECertificate`. Code-signing inventory should only query `userCertificate` (the standard attribute; CONTEXT.md says "LDAP `userCertificate`").
**Why it happens:** Copy-pasting from smime_scanner.py brings along `_SMIME_ATTRS = ("userCertificate", "userSMIMECertificate")` without adjustment.
**How to avoid:** Define `_CODESIGN_ATTRS = ("userCertificate",)` — only the standard RFC 4523 attribute.
**Warning signs:** Scanner returns extra findings from `userSMIMECertificate` entries that don't have CodeSigning EKU (they would be filtered by EKU check, so this is low-risk but wastes an LDAP attribute fetch).

### Pitfall 5: Chaos lab triple-update rule

**What goes wrong:** Updating `expected_results_v4.md` without updating `README.md` or without updating the LDAP seed data to include the code-signing fixture causes lab validation to fail.
**Why it happens:** Three separate files; CLAUDE.md Chaos Lab Maintenance rule is easy to miss.
**How to avoid:** The `ldaps` profile uses a plain OpenLDAP instance with no seed sidecar today — there are no LDIF fixture files for it. Adding a code-signing fixture requires adding a seed mechanism (sidecar like smime-seed, or an init script) plus a DER cert file with CodeSigning EKU. The `_derive_all_profiles()` function reads profiles from docker-compose.yml dynamically — `ldaps` is already included; no change to `lab.sh` ALL_PROFILES enumeration is needed. Only `expected_results_v4.md` and `README.md` need updating for the oracle.
**Warning signs:** Lab validation shows no code-signing finding from ldaps; lab.sh diff absent for triple-update.

### Pitfall 6: EC<256 not covered by `is_weak_cipher()`

**What goes wrong:** `is_weak_cipher("ECDSA")` returns False (correctly — "ECDSA" alone is not a weak cipher token). EC<256 detection requires explicit key-size check.
**Why it happens:** Developers assume `is_weak_cipher()` covers all weak-algo cases.
**How to avoid:** Add inline EC<256 check alongside RSA<2048 check in `_classify_codesign_severity()`:
```python
if key_alg == "ECDSA" and isinstance(key_bits, int) and key_bits < 256:
    reasons.append("weak-ec-key")
```
**Warning signs:** EC-192 or EC-224 cert does not emit HIGH finding.

---

## Code Examples

### EKU detection from a parsed cert

```python
# Source: cryptography library, confirmed via REPL on cryptography 46.0.6 (VERIFIED)
from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID

EKU_CODE_SIGNING = ExtendedKeyUsageOID.CODE_SIGNING  # OID 1.3.6.1.5.5.7.3.3

def _has_codesigning_eku(cert: "x509.Certificate") -> bool:
    try:
        eku_ext = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        return EKU_CODE_SIGNING in eku_ext.value
    except x509.ExtensionNotFound:
        return False
    except Exception:
        return False
```

### SHA-256 fingerprint computation

```python
# Source: cryptography library, confirmed via REPL on cryptography 46.0.6 (VERIFIED)
from cryptography.hazmat.primitives import hashes

def _cert_fingerprint_sha256(cert: "x509.Certificate") -> str:
    return cert.fingerprint(hashes.SHA256()).hex()
```

### SCORE_WEIGHTS update (target state)

```python
# Source: quirk/intelligence/scoring.py:59-60 — current state (VERIFIED: read 2026-05-23)
# Current (Phase 94, sum=293.0, count=39):
"agility_weak_jwt_alg_ratio": 6.0,      # Phase 94 SCORE-01
"agility_openapi_plaintext_ratio": 4.0, # Phase 94 SCORE-01

# Phase 95 addition (sum → 299.0, count → 40):
"agility_codesign_weak_algo_ratio": 6.0,  # Phase 95 SCORE-01 — weak RSA/EC/SHA-1 on code-signing cert
```

### test_score_weights_invariant.py — target state of both assertions

```python
# Source: tests/test_score_weights_invariant.py (VERIFIED: read 2026-05-23)
# test_score_weights_sum_invariant: change 293.0 → 299.0
assert abs(sum(SCORE_WEIGHTS.values()) - 299.0) < 1e-9

# test_score_weights_count_invariant: change 39 → 40
assert len(SCORE_WEIGHTS) == 40
```

### _PROTOCOL_KEYS addition in evidence.py

```python
# Source: quirk/intelligence/evidence.py:11-17 (VERIFIED: read 2026-05-23)
# Current state ends with:
"BEARER_TOKEN", "OPENAPI")

# Phase 95 target:
"BEARER_TOKEN", "OPENAPI",
"CODE_SIGNING")   # Phase 95 CSIGN-01
```

### ConnectorsCfg additions in config.py

```python
# Source: quirk/config.py:224-238 (VERIFIED: read 2026-05-23)
# Mirror of SMIME pattern:
enable_codesign: bool = False
codesign_targets: list = field(default_factory=list)
codesign_search_base: Optional[str] = None
codesign_timeout: int = 10
```

### run_scan.py _dar_protocols addition

```python
# Source: run_scan.py:1503 (VERIFIED: read 2026-05-23)
# Current:
_dar_protocols = ("S3", "AZURE-BLOB", "K8S", "GCS", "VAULT", "DNSSEC", "SAML",
                  "KERBEROS", "SMIME", "ADCS")
# Phase 95 target:
_dar_protocols = ("S3", "AZURE-BLOB", "K8S", "GCS", "VAULT", "DNSSEC", "SAML",
                  "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `smime_scanner.py` queries both `userCertificate` and `userSMIMECertificate` | `codesign_scanner.py` queries only `userCertificate`, filtered to CodeSigning EKU | Phase 95 (new) | Narrower query; no S/MIME-only certs inadvertently captured |
| CBOM cert dedup keyed by host:port in Pass-2 | CODE_SIGNING endpoints skip Pass-2; fingerprint-based annotation step | Phase 95 (new) | Prevents cert component duplication across two discovery paths |
| SCORE_WEIGHTS sum=293.0 / count=39 | sum=299.0 / count=40 | Phase 95 | Single new agility weight for code-signing weak-algo ratio |

**Deprecated/outdated:**
- The pattern of `_SMIME_ATTRS = ("userCertificate", "userSMIMECertificate")` for code-signing is inapplicable. Code-signing MUST only look at `userCertificate`.

---

## Runtime State Inventory

> Phase 95 is a greenfield feature addition, not a rename/refactor. No runtime state inventory required.

None — verified by scope inspection. Phase adds new code paths; does not rename existing strings or migrate stored data.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cryptography` (Python lib) | EKU detection, SHA-256 fingerprint, cert parsing | ✓ | 46.0.6 | — |
| `ldap3` (Python lib) | LDAP bind + paged search | ✓ [ASSUMED: same as smime/adcs scanners] | — | Scanner returns [] with warning |
| `bitnamilegacy/openldap:2.6.10-debian-12-r4` (Docker) | Chaos lab `ldaps` profile | ✓ [per expected_results_v4.md] | 2.6.10 | — |
| `.venv/bin/python` | Test execution | ✓ [project standard] | 3.11+ | Do not use system python3 |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pytest.ini` or `pyproject.toml [tool.pytest]` |
| Quick run command | `.venv/bin/python -m pytest tests/test_codesign_scanner.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CSIGN-01 | LDAP userCertificate discovery returns CODE_SIGNING endpoints | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_ldap_codesign_eku_filter -x` | ❌ Wave 0 |
| CSIGN-01 | TLS EKU in-process check returns CODE_SIGNING endpoints | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_tls_eku_check -x` | ❌ Wave 0 |
| CSIGN-01 | Non-CodeSigning certs not emitted | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_non_codesign_cert_filtered -x` | ❌ Wave 0 |
| CSIGN-02 | RSA<2048 → HIGH severity | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_rsa1024_emits_high -x` | ❌ Wave 0 |
| CSIGN-02 | EC<256 → HIGH severity | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_ec192_emits_high -x` | ❌ Wave 0 |
| CSIGN-02 | SHA-1 sig hash → HIGH severity | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_sha1_sig_emits_high -x` | ❌ Wave 0 |
| CSIGN-02 | Strong cert → no endpoint emitted | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_strong_cert_safe -x` | ❌ Wave 0 |
| CSIGN-03 | Same cert via two paths → stable CBOM count | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py::test_cbom_dedup_stable_count -x` | ❌ Wave 0 |
| SCORE-01 | SCORE_WEIGHTS sum == 299.0 | unit | `.venv/bin/python -m pytest tests/test_score_weights_invariant.py -x` | ✅ (update) |
| SCORE-01 | SCORE_WEIGHTS count == 40 | unit | `.venv/bin/python -m pytest tests/test_score_weights_invariant.py -x` | ✅ (update) |
| SCORE-01 | codesign_weak_algo_count in evidence dict | unit | `.venv/bin/python -m pytest tests/test_evidence.py -x -k codesign` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_codesign_scanner.py tests/test_score_weights_invariant.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_codesign_scanner.py` — covers CSIGN-01/02/03
- [ ] `tests/fixtures/codesign/` — DER cert fixtures: `codesign_rsa1024_sha1.der`, `codesign_ec192.der`, `codesign_rsa2048_sha256.der` (strong, filtered), `codesign_rsa2048_sha256_noncoding.der` (no CodeSigning EKU, filtered)
- [ ] `tests/test_score_weights_invariant.py` — update assertions (existing file; edit not create)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Scanner uses anonymous LDAP bind (passive read-only) |
| V3 Session Management | No | No session state |
| V4 Access Control | No | Read-only LDAP; no writes |
| V5 Input Validation | Yes | `safe_str()` on all LDAP-derived strings (per smime/adcs pattern); paged search filter is hardcoded |
| V6 Cryptography | No | Using cryptography library for parsing only |

### Known Threat Patterns for LDAP + Cert Parsing Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LDAP injection via DN/filter | Tampering | Filter `userCertificate=*` is hardcoded literal — not constructed from user input |
| Malformed DER cert causing exception | Denial of Service | DER parse wrapped in try/except; returns `None` on failure (mirrors smime_scanner.py:64-72) |
| Very large cert value causing OOM | Denial of Service | paged_search limits to 500 entries per page; individual cert parse is bounded by cryptography library |
| `service_detail` leaking sensitive cert data | Information Disclosure | Embed only fingerprint hex + key metadata — never cert subject of a person. `user_dn` embeds LDAP DN (mirrors smime_scanner.py practice; acceptable for internal consultant tool) |

---

## Open Questions (RESOLVED)

**RESOLVED (OQ1):** CSIGN-03 dedup uses a split contract — LDAP-sourced CODE_SIGNING certs (full DER available) dedup by SHA-256 fingerprint; the TLS-EKU path uses a surrogate compound key `(cert_subject, cert_pubkey_alg, cert_not_after)` to annotate the existing TLS-derived component (TLS wins) rather than emit a duplicate. Plan 95-02 implements both paths and adds `test_cbom_tls_plus_codesign_no_dup` proving a stable component count when the same cert is seen via both sources.

**RESOLVED (OQ2):** `scan_codesign_from_tls_endpoints(tls_endpoints, ...)` is a separate function in `codesign_scanner.py` (testability); `run_scan.py::_run_codesign_phase` calls it AFTER the TLS scan with the captured `tls_endpoints` and folds its CODE_SIGNING endpoints into the final list (Plan 95-03, wired + tested via `test_tls_eku_path_invoked` and `test_tls_eku_check`).

1. **How to embed fingerprint for TLS-path EKU check**
   - What we know: TLS scanner stores parsed metadata (cert_subject, cert_pubkey_alg, cert_not_after) but NOT raw DER bytes in CryptoEndpoint model. SHA-256 fingerprint requires the full DER cert.
   - What's unclear: The TLS EKU path (`scan_codesign_from_tls_endpoints`) receives CryptoEndpoint objects with `cert_pubkey_alg` etc. but no raw cert bytes. Computing fingerprint requires the DER, which is only available during TLS scanning.
   - Recommendation: For the TLS-EKU path, dedup against other CODE_SIGNING endpoints using fingerprint (which TLS path cannot compute from CryptoEndpoint alone). The TLS path should instead use `(cert_subject + cert_pubkey_alg + cert_not_after)` as a compound surrogate dedup key when raw DER is unavailable. Alternatively, scope TLS EKU dedup to: "if a CODE_SIGNING endpoint matches by host:port an existing TLS endpoint, annotate — don't duplicate." The CSIGN-03 automated test must specify the exact contract (fingerprint-based vs surrogate-key-based).

2. **Whether codesign_scanner.py calls the TLS-EKU check internally or run_scan.py passes tls_endpoints to it**
   - What we know: CONTEXT says "in-process EKU check" on already-captured TLS certs. SMIME scanner gets `targets` (list of LDAP URLs). TLS EKU check would get a list of CryptoEndpoint objects.
   - What's unclear: Whether the function signature is `scan_codesign_from_tls_endpoints(tls_endpoints: list[CryptoEndpoint])` or whether run_scan.py does the EKU check inline.
   - Recommendation: Separate function in codesign_scanner.py for clarity and testability. run_scan.py passes `tls_endpoints` to it after TLS scanning completes.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ldap3` version in project venv is compatible with existing smime/adcs scanner usage | Standard Stack | Zero risk — already in use by 2 other scanners; any incompatibility would already be failing |
| A2 | `bitnamilegacy/openldap:2.6.10-debian-12-r4` supports `userCertificate` attribute natively | Chaos lab | If not natively supported, a custom schema would need to be loaded (like adcs-openldap does with msPKI OIDs) — MEDIUM complexity fix |
| A3 | The `ldaps` profile at port 636 has no existing seed sidecar for user data | Architecture | If incorrect, there's already an LDIF mechanism and only a new user + cert entry is needed |

---

## Sources

### Primary (HIGH confidence)
- `quirk/scanner/smime_scanner.py` — LDAP `userCertificate` discovery pattern, cert parse, severity classification [VERIFIED: read 2026-05-23]
- `quirk/scanner/adcs_scanner.py` — EKU OID constants, weak-algo classification [VERIFIED: read 2026-05-23]
- `quirk/util/weak_crypto.py` — `is_weak_cipher()` token set [VERIFIED: read 2026-05-23]
- `quirk/cbom/builder.py` — Pass-1/2/3 structure, SMIME/ADCS/BEARER_TOKEN branch patterns, skip tuples [VERIFIED: read 2026-05-23]
- `quirk/intelligence/evidence.py` — `_PROTOCOL_KEYS`, Phase 94 bearer/openapi counter patterns [VERIFIED: read 2026-05-23]
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` current state (293.0 / 39 entries), agility block structure [VERIFIED: read 2026-05-23]
- `tests/test_score_weights_invariant.py` — exact assertion values and docstring history [VERIFIED: read 2026-05-23]
- `run_scan.py` — `_run_smime_phase` / `_run_adcs_phase` wiring pattern, `_dar_protocols` tuple, `--openapi-spec` CLI flag pattern [VERIFIED: read 2026-05-23]
- `quirk/config.py` — `ConnectorsCfg` fields for smime/adcs, `_KNOWN_CONNECTOR_KEYS` pattern [VERIFIED: read 2026-05-23]
- `quirk/models.py` — `CryptoEndpoint` model fields [VERIFIED: read 2026-05-23]
- `quantum-chaos-enterprise-lab/docker-compose.yml` — `ldaps` profile at port 636 [VERIFIED: read 2026-05-23]
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — ldaps oracle section [VERIFIED: read 2026-05-23]
- `quantum-chaos-enterprise-lab/smime/certs/regen.sh` — DER cert generation pattern for fixtures [VERIFIED: read 2026-05-23]
- `cryptography` library REPL: `ExtendedKeyUsageOID.CODE_SIGNING.dotted_string == "1.3.6.1.5.5.7.3.3"`, `cert.fingerprint(hashes.SHA256()).hex()` [VERIFIED: Python REPL 2026-05-23]

### Secondary (MEDIUM confidence)
- `quantum-chaos-enterprise-lab/lab.sh` — `_derive_all_profiles()` dynamically reads profiles from compose file; no hardcoded ALL_PROFILES list [VERIFIED: read 2026-05-23]

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — no new packages; existing deps confirmed
- Architecture: HIGH — all patterns directly verified in codebase
- Pitfalls: HIGH — directly observed from codebase invariants and CONTEXT.md lessons
- CBOM dedup contract: MEDIUM — the exact dedup mechanism for TLS-path EKU check has one open question (raw DER not stored in CryptoEndpoint); surrogate key approach documented

**Research date:** 2026-05-23
**Valid until:** 2026-07-01 (stable codebase; no external API dependencies)

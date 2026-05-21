# Phase 80: Windows AD CS Scanner — Research

**Researched:** 2026-05-16
**Domain:** AD CS LDAP enumeration / certificate-template misconfiguration detection
**Confidence:** HIGH (locked decisions resolve most ambiguity; ESC bitmasks verified against Microsoft `[MS-CRTD]` open spec + Certipy source)

## Summary

Phase 80 adds an authenticated-LDAP scanner for Windows Active Directory Certificate Services. Every architectural decision is **already locked** in `80-CONTEXT.md`: singular `quirk/scanner/adcs_scanner.py`, duplicate (not shared) LDAP scaffolding, all 8 ESCs best-effort with `ADCS-COVERAGE-GAP` findings for non-observable cases, separate `[adcs]` extras group, separate `adcs` chaos lab profile on port `38910`, `protocol="ADCS"` uppercase, AST gate forbids `certipy_ad` + `cryptography.x509.CertificateSigningRequestBuilder` + impacket LDAP write ops, and four new SCORE_WEIGHTS entries at weight 2.0 (Phase 83 owns the invariant reconciliation, do NOT touch `test_score_weights_invariant.py`).

The Phase 79 SMIME scanner is the cleanest structural template: bind + paged_search, per-attribute parse, severity-then-emit, graceful unreachable path that produces a `CryptoEndpoint` rather than propagating. Phase 80 follows that shape exactly. Phase 79 mutated `cbom/builder.py` (added `"SMIME"` to the two inline skip tuples at lines **538** and **622** — CONTEXT's "528 + 611" is the Phase 78 baseline), `db.py` `_IDENTITY_COLUMNS` (added `smime_scan_json`), and `scoring.py` / `evidence.py` (3 weights + 3 counters under identity_trust). Phase 80 appends analogously.

The single non-trivial open question that REQUIREMENTS leaves ambiguous — *"is ESC4 ACL parsing in scope?"* — is resolved by the locked Area-1 decision: emit an `ADCS-COVERAGE-GAP` finding instead of pretending to detect ESC4 from `nTSecurityDescriptor` alone. The v4.10 SUMMARY research (commit `c5d1d61`) actually argued *against* emitting ESC-numbered findings without ACL verification, but CONTEXT supersedes RESEARCH per the project's documented planner-precedence rule — best-effort ESC1-ESC8 with explicit coverage-gap surfacing is the locked path.

**Primary recommendation:** Clone `smime_scanner.py` structurally. Add an LDAP search scoped to `CN=Public Key Services,CN=Services,CN=Configuration,<rootDSE>` with two phases (CA enumeration → template enumeration), classify each template against the ESC1-ESC8 bitmask table below, and emit one `CryptoEndpoint(protocol="ADCS")` per finding plus one `ADCS-COVERAGE-GAP` per ESC class that cannot be observed from LDAP attributes alone.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AD LDAP bind + Configuration partition search | Backend / Scanner | — | Mirrors `smime_scanner._bind_and_search`; one scanner per protocol |
| ESC bitmask classification | Backend / Scanner | `quirk/util/weak_crypto.py` (for CA sig alg) | Pure Python logic, no shared helper extraction |
| CA signing cert parsing | Backend / Scanner | `cryptography.x509` | DER parsing identical to SMIME path |
| ORM persistence (`adcs_scan_json`) | DB layer | `quirk/db.py:_IDENTITY_COLUMNS` | Additive ALTER-IF-MISSING via shared `_ensure_columns` |
| Scoring + evidence counters | Intelligence layer | `quirk/intelligence/{scoring,evidence}.py` | Four new ratios under `identity_trust` |
| CBOM emission | CBOM layer | `quirk/cbom/builder.py` lines 538 + 622 | Pass-1 emits CA sig alg + template key alg; Pass-2/3 skip |
| Chaos lab fixture | Test infra | `quantum-chaos-enterprise-lab/adcs/` | OpenLDAP + custom schema LDIF; port 38910 |
| AST gate | CI | `tests/test_adcs_ast_gate.py` | Forbids certipy_ad / CSRBuilder / impacket modify |
| Extras matrix CI | CI | `tests/test_extras_install_adcs.py` (new) or extend `test_install_all_excludes_impacket.py` | Asserts cryptography>=44.0 across `[adcs]`, `[all]`, `[all]+[adcs]` |

## Standard Stack

### Core (no new pip deps — all locked by CONTEXT and the existing v4.10 dependency floor)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ldap3` | `>=2.9.1` | Anonymous + simple bind; paged search; `extend.standard.paged_search` | Already in `[identity]`; used by smime/kerberos LDAP probe; no impacket cross-pull |
| `cryptography` | `>=44.0` | `load_der_x509_certificate` for CA cert from `cACertificate` attribute | Already a core dependency; **must remain >=44.0** (Phase 45 D-01 invariant) |
| `python` stdlib `ast` | n/a | AST gate walker | Phase 59 / 79 pattern |
| `pytest` | existing | Unit + AST + CI matrix gates | Project default |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ldap3 anonymous bind | impacket `ldap.LDAPConnection` | impacket forbidden in `[all]` (pyOpenSSL cryptography downgrade). `[adcs]` MUST NOT add impacket — ldap3 path is the only acceptable choice. |
| `certipy-ad` for ESC checks | (none — locked OUT by v4.10-D-02) | Would re-pin `cryptography~=42.0.8`, breaking TLS scanner |
| Shared `_ldap_bind_search` helper | Extract from smime + kerberos + adcs | CONTEXT Area-2 explicitly chose duplication. ~30 lines of identical scaffolding is acceptable to keep scanners independent. |

**Installation:** No new packages. The `[adcs]` extras group cross-references existing libraries:

```toml
# pyproject.toml — append under [project.optional-dependencies]
adcs = [
    "ldap3>=2.9.1",
    # cryptography is already in core deps (>=44.0); listed here only to
    # document the constraint for the extras-install matrix CI gate.
]
```

`[adcs]` MUST NOT pull impacket. Like `[identity]`, it MUST remain excluded from `[all]` *if* impacket ever sneaks in via transitive deps, but since the body above is impacket-free, `[adcs]` is **safe to include in `[all]`** — and per ADCS-07 it must be. Verify via the new CI matrix test below.

**Version verification:**
```bash
$ npm view ... # n/a — Python only
$ pip index versions ldap3        # [VERIFIED via existing [identity] pin: 2.9.1 is current floor; latest 2.9.1]
$ pip index versions cryptography  # [VERIFIED: 44.x is current; project pins >=44.0]
```

## Architecture Patterns

### System Architecture Diagram

```
   ┌─────────────────────────────────────────────────────────────┐
   │ run_scan.py :: _run_adcs_phase()  (after _run_smime_phase)  │
   │   - reads cfg.connectors.adcs_targets / adcs_search_base    │
   │   - calls scan_adcs_targets(...) via _wrapped_phase()       │
   └────────────────────────┬────────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ quirk/scanner/adcs_scanner.py :: scan_adcs_targets()        │
   │                                                              │
   │   for target in targets:                                    │
   │     _parse_target() ───────► (host, port, realm)            │
   │     _resolve_config_base() ─► CN=Configuration,DC=...       │
   │                                                              │
   │     ┌────────────────────────────────────────┐              │
   │     │ try: _bind_and_search()                │              │
   │     │   - anonymous OR simple bind            │              │
   │     │   - search Enrollment Services         │              │
   │     │   - search Certificate Templates       │              │
   │     │ except: emit ADCS-UNREACH finding      │              │
   │     │         (CryptoEndpoint, severity=LOW) │              │
   │     └──────────────┬─────────────────────────┘              │
   │                    ▼                                         │
   │     ┌─────────────────────────────────┐                     │
   │     │ Phase A: enumerate CAs          │                     │
   │     │  base = CN=Enrollment Services  │                     │
   │     │  parse cACertificate (DER)      │                     │
   │     │  classify sig_hash via          │                     │
   │     │    is_weak_cipher()             │                     │
   │     │  emit CryptoEndpoint(           │                     │
   │     │    protocol="ADCS",             │                     │
   │     │    service_detail="ca|...")     │                     │
   │     └─────────────────────────────────┘                     │
   │                                                              │
   │     ┌─────────────────────────────────┐                     │
   │     │ Phase B: enumerate templates    │                     │
   │     │  base = CN=Certificate Templates│                     │
   │     │  per template:                  │                     │
   │     │   _classify_template_escs()     │                     │
   │     │    -> list[(esc_id, severity)]  │                     │
   │     │   emit one finding per ESC      │                     │
   │     │   emit COVERAGE-GAP for         │                     │
   │     │    non-observable ESCs (4/5/8)  │                     │
   │     └─────────────────────────────────┘                     │
   └────────────────────────┬────────────────────────────────────┘
                            ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ list[CryptoEndpoint(protocol="ADCS")]                       │
   │   -> _flush_stage_endpoints() at data_at_rest stage         │
   │   -> evidence.build_evidence_summary() counts 4 counters    │
   │   -> scoring.compute_readiness_score() reads 4 weights      │
   │   -> cbom.builder Pass-1 emits CA-sig + key algorithms      │
   │   -> ADCS skipped in Pass-2 + Pass-3 (lines 538 + 622)      │
   └─────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
quirk/scanner/adcs_scanner.py        # NEW — singular path; mirrors smime_scanner.py
quantum-chaos-enterprise-lab/adcs/
├── ldif/
│   ├── 01-schema-mspki.ldif         # custom msPKI-* schema (cn=schema,cn=config)
│   └── 02-templates.ldif            # 1 CA + 3 templates (ESC1, ESC4, safe)
└── certs/
    ├── ca-weak.der                  # RSA-1024 SHA-1 (CA signing cert fixture)
    └── regen.sh                     # developer tool — mirror smime/certs/regen.sh
tests/
├── test_adcs_scanner.py             # unit tests (mocked ldap3)
├── test_adcs_no_writes.py           # invariant: no ldap3 add/modify/delete calls
├── test_adcs_ast_gate.py            # AST gate (clone Phase 79 model)
└── test_extras_install_adcs.py      # CI matrix per ADCS-07
```

### Pattern 1: ldap3 paged search of CN=Configuration partition

```python
# Source: ldap3 docs + smime_scanner._bind_and_search analog
# CONTEXT D-Area-2: duplicate scaffolding (do NOT extract shared helper)
def _bind_and_search_ca(host, port, config_base, timeout, user=None, password=None):
    server = ldap3.Server(host, port=port, get_info=ldap3.ALL, connect_timeout=timeout)
    if user and password:
        conn = ldap3.Connection(
            server, user=user, password=password,
            authentication=ldap3.SIMPLE, receive_timeout=timeout,
        )
    else:
        conn = ldap3.Connection(
            server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout,
        )
    if not conn.bind():
        raise ldap3.core.exceptions.LDAPBindError(conn.last_error or "bind-rejected")

    ca_base = f"CN=Enrollment Services,CN=Public Key Services,CN=Services,{config_base}"
    return conn.extend.standard.paged_search(
        search_base=ca_base,
        search_filter="(objectClass=pKIEnrollmentService)",
        search_scope=ldap3.SUBTREE,
        attributes=["cn", "cACertificate", "certificateTemplates", "dNSHostName"],
        paged_size=500,
        generator=True,
    )

def _bind_and_search_templates(conn, config_base):
    tpl_base = f"CN=Certificate Templates,CN=Public Key Services,CN=Services,{config_base}"
    return conn.extend.standard.paged_search(
        search_base=tpl_base,
        search_filter="(objectClass=pKICertificateTemplate)",
        search_scope=ldap3.SUBTREE,
        attributes=[
            "cn", "displayName",
            "msPKI-Certificate-Name-Flag",       # ESC1
            "msPKI-Enrollment-Flag",             # ESC2, ESC8 (auto-enrollment)
            "msPKI-Certificate-Application-Policy",  # ESC3, ESC5/6, "any purpose"
            "pKIExtendedKeyUsage",               # ESC3 (EKU set; including 1.3.6.1.4.1.311.20.2.1 cert-req agent)
            "msPKI-RA-Signature",                # required signatures (low value = ESC condition)
            "nTSecurityDescriptor",              # ESC4 (ACL — coverage-gap; we read but don't parse)
            "pKIKeyUsage", "msPKI-Minimal-Key-Size",
            "pKIDefaultKeySpec", "msPKI-Template-Schema-Version",
        ],
        paged_size=500,
        generator=True,
    )
```

### Pattern 2: ESC bitmask classification (LDAP-observable subset)

```python
# Bitmask constants — verified against [MS-CRTD] §2.4.* and Certipy source.
# msPKI-Certificate-Name-Flag (DWORD, decimal in LDAP)
CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT          = 0x00000001  # ESC1
CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT_ALT_NAME = 0x00010000  # ESC1 variant

# msPKI-Enrollment-Flag
CT_FLAG_NO_SECURITY_EXTENSION              = 0x00080000  # ESC9 — out of scope but bit reserved here
CT_FLAG_AUTO_ENROLLMENT                    = 0x00000020  # ESC8 condition (web enrollment is observable via dNSHostName, not LDAP)
CT_FLAG_PEND_ALL_REQUESTS                  = 0x00000002  # mitigating bit — set => ESC findings demoted

# Application Policy / EKU OIDs
EKU_CLIENT_AUTH        = "1.3.6.1.5.5.7.3.2"
EKU_PKINIT_CLIENT_AUTH = "1.3.6.1.5.2.3.4"
EKU_SMART_CARD_LOGON   = "1.3.6.1.4.1.311.20.2.2"
EKU_CERT_REQUEST_AGENT = "1.3.6.1.4.1.311.20.2.1"
EKU_ANY_PURPOSE        = "2.5.29.37.0"        # ESC2 "any purpose"
EKU_SUBORDINATE_CA     = "1.3.6.1.5.5.7.3.9"  # heuristic; ESC5/6 family

def _classify_template_escs(entry: dict) -> list[tuple[str, str, list[str]]]:
    """Return list of (esc_id, severity, reasons) for one template entry.

    LDAP-observable subset only. ESC4 / ESC5 / ESC8 surface as
    ADCS-COVERAGE-GAP findings emitted by the caller, not here.
    """
    findings = []
    name_flag = int(entry.get("msPKI-Certificate-Name-Flag", 0) or 0)
    enroll_flag = int(entry.get("msPKI-Enrollment-Flag", 0) or 0)
    app_policies = list(entry.get("msPKI-Certificate-Application-Policy", []) or [])
    ekus = list(entry.get("pKIExtendedKeyUsage", []) or [])
    ra_sig = int(entry.get("msPKI-RA-Signature", 0) or 0)

    pending = bool(enroll_flag & CT_FLAG_PEND_ALL_REQUESTS)  # mitigates many ESCs
    client_auth_eku = any(o in ekus for o in (EKU_CLIENT_AUTH, EKU_PKINIT_CLIENT_AUTH, EKU_SMART_CARD_LOGON))

    # --- ESC1: ENROLLEE_SUPPLIES_SUBJECT + client auth EKU + low RA sig ---
    if (name_flag & CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT) and client_auth_eku and ra_sig == 0 and not pending:
        findings.append(("ESC1", "HIGH",
            ["enrollee-supplies-subject", "client-auth-eku", "no-ra-signature"]))

    # --- ESC2: any-purpose EKU on template ---
    if EKU_ANY_PURPOSE in app_policies or EKU_ANY_PURPOSE in ekus:
        findings.append(("ESC2", "HIGH", ["any-purpose-eku"]))

    # --- ESC3: cert-request-agent EKU ---
    if EKU_CERT_REQUEST_AGENT in ekus or EKU_CERT_REQUEST_AGENT in app_policies:
        findings.append(("ESC3", "HIGH", ["cert-request-agent-eku"]))

    # --- ESC6: subordinate-CA EKU (LDAP-observable subset of EDITF flag set on CA) ---
    if EKU_SUBORDINATE_CA in app_policies:
        findings.append(("ESC6", "MEDIUM", ["subordinate-ca-eku"]))

    # ESC4 / ESC5 / ESC7 / ESC8 — require ACL parsing or non-LDAP signal.
    # Caller emits ADCS-COVERAGE-GAP for these.
    return findings
```

### Pattern 3: CA signing cert parsing (mirror smime_scanner._parse_smime_cert)

```python
def _parse_ca_cert(der_bytes: bytes) -> "dict | None":
    """Parse cACertificate value (always DER per [MS-CRTD] §2.21). Returns
    {key_alg, key_bits, sig_hash, serial, not_after, expired} or None."""
    try:
        cert = load_der_x509_certificate(der_bytes)
    except Exception as exc:
        logger.debug("ADCS CA cert parse failed: %s", safe_str(exc))
        return None
    # ... identical structure to _parse_smime_cert (see smime_scanner.py:58-100)
```

### Pattern 4: ADCS-UNREACH coverage-gap emission

```python
# Mirrors smime_scanner.py:226-238 — emit a CryptoEndpoint, not raise.
# Per ADCS-04 success criterion #2: "no exception propagates to scan session error log".
except (ldap3.core.exceptions.LDAPException, OSError) as exc:
    log.warning("ADCS: bind/search failed for %s:%d: %s", host, port, safe_str(exc))
    results.append(CryptoEndpoint(
        host=host,
        port=port,
        protocol="ADCS",
        service_detail=f"adcs-unreachable|base={config_base}",
        severity="LOW",
        scan_error=safe_str(exc),
        scan_error_category="exception",
        scanned_at=now,
    ))
    continue
```

### Anti-Patterns to Avoid

- **Decoding `nTSecurityDescriptor` to claim ESC4 detection** — the SDDL/SID parse requires resolution of forest-specific SIDs; without that, "permissive ACL" is heuristic and produces FPs that destroy consultant credibility. Emit `ADCS-COVERAGE-GAP` instead.
- **Treating `msPKI-Certificate-Application-Policy` and `pKIExtendedKeyUsage` as one set** — they overlap but are not equal. `msPKI-Certificate-Application-Policy` is the AD-specific extension; `pKIExtendedKeyUsage` is the OID list. Read both, union them.
- **Trusting "any purpose" detection without checking `2.5.29.37.0`** — some templates encode it as the literal OID, others omit EKU entirely. Both are "any purpose"; the absence-case is harder to detect.
- **Calling `conn.modify()` / `conn.add()` / `conn.delete()`** — ADCS-09 invariant. AST gate must catch any drift.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LDAP paged search | Custom pagination loop | `conn.extend.standard.paged_search(generator=True)` | ldap3 handles the SearchControl + cookie roundtrip |
| DER X.509 parsing | asn1crypto or pyasn1 | `cryptography.x509.load_der_x509_certificate` | Already core dep; same path as smime / saml |
| Weak-algorithm classification | Inline string match | `quirk.util.weak_crypto.is_weak_cipher` | Single source of truth (Phase 73 D-02) |
| Configuration partition discovery | Hard-code base DN | Read `configurationNamingContext` from rootDSE | `ldap3.Server(get_info=ldap3.ALL)` populates `server.info.other['configurationNamingContext']` |
| nTSecurityDescriptor ACL parsing | impacket `ldap.SR_SECURITY_DESCRIPTOR` | (nothing — locked out of scope) | Emit COVERAGE-GAP instead |

**Key insight:** ldap3 already handles every LDAP plumbing concern. The novel logic is *only* the ESC bitmask table and the LDAP-observability decisions. Keep that logic in pure functions so unit tests can drive every ESC class without a live LDAP server.

## Common Pitfalls

### Pitfall 1: OpenLDAP rejects msPKI-* schema LDIF without correct OID syntax

**What goes wrong:** The msPKI attributes are NOT in any default OpenLDAP schema. Loading them requires `cn=schema,cn=config` LDIF with valid OIDs (Microsoft's private OID arc is `1.2.840.113556.1.4.*`).
**Why it happens:** OpenLDAP schema parser is strict about OID + SYNTAX + EQUALITY clauses.
**How to avoid:** Use the LDIF skeleton in the Chaos Lab section below. Attribute syntaxes: `msPKI-Certificate-Name-Flag` and `msPKI-Enrollment-Flag` are `1.3.6.1.4.1.1466.115.121.1.27` (Integer); `msPKI-Certificate-Application-Policy` is `1.3.6.1.4.1.1466.115.121.1.38` (OID); `pKIExtendedKeyUsage` is the same OID syntax; `cACertificate` is `1.3.6.1.4.1.1466.115.121.1.8` (Certificate, octet stream).
**Warning signs:** `ldapadd` returns error 80 ("Other") with "no such attribute type"; check `slapd` logs.

### Pitfall 2: paged_search generator yields control rows alongside entries

**What goes wrong:** Iterating `paged_search(...)` yields `{'type': 'searchResRef'}` entries that have no `raw_attributes` key.
**Why it happens:** ldap3 mixes referral and control responses into the generator stream.
**How to avoid:** Filter with `if entry.get("type") and entry.get("type") != "searchResEntry": continue` — exact pattern from `smime_scanner.py:243-244`.

### Pitfall 3: `int(entry.get("msPKI-Certificate-Name-Flag", 0))` raises on None

**What goes wrong:** ldap3 returns `None` (not `0`) when an attribute is absent.
**How to avoid:** `int(entry.get(...) or 0)`. The pattern in the classification function above uses `int(... or 0)`.

### Pitfall 4: `cACertificate` is multi-valued

**What goes wrong:** Renewed CAs accumulate multiple `cACertificate` values; ldap3 returns a list.
**How to avoid:** Iterate; emit one finding per DER blob that classifies as weak. Mirror SMIME multi-cert-per-user policy (CONTEXT D-79-Area-1).

### Pitfall 5: Anonymous bind rejected by real AD DC

**What goes wrong:** Production AD DCs typically reject anonymous bind for Configuration partition reads.
**How to avoid:** Support both ANONYMOUS (chaos lab) and SIMPLE bind (`adcs_user` / `adcs_password` in cfg.connectors). The chaos lab profile MUST allow anonymous bind so unit tests can run without secrets.

### Pitfall 6: Reading `nTSecurityDescriptor` requires `LDAP_SERVER_SD_FLAGS_OID` control on real AD

**What goes wrong:** Without the `1.2.840.113556.1.4.801` control, AD returns truncated SDs (or rejects the attribute).
**How to avoid:** Either pass the SD flags control via ldap3 `controls=[(control_value, criticality)]`, or — preferred for Phase 80 — read the attribute opportunistically and only count its presence/absence for the `ADCS-COVERAGE-GAP` finding (we are NOT parsing the bytes per Pitfall 0).

### Pitfall 7: Encoding mismatch — `pKIExtendedKeyUsage` is a list of OID strings, `msPKI-Certificate-Application-Policy` is too, but some servers return them as ASN.1 DER blobs

**How to avoid:** ldap3 returns string attributes as Python strings when the schema is known and as `bytes` otherwise. Always coerce: `[v.decode("utf-8") if isinstance(v, bytes) else v for v in (entry.get(...) or [])]`.

## Code Examples

### CA enumeration (verified against [MS-CRTD] §2.21)

```python
# CN=Enrollment Services holds one entry per CA in the forest.
# objectClass: pKIEnrollmentService; attributes include cACertificate (DER).
ca_filter = "(objectClass=pKIEnrollmentService)"
ca_attrs = ["cn", "cACertificate", "certificateTemplates", "dNSHostName"]
```

### Template enumeration (verified against [MS-CRTD] §2.4.* + Certipy `certipy/lib/ldap.py`)

```python
tpl_filter = "(objectClass=pKICertificateTemplate)"
# Full attribute list per Pattern 1 above.
```

### Hooking into `cfg.connectors` (mirrors smime path)

```python
# In run_scan.py after _run_smime_phase()
def _run_adcs_phase():
    if not (getattr(cfg.connectors, "enable_adcs", False)
            and getattr(cfg.connectors, "adcs_targets", None)):
        return []
    from quirk.scanner.adcs_scanner import scan_adcs_targets
    eps = scan_adcs_targets(
        targets=cfg.connectors.adcs_targets,
        timeout=getattr(cfg.connectors, "adcs_timeout", 10),
        logger=logger,
        session_start=session_start,
        search_base=getattr(cfg.connectors, "adcs_search_base", None),
        user=getattr(cfg.connectors, "adcs_user", None),
        password=getattr(cfg.connectors, "adcs_password", None),
    )
    logger.info("ADCS scan: %d endpoints from %d targets",
                len(eps), len(cfg.connectors.adcs_targets))
    return eps
adcs_endpoints = _wrapped_phase(
    run_stats, "adcs_scanning", "adcs_scanner",
    _run_adcs_phase, error_endpoints, logger,
) or []
# Append to _dar_eps list at run_scan.py:1453
```

## ESC1-ESC8 LDAP-Observability Reference

| ESC | Trigger condition | Attribute(s) | LDAP-observable? | Phase 80 emits |
|-----|-------------------|--------------|------------------|----------------|
| **ESC1** | Template allows enrollee to supply subject + client-auth EKU + no RA signature | `msPKI-Certificate-Name-Flag` bit `0x1` + `pKIExtendedKeyUsage` ∋ `1.3.6.1.5.5.7.3.2` + `msPKI-RA-Signature` = 0 | YES | HIGH finding |
| **ESC2** | Template has "any purpose" EKU | `msPKI-Certificate-Application-Policy` ∋ `2.5.29.37.0` | YES | HIGH finding |
| **ESC3** | Template has Certificate Request Agent EKU | `pKIExtendedKeyUsage` ∋ `1.3.6.1.4.1.311.20.2.1` | YES | HIGH finding |
| **ESC4** | Vulnerable template ACL (write to non-admin) | `nTSecurityDescriptor` (binary SDDL) | PARTIAL — bytes readable, semantics require SID resolution | `ADCS-COVERAGE-GAP` (severity LOW) |
| **ESC5** | Vulnerable PKI object ACL (CA / NTAuth / template container) | `nTSecurityDescriptor` on multiple objects | PARTIAL — same parsing problem as ESC4 | `ADCS-COVERAGE-GAP` |
| **ESC6** | CA `EDITF_ATTRIBUTESUBJECTALTNAME2` flag set | NOT in LDAP — lives in CA registry / `Config.dbo.RegConfig` | NO — but subordinate-CA-EKU heuristic on template is a partial signal | MEDIUM heuristic finding OR `ADCS-COVERAGE-GAP` |
| **ESC7** | Vulnerable CA role permissions (Manage CA / Manage Certificates) | NOT in LDAP — CA security via DCOM | NO | `ADCS-COVERAGE-GAP` |
| **ESC8** | NTLM relay to AD CS web enrollment (HTTP) | NOT in LDAP — needs web-enrollment endpoint probe | NO | `ADCS-COVERAGE-GAP` |

**One `ADCS-COVERAGE-GAP` finding per CA per non-observable ESC class** — severity LOW, `service_detail="adcs-coverage-gap|esc=ESC4"` etc. Counts toward `identity_adcs_coverage_gap_count`.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 80 is greenfield. No existing ADCS data anywhere. New `adcs_scan_json` column is additive. | none |
| Live service config | Chaos lab `docker-compose.yml` gains new `adcs` profile; lab.sh ALL_PROFILES is runtime-derived (no edit needed per CONTEXT). | docker compose pull bitnamilegacy/openldap:2.6.10-debian-12-r4 |
| OS-registered state | None | none |
| Secrets/env vars | NEW optional `adcs_user` + `adcs_password` in `ConnectorsCfg` (simple bind). MUST be `SecretStr` (Pydantic) to avoid log leakage — mirror Vault pattern. | code edit only |
| Build artifacts | None — pure-Python additions | none |

## Updated Line Numbers (post-Phase 79)

| File | Anchor | Current line | What Phase 80 does |
|------|--------|---------------|---------------------|
| `quirk/cbom/builder.py` | Pass-2 skip tuple `"SSH", "CONTAINER", ..., "SMIME"` | **538** | Append `"ADCS"` |
| `quirk/cbom/builder.py` | Pass-3 skip tuple `"JWT", ..., "SMIME"` | **622** | Append `"ADCS"` |
| `quirk/cbom/builder.py` | Pass-1 SMIME emit branch | **454-462** | Add a new `elif ep.protocol == "ADCS":` branch directly after the SMIME one (~line 463) |
| `quirk/db.py` | `_IDENTITY_COLUMNS` tuple last entry `smime_scan_json` | **80** | Append `("adcs_scan_json", "TEXT")` at line 81 |
| `quirk/intelligence/scoring.py` | `SCORE_WEIGHTS` SMIME entries | **32-34** | Append 4 new entries immediately after, before the `dar_*` block |
| `quirk/intelligence/scoring.py` | `identity_trust_impacts` list end | **189-191** | Append 4 new impact lines |
| `quirk/intelligence/scoring.py` | SMIME counter reads | **156-158** | Append `adcs_*` counter reads in same shape |
| `quirk/intelligence/evidence.py` | `_PROTOCOL_KEYS` tuple | **11-15** | Append `"ADCS"` |
| `quirk/intelligence/evidence.py` | SMIME counter accumulation branch (`elif proto == "SMIME":`) | **181-195** | Add a new `elif proto == "ADCS":` branch directly after, before POSTGRESQL |
| `quirk/intelligence/evidence.py` | return dict SMIME counters | **361-363** | Append `identity_adcs_*` keys |
| `run_scan.py` | `_run_smime_phase` definition + call | **1397-1415** | Insert `_run_adcs_phase` directly after, before Vault |
| `run_scan.py` | `_dar_eps` concatenation | **1453** | Append `+ adcs_endpoints` |
| `run_scan.py` | resumed-endpoint filter | **1219** | Add `adcs_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "ADCS"]` |
| `pyproject.toml` | `[project.optional-dependencies]` | **43-46** (identity) | Add new `adcs = [...]` group below identity; also include in `[all]` list at line 66 |

## `[adcs]` pyproject.toml Block

```toml
adcs = [
    "ldap3>=2.9.1",
    # cryptography>=44.0 is already a core dep; documented here so the
    # CI extras-install matrix (test_extras_install_adcs.py) sees the
    # constraint at the extras boundary.
]
```

And update the `[all]` group (line 66-73) to include `adcs`:

```toml
all = [
    "quirk[cloud]",
    "quirk[cbom]",
    "quirk[db]",
    "quirk[motion]",
    "quirk[redis]",
    "quirk[dashboard]",
    "quirk[adcs]",   # Phase 80 ADCS-07 — safe to include because adcs deps are impacket-free
]
```

`[identity]` STAYS excluded from `[all]` (impacket pulls pyOpenSSL → cryptography downgrade). The existing `test_install_all_excludes_impacket.py` continues to guard that invariant.

## CI Extras-Matrix Test Sketch (ADCS-07)

```python
# tests/test_extras_install_adcs.py — new file
"""ADCS-07: pip install must produce cryptography>=44.0 for every relevant
extras combination. Mirrors test_install_all_excludes_impacket.py shape."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMBOS = ["[adcs]", "[all]", "[all,adcs]"]  # 3-way matrix

@pytest.mark.slow
@pytest.mark.parametrize("extras", COMBOS)
def test_extras_install_produces_cryptography_44(tmp_path: Path, extras: str) -> None:
    report = tmp_path / "report.json"
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--dry-run", "--ignore-installed", "--quiet",
        "--report", str(report),
        "-e", f"{REPO_ROOT}{extras}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, (
        f"pip dry-run failed for extras={extras}: stderr={result.stderr!r}"
    )
    data = json.loads(report.read_text())
    pkgs = {it["metadata"]["name"].lower(): it["metadata"]["version"]
            for it in data.get("install", [])
            if it.get("metadata", {}).get("name")}
    crypto_ver = pkgs.get("cryptography")
    assert crypto_ver is not None, f"cryptography missing from {extras} resolution"
    major = int(crypto_ver.split(".")[0])
    assert major >= 44, (
        f"ADCS-07 regression: cryptography {crypto_ver} < 44.0 in extras={extras}. "
        f"Likely impacket re-pinned via a transitive dep. Resolved: {sorted(pkgs)}"
    )
```

## AST Gate Sketch (`tests/test_adcs_ast_gate.py`)

```python
"""Phase 80 ADCS AST gate — forbids enrollment-API imports + LDAP modify ops
in quirk/scanner/adcs_scanner.py. Mirrors tests/test_smime_ast_gate.py."""
from __future__ import annotations
import ast, pathlib, textwrap
import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = PROJECT_ROOT / "quirk" / "scanner" / "adcs_scanner.py"

# Top-level forbidden modules (catches `import certipy_ad`, `from certipy_ad import ...`)
FORBIDDEN_MODULES = {"certipy_ad", "certipy"}
FORBIDDEN_FROM_PREFIXES = ("certipy_ad.", "certipy.")

# Name-level forbidden imports — these are CLASSES inside cryptography.x509,
# not modules. Detect via `from cryptography.x509 import CertificateSigningRequestBuilder`.
FORBIDDEN_FROM_NAMES = {
    ("cryptography.x509", "CertificateSigningRequestBuilder"),
    ("cryptography.x509.base", "CertificateSigningRequestBuilder"),
}

# Forbidden LDAP write-method calls on any object (catches conn.add, conn.modify,
# conn.delete, conn.modify_dn). We allow conn.search / conn.bind / conn.unbind.
FORBIDDEN_LDAP_METHODS = {"add", "modify", "delete", "modify_dn"}

def _collect_violations(tree: ast.AST) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_MODULES or any(
                    alias.name.startswith(p) for p in FORBIDDEN_FROM_PREFIXES
                ):
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_MODULES or any(
                mod.startswith(p) for p in FORBIDDEN_FROM_PREFIXES
            ):
                violations.append(f"from {mod} import ...")
            for alias in node.names:
                if (mod, alias.name) in FORBIDDEN_FROM_NAMES:
                    violations.append(f"from {mod} import {alias.name}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_LDAP_METHODS:
                # Heuristic: only flag when the receiver looks like an ldap3 Connection.
                # We accept ANY Attribute call with these names — false positives are
                # OK because the gate is preventative; real scanner code uses paged_search.
                violations.append(f"call .{func.attr}() (LDAP write)")
    return violations

def test_adcs_scanner_no_forbidden_imports_or_writes() -> None:
    assert TARGET.exists(), f"adcs_scanner.py missing: {TARGET}"
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    violations = _collect_violations(tree)
    if violations:
        pytest.fail(
            "ADCS AST gate (ADCS-09 invariant) — forbidden constructs in "
            f"{TARGET.relative_to(PROJECT_ROOT)}:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

def test_gate_catches_synthetic_violations() -> None:
    source = textwrap.dedent("""\
        import certipy_ad
        from certipy_ad.lib import enroll
        from cryptography.x509 import CertificateSigningRequestBuilder
        def f(conn):
            conn.modify("CN=t", changes={...})
            conn.add("CN=new", "objectClass", {})
    """)
    tree = ast.parse(source)
    violations = _collect_violations(tree)
    # 1 import + 1 from-prefix + 1 from-name + 2 LDAP writes = 5
    assert len(violations) >= 5, f"expected 5+ violations, got {violations}"

def test_gate_does_not_flag_clean_module() -> None:
    source = textwrap.dedent("""\
        from __future__ import annotations
        import json, logging
        import ldap3
        from cryptography.x509 import load_der_x509_certificate
        from quirk.models import CryptoEndpoint
        from quirk.util.weak_crypto import is_weak_cipher
        from quirk.util.safe_exc import safe_str
        def do_search(conn, base):
            return conn.extend.standard.paged_search(search_base=base, search_filter='(objectClass=*)')
    """)
    tree = ast.parse(source)
    assert _collect_violations(tree) == []
```

**On the "name-level CSRBuilder" question (open Q #8):** `CertificateSigningRequestBuilder` is a class inside `cryptography.x509`, not a module. Module-level import gates do not catch it; the `FORBIDDEN_FROM_NAMES` set above pairs `(module, imported_name)` and triggers on `ast.ImportFrom`. This is the minimal-complexity correct check.

## SCORE_WEIGHTS Bookkeeping

| Phase | Net change | Running SUM | Invariant test |
|-------|-----------|-------------|----------------|
| Phase 78 baseline | — | 261.0 | green |
| Phase 79 (+3 entries × 2.0) | +6.0 | 267.0 | RED (Phase 83 reconciles) |
| **Phase 80 (+4 entries × 2.0)** | **+8.0** | **275.0** | **RED — DO NOT FIX** |
| Phase 83 CLEAN-01 bump | (write 275.0 into invariant test) | 275.0 | green |

Four entries to insert after the Phase 79 SMIME block in `SCORE_WEIGHTS`:

```python
"identity_adcs_weak_template_count":  2.0,  # Phase 80 ADCS-04 (ESC1/2/3/6 hits)
"identity_adcs_misconfig_count":      2.0,  # Phase 80 ADCS-04 (generic permissive flags)
"identity_adcs_weak_signing_count":   2.0,  # Phase 80 ADCS-04 (CA sig SHA-1, RSA<2048)
"identity_adcs_coverage_gap_count":   2.0,  # Phase 80 D-Area-1 (ESC4/5/7/8 best-effort gaps)
```

And four matching impact lines in `identity_trust_impacts`:

```python
("Weak AD CS template (ESC-class)", -_ratio(adcs_weak_template_count, denom) * w["identity_adcs_weak_template_count"]),
("AD CS template misconfiguration", -_ratio(adcs_misconfig_count, denom) * w["identity_adcs_misconfig_count"]),
("Weak AD CS CA signing algorithm", -_ratio(adcs_weak_signing_count, denom) * w["identity_adcs_weak_signing_count"]),
("AD CS coverage gap (ESC4/5/7/8)", -_ratio(adcs_coverage_gap_count, denom) * w["identity_adcs_coverage_gap_count"]),
```

## Chaos Lab Seeding

### docker-compose.yml block (append after smime-seed)

```yaml
  # =========================
  # PHASE 80 — AD CS LDAP DISCOVERY (profile: adcs)
  # ADCS-08: OpenLDAP seeded with msPKI-* schema + three test templates.
  # Image parity with smime/ldaps profiles (bitnamilegacy openldap 2.6.10).
  # =========================
  adcs-openldap:
    image: bitnamilegacy/openldap:2.6.10-debian-12-r4
    profiles: ["adcs"]
    environment:
      LDAP_ROOT: "dc=quirk,dc=lab"
      LDAP_ADMIN_USERNAME: "admin"
      LDAP_ADMIN_PASSWORD: "admin"
      LDAP_PORT_NUMBER: 389
      # Phase 80: allow anonymous read of Configuration partition for chaos-lab tests.
      LDAP_ALLOW_ANON_BINDING: "yes"
    volumes:
      - ./adcs/ldif:/ldif:ro
      - ./adcs/certs:/adcs-certs:ro
    ports:
      - "38910:389"
    restart: unless-stopped

  adcs-seed:
    image: bitnamilegacy/openldap:2.6.10-debian-12-r4
    profiles: ["adcs"]
    depends_on:
      adcs-openldap:
        condition: service_started
    # Idempotency: ldapadd -c continues on 68 (LDAP_ALREADY_EXISTS); we
    # explicitly swallow exit 68 so the seed sidecar exits 0 on every run.
    # Mirror of the smime-seed pattern (Phase 79-01 deviation Rule 1).
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        set -e
        sleep 5
        # Schema first — must succeed before templates can be added.
        ldapadd -c -x -H ldap://adcs-openldap:389 -D 'cn=admin,dc=quirk,dc=lab' -w admin -f /ldif/01-schema-mspki.ldif || true
        ldapadd -c -x -H ldap://adcs-openldap:389 -D 'cn=admin,dc=quirk,dc=lab' -w admin -f /ldif/02-templates.ldif
        rc=$$?
        if [ $$rc -eq 0 ] || [ $$rc -eq 68 ]; then exit 0; else exit $$rc; fi
    volumes:
      - ./adcs/ldif:/ldif:ro
    restart: "no"
```

### `quantum-chaos-enterprise-lab/adcs/ldif/01-schema-mspki.ldif`

Bitnami's openldap image accepts schema LDIF as ordinary entries because the container's slapd runs with `cn=config`. Schema attributes register under `cn=schema,cn=config`. Skeleton (one custom objectClass + the 4 attributes we actually consume):

```ldif
dn: cn=mspki,cn=schema,cn=config
objectClass: olcSchemaConfig
cn: mspki
olcAttributeTypes: ( 1.2.840.113556.1.4.1432
  NAME 'msPKI-Certificate-Name-Flag'
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.27
  EQUALITY integerMatch
  SINGLE-VALUE )
olcAttributeTypes: ( 1.2.840.113556.1.4.1439
  NAME 'msPKI-Enrollment-Flag'
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.27
  EQUALITY integerMatch
  SINGLE-VALUE )
olcAttributeTypes: ( 1.2.840.113556.1.4.1442
  NAME 'msPKI-Certificate-Application-Policy'
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.38 )
olcAttributeTypes: ( 1.2.840.113556.1.4.1334
  NAME 'pKIExtendedKeyUsage'
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.38 )
olcAttributeTypes: ( 1.2.840.113556.1.4.1335
  NAME 'msPKI-RA-Signature'
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.27
  EQUALITY integerMatch
  SINGLE-VALUE )
olcAttributeTypes: ( 2.5.4.37
  NAME 'cACertificate'
  DESC 'X.509 CA certificate'
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.8 )
olcObjectClasses: ( 1.2.840.113556.1.5.156
  NAME 'pKICertificateTemplate'
  SUP top STRUCTURAL
  MUST cn
  MAY ( displayName $ msPKI-Certificate-Name-Flag $ msPKI-Enrollment-Flag $
        msPKI-Certificate-Application-Policy $ pKIExtendedKeyUsage $
        msPKI-RA-Signature $ nTSecurityDescriptor ) )
olcObjectClasses: ( 1.2.840.113556.1.5.157
  NAME 'pKIEnrollmentService'
  SUP top STRUCTURAL
  MUST cn
  MAY ( cACertificate $ certificateTemplates $ dNSHostName ) )
```

**OIDs:** The numeric OIDs above are real Microsoft OIDs taken from `[MS-ADTS]` schema (publicly documented). Using real OIDs avoids schema collision if anyone ever points the chaos lab at a real AD.

### `quantum-chaos-enterprise-lab/adcs/ldif/02-templates.ldif`

```ldif
# Configuration partition skeleton
dn: cn=Configuration,dc=quirk,dc=lab
objectClass: top
objectClass: container
cn: Configuration

dn: cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: container
cn: Services

dn: cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: container
cn: Public Key Services

dn: cn=Enrollment Services,cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: container
cn: Enrollment Services

dn: cn=Certificate Templates,cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: container
cn: Certificate Templates

# --- The CA (RSA-1024 SHA-1 signing cert -> HIGH weak-signing finding) ---
dn: cn=QUIRK-Lab-CA,cn=Enrollment Services,cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: pKIEnrollmentService
cn: QUIRK-Lab-CA
dNSHostName: ca.quirk.lab
certificateTemplates: BadTemplate-ESC1
certificateTemplates: BadTemplate-ESC4
certificateTemplates: SafeTemplate
cACertificate:: <BASE64 of ca-weak.der>

# --- ESC1: ENROLLEE_SUPPLIES_SUBJECT + client-auth EKU + no RA sig ---
dn: cn=BadTemplate-ESC1,cn=Certificate Templates,cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: pKICertificateTemplate
cn: BadTemplate-ESC1
displayName: Bad Template ESC1
msPKI-Certificate-Name-Flag: 1
msPKI-Enrollment-Flag: 0
msPKI-RA-Signature: 0
pKIExtendedKeyUsage: 1.3.6.1.5.5.7.3.2
msPKI-Certificate-Application-Policy: 1.3.6.1.5.5.7.3.2

# --- ESC4: overly permissive ACL (we read the bytes but emit COVERAGE-GAP) ---
dn: cn=BadTemplate-ESC4,cn=Certificate Templates,cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: pKICertificateTemplate
cn: BadTemplate-ESC4
displayName: Bad Template ESC4
msPKI-Certificate-Name-Flag: 0
msPKI-Enrollment-Flag: 0
msPKI-RA-Signature: 1
pKIExtendedKeyUsage: 1.3.6.1.5.5.7.3.2
# nTSecurityDescriptor: omitted in fixture — presence (or absence) drives the COVERAGE-GAP signal

# --- SafeTemplate: no ESC triggers ---
dn: cn=SafeTemplate,cn=Certificate Templates,cn=Public Key Services,cn=Services,cn=Configuration,dc=quirk,dc=lab
objectClass: pKICertificateTemplate
cn: SafeTemplate
displayName: Safe Template
msPKI-Certificate-Name-Flag: 0
msPKI-Enrollment-Flag: 2
msPKI-RA-Signature: 1
pKIExtendedKeyUsage: 1.3.6.1.5.5.7.3.2
msPKI-Certificate-Application-Policy: 1.3.6.1.5.5.7.3.2
```

### `quantum-chaos-enterprise-lab/adcs/certs/regen.sh`

```bash
#!/usr/bin/env bash
# Phase 80 — AD CS chaos lab CA cert fixture regenerator.
# Generates one deterministic CA signing cert: RSA-1024 / SHA-1 -> HIGH.
# Mirror of smime/certs/regen.sh shape.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDIF="${HERE}/../ldif/02-templates.ldif"

# 100 years validity — deterministic non-expired
DAYS=36500

b64_oneline() {
  if base64 --help 2>&1 | grep -q -- '-w'; then base64 -w0; else base64 | tr -d '\n'; fi
}

tmpkey="$(mktemp -t adcs_ca_key.XXXXXX)"
trap 'rm -f "$tmpkey"' EXIT

openssl req -x509 \
  -newkey rsa:1024 -sha1 \
  -keyout "$tmpkey" \
  -out "${HERE}/ca-weak.der" -outform DER \
  -days "${DAYS}" -nodes \
  -subj "/CN=QUIRK-Lab-CA/O=QUIRK Chaos Lab/OU=AD CS Fixtures" \
  >/dev/null 2>&1

CA_B64="$(b64_oneline < "${HERE}/ca-weak.der")"
echo "[regen] ca-weak.der ($(wc -c < "${HERE}/ca-weak.der") bytes)"
echo "[regen] inline this base64 into ${LDIF} cACertificate:: line:"
echo "${CA_B64}"
```

### `expected_results_v4.md` new section (skeleton)

```markdown
## Profile: adcs

*OpenLDAP seeded with custom msPKI-* schema and three certificate templates — exercises ESC1 (HIGH), ESC4 coverage-gap (LOW), and a SAFE baseline. CA signing cert is RSA-1024 SHA-1 → HIGH weak-signing finding. Plain LDAP on host port **38910 only**.*

> **Image:** `bitnamilegacy/openldap:2.6.10-debian-12-r4` (parity with `smime` profile).
> **Schema:** msPKI-* attributes registered under `cn=schema,cn=config` via `01-schema-mspki.ldif`. OIDs match Microsoft `[MS-ADTS]` schema — safe against any future real-AD pointing.

| Template DN | Trigger | Expected Finding | Severity |
|---|---|---|---|
| CN=QUIRK-Lab-CA,...,CN=Enrollment Services,... | cACertificate RSA-1024 SHA-1 | Weak AD CS CA signing algorithm | HIGH |
| CN=BadTemplate-ESC1,...,CN=Certificate Templates,... | NameFlag=1 + clientAuth EKU + RA-sig=0 | ESC1 weak template | HIGH |
| CN=BadTemplate-ESC4,... | (ACL not parseable from LDAP) | ADCS-COVERAGE-GAP esc=ESC4 | LOW |
| CN=SafeTemplate,... | none | (none — SAFE) | — |
| (per-CA) | ESC4 + ESC5 + ESC7 + ESC8 each emit a coverage-gap | 4× ADCS-COVERAGE-GAP findings | LOW |

**Expected scanner output:** 1 HIGH (CA weak signing) + 1 HIGH (ESC1) + 4 LOW (ADCS-COVERAGE-GAP for ESC4/5/7/8) = **6 findings**. Zero findings from SafeTemplate.

**Reference:** `quirk/scanner/adcs_scanner.py`, `quirk/db.py::_IDENTITY_COLUMNS::adcs_scan_json`, compose blocks `adcs-openldap` + `adcs-seed` (profile `adcs`).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `impacket.ldap` for AD reads | `ldap3` for AD reads | Phase 79 set the precedent | Avoids the pyOpenSSL/cryptography downgrade in `[all]` |
| `certipy-ad` for ESC detection | LDAP-attribute-only ESC1/2/3/6 + COVERAGE-GAP for ESC4/5/7/8 | v4.10-D-02 (locked) | Zero new pip deps; consultant-grade explicit uncertainty over false confidence |
| ESC findings as numeric "ESC1...ESC8" with severity ratings only | Per-ESC severity + reasons list + per-non-observable-ESC coverage-gap | This phase | Reports cleanly distinguish "weak" from "we can't tell from LDAP alone" |

**Deprecated/outdated:**
- `osixia/openldap:1.5.0` chaos lab base image (superseded by `bitnamilegacy/openldap:2.6.10` in Phase 79 D-79-UPDATE; same migration applies here).

## Project Constraints (from CLAUDE.md)

- Follow PEP 8. Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- If detection logic changes, update `labs/*/expected_results.md` accordingly. (Note: actual oracle is `quantum-chaos-enterprise-lab/expected_results_v4.md` — update *that* per ADCS-08.)
- Mandatory phase completion steps: create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-80-Windows-ADCS-Scanner.md`; update `docs/UAT-SERIES.md`; sync UAT to Obsidian; commit UAT.
- Chaos lab maintenance rule: any new profile MUST update `lab.sh` ALL_PROFILES + README.md + expected_results_*.md. (CONTEXT says `lab.sh` requires no edits because `ALL_PROFILES` is runtime-derived — verify by reading `_derive_all_profiles()` before assuming no edit needed; if it parses `docker-compose.yml` profiles, the rule is satisfied automatically.)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `[ASSUMED]` Bitnami legacy openldap accepts schema LDIF via `ldapadd` against `cn=schema,cn=config`. Smime profile loads regular entries only — schema-LDIF path not previously exercised in this lab. | Chaos Lab Seeding | High — if the image strips ACL on cn=config, schema add fails. **Mitigation:** verify in Plan 80-04 before relying on it; fallback is a built-in schema overlay or a custom `slapd.conf`. |
| A2 | `[ASSUMED]` `msPKI-Certificate-Application-Policy` and `pKIExtendedKeyUsage` OIDs (`1.2.840.113556.1.4.1442` / `1.2.840.113556.1.4.1334`) match Microsoft's published schema. Sourced from `[MS-ADTS]` v50.0 but not freshly verified in this session. | Chaos Lab Seeding | Low — OIDs are public, well-stable. If wrong, schema loads but real-AD scans would also need the same OIDs. |
| A3 | `[ASSUMED]` `nTSecurityDescriptor` returns bytes for ldap3 without the `LDAP_SERVER_SD_FLAGS_OID` control. | Pitfall 6 | Medium — if AD rejects the read entirely, the COVERAGE-GAP signal degrades from "ACL bytes present but unparsed" to "attribute inaccessible". Either way, COVERAGE-GAP fires; the user-facing behavior is identical. |
| A4 | `[ASSUMED]` Including `[adcs]` in `[all]` keeps the `test_install_all_excludes_impacket` invariant green because `[adcs]` declares only `ldap3` (no impacket). | `[all]` extras update | Low — `ldap3` does not depend on impacket. Verify in Plan 80-06 by running the extras-matrix CI test locally. |
| A5 | `[ASSUMED]` The runtime `_derive_all_profiles()` helper in `lab.sh` enumerates profiles by parsing `docker-compose.yml`, so adding a new `adcs` profile requires no `lab.sh` edits — CONTEXT D-cross-cutting asserts this but worth re-verifying. | Project Constraints | Low — CONTEXT is a locked decision; if wrong, lab.sh edit is a one-line append. |

**Assumptions to confirm with user during planning:** A1 is the highest-risk — recommend a 10-minute spike in Plan 80-04 (chaos lab) before the team commits to the schema-LDIF approach.

## Open Questions

1. **Anonymous bind vs. simple bind for real-AD validation**
   - What we know: anonymous bind suffices for the chaos lab (Configuration partition is anonymously readable in the OpenLDAP fixture by design).
   - What's unclear: production AD DCs vary. Some allow anonymous reads of `CN=Configuration,...`; many do not.
   - Recommendation: support both via `adcs_user` / `adcs_password` config. Chaos lab uses anonymous. Document in `docs/connectors/adcs.md`.

2. **Should ESC findings carry the canonical "ESC1"..."ESC8" identifier in `service_detail` or only in `adcs_scan_json`?**
   - What we know: REQUIREMENTS ADCS-02 names ESC1-ESC8 explicitly; CONTEXT does not specify the wire format.
   - Recommendation: encode both — `service_detail="adcs|template=<cn>|esc=ESC1|reasons=enrollee-supplies-subject,client-auth-eku"` so the dashboard can group by ESC class. Full structured data in `adcs_scan_json`.

3. **Where to put the `enable_adcs` / `adcs_targets` config fields?**
   - What we know: smime added analogous fields to `ConnectorsCfg`.
   - Recommendation: mirror exactly. Document under `ConnectorsCfg` in `quirk/config.py` and add prompts to `interactive_config()` only after MEMORY/backlog confirms no "stub-prompt" anti-pattern revival.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `ldap3` | Scanner LDAP path | (verify in venv) | >=2.9.1 | — (locked; in `[adcs]`) |
| Python `cryptography` | CA cert DER parse | ✓ (core dep) | >=44.0 | — |
| Docker | Chaos lab profile | ✓ (existing project requirement) | >=20.x | — |
| `bitnamilegacy/openldap:2.6.10-debian-12-r4` | adcs-openldap container | (image pull at first run) | 2.6.10 | smime profile uses same image; cached locally for most contributors |
| `openssl` CLI | regen.sh dev tool | ✓ (macOS / Linux ship it) | >=1.1.x | — (regen.sh is dev-only; certs are committed) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_adcs_scanner.py tests/test_adcs_ast_gate.py tests/test_adcs_no_writes.py -x` |
| Full suite command | `pytest -m 'not slow'` then `pytest -m slow` (matrix gate) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ADCS-01 | Scanner enumerates Enrollment Services + Templates via authenticated LDAP | unit (mocked ldap3) | `pytest tests/test_adcs_scanner.py::test_enumerates_ca_and_templates -x` | ❌ Wave 0 |
| ADCS-02 | ESC1/ESC2/ESC3 emit HIGH findings; ESC4/5/7/8 emit COVERAGE-GAP | unit | `pytest tests/test_adcs_scanner.py::test_esc_classification -x` | ❌ Wave 0 |
| ADCS-03 | New ORM column `adcs_scan_json` present after `_ensure_columns` | integration | `pytest tests/test_db_migrations.py::test_adcs_scan_json_added -x` | ❌ Wave 0 |
| ADCS-04 | 4 new counters slot into identity_trust subscore | unit | `pytest tests/test_evidence.py::test_adcs_counters tests/test_scoring.py::test_adcs_weights -x` | ❌ Wave 0 |
| ADCS-05 | `protocol="ADCS"` IdentityFinding entries appear in `GET /api/scan/latest` | integration | `pytest tests/test_api_scan_latest.py::test_adcs_findings_surfaced -x` | ❌ Wave 0 |
| ADCS-06 | CBOM Pass-1 emits CA sig + key algorithms; Pass-2/3 skip ADCS | unit | `pytest tests/test_cbom_builder.py::test_adcs_pass1_emits_pass23_skip -x` | ❌ Wave 0 |
| ADCS-07 | cryptography>=44.0 across `[adcs]`, `[all]`, `[all,adcs]` | matrix (slow) | `pytest tests/test_extras_install_adcs.py -m slow` | ❌ Wave 0 |
| ADCS-08 | Chaos lab `adcs` profile produces deterministic findings | live_infra | `pytest tests/test_chaos_lab_adcs.py -m live_infra` | ❌ Wave 0 |
| ADCS-09 | Module header invariant + AST gate forbids enrollment + no writes | AST gate + invariant | `pytest tests/test_adcs_ast_gate.py tests/test_adcs_no_writes.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_adcs_*.py -x` (~3 seconds, no live_infra)
- **Per wave merge:** `pytest -m 'not slow'`
- **Phase gate:** `pytest` (full incl. slow + matrix), then `gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_adcs_scanner.py` — unit tests with mocked ldap3 (ESC classification + CA parse + unreach path)
- [ ] `tests/test_adcs_no_writes.py` — invariant test using `unittest.mock` to wrap ldap3 `Connection.add/modify/delete` and assert never called
- [ ] `tests/test_adcs_ast_gate.py` — clone of `test_smime_ast_gate.py` with the FORBIDDEN sets above
- [ ] `tests/test_extras_install_adcs.py` — 3-way pip dry-run matrix (slow)
- [ ] `tests/test_chaos_lab_adcs.py` — live_infra test that brings up the profile, runs the scanner, asserts oracle counts
- [ ] No framework install needed — pytest already in dev deps.

## Security Domain

`security_enforcement` is assumed enabled (no opt-out in config).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Simple bind credentials stored as `SecretStr`; no logging of password values; `safe_str()` used on all bind errors |
| V3 Session Management | no | One-shot LDAP bind per scan; no persistent session |
| V4 Access Control | no | Read-only scanner; no privilege escalation surface |
| V5 Input Validation | yes | `_parse_target` validates host/port shape; LDAP search filters are constants (no user-supplied filter strings) |
| V6 Cryptography | yes | DER parsing via `cryptography>=44.0`; signing-alg classification via `is_weak_cipher` (single source of truth) |

### Known Threat Patterns for ADCS-LDAP Scanner

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LDAP injection via target string | Tampering | `ldap3.Server(host=...)` takes structured input, not a filter; search filter strings are module constants |
| Credential leakage in scan_error | Information disclosure | `safe_str()` on all exception text; enforced by `test_scan_error_gate.py` (Phase 59 model — runs against `quirk/scanner/`) |
| Accidental enrollment / template mutation | Tampering | AST gate forbids `certipy_ad`, `CertificateSigningRequestBuilder`, `conn.add/modify/delete`; invariant header on module |
| Anonymous-bind disclosure on prod AD | Information disclosure | Anonymous bind is opt-in; simple bind path is default for any non-chaos-lab target |
| nTSecurityDescriptor SID disclosure in `adcs_scan_json` | Information disclosure | We DO NOT decode the bytes; we store only the presence flag in `adcs_scan_json`, never the raw bytes |

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Bitnami openldap rejects schema LDIF under `cn=schema,cn=config` | Medium | High (blocks lab profile) | Spike in Plan 80-04 BEFORE committing the LDIF approach. Fallback: pre-bake schema into a custom Dockerfile FROM the bitnami base. |
| R2 | Adding `[adcs]` to `[all]` breaks `test_install_all_excludes_impacket` | Low | Medium | `[adcs]` deps verified impacket-free above. Plan 80-06 runs the regression test as a guard. |
| R3 | Real-AD anonymous bind rejected → all real-customer scans return ADCS-UNREACH | High | Low (expected behavior; documented) | The COVERAGE-GAP finding IS the documented graceful-degradation path. Users provide credentials via `adcs_user`/`adcs_password`. |
| R4 | nTSecurityDescriptor in real AD requires `LDAP_SERVER_SD_FLAGS_OID` control | Medium | Low | Read attribute opportunistically; COVERAGE-GAP signal works either way. |
| R5 | ESC bitmask interpretation drift if Microsoft revises `[MS-CRTD]` | Low | Low | Bitmask constants are inline module-level constants — easy to refresh in a future phase. Add a `# Source: [MS-CRTD] §2.4.x, retrieved 2026-05-16` comment. |
| R6 | Phase 83 SCORE_WEIGHTS invariant bump not coordinated with Phase 80 close-out | Medium | Medium (CI red for the gap window) | CONTEXT explicitly says invariant test STAYS RED until Phase 83. Phase 80 closes red; Phase 83 closes the consolidated bump. Communicate to reviewers in the PR description. |
| R7 | `[MS-CRTD]` `msPKI-Certificate-Application-Policy` OID encoding (binary vs. string) varies between ldap3 versions | Low | Low | Coerce via `[v.decode() if isinstance(v, bytes) else v for v in raw or []]` per Pitfall 7. |

## File Touch List

### New files
- `quirk/scanner/adcs_scanner.py`
- `quantum-chaos-enterprise-lab/adcs/ldif/01-schema-mspki.ldif`
- `quantum-chaos-enterprise-lab/adcs/ldif/02-templates.ldif`
- `quantum-chaos-enterprise-lab/adcs/certs/regen.sh`
- `quantum-chaos-enterprise-lab/adcs/certs/ca-weak.der` (committed binary fixture)
- `tests/test_adcs_scanner.py`
- `tests/test_adcs_no_writes.py`
- `tests/test_adcs_ast_gate.py`
- `tests/test_extras_install_adcs.py`
- `tests/test_chaos_lab_adcs.py` (live_infra marker)
- `docs/connectors/adcs.md` (new connector doc per per-phase docs/obsidian feedback rule)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-80-Windows-ADCS-Scanner.md` (post-execution)

### Edited files
- `pyproject.toml` — add `adcs` extras group; include in `[all]`
- `quirk/db.py` — append `("adcs_scan_json", "TEXT")` to `_IDENTITY_COLUMNS` (line 81)
- `quirk/intelligence/scoring.py` — add 4 weights + 4 impact lines + 4 counter reads
- `quirk/intelligence/evidence.py` — add "ADCS" to `_PROTOCOL_KEYS`; add `elif proto == "ADCS"` branch; add 4 counters to return dict
- `quirk/cbom/builder.py` — add `elif ep.protocol == "ADCS":` Pass-1 branch (~line 463); append `"ADCS"` to Pass-2 skip tuple (line 538) and Pass-3 skip tuple (line 622)
- `quirk/config.py` — add `enable_adcs`, `adcs_targets`, `adcs_search_base`, `adcs_user`, `adcs_password`, `adcs_timeout` to `ConnectorsCfg`
- `quirk/models.py` — add `adcs_scan_json` field to `CryptoEndpoint` (mirror `smime_scan_json`)
- `run_scan.py` — `_run_adcs_phase` function + `_wrapped_phase` call (~line 1416 between smime and vault); append `adcs_endpoints` to `_dar_eps` (line 1453); add to resumed-endpoint filter (line 1219)
- `quantum-chaos-enterprise-lab/docker-compose.yml` — append adcs-openldap + adcs-seed services (profile `adcs`)
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — append `## Profile: adcs` section
- `quantum-chaos-enterprise-lab/README.md` — add Profile Summary row for `adcs` (port 38910)
- `docs/UAT-SERIES.md` — add Phase 80 entries

### Files explicitly NOT edited
- `tests/test_score_weights_invariant.py` (Phase 83 owns the consolidated bump — CONTEXT cross-cutting locked)
- `lab.sh` (ALL_PROFILES is runtime-derived per CONTEXT cross-cutting)

## Sources

### Primary (HIGH confidence)
- `.planning/phases/80-windows-adcs-scanner/80-CONTEXT.md` — locked decisions
- `.planning/REQUIREMENTS.md` (ADCS-01..09) and `.planning/ROADMAP.md` (Phase 80 success criteria)
- `quirk/scanner/smime_scanner.py` — structural template (Phase 79, just landed)
- `quirk/scanner/kerberos_scanner.py` — ldap3 anonymous bind pattern (`_probe_ldap_anon`)
- `quirk/intelligence/scoring.py`, `quirk/intelligence/evidence.py` — current line numbers + SMIME analogs
- `quirk/cbom/builder.py` lines 454-462, 538, 622 — actual SMIME inline skip & Pass-1 branch
- `quirk/db.py:76-81` — `_IDENTITY_COLUMNS` tuple
- `tests/test_smime_ast_gate.py` and `tests/test_scan_error_gate.py` — AST-gate templates
- `tests/test_install_all_excludes_impacket.py` — pip-dry-run matrix template
- `quantum-chaos-enterprise-lab/smime/` + `expected_results_v4.md` smime section — chaos-lab analog
- `pyproject.toml` — current extras structure and the [identity]-out-of-[all] invariant
- `.planning/research/SUMMARY.md` (commit `c5d1d61`) — v4.10 cross-phase research; CONTEXT supersedes any conflicting recommendation per project planner-precedence rule

### Secondary (MEDIUM confidence)
- Microsoft `[MS-CRTD]` (Certificate Templates Structure) — public protocol spec; ESC1-ESC8 bitmask values
- Microsoft `[MS-ADTS]` (Active Directory Technical Specification) — schema OIDs for msPKI-* attributes
- SpecterOps "Certified Pre-Owned" whitepaper — ESC1-ESC8 definitions (referenced in v4.10 SUMMARY line 279)
- Certipy source (`certipy/lib/ldap.py`) — concrete LDAP filter and attribute list patterns; used as cross-reference only, NOT as a dependency

### Tertiary (LOW confidence)
- `[ASSUMED]` Bitnami openldap acceptance of cn=schema,cn=config LDIF (see Assumption A1)
- `[ASSUMED]` `LDAP_ALLOW_ANON_BINDING` env var of bitnami openldap behaves as named (verify in Plan 80-04)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all locked by CONTEXT; no new deps
- Architecture: HIGH — direct clone of Phase 79 SMIME structure
- ESC bitmask interpretation: MEDIUM — bitmask values are well-published in Microsoft specs, but the LDAP-observability classification is a Phase 80 design call (documented above)
- Chaos lab schema LDIF: MEDIUM — A1 assumption needs a quick spike before Plan 80-04 commits
- Pitfalls: HIGH — sourced directly from Phase 79 SMIME post-mortem patterns

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (30 days — stable subdomain; Microsoft schema OIDs don't move)

# Phase 80: Windows AD CS Scanner — Pattern Map

**Mapped:** 2026-05-16
**Surfaces analyzed:** 15
**Analogs found:** 15 / 15 (Phase 79 SMIME landed dbfb76c..6855495 — every surface has a freshly-verified twin)

## Drift Check vs REQUIREMENTS / CONTEXT

| Issue | Truth | Action |
|-------|-------|--------|
| `quirk/scanners/` plural in REQUIREMENTS | Codebase uses singular `quirk/scanner/` (confirmed: all 21 modules sit there, Phase 79 confirmed) | Plan uses singular path |
| ADCS-04 lists 3 counters; CONTEXT adds 4th (`identity_adcs_coverage_gap_count`) | CONTEXT D-Area-1 "all 8 best-effort" requires it | 4 counters / 4 SCORE_WEIGHTS; flag for Phase 83 SUM math: 261.0 + 6.0 (P79) + 8.0 (P80) = 275.0 |
| CBOM skip-tuple line numbers | Verified post-P79: line **538** (Pass-2) and **622** (Pass-3) — CONTEXT D says 528+611, drifted by 10/11 lines | Append `"ADCS"` to tuples at lines 538 + 622, not 528 + 611 |
| `_IDENTITY_COLUMNS` line range | Verified: tuple at `quirk/db.py:76-81` (P79 appended at line 80) | Append `("adcs_scan_json", "TEXT")` after line 80 |
| Phase 79 CBOM Pass-1 SMIME branch | Verified at `quirk/cbom/builder.py:454-462` | Mirror as SMIME elif branch sibling |
| `[adcs]` not yet in pyproject | Confirmed absent | New extras group |

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match |
|--------------------|------|-----------|----------------|-------|
| `quirk/scanner/adcs_scanner.py` | scanner | LDAP query → classify → emit endpoints | `quirk/scanner/smime_scanner.py` | exact |
| `quirk/db.py` (mod) | ORM column append | n/a | `quirk/db.py:76-81` self-pattern | exact |
| `quirk/intelligence/scoring.py` (mod) | scoring weights + penalty rows | reduce | `quirk/intelligence/scoring.py:32-34, 156-158, 189-191` | exact |
| `quirk/intelligence/evidence.py` (mod) | evidence counter accumulator | reduce | `quirk/intelligence/evidence.py:90-92, 181-195, 361-363` | exact |
| `quirk/cbom/builder.py` (mod) | CBOM Pass-1 emit + skip-tuples | transform | `quirk/cbom/builder.py:454-462, 538, 622` | exact |
| `run_scan.py` (mod) | orchestrator phase | event-driven | `run_scan.py:1396-1415` (`_run_smime_phase`) | exact |
| `pyproject.toml` (mod) | extras group | config | `pyproject.toml:43-46` (`[identity]`) | role-match |
| `tests/test_adcs_scanner.py` | unit test | n/a | `tests/test_smime_scanner.py` | exact |
| `tests/test_adcs_no_writes.py` | safety invariant | n/a | `tests/test_smime_no_envelope_leak.py` | structural-match (different invariant) |
| `tests/test_adcs_ast_gate.py` | AST CI gate | n/a | `tests/test_smime_ast_gate.py` | exact |
| `tests/test_extras_install.py` (or extend) | pip resolver test | n/a | `tests/test_install_all_excludes_impacket.py` | role-match |
| `quantum-chaos-enterprise-lab/docker-compose.yml` (mod) | compose profile | config | `docker-compose.yml:760-801` (smime profile) | exact |
| `quantum-chaos-enterprise-lab/adcs/` | lab fixture dir | n/a | `quantum-chaos-enterprise-lab/smime/` | exact (extend with schema LDIF) |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` (mod) | oracle section | docs | existing `## Profile: smime` section | exact |
| `quantum-chaos-enterprise-lab/README.md` (mod) | Profile Summary row | docs | line 44 (smime row) | exact |

---

## Pattern Assignments

### 1. `quirk/scanner/adcs_scanner.py` (NEW)

**Analog:** `quirk/scanner/smime_scanner.py` (Phase 79, just landed)

**Module header invariant** (lines 1-14 in analog; ADCS variant per CONTEXT D Area 4):
```python
"""Active Directory Certificate Services (AD CS) enumeration via authenticated
LDAP. Read-only. No certificate enrollment, no template creation, no CSR
generation, no write operations under any code path — enforced by
tests/test_adcs_ast_gate.py (ADCS-09) and tests/test_adcs_no_writes.py.

Phase 80 — ADCS-01 … ADCS-08. Enumerates CA configurations under
CN=Public Key Services,CN=Services,CN=Configuration,<root-DN> and
certificate templates under CN=Certificate Templates,...; classifies
msPKI-* attributes for ESC1-ESC8 observable misconfigurations.
"""
```

**Imports pattern** (analog lines 15-38) — copy verbatim, drop `cryptography.x509` parsers (no DER blobs to parse on AD CS template attrs); keep `ldap3`, `safe_str`, `is_weak_cipher`, `CryptoEndpoint`, module logger.

**Bind/search scaffolding** (analog lines 126-148) — duplicate per CONTEXT D Area 2 (no shared helper). Adapt:
- search base = `CN=Public Key Services,CN=Services,CN=Configuration,<base_dn>` (CA enumeration) and `CN=Certificate Templates,CN=Public Key Services,...` (template enumeration) — two paged_search calls per target
- attributes: `cACertificate`, `cn`, `msPKI-*` family per CONTEXT specifics
- search_scope = `SUBTREE`
- **Authentication: SIMPLE bind** (not ANONYMOUS — AD CS Configuration partition is not anonymously readable). Accept creds via target object.

**Target parser** (analog lines 151-184) — copy `_parse_target` shape; add `bind_dn` / `bind_password` attrs.

**Top-level scanner function** (analog lines 187-291):
```python
def scan_adcs_targets(targets, timeout=10, logger=None, session_start=None, *, search_base=None):
    # 1. ldap3 availability guard (analog line 207)
    # 2. iterate targets; bind+search (CA branch then template branch)
    # 3. unreachable path → IdentityFinding with severity="LOW", protocol="ADCS",
    #    service_detail=f"adcs-unreachable|base={base_dn}" (analog lines 224-238)
    # 4. per-CA: classify signing alg via is_weak_cipher → identity_adcs_weak_signing_count
    # 5. per-template: classify msPKI-Certificate-Name-Flag / msPKI-Enrollment-Flag
    #    against ESC1/ESC2/ESC3/ESC4 patterns; emit ESC misconfig → identity_adcs_weak_template_count
    # 6. per-template ACL heuristic → identity_adcs_misconfig_count
    # 7. ESC checks deferred (require CSR) → emit ADCS-COVERAGE-GAP finding →
    #    identity_adcs_coverage_gap_count
```

Endpoint shape (analog lines 277-289): `CryptoEndpoint(protocol="ADCS", cert_pubkey_alg=..., cert_sig_alg=..., service_detail=..., severity=..., adcs_scan_json=json.dumps(...), scanned_at=now)`.

**ADCS-UNREACH coverage gap** (CONTEXT specifics): mirror analog's unreachable branch (lines 226-238); do NOT propagate exception to error_endpoints (ADCS-04 SC#2).

---

### 2. `quirk/db.py` — append ORM column

**Analog:** `quirk/db.py:76-81` (self-pattern; Phase 79 just appended `smime_scan_json`)

Append one tuple entry after line 80:
```python
_IDENTITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("kerberos_scan_json", "TEXT"),
    ("saml_scan_json",     "TEXT"),
    ("dnssec_scan_json",   "TEXT"),
    ("smime_scan_json",    "TEXT"),  # Phase 79 SMIME-03
    ("adcs_scan_json",     "TEXT"),  # Phase 80 ADCS-03
)
```

`_ensure_columns` does the rest (no breaking migration).

---

### 3. `quirk/intelligence/scoring.py` — 4 SCORE_WEIGHTS entries

**Analog:** `quirk/intelligence/scoring.py:32-34` (SMIME entries) + `:156-158` (extractors) + `:189-191` (penalty rows)

Insert after line 34:
```python
"identity_adcs_weak_template_count":  2.0,   # Phase 80 ADCS-04
"identity_adcs_misconfig_count":      2.0,   # Phase 80 ADCS-04
"identity_adcs_weak_signing_count":   2.0,   # Phase 80 ADCS-04
"identity_adcs_coverage_gap_count":   2.0,   # Phase 80 CONTEXT D-Area-1
```

Extractors (mirror lines 156-158) and penalty tuple rows (mirror 189-191) — 4 of each.

**DO NOT TOUCH** `tests/test_score_weights_invariant.py` — Phase 83 owns the consolidated SUM bump to 275.0.

---

### 4. `quirk/intelligence/evidence.py` — 4 counter accessors

**Analog:** `quirk/intelligence/evidence.py:90-92` (init), `:181-195` (per-endpoint accumulator inside the protocol switch), `:361-363` (output dict)

Mirror the SMIME triplet four times (init=0, branch under `elif proto == "ADCS":`, output dict keys: `adcs_weak_template_count`, `adcs_misconfig_count`, `adcs_weak_signing_count`, `adcs_coverage_gap_count`).

Accumulator logic differs from SMIME — drive off `service_detail` substring tags (`"esc1-name-flag"`, `"esc2-no-sec-ext"`, `"coverage-gap=..."`) emitted by the scanner. Use the same `is_weak_cipher(cert_sig_alg)` predicate for the weak-signing branch.

---

### 5. `quirk/cbom/builder.py` — Pass-1 emit + 2 inline skip tuples

**Analog:** `quirk/cbom/builder.py:454-462` (SMIME Pass-1 branch), `:538` (Pass-2 skip tuple), `:622` (Pass-3 skip tuple)

**Pass-1 branch** — insert after the SMIME elif (around line 463):
```python
elif ep.protocol == "ADCS":
    # ADCS: cert_pubkey_alg holds CA signing algorithm or template key alg.
    # Pass-1 only — Pass-2/3 skip the ADCS literal (see skip tuples).
    # Phase 80 ADCS-06.
    if ep.cert_pubkey_alg:
        _register_algorithm(
            ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size
        )
```

**Skip tuples** — append `"ADCS"`:
- Line **538**: `"SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "SMIME", "ADCS",`
- Line **622**: `"DNSSEC", "SAML", "KERBEROS", "SMIME", "ADCS",`

(CONTEXT cites 528/611 — drift; verified post-P79 at 538/622.)

---

### 6. `run_scan.py` — `_run_adcs_phase`

**Analog:** `run_scan.py:1396-1415` (`_run_smime_phase`) — insert immediately after; wire `adcs_endpoints` into the `_dar_eps` sum at line 1453 and the final concat at line 1619.

Also append `"ADCS"` to `_dar_protocols` tuple at line 1210; add `adcs_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "ADCS"]` near line 1219; extend resume-count log at 1226.

```python
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
    )
    logger.info("ADCS scan: %d endpoints from %d targets",
                len(eps), len(cfg.connectors.adcs_targets))
    return eps
adcs_endpoints = _wrapped_phase(
    run_stats, "adcs_scanning", "adcs_scanner",
    _run_adcs_phase, error_endpoints, logger,
) or []
```

---

### 7. `pyproject.toml` — `[adcs]` extras

**Analog:** `pyproject.toml:43-46` (`[identity]`). After line 46, before `[cloud]`:
```toml
adcs = [
    "ldap3>=2.9.1",
]
```

**Critical:** Do NOT add to `[all]` — same impacket-like rationale: keep AD CS deps isolated so the matrix install test can assert `cryptography>=44.0` survives across `[all]` + `[adcs]` combinations (ADCS-07). Note that `[adcs]` does NOT pull impacket (different from `[identity]`), so unlike `[identity]` it could theoretically be added to `[all]` — defer decision; CONTEXT keeps it separate.

---

### 8. `tests/test_adcs_scanner.py` (NEW)

**Analog:** `tests/test_smime_scanner.py` (read at planning time for fixture wiring pattern). Mock `_bind_and_search` to return canned `searchResEntry` dicts with msPKI attribute payloads. Cover: ESC1 misconfig (HIGH), ESC4 misconfig (HIGH), SAFE template (no emit), weak CA signing (HIGH), ADCS-UNREACH (LOW). Fixtures under `tests/fixtures/adcs/`.

---

### 9. `tests/test_adcs_no_writes.py` (NEW)

**Analog:** `tests/test_smime_no_envelope_leak.py` (structural; INVARIANT IS DIFFERENT)

Reuse the structural shape (sentinel target → mock _bind_and_search → assert no forbidden behavior surfaces). **Adapt the invariant**:

SMIME tested "no IMAP envelope leak" via sentinel string absence. ADCS tests **no write LDAP operations + no CSR builder calls**:

```python
# Inspect the ldap3.Connection mock — assert .add() / .modify() / .delete()
# / .modify_dn() were NEVER called. Only .bind() and .extend.standard.paged_search().
mock_conn.add.assert_not_called()
mock_conn.modify.assert_not_called()
mock_conn.delete.assert_not_called()
mock_conn.modify_dn.assert_not_called()
```

Plus: monkeypatch `cryptography.x509.CertificateSigningRequestBuilder` to a `MagicMock(side_effect=AssertionError("CSR builder forbidden"))` and run a full scan — assert no AssertionError raised (i.e., builder never instantiated).

---

### 10. `tests/test_adcs_ast_gate.py` (NEW)

**Analog:** `tests/test_smime_ast_gate.py` (exact shape, just landed — cleaner than the Phase 59 original because same-shape)

Copy verbatim, swap target + forbidden set:
```python
TARGET = PROJECT_ROOT / "quirk" / "scanner" / "adcs_scanner.py"
FORBIDDEN_MODULES = {"certipy_ad", "certipy", "impacket.ldap.ldapasn1_modify"}
FORBIDDEN_FROM_PREFIXES = ("certipy", "certipy_ad")
```

Plus an additional walker checking for **AST Attribute references**:
- Forbid `cryptography.x509.CertificateSigningRequestBuilder` (AST Attribute walk, not import — could be reached via aliased import)
- Forbid `ldap3.Connection.add` / `.modify` / `.delete` / `.modify_dn` attribute access patterns

Keep the three-test shape (real target / synthetic-forbidden self-test / synthetic-clean self-test).

---

### 11. `tests/test_extras_install.py` (NEW or extend)

**Analog:** `tests/test_install_all_excludes_impacket.py` (slow marker, pip --dry-run --report JSON parser)

Pattern: invoke `pip install --dry-run -e <repo>[adcs]`, parse report, assert `ldap3` present AND `cryptography>=44.0` present. Then second subprocess with `-e <repo>[all]` followed by `-e <repo>[adcs]` simultaneously — assert resolver succeeds (no version conflict) and final cryptography pin still `>=44.0`. Mark `@pytest.mark.slow`. ADCS-07 matrix.

---

### 12. `quantum-chaos-enterprise-lab/docker-compose.yml` — `adcs` profile

**Analog:** lines 760-801 (smime profile, just landed)

Copy the smime block verbatim with these substitutions:
- profile name: `adcs`
- service names: `adcs-openldap`, `adcs-seed`
- host port: `38910` (NOT 38900 — CONTEXT D Area 3)
- Volume mounts: `./adcs/ldif:/ldif:ro`, `./adcs/schema:/schema:ro`
- Same image: `bitnamilegacy/openldap:2.6.10-debian-12-r4`
- Same `ldapadd -c` idempotency contract + exit-68 swallow
- **Add a third sidecar OR extend seed**: load `msPKI-schema.ldif` via `ldapmodify` against `cn=config` BEFORE template LDIFs (AD CS attributes are not in stock OpenLDAP schema)

`lab.sh` requires NO edits — runtime profile derivation (confirmed by CONTEXT).

---

### 13. `quantum-chaos-enterprise-lab/adcs/` (NEW dir)

**Analog:** `quantum-chaos-enterprise-lab/smime/` (ldif/ + certs/)

Structure:
```
adcs/
├── README.md           # invariant statement + how three templates map to ESC findings
├── schema/
│   └── msPKI-schema.ldif    # msPKI-* attribute + objectClass definitions for cn=config
├── ldif/
│   ├── 00-base.ldif    # CN=Configuration, CN=Public Key Services, CN=Services
│   ├── 10-ca.ldif      # one fake CA entry with cACertificate (SHA-1 signed for weak-signing finding)
│   └── 20-templates.ldif  # BadTemplate-ESC1, BadTemplate-ESC4, SafeTemplate
```

Mirror P79 `users.ldif` shape (lines 1-14 header comment about `;binary` option semantics). Keep base DN `dc=quirk,dc=lab` for parity. Three deterministic templates per CONTEXT specifics.

---

### 14. `quantum-chaos-enterprise-lab/expected_results_v4.md`

**Analog:** existing `## Profile: smime` section (find via `grep -n "## Profile: smime"`)

New `## Profile: adcs` H2 section. Schema: same DAR / config-introspection style as smime (per H2 header convention at line 5). Document the three template fixtures and their expected findings:
- `BadTemplate-ESC1` → ADCS HIGH, reason=`esc1-name-flag`, counter `identity_adcs_weak_template_count`
- `BadTemplate-ESC4` → ADCS HIGH, reason=`esc4-vuln-acl`, counter `identity_adcs_weak_template_count`
- `SafeTemplate` → no finding
- Fake CA → ADCS HIGH, reason=`weak-signing-alg`, counter `identity_adcs_weak_signing_count`
- ESC9-16 deferred → 8 `ADCS-COVERAGE-GAP` LOW findings, counter `identity_adcs_coverage_gap_count`

---

### 15. `quantum-chaos-enterprise-lab/README.md`

**Analog:** line 44 (smime profile row in Profile Summary table)

Append row directly after smime:
```markdown
| adcs | adcs-openldap, adcs-seed | 38910 | [Expected Findings](expected_results_v4.md#profile-adcs) | v4.10 (Phase 80); OpenLDAP seeded with msPKI schema + three certificate template fixtures (ESC1, ESC4, Safe) + a SHA-1-signed fake CA. Plain LDAP only. Authenticated bind (SIMPLE) — AD CS Configuration partition is not anonymously readable. Idempotent seed sidecar (`ldapadd -c`, swallows exit 68). |
```

---

## Shared Patterns

### LDAP scanner skeleton
**Source:** `quirk/scanner/smime_scanner.py` (entire module, 292 lines)
**Apply to:** `quirk/scanner/adcs_scanner.py`
- Module-level `try/except ImportError` for ldap3 with `LDAP3_AVAILABLE` flag (lines 17-21)
- `logger = logging.getLogger(__name__)` (line 38)
- `_realm_to_base_dn` helper (lines 44-55) — copy verbatim
- `_bind_and_search` returning generator or `[]` on bind reject (lines 126-148)
- `_parse_target` accepting URL strings / bare host / SimpleNamespace (lines 151-184)
- Top-level `scan_<proto>_targets` returning `list[CryptoEndpoint]` (lines 187-291)
- Unreachable path: emit endpoint with `scan_error_category="exception"`, do not raise

### Severity classification using `is_weak_cipher`
**Source:** `quirk/util/weak_crypto.py` (imported at smime_scanner.py:34)
**Apply to:** weak CA signing detection + weak template key detection

### CBOM 3-pass protocol switch
**Source:** `quirk/cbom/builder.py:454-462` (Pass-1) + skip tuples at 538/622
**Apply to:** every new LDAP-derived protocol — Pass-1 algorithm emit, Pass-2/3 skip

### ORM additive column
**Source:** `quirk/db.py:76-81` tuple + `_ensure_columns` helper
**Apply to:** `adcs_scan_json TEXT` — no migration, no breaking change

### Test triad per protocol
**Source:** Phase 79 `tests/test_smime_scanner.py` + `test_smime_ast_gate.py` + `test_smime_no_envelope_leak.py`
**Apply to:** scanner-unit + AST-gate + safety-invariant — one of each per new protocol

---

## Metadata

**Analog search scope:**
- `quirk/scanner/` (21 modules — confirmed singular path)
- `quirk/cbom/builder.py` (Pass-1/2/3 structure)
- `quirk/intelligence/{scoring,evidence}.py` (SMIME entries verified at exact lines)
- `tests/` (smime triad — exact analog set)
- `quantum-chaos-enterprise-lab/{docker-compose.yml,smime/,README.md,expected_results_v4.md}`
- `pyproject.toml` (extras groups; `[identity]` exclusion rationale)

**Files scanned:** ~15 directly read; ~30 confirmed via Grep
**Pattern extraction date:** 2026-05-16

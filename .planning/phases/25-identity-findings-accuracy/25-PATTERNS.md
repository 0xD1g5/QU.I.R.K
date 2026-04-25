# Phase 25: Identity Findings Accuracy — Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 4 (2 code modifications, 1 config edit, 1 doc update)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/dashboard/api/routes/scan.py` | service/route helper | request-response, transform | itself (existing `_derive_identity_findings` SAML branch) | exact — modifying two functions within this file |
| `quirk/scanner/saml_scanner.py` | scanner/utility | transform | itself (read-only reference for `OIDC_ALG_SEVERITY`) | exact — import source only |
| `pyproject.toml` | config | n/a | itself (existing `[identity]` extras block) | exact — one-line addition |
| `quantum-chaos-enterprise-lab/expected_results_v3.md` | documentation | n/a | existing Phase 4 profile tables in same file | role-match — doc-only, same table format |

---

## Pattern Assignments

### `quirk/dashboard/api/routes/scan.py` — Fix 1: RS-family detection in `_derive_identity_findings()`

**Analog:** `quirk/dashboard/api/routes/scan.py` (existing SAML branch, lines 217–256) and `tests/test_identity_surface.py` (existing derivation test fixtures)

**Import pattern — add to existing import block (lines 13–27):**
```python
# Current imports from quirk.scanner are done inline (line 152):
from quirk.cbom.classifier import classify_algorithm, quantum_safety_label

# New import to add at top-level import block (after quirk.models import):
from quirk.scanner.saml_scanner import OIDC_ALG_SEVERITY
```
Source of `OIDC_ALG_SEVERITY` — `quirk/scanner/saml_scanner.py` lines 44–50:
```python
OIDC_ALG_SEVERITY = {
    "RS256": "HIGH", "RS384": "HIGH", "RS512": "HIGH",
    "PS256": "HIGH", "PS384": "HIGH", "PS512": "HIGH",
    "ES256": None,   "ES384": None,   "ES512": None,
    "HS256": None,   "HS384": None,   "HS512": None,
    "EdDSA": None,
}
```

**Core pattern — SAML branch ordering in `_derive_identity_findings()` (lines 217–256):**

The existing SAML branch checks `alg == "SHA1"` first, then `size < 2048`. The new RS-family check must be inserted BEFORE the SHA1 check (highest specificity first). `SHA1` is not in `OIDC_ALG_SEVERITY`, so it falls through naturally.

Existing branch structure to extend (lines 217–256):
```python
elif proto == "SAML":
    alg = (ep.cert_pubkey_alg or "").upper()
    size = ep.cert_pubkey_size
    sd = ep.service_detail or ""

    # NEW BLOCK — insert here, before the SHA1 check:
    # RS-family OIDC check (D-01, D-02)
    severity = OIDC_ALG_SEVERITY.get(alg)
    if severity is not None:
        results.append(IdentityFinding(
            host=ep.host,
            port=ep.port,
            severity=severity,
            title=f"OIDC RS-family algorithm: {alg}",
            protocol="SAML",
            description=(
                f"OIDC endpoint uses {alg} which relies on RSA. "
                f"RSA is quantum-vulnerable and will be broken by Shor's algorithm."
            ),
            remediation=(
                "Migrate OIDC token signing to ECDSA (ES256/ES384) or EdDSA "
                "per NIST PQC roadmap recommendations."
            ),
            quantum_risk="Vulnerable",
            source="saml",
            algorithm=alg,
        ))
    elif alg == "SHA1":
        # existing SHA1 block unchanged
        results.append(IdentityFinding(...))
    elif size is not None and isinstance(size, int) and size < 2048:
        # existing weak-key block unchanged
        results.append(IdentityFinding(...))
```

**IdentityFinding field contract** — `quirk/dashboard/api/schemas.py` lines 79–90:
```python
class IdentityFinding(BaseModel):
    host: str
    port: int
    severity: str            # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    protocol: Optional[str] = None    # KERBEROS / SAML / DNSSEC
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None
    algorithm: str           # e.g. "rc4-hmac", "RSA-1024", "RSASHA1"
```

Required field values for RS-family OIDC finding per D-02:
- `source="saml"` (OIDC lives under the SAML/OIDC scanner)
- `severity` from `OIDC_ALG_SEVERITY.get(alg)` (RS256/RS384/RS512 → `"HIGH"`)
- `algorithm=alg` (the raw alg string, e.g., `"RS256"`)
- `protocol="SAML"`

**Text style reference** — follow the KERBEROS finding description pattern (lines 204–214):
```python
description=(
    f"KDC accepts etype {etype_id} ({name}) which is classified as {severity}. "
    f"RC4 and DES etypes are cryptographically weak and quantum-vulnerable."
),
remediation=(
    "Disable RC4-HMAC and DES etypes in KDC configuration. "
    "Enforce AES-256 (etype 18/20) as minimum."
),
```

And the DNSSEC pattern (lines 282–297):
```python
remediation = "Migrate to ECDSAP256SHA256 (algorithm 13) or Ed25519 (algorithm 15) per RFC 8624."
results.append(IdentityFinding(
    ...
    quantum_risk="Vulnerable" if severity == "CRITICAL" else None,
    source="dnssec",
    algorithm=ep.cert_pubkey_alg or alg,  # preserve original case
))
```

**Severity sort pattern** — both functions use the same sort at the bottom (lines 299–302):
```python
_severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
results.sort(key=lambda f: _severity_order.get(f.severity, 99))
return results
```

---

### `quirk/dashboard/api/routes/scan.py` — Fix 2: TLS-bleed guard in `_derive_findings()`

**Analog:** `quirk/dashboard/api/routes/scan.py` `_derive_identity_findings()` proto routing (lines 186–188) — same `proto in {...}` idiom.

**Existing proto routing pattern in `_derive_identity_findings()` (lines 186–188):**
```python
for ep in endpoints:
    proto = (ep.protocol or "").upper()

    if proto == "KERBEROS":
        ...
    elif proto == "SAML":
        ...
    elif proto == "DNSSEC":
        ...
```

**Core pattern — broad guard to add as very first statement in `_derive_findings()` loop (after line 50):**

`_derive_findings()` currently starts its loop body at line 51 with the HTTP check. The guard goes BEFORE all existing checks:
```python
for ep in endpoints:
    # D-03: skip all identity protocol endpoints — handled exclusively by
    # _derive_identity_findings(); none of the TLS checks apply to them.
    proto = (ep.protocol or "").upper()
    if proto in {"KERBEROS", "SAML", "DNSSEC"}:
        continue

    # Unencrypted HTTP (existing, line 52)
    if ep.protocol and ep.protocol.upper() == "HTTP":
        ...
```

Note: `proto` can be extracted as a module-level constant or kept inline (Claude's Discretion per CONTEXT.md). If extracted:
```python
_IDENTITY_PROTOCOLS = {"KERBEROS", "SAML", "DNSSEC"}
```

---

### `pyproject.toml` — Add `ldap3>=2.9.1` to `[identity]` extras

**Analog:** Existing `[identity]` extras block (lines 40–42) and impacket version pin style.

**Current `[identity]` block (lines 40–42):**
```toml
identity = [
    "impacket>=0.13.0,<0.14",
]
```

**Target state after D-04:**
```toml
identity = [
    "impacket>=0.13.0,<0.14",
    "ldap3>=2.9.1",
]
```

Pattern: lower-bound-only pin (no upper bound). Matches `ldap3>=2.9.1` per REQUIREMENTS.md KERB-03. No upper bound needed (no known conflict with impacket).

---

### `quantum-chaos-enterprise-lab/expected_results_v3.md` — Identity chaos lab entries (D-05)

**Analog:** Phase 4 profile table blocks in the same file (e.g., lines 114–127 for JWT profile, lines 189–204 for SSH-Weak profile).

**Existing table format pattern** (lines 189–204):
```markdown
## Phase 4 — SSH-Weak Profile (profile: ssh-weak)

| Port | Service | Algorithm Class | Expected ssh-audit Finding | Severity |
|-----:|---------|----------------|---------------------------|----------|
| 20022 | ssh-weak | KEX | diffie-hellman-group1-sha1 | CRITICAL |
...

**Scanner validation command:**
```
docker compose --profile ssh-weak up -d && sleep 5 && ssh-audit localhost:20022
```
**Expected:** ssh-audit returns >= 3 critical/warning findings ...
```

**Pattern elements to replicate for three new identity profile sections:**
1. `## Phase NN — <Name> Profile (profile: <profile-name>)` heading
2. Markdown table with columns appropriate to scanner type
3. `**Scanner validation command:**` fenced code block
4. `**Expected:**` plain-English summary sentence

Three sections to add (D-05):
- `## Phase 25 — DNSSEC Profile (profile: bind9)` — 4 zones × expected classification
- `## Phase 25 — SAML/OIDC Profile (profile: simpla-samlphp)` — RSA-1024 signing cert finding
- `## Phase 25 — Kerberos Profile (profile: samba-dc)` — RC4 etype finding

---

## Shared Patterns

### Test fixture: `_Ep` dataclass
**Source:** `tests/test_identity_surface.py` lines 36–50
**Apply to:** Plan 01 RED test scaffold (new `tests/test_identity_findings_accuracy.py`)

```python
@dataclass
class _Ep:
    host: str
    port: int
    protocol: str
    cert_pubkey_alg: Optional[str] = None
    cert_pubkey_size: Optional[int] = None
    service_detail: Optional[str] = None
    scanned_at: Optional[object] = None
    scan_error: Optional[str] = None
    tls_blocker_reason: Optional[str] = None
    cert_not_after: Optional[object] = None
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None
```

### Test fixture: OIDC RS256 endpoint
**Source:** `tests/test_identity_surface.py` fixtures pattern; extend with OIDC-specific `service_detail` format.

From `quirk/scanner/saml_scanner.py` OIDC storage convention (service_detail uses `oidc-discovery|...` prefix):
```python
def _oidc_rs256_ep() -> _Ep:
    return _Ep(
        host="auth.example.com",
        port=443,
        protocol="SAML",          # OIDC endpoints stored as protocol="SAML"
        cert_pubkey_alg="RS256",
        cert_pubkey_size=None,
        service_detail="oidc-discovery|https://auth.example.com/.well-known/openid-configuration",
    )
```

### Test class structure: RED scaffold
**Source:** `tests/test_identity_surface.py` lines 181–257 (class + docstring + test methods), `tests/test_identity_infra.py` lines 18–315

```python
class TestIdentityFindingsAccuracy(unittest.TestCase):
    """RED scaffold for Phase 25 fixes.

    Tests MUST FAIL before Plan 02 implementation lands.
    Covers SAML-04 (RS-family OIDC findings), IDENT-02/03 (no TLS-bleed).
    """

    def test_<specific_behavior>(self) -> None:
        """REQID: One-line description of what passes GREEN."""
        from quirk.dashboard.api.routes.scan import _derive_identity_findings
        results = _derive_identity_findings([_oidc_rs256_ep()])
        # assertions...
```

### Test method: pyproject assertion pattern
**Source:** `tests/test_identity_infra.py` lines 220–261 — assertIn checks on `pathlib.Path("pyproject.toml").read_text()`

```python
def test_pyproject_ldap3_in_identity_extras(self):
    """KERB-03: pyproject.toml [identity] group must include ldap3>=2.9.1."""
    source = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    self.assertIn(
        '"ldap3>=2.9.1"',
        source,
        "pyproject.toml [identity] group missing ldap3>=2.9.1 -- add per D-04",
    )
```

### Sorting pattern
**Source:** `quirk/dashboard/api/routes/scan.py` lines 171–173 and 299–302 (identical pattern in both functions)
**Apply to:** No new sorting needed — new findings flow into existing sort at end of `_derive_identity_findings()`

```python
_severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
results.sort(key=lambda f: _severity_order.get(f.severity, 99))
```

---

## No Analog Found

None. All four files have clear existing analogs in the codebase.

---

## Metadata

**Analog search scope:** `quirk/dashboard/api/routes/`, `quirk/scanner/`, `quirk/dashboard/api/schemas.py`, `tests/`, `pyproject.toml`, `quantum-chaos-enterprise-lab/expected_results_v3.md`
**Files scanned:** 8 source files read directly
**Pattern extraction date:** 2026-04-24

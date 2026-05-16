# Phase 79: S/MIME LDAP Discovery Scanner — Research

**Researched:** 2026-05-16
**Domain:** LDAP enumeration + X.509 parsing + identity-protocol CBOM integration
**Confidence:** HIGH (all integration points verified in-repo; ldap3 binary syntax verified via official docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — LDAP enumeration strategy**
- Search base: configurable `smime_search_base` defaulting to AD root DN derived from Kerberos realm (`QUIRK.LAB` → `DC=quirk,DC=lab`).
- Paging: `ldap3.SUBTREE` scope; `paged_size=500`; via `conn.extend.standard.paged_search(...)`.
- Attributes queried: BOTH `userCertificate` AND `userSMIMECertificate` (binary).
- Multi-valued: iterate every cert in the multi-valued attribute and classify independently.

**Area 2 — Certificate parsing + classification**
- Expired = MEDIUM; bumped to HIGH if also weak algo or sub-2048 RSA.
- DER first (RFC 4523); PEM fallback on parse failure.
- Reuse `quirk/util/weak_crypto.py` thresholds (SMIME-02 mandate).
- Reuse 50-entry NIST PQC table from CBOM Pass-1.

**Area 3 — Chaos lab `smime` profile**
- Image: `osixia/openldap:1.5.0` (pinned).
- Ports: `38900` (LDAP) + `38901` (LDAPS).
- One-shot `ldapadd` seed container with deterministic LDIF.
- Pre-built static certs in `quantum-chaos-enterprise-lab/smime/certs/` (intentionally weak — no rotation).
- Three users: alice (RSA-1024 SHA-1, HIGH), bob (RSA-1024 SHA-256, HIGH key-size), carol (RSA-2048 SHA-256, SAFE).

**Area 4 — CBOM + scoring wiring**
- `protocol="SMIME"` uppercase literal.
- CBOM Pass-1: emit algorithm component per discovered cert.
- CBOM Pass-2/3: add `"SMIME"` to identity skip-tuple (note: there is no named `IDENTITY_SKIP_PROTOCOLS` constant — see Pitfall 1).
- Three SCORE_WEIGHTS entries at 2.0 each, all under `identity_trust`: `identity_smime_weak_signing_count`, `identity_smime_expired_count`, `identity_smime_weak_key_count`.
- NO new top-level subscore.

**Cross-cutting**
- No IMAP, no mailbox content — privacy invariant.
- AST CI gate forbids `imaplib` and `email.*` imports in the scanner module.
- Path: `quirk/scanner/smime_scanner.py` (singular — correcting REQUIREMENTS.md drift).
- `tests/test_score_weights_invariant.py` is **owned by Phase 83** — Phase 79 must NOT edit it.

### Claude's Discretion
- Exact LDIF formatting and ldapadd container command shape.
- Whether to expose LDAPS port (38901) — plain LDAP on 38900 is mandatory; LDAPS is optional polish.
- Internal function decomposition within `smime_scanner.py`.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SMIME-01 | New `smime_scanner.py` queries `userCertificate` + `userSMIMECertificate` via ldap3 — no IMAP, no mailbox content | Reuse `ldap3.Connection` pattern from `kerberos_scanner._probe_ldap_anon` (anonymous bind); add `;binary` attribute syntax + `extend.standard.paged_search` |
| SMIME-02 | Parse DER via `cryptography.x509.load_der_x509_certificate`; classify via shared `quirk/util/weak_crypto.py` | `is_weak_cipher()` already covers SHA-1, MD5, DES, RC4. Mirror `saml_scanner._parse_cert_element` + `_classify_key_severity` |
| SMIME-03 | Additive ORM column `smime_scan_json TEXT` on `crypto_endpoints` | Append to `_IDENTITY_COLUMNS` tuple in `quirk/db.py:77`; add `Column(Text, nullable=True)` to `CryptoEndpoint` in `quirk/models.py:70` after `dnssec_scan_json` |
| SMIME-04 | Three new evidence counters routed to `identity_trust` weights @ 2.0 each | Add 3 entries to `SCORE_WEIGHTS` dict in `quirk/intelligence/scoring.py:18`; mirror `saml_weak_signing_count` accounting pattern in `evidence.py:160` |
| SMIME-05 | IdentityFinding emitted with `protocol="SMIME"`; React picks up via existing list rendering | Use `CryptoEndpoint(protocol="SMIME", ...)` — `saml_scanner.py:282` is the model (no new Pydantic) |
| SMIME-06 | CBOM Pass-1 emits `algorithm` components; Pass-2/3 skip-list excludes SMIME from TLS-style cert/protocol components | Add `elif ep.protocol == "SMIME":` branch in `builder.py` Pass-1 (after KERBEROS branch at line 454); append `"SMIME"` to both Pass-2 tuple (line 528) and Pass-3 tuple (line 612) |
| SMIME-07 | Chaos lab `smime` profile: OpenLDAP + 3 deterministic test users; oracle in `expected_results_v4.md` | New compose service block + seed container; `lab.sh` auto-derives via `_derive_all_profiles()` — no script edit |
| SMIME-08 | AST CI gate exits non-zero if `imaplib`/`email.*` imports appear in `smime_scanner.py` | Clone `tests/test_scan_error_gate.py` shape — `ast.walk` for `ast.Import`/`ast.ImportFrom`, match forbidden names |
</phase_requirements>

## Summary

Phase 79 is a **wiring phase**, not a greenfield phase. Every integration point already
has an established pattern in the codebase, and the locked decisions pre-resolve the
design choices that would otherwise need research. The research effort is mostly
**confirming exact line numbers, syntax, and shape** to remove friction from the
planner.

Key insights that emerged from reading the codebase:

1. **`IDENTITY_SKIP_PROTOCOLS` does not exist as a named constant** — CONTEXT.md and
   REQUIREMENTS.md both reference it, but `quirk/cbom/builder.py` uses **inline tuples**
   at Pass-2 (line 527-531) and Pass-3 (line 610-615) instead. The "skip-list edit"
   is two surgical tuple extensions. Plan must reflect this.
2. **`tests/test_chaos_lab_idempotency.py` does not exist yet** — it is created by
   Phase 82 per the ROADMAP. Phase 79 must produce an idempotent seed container,
   but cannot assert against a test that does not yet exist. The phase's success
   criterion ("seed container in `Exited (0)` on re-up") is verifiable manually
   via `./lab.sh up --profile smime` twice.
3. **ldap3 `;binary` semantics** — the `;binary` modifier is **only required for
   modify/add** operations per the ldap3 issue tracker; **for search** the library
   automatically returns binary attributes as bytes when retrieved via
   `raw_attributes`. The plan should use both `attributes=['userCertificate',
   'userSMIMECertificate']` AND read from `entry.raw_attributes` (NOT `.attributes`)
   to ensure DER bytes, not the formatted string representation.
4. **AD root DN derivation already exists** in `kerberos_scanner._derive_realm()`
   but only as the uppercased realm (`QUIRK.LAB`). Phase 79 needs a sibling helper
   `_realm_to_base_dn(realm)` that returns `DC=quirk,DC=lab` — trivial one-liner.

**Primary recommendation:** Treat this as a 6-task phase — (1) ORM column,
(2) scanner module, (3) AST gate test, (4) CBOM Pass-1/2/3 edits, (5) scoring +
evidence wiring, (6) chaos lab profile + oracle. Wave A1 (parallel-safe with
other Wave A phases) covers tasks 1, 2, 3, 4, 5 because they touch independent
files; task 6 (lab + oracle) is independent too. No internal ordering constraint
beyond "ORM column before scanner can write to it."

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LDAP cert enumeration | Scanner backend (Python) | — | Pure server-side network I/O via ldap3 |
| X.509 parsing / classification | Scanner backend | Shared util (`weak_crypto.py`) | Single-source classifier per SMIME-02 |
| Persistence | DB layer (SQLAlchemy + SQLite) | — | Append-only column; ALTER-TABLE-IF-MISSING via existing helper |
| Scoring weights | Intelligence layer | — | `SCORE_WEIGHTS` is the single locus |
| CBOM emission | CBOM builder | — | Pass-1/2/3 model |
| API surface | FastAPI (`/api/scan/latest`) | React Identity tab | Protocol-agnostic pickup — zero change needed |
| Chaos lab | Docker Compose + bash | `expected_results_v4.md` oracle | Compose is source of truth; lab.sh runtime-derives profiles |
| CI safety net | pytest AST gate | — | Static analysis on `quirk/scanner/smime_scanner.py` AST |

## Standard Stack

### Core (already pinned — zero new dependencies)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| `ldap3` | `>=2.9.1` | LDAP client + paged search | `pyproject.toml:45` (already in `[identity]` extra) [VERIFIED] |
| `cryptography` | (transitive) | X.509 DER/PEM parsing | Used by `saml_scanner.py:39` [VERIFIED] |
| SQLAlchemy | (existing) | ORM + ALTER TABLE helper | `quirk/db.py:107` [VERIFIED] |

**No `pip install` needed.** `ldap3` is already declared in the `[identity]` optional-dependencies extra (added in Phase 25 per CONTEXT).

### Documentation references

- ldap3 docs (2.10.2): paged_search wrapper [CITED: https://ldap3.readthedocs.io/en/latest/standard.html]
- ldap3 search tutorial [CITED: https://ldap3.readthedocs.io/en/latest/tutorial_searches.html]
- RFC 4523 — Lightweight Directory Access Protocol (LDAP) Schema Definitions for X.509 Certificates [CITED]
- ldap3 issue #280 — binary attribute add/modify needs `;binary` suffix [CITED: https://github.com/cannatag/ldap3/issues/280]

## Open Question Resolutions

### Q1. ldap3 binary attribute handling

**Verified pattern** (search-side; the codebase only reads, never writes):

```python
import ldap3

server = ldap3.Server(host, port=389, get_info=ldap3.ALL, connect_timeout=timeout)
conn = ldap3.Connection(server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout)
if not conn.bind():
    return  # graceful failure — same shape as kerberos_scanner._probe_ldap_anon

# Paged search — extend.standard wrapper handles cookie loop internally
entries = conn.extend.standard.paged_search(
    search_base=base_dn,
    search_filter='(objectClass=*)',
    search_scope=ldap3.SUBTREE,
    attributes=['userCertificate', 'userSMIMECertificate', 'cn', 'uid'],
    paged_size=500,
    generator=True,  # explicit; default is True in 2.x
)

for entry in entries:
    # entry is a dict; binary attrs live under entry['raw_attributes']
    raw = entry.get('raw_attributes', {})
    user_cn = entry.get('dn', '')
    for cert_bytes in raw.get('userSMIMECertificate', []):
        # cert_bytes is bytes (DER) — feed to load_der_x509_certificate
        ...
    for cert_bytes in raw.get('userCertificate', []):
        ...
```

**Key facts** [VERIFIED via ldap3 docs + issue #280]:
- For **search**, the `;binary` suffix is **not required** — ldap3 returns binary
  values from binary-syntax attributes via `entry['raw_attributes'][name]` as a list of
  bytes. The `;binary` suffix is only mandated for **modify/add** (cannatag/ldap3#280).
- `userCertificate` is RFC 4523 §5 defined with BER syntax — ldap3 schema
  detection recognizes it when `get_info=ldap3.ALL` is set.
- `raw_attributes` returns a `list[bytes]` even when multi-valued — iterate
  unconditionally.
- AD's 1000-row default cap requires paged_search; `paged_size=500` keeps us under
  the cap with room.

### Q2. AD root DN derivation from Kerberos realm

**Concrete helper** (place in `smime_scanner.py`, NOT in `kerberos_scanner.py` —
keeping it local avoids cross-scanner coupling):

```python
def _realm_to_base_dn(realm: str) -> str:
    """Convert Kerberos realm to AD root DN.

    Examples:
        QUIRK.LAB           -> DC=quirk,DC=lab
        CORP.EXAMPLE.COM    -> DC=corp,DC=example,DC=com
        SINGLELABEL         -> DC=singlelabel
        127.0.0.1           -> DC=127.0.0.1   (degenerate; caller should set
                                                smime_search_base explicitly)
    """
    if not realm:
        return ""
    return ",".join(f"DC={part.lower()}" for part in realm.split("."))
```

Note: `kerberos_scanner._derive_realm()` already produces the realm
(`quirk/scanner/kerberos_scanner.py:51-73`); the planner can chain the two.

### Q3. OpenLDAP LDIF user fixture format

**Verified LDIF** (binary attributes use `::` double-colon for base64):

```ldif
dn: cn=alice,dc=chaos,dc=local
objectClass: inetOrgPerson
objectClass: top
cn: alice
sn: Test
uid: alice
userSMIMECertificate;binary:: MIIBz...BASE64-DER-CERT-RSA-1024-SHA1...==

dn: cn=bob,dc=chaos,dc=local
objectClass: inetOrgPerson
objectClass: top
cn: bob
sn: Test
uid: bob
userSMIMECertificate;binary:: MIIBz...BASE64-DER-CERT-RSA-1024-SHA256...==

dn: cn=carol,dc=chaos,dc=local
objectClass: inetOrgPerson
objectClass: top
cn: carol
sn: Test
uid: carol
userSMIMECertificate;binary:: MIIDz...BASE64-DER-CERT-RSA-2048-SHA256...==
```

**Critical LDIF rules** [CITED: RFC 2849]:
- Binary attribute values use `::` (double colon) — single colon means UTF-8 string.
- The `;binary` suffix in LDIF is the schema-disambiguation marker for ASN.1
  values; `userSMIMECertificate` defaults to certificateExactMatch syntax so
  the `;binary` form is the conventional and broadly-portable LDIF form.
- One blank line separates entries.
- Long base64 lines may be wrapped with leading-space continuation; `ldapadd`
  unfolds them.

**Idempotent seeding via `ldapadd -c`:**

```bash
# `-c` = continuous: skip entries that already exist (exit code 0 on AlreadyExists)
ldapadd -x -H ldap://openldap-smime:389 -D "cn=admin,dc=chaos,dc=local" \
    -w admin -c -f /ldif/users.ldif
```

`ldapadd -c` returns 0 even when entries already exist (it logs `ldap_add:
Already exists (68)` and continues). This is the idempotency primitive. The
seed container should `exit 0` on the second `up`; verify by examining
`docker compose logs ldap-seed`.

### Q4. Cert pre-generation commands (deterministic)

Pre-build once, commit DER to `quantum-chaos-enterprise-lab/smime/certs/`:

```bash
# alice — RSA-1024 SHA-1 (HIGH: weak algo AND weak key)
openssl req -x509 -newkey rsa:1024 -sha1 -nodes \
    -days 365 \
    -keyout smime/certs/alice.key \
    -out smime/certs/alice.pem \
    -subj "/CN=alice/O=ChaosLab/C=US"
openssl x509 -in smime/certs/alice.pem -outform DER -out smime/certs/alice.der

# bob — RSA-1024 SHA-256 (HIGH key size only)
openssl req -x509 -newkey rsa:1024 -sha256 -nodes \
    -days 365 \
    -keyout smime/certs/bob.key \
    -out smime/certs/bob.pem \
    -subj "/CN=bob/O=ChaosLab/C=US"
openssl x509 -in smime/certs/bob.pem -outform DER -out smime/certs/bob.der

# carol — RSA-2048 SHA-256 (SAFE — no S/MIME finding)
openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
    -days 365 \
    -keyout smime/certs/carol.key \
    -out smime/certs/carol.pem \
    -subj "/CN=carol/O=ChaosLab/C=US"
openssl x509 -in smime/certs/carol.pem -outform DER -out smime/certs/carol.der

# Convert DER to base64 for LDIF embedding
base64 -i smime/certs/alice.der | tr -d '\n' > smime/certs/alice.b64
base64 -i smime/certs/bob.der   | tr -d '\n' > smime/certs/bob.b64
base64 -i smime/certs/carol.der | tr -d '\n' > smime/certs/carol.b64
```

**Pitfall on macOS:** `base64 -i ... -o ...` works on macOS; on GNU `base64`
the `-i` flag means "ignore non-alphabet" (different semantic). Use `base64 <
file` for portability.

**Deterministic seeding:** Because `-keyout` produces a fresh keypair each
run, you must **commit the generated certs** to the repo — the openssl
invocation is a one-time build step, not a container entrypoint. Otherwise
the LDIF would need to be rebuilt every up.

**OpenSSL 3.x note:** OpenSSL 3 marks SHA-1 as a "legacy" digest. `openssl
req ... -sha1` may emit a warning but **does succeed**. If a contributor
hits "unsupported" errors, add `-provider legacy` or use OpenSSL 1.1.x for
the cert-baking step. The certs themselves are static fixtures so the build
host's OpenSSL version is irrelevant to runtime.

### Q5. CBOM Pass-1 emission pattern

The pattern is **already established** in `quirk/cbom/builder.py`. Sketch:

```python
# In quirk/cbom/builder.py inside build_cbom(), after line 458 (KERBEROS branch):
elif ep.protocol == "SMIME":
    # SMIME: cert_pubkey_alg holds key algorithm (RSA, ECDSA);
    # cert_pubkey_size holds bit length. Mirror SAML pattern (line 449-452).
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry,
                            key_size=ep.cert_pubkey_size)
    # Also register the signature algorithm if surfaced via cert_sig_alg
    # (parity with how POSTGRESQL/RDS branch handles cert_sig_alg at line 520).
    if ep.cert_sig_alg:
        _register_algorithm(ep.cert_sig_alg, algo_registry)
```

`_register_algorithm()` (line 350) and `_make_algorithm_component()` (line 295)
handle bom_ref normalization, NIST PQC classification, and FIPS-140-3 status
property emission. The scanner just needs to populate
`cert_pubkey_alg`/`cert_pubkey_size`/`cert_sig_alg` on the CryptoEndpoint and
Pass-1 picks it up automatically.

**Pass-2 skip-list edit** (`builder.py:527-531`):

```python
if ep.protocol in (
    "SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "SMIME",  # +SMIME
    *DAR_SKIP_PROTOCOLS,
    *MOTION_PLAINTEXT_PROTOCOLS,
):
    continue
```

**Pass-3 skip-list edit** (`builder.py:610-615`):

```python
elif ep.protocol in (
    "JWT", "CONTAINER", "SOURCE", "AWS", "AZURE",
    "DNSSEC", "SAML", "KERBEROS", "SMIME",  # +SMIME
    *DAR_SKIP_PROTOCOLS,
    *MOTION_PLAINTEXT_PROTOCOLS,
):
    continue
```

### Q6. Evidence counter accessor pattern

`quirk/intelligence/evidence.py:160-166` shows the SAML pattern. Sketch for
SMIME — insert after the SAML branch (around line 167):

```python
elif proto == "SMIME":
    # Mirror SAML accounting (lines 160-166), split into three counters per D-04.
    _smime_alg     = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
    _smime_size    = getattr(ep, "cert_pubkey_size", None)
    _smime_sig_alg = str(getattr(ep, "cert_sig_alg", "") or "").upper()
    _smime_severity = str(getattr(ep, "severity", "") or "").upper()

    # Weak signing algorithm (SHA-1, MD5, etc. — anything is_weak_cipher rejects)
    if is_weak_cipher(_smime_sig_alg) or is_weak_cipher(_smime_alg):
        identity_smime_weak_signing_count += 1
    # Sub-2048 RSA = weak key
    if (_smime_alg.startswith("RSA")
            and isinstance(_smime_size, int)
            and _smime_size < 2048):
        identity_smime_weak_key_count += 1
    # Expired — surfaced via cert_not_after < ref_utc; reuse cert_expired_count
    # walk OR add a service_detail substring marker (e.g., "smime/expired") that
    # the scanner sets. Recommend the latter — keeps counters decoupled from
    # cert_not_after generic walk.
    if "smime/expired" in str(getattr(ep, "service_detail", "") or ""):
        identity_smime_expired_count += 1
```

And declare the three counters up at line ~89 alongside `saml_weak_signing_count`:

```python
identity_smime_weak_signing_count = 0
identity_smime_expired_count = 0
identity_smime_weak_key_count = 0
```

Emit them in the returned dict (around line 340 next to `saml_weak_signing_count`):

```python
"identity_smime_weak_signing_count": identity_smime_weak_signing_count,
"identity_smime_expired_count":      identity_smime_expired_count,
"identity_smime_weak_key_count":     identity_smime_weak_key_count,
"identity_smime_weak_signing_ratio": round(identity_smime_weak_signing_count / total_endpoints, 4) if total_endpoints else 0.0,
"identity_smime_expired_ratio":      round(identity_smime_expired_count / total_endpoints, 4) if total_endpoints else 0.0,
"identity_smime_weak_key_ratio":     round(identity_smime_weak_key_count / total_endpoints, 4) if total_endpoints else 0.0,
```

**Scoring wiring** in `quirk/intelligence/scoring.py`:

```python
# At line 31 (inside SCORE_WEIGHTS dict, after identity_dnssec_weak_algo_ratio):
"identity_smime_weak_signing_count": 2.0,
"identity_smime_expired_count":      2.0,
"identity_smime_weak_key_count":     2.0,
```

And add three lines to the `identity_trust_impacts` list (around line 175-183):

```python
("Weak S/MIME signing", -_ratio(smime_weak_signing_count, denom) * w["identity_smime_weak_signing_count"]),
("Expired S/MIME certs", -_ratio(smime_expired_count, denom) * w["identity_smime_expired_count"]),
("Weak S/MIME key", -_ratio(smime_weak_key_count, denom) * w["identity_smime_weak_key_count"]),
```

with three local extractions above:

```python
smime_weak_signing_count = max(0, _as_int(evidence.get("identity_smime_weak_signing_count", 0)))
smime_expired_count = max(0, _as_int(evidence.get("identity_smime_expired_count", 0)))
smime_weak_key_count = max(0, _as_int(evidence.get("identity_smime_weak_key_count", 0)))
```

**CONTEXT D-04 nomenclature note:** the locked weight keys use the `_count`
suffix (e.g., `identity_smime_weak_signing_count`), unlike the existing
identity_trust weights which use `_ratio`. The CONTEXT is the source of truth
— honor it. The existing weights are named `_ratio` for historical reasons
(they're applied to ratios computed inline), but the dict key is just a
string. Three new entries with `_count` suffix at weight `2.0` is exactly
what CONTEXT D-04 mandates.

### Q7. AST gate scope

**Forbidden module names** (every Python module that touches IMAP/email envelopes):

| Module/Symbol | Source |
|---------------|--------|
| `imaplib` | stdlib IMAP client |
| `email.message` | stdlib email object |
| `email.header` | stdlib header parsing |
| `email.parser` | stdlib email parser |
| `email.policy` | stdlib email parsing policy |
| `email.utils` | stdlib email helpers (addresslib, parsedate, etc.) |
| `email.iterators` | stdlib message walking |
| `email.generator` | stdlib message emission |
| `smtplib` | stdlib SMTP client (preventative — outbound mail) |
| `email_scanner` (quirk's own module) | already handles motion email scope |

**Allowed:** `from email import *` is permitted **only** if the symbol
imported is the bare `email` package alone with no submodule access AND
nothing in the module references it. To keep the gate strict and simple,
forbid **all** `email.*` and any bare `email` import too. The scanner needs
ZERO mail-related imports; `cryptography.x509`, `ldap3`, and stdlib
`base64`/`json`/`datetime`/`logging` are sufficient.

**AST gate test sketch** — clone of `tests/test_scan_error_gate.py` shape:

```python
# tests/test_smime_ast_gate.py
"""Phase 79 SMIME-08: AST CI gate forbidding IMAP/email envelope imports
in quirk/scanner/smime_scanner.py.

Mechanism: parse the module via ast.parse, walk every ast.Import and
ast.ImportFrom node, fail the test if any name in FORBIDDEN_ROOTS appears
as either an Import alias or an ImportFrom module.

Rationale: privacy invariant (SMIME-08). The scanner reads LDAP cert
attributes only; mailbox/envelope content is never touched. The gate is
preventative for future drift.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCANNER_FILE = PROJECT_ROOT / "quirk" / "scanner" / "smime_scanner.py"

FORBIDDEN_ROOTS: frozenset[str] = frozenset({
    "imaplib",
    "smtplib",
    "email",          # bans bare `import email` AND `from email import x`
})


def _is_forbidden(name: str) -> bool:
    """True iff name matches a forbidden root or any dotted descendant."""
    root = name.split(".", 1)[0]
    return root in FORBIDDEN_ROOTS


def test_smime_scanner_has_no_imap_or_email_imports() -> None:
    assert SCANNER_FILE.exists(), f"missing {SCANNER_FILE}"
    source = SCANNER_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SCANNER_FILE))

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden(alias.name):
                    violations.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if _is_forbidden(mod):
                violations.append((node.lineno, f"from {mod} import ..."))

    if violations:
        formatted = "\n".join(f"  line {ln}: {msg}" for ln, msg in violations)
        pytest.fail(
            "SMIME-08 privacy invariant violation — IMAP/email envelope "
            f"imports forbidden in {SCANNER_FILE.name}:\n{formatted}"
        )


def test_gate_catches_synthetic_bypass(tmp_path: pathlib.Path) -> None:
    """Self-test: synthetic source with `import imaplib` must be flagged."""
    synthetic = "import imaplib\nfrom email.message import Message\n"
    tree = ast.parse(synthetic)

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden(alias.name):
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if _is_forbidden(mod):
                violations.append(mod)

    assert violations == ["imaplib", "email.message"], (
        f"Gate self-test broken — expected 2 violations, got: {violations}"
    )
```

This is a **deliberately stricter** gate than the Phase 59 model (which
walks multiple directories): it targets exactly one file. Stricter is fine
here because SMIME-08 is preventative and the scope is one module.

### Q8. OpenLDAP TLS in chaos lab (port 38901)

**LDAPS is OPTIONAL for Phase 79.** Plain LDAP on 38900 is the mandatory
minimum — the scanner currently uses anonymous bind on plain LDAP
(`kerberos_scanner._probe_ldap_anon` uses port 389). The LDAPS port can be
deferred or omitted entirely without breaking SMIME-07.

**If LDAPS is desired:** reuse the existing `./certs/modern.{crt,key}` and
`./certs/ca.crt` bundle that the `ldaps` profile uses (verified in
docker-compose.yml:751-755). This sidesteps the macOS bind-mount chown issue
that forced the `ldaps` profile to switch from osixia to bitnamilegacy
(see expected_results_v4.md:253).

**Recommendation:** Ship plain LDAP only on 38900 for Phase 79. Document
"LDAPS deferred — out of phase scope" in the oracle. This avoids the macOS
osixia chown issue entirely.

**Image-pin gate (CHAOS-05):** `osixia/openldap:1.5.0` is the pinned tag —
matches the existing `openldap` service at docker-compose.yml:451. CHAOS-05
gate is already satisfied by Phase 82; no new exemption needed.

### Q9. `expected_results_v4.md` template — smime oracle text

Drop in after the `kerberos` profile section (~line 354, before `database`):

```markdown
## Profile: smime

*OpenLDAP pre-seeded with three test users carrying S/MIME signing certs of
varying strength in `userSMIMECertificate`. No TLS — plain LDAP on 38900
only. LDAPS deferred to a future phase.*

```bash
PROFILE_ARGS="--profile smime" ./lab.sh up
```

| User | Cert | Algorithm | Key Size | Expected Finding | Severity |
|------|------|-----------|----------|-----------------|----------|
| alice | RSA-1024 / SHA-1 | RSA | 1024 | Weak S/MIME signing (SHA-1) + Weak S/MIME key (RSA<2048) | HIGH |
| bob   | RSA-1024 / SHA-256 | RSA | 1024 | Weak S/MIME key (RSA<2048) | HIGH |
| carol | RSA-2048 / SHA-256 | RSA | 2048 | — (SAFE; no finding emitted) | — |

**Scanner validation command:**
```
docker compose --profile smime up -d && sleep 10 && \
  quirk scan --targets ldap://localhost:38900
```

**Expected:** S/MIME scanner returns ≥ 2 HIGH findings (one for alice, one
for bob). carol produces no S/MIME finding. Findings appear in the Identity
tab (`protocol="SMIME"`). `smime_scan_json` column populated on the resulting
ScanSession.

**Ports:** 38900/tcp (service: openldap-smime), seed container exits 0.

**Idempotency:** `./lab.sh up --profile smime` twice in succession — the
seed container's second run logs `ldap_add: Already exists (68)` for each
entry and exits 0 (verified via `ldapadd -c` flag).

---
```

## Architecture Patterns

### Recommended Project Structure (additive only)

```
quirk/scanner/
└── smime_scanner.py                    # NEW — singular per codebase convention

tests/
├── test_smime_scanner.py              # NEW — unit tests
├── test_smime_no_envelope_leak.py     # NEW — SMIME-04 IMAP-envelope absence
└── test_smime_ast_gate.py             # NEW — SMIME-08 AST CI gate

quantum-chaos-enterprise-lab/smime/
├── certs/
│   ├── alice.der
│   ├── bob.der
│   ├── carol.der
│   ├── alice.b64                       # base64 DER for LDIF embedding
│   ├── bob.b64
│   └── carol.b64
├── ldif/
│   └── users.ldif                     # build-time generated from .b64 files
└── seed/
    └── Dockerfile                     # one-shot ldapadd container
```

### Pattern 1: Scanner entry point shape

Mirror `scan_kerberos_targets` and `scan_saml_targets` — single `scan_smime_targets(targets, cfg, session_start, logger)` callable returning `list[CryptoEndpoint]`.

```python
def scan_smime_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    session_start=None,
    *,
    smime_search_base: str | None = None,
) -> list:
    """Enumerate S/MIME certs from LDAP userCertificate/userSMIMECertificate.

    Returns list[CryptoEndpoint] — one per discovered cert.
    Graceful degradation: returns [] if ldap3 missing or all binds fail.
    NO IMAP. NO mailbox content.
    """
    ...
```

### Pattern 2: Per-cert CryptoEndpoint emission

One endpoint per (user, cert) pair. Mirror `saml_scanner._parse_saml_metadata`
(lines 251-291). `service_detail` carries the breadcrumb:

```python
ep = CryptoEndpoint(
    host=target,                          # ldap server host
    port=port,                            # 389 or 38900
    protocol="SMIME",
    cert_pubkey_alg=key_alg,              # "RSA"
    cert_pubkey_size=key_bits,            # 1024
    cert_sig_alg=sig_alg_oid_or_name,     # e.g., "sha1WithRSAEncryption"
    cert_not_before=cert.not_valid_before_utc,
    cert_not_after=cert.not_valid_after_utc,
    cert_subject=str(cert.subject.rfc4514_string()),
    cert_issuer=str(cert.issuer.rfc4514_string()),
    severity=severity,                     # "HIGH"/"MEDIUM"/None
    service_detail=f"smime|user={user_cn}|attr={attr_name}|serial={cert.serial_number:x}"
                   + ("|expired" if is_expired else ""),
    smime_scan_json=json.dumps(scan_dict),
    scanned_at=now,
)
```

The `|expired` suffix in service_detail is the marker the evidence counter reads.

### Anti-Patterns to Avoid

- **Do not** import `email.*` or `imaplib` anywhere in `smime_scanner.py` — the
  AST gate will fail CI.
- **Do not** add a top-level subscore for SMIME — CONTEXT D-04 locks routing
  to existing `identity_trust`.
- **Do not** edit `tests/test_score_weights_invariant.py` — Phase 83 owns
  the SCORE_WEIGHTS sum bump after both Phase 79 (SMIME, +3 weights) and
  Phase 80 (AD CS, +1 weight) have landed. Phase 79 will temporarily break
  this invariant test; that is **by design** and Phase 83 closes it.
- **Do not** reuse the existing `openldap` service from the `identity` profile —
  it has a different DN (`dc=chaos,dc=local`) and is already busy with mTLS
  workflows. The `smime` profile gets a new dedicated container.
- **Do not** name the scanner module `quirk/scanners/` (plural) — the codebase
  uses `quirk/scanner/` (singular). REQUIREMENTS.md has the drift; CONTEXT
  D-cross-cutting explicitly corrects it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LDAP paging cookie loop | Manual cookie + re-search loop | `conn.extend.standard.paged_search(...)` | RFC 2696 edge cases (server-side cookie expiry, cookie length limits) |
| Base64 cert decode | Manual whitespace stripping | `cryptography.x509.load_der_x509_certificate` after `base64.b64decode` — and even DER loading directly when `raw_attributes` returns bytes | DER is already decoded; only PEM fallback needs base64 |
| X.509 parsing | `pyasn1` directly | `cryptography.x509` | Battle-tested; OID resolution; expiry helpers |
| Weak-cipher detection | New tokens | `quirk/util/weak_crypto.is_weak_cipher` | SMIME-02 mandate; single source of truth |
| LDIF seeding idempotency | Custom check-then-add | `ldapadd -c` | Native AlreadyExists handling, exit 0 |
| AD root DN parsing | Configurable per-deployment guessing | `_realm_to_base_dn(realm)` derived from Kerberos | One canonical formula |

## Runtime State Inventory

Not applicable — Phase 79 is **purely additive**. No rename, no refactor, no
migration. New file, new column, new test files, new docker compose service block.

**Stored data:** None — `smime_scan_json` is a new column; existing rows
default to NULL.

**Live service config:** None — chaos lab is rebuilt from compose on every up.

**OS-registered state:** None.

**Secrets/env vars:** None.

**Build artifacts:** The smime cert fixtures (`alice.der`, `bob.der`, `carol.der`)
must be committed. They are one-time build artifacts whose generation
command is preserved in `quantum-chaos-enterprise-lab/smime/certs/README.md`
(create as part of the phase).

## Common Pitfalls

### Pitfall 1: `IDENTITY_SKIP_PROTOCOLS` named constant doesn't exist

**What goes wrong:** Plan calls for "appending SMIME to `IDENTITY_SKIP_PROTOCOLS`
in builder.py" — searching for that symbol returns zero hits in code (only
references are in CONTEXT.md and this RESEARCH.md).

**Root cause:** The Pass-2 and Pass-3 skip-lists are **inline tuples** at
`builder.py:527-531` and `builder.py:610-615`. They share a `DAR_SKIP_PROTOCOLS`
frozenset for the DAR portion but identity protocols (SSH, KERBEROS, SAML,
DNSSEC) are inlined directly.

**Prevention:** Plan must specify "extend the inline tuple at line 528 AND
the inline tuple at line 612 with `"SMIME"`. Do NOT search for a constant
named `IDENTITY_SKIP_PROTOCOLS` — it does not exist."

**Optional improvement (out of scope but worth flagging):** A follow-up phase
could promote the inline tuple to a named `IDENTITY_SKIP_PROTOCOLS` frozenset
for symmetry with `DAR_SKIP_PROTOCOLS`. Not Phase 79's job.

### Pitfall 2: ldap3 `attributes=` vs `raw_attributes` access

**What goes wrong:** Calling `entry['userCertificate']` (or `.userCertificate` on
the Reader API) returns the **formatted** value — for binary attrs this is
typically the base64-encoded string. Feeding that to `load_der_x509_certificate`
crashes with `ValueError: unable to load certificate`.

**Prevention:** Use `entry['raw_attributes']['userCertificate']` (lowercase
the key first — AD returns the schema-canonical capitalization but ldap3
preserves it). Always iterate; always type-check it's bytes.

```python
raw = entry.get('raw_attributes', {})
# AD returns capitalized; some servers return lowercased
for key in ('userCertificate', 'usercertificate', 'userSMIMECertificate', 'usersmimecertificate'):
    for cert_bytes in raw.get(key, []):
        if isinstance(cert_bytes, (bytes, bytearray)):
            ...
```

### Pitfall 3: SCORE_WEIGHTS invariant test will fail until Phase 83

**What goes wrong:** Adding three new weight entries (sum changes from 261.0
to 267.0) breaks `tests/test_score_weights_invariant.py` immediately upon
Phase 79 merge.

**Root cause:** Phase 83 owns the invariant test bump per CLEAN-01 success
criterion #1.

**Prevention:** Document in the Phase 79 commit that this is **expected**.
Phase 82 and 83 may need to merge with a `-x` or `xfail` marker for the
intermediate state. Alternatively: stage the merge order so Phase 83 lands
last and updates the test once.

**Recommendation:** Phase 79's plan should explicitly add an item: "DO NOT
edit `tests/test_score_weights_invariant.py` — Phase 83 owns it. Expect the
test to break locally; it is closed by the time the v4.10 milestone ships."

### Pitfall 4: macOS osixia chown failure

**What goes wrong:** `osixia/openldap:1.5.0` chowns its bind-mounted cert
directory at startup. On macOS Docker Desktop, bind-mounts are read-only
host paths — chown fails with EROFS and the container exits.

**Prevention:** Phase 79 ships plain LDAP only (no TLS, no cert bind-mount).
The fixtures bind-mount is `./smime/ldif/users.ldif:/ldif/users.ldif:ro` —
the **seed container** uses this, not the openldap container itself. The
openldap container has no bind-mount, so chown is irrelevant.

If a future phase adds LDAPS to the smime profile, switch to
`bitnamilegacy/openldap:2.6.10-debian-12-r4` (see ldaps profile precedent).

### Pitfall 5: REQUIREMENTS.md path drift (`quirk/scanners/` plural)

**What goes wrong:** REQUIREMENTS.md SMIME-01 says
`quirk/scanners/smime_scanner.py` (plural). CONTEXT.md cross-cutting decision
corrects this to `quirk/scanner/` (singular).

**Prevention:** Always check the existing path:
```bash
ls /Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/scanner/
# returns kerberos_scanner.py, saml_scanner.py, ... — singular is correct
```

The AST gate test must also use the singular path. The CBOM AST gate
(`tests/test_scan_error_gate.py:28-32`) walks `quirk/scanner/` (singular) —
parity confirmed.

### Pitfall 6: ldap3 ALL_ATTRIBUTES vs explicit list

**What goes wrong:** Using `attributes=ldap3.ALL_ATTRIBUTES` pulls every attribute
from every entry — wasteful on large directories, and `userCertificate` may
not be returned by some AD installations unless explicitly requested.

**Prevention:** Always pass an explicit attribute list:
`attributes=['userCertificate', 'userSMIMECertificate', 'cn', 'uid', 'sn']`.

### Pitfall 7: Search filter scope

**What goes wrong:** `search_filter='(objectClass=*)'` returns every object
in the directory (containers, OUs, computers, the Domain root itself). Most
will lack cert attributes — wasted work.

**Prevention:** Narrow the filter to user objects:
`search_filter='(&(objectClass=person)(|(userCertificate=*)(userSMIMECertificate=*)))'`.
The `=*` presence-test filters server-side. On AD, `(objectCategory=user)`
is faster; for OpenLDAP, `(objectClass=inetOrgPerson)`. Use the AD form by
default; document the OpenLDAP form for lab use.

**Recommendation:** Two filter strings, selected based on `cfg.scan.smime_ldap_dialect`
(default: `ad`). The chaos lab uses OpenLDAP and needs the inetOrgPerson form.

### Pitfall 8: Cert expiry semantics under MEDIUM-vs-HIGH bump

**What goes wrong:** Two findings emitted for one expired+weak cert if
classification logic is naive — once for "weak signing" (HIGH) and once for
"expired" (MEDIUM). Score is double-counted.

**Prevention:** Emit ONE CryptoEndpoint per cert with the strongest severity.
Add expiry as a service_detail breadcrumb (`|expired`), not a separate
endpoint. The evidence counter reads the substring marker to increment
`identity_smime_expired_count` separately from `identity_smime_weak_signing_count`,
but the **endpoint count** for `total_endpoints` is one. This keeps the
ratio denominator honest.

## Code Examples

### Full scanner skeleton (illustrative — for the planner's task author)

```python
"""S/MIME LDAP discovery scanner — Phase 79.

Privacy invariant: queries userCertificate / userSMIMECertificate LDAP
attributes ONLY. No IMAP. No mailbox content. The SMIME-08 AST CI gate
enforces this by forbidding imaplib / email.* imports in this file.
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

try:
    import ldap3
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False

from cryptography.x509 import (
    load_der_x509_certificate,
    load_pem_x509_certificate,
)
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from quirk.models import CryptoEndpoint
from quirk.util.weak_crypto import is_weak_cipher

logger = logging.getLogger(__name__)


def _realm_to_base_dn(realm: str) -> str:
    """QUIRK.LAB -> DC=quirk,DC=lab"""
    if not realm:
        return ""
    return ",".join(f"DC={p.lower()}" for p in realm.split("."))


def _classify_severity(
    key_alg: str,
    key_bits: int | None,
    sig_alg: str,
    is_expired: bool,
) -> str | None:
    """Return HIGH / MEDIUM / None per CONTEXT D-Area-2."""
    weak_sig = is_weak_cipher(sig_alg) or is_weak_cipher(key_alg)
    weak_key = key_alg.upper() == "RSA" and (key_bits is not None and key_bits < 2048)
    if weak_sig or weak_key:
        return "HIGH"
    if is_expired:
        return "MEDIUM"
    return None


def _parse_cert(der_or_pem: bytes) -> dict[str, Any] | None:
    """DER first, PEM fallback (CONTEXT Area-2)."""
    cert = None
    try:
        cert = load_der_x509_certificate(der_or_pem)
    except Exception:
        try:
            cert = load_pem_x509_certificate(der_or_pem)
        except Exception:
            return None
    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        key_alg, key_bits = "RSA", pub.key_size
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        key_alg, key_bits = "ECDSA", pub.key_size
    else:
        key_alg, key_bits = "UNKNOWN", None
    return {
        "key_alg": key_alg,
        "key_bits": key_bits,
        "sig_alg": cert.signature_algorithm_oid._name,
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_before": cert.not_valid_before_utc,
        "not_after": cert.not_valid_after_utc,
        "serial": format(cert.serial_number, 'x'),
    }


def scan_smime_targets(
    targets: list[str],
    timeout: int = 10,
    logger=None,
    session_start=None,
    *,
    smime_search_base: str | None = None,
) -> list[CryptoEndpoint]:
    if not LDAP3_AVAILABLE:
        return []
    log = logger or logging.getLogger(__name__)
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: list[CryptoEndpoint] = []

    for target in targets:
        # Parse target: "ldap://host:port" or "host"
        host, port = _parse_target(target)  # implementation left to task author

        # Derive base DN
        base_dn = smime_search_base or _realm_to_base_dn(_derive_realm_from_host(host))
        if not base_dn:
            log.warning("SMIME: cannot derive base DN for %s; skipping", host)
            continue

        try:
            server = ldap3.Server(host, port=port, get_info=ldap3.ALL,
                                   connect_timeout=timeout)
            conn = ldap3.Connection(server, authentication=ldap3.ANONYMOUS,
                                     receive_timeout=timeout)
            if not conn.bind():
                log.warning("SMIME: anon bind rejected on %s: %s",
                            host, conn.last_error)
                continue
        except Exception as exc:
            log.warning("SMIME: connection failed for %s: %s", host, exc)
            continue

        try:
            entries = conn.extend.standard.paged_search(
                search_base=base_dn,
                search_filter='(&(objectClass=inetOrgPerson)'
                              '(|(userCertificate=*)(userSMIMECertificate=*)))',
                search_scope=ldap3.SUBTREE,
                attributes=['userCertificate', 'userSMIMECertificate',
                            'cn', 'uid'],
                paged_size=500,
                generator=True,
            )
            for entry in entries:
                dn = entry.get('dn', '')
                user_cn = (entry.get('attributes', {}).get('cn', [None]) or [None])[0]
                raw = entry.get('raw_attributes', {})
                for attr_name in ('userCertificate', 'usercertificate',
                                  'userSMIMECertificate', 'usersmimecertificate'):
                    for cert_bytes in raw.get(attr_name, []):
                        if not isinstance(cert_bytes, (bytes, bytearray)):
                            continue
                        info = _parse_cert(bytes(cert_bytes))
                        if info is None:
                            continue
                        is_expired = info['not_after'].replace(tzinfo=None) < now
                        severity = _classify_severity(
                            info['key_alg'], info['key_bits'],
                            info['sig_alg'], is_expired
                        )
                        scan_dict = {
                            "user_dn": dn,
                            "user_cn": user_cn,
                            "attr": attr_name,
                            "key_alg": info['key_alg'],
                            "key_bits": info['key_bits'],
                            "sig_alg": info['sig_alg'],
                            "serial": info['serial'],
                            "expired": is_expired,
                            "severity": severity,
                        }
                        sd_parts = [f"smime|user={user_cn}|attr={attr_name}",
                                    f"serial={info['serial']}"]
                        if is_expired:
                            sd_parts.append("expired")
                        ep = CryptoEndpoint(
                            host=host,
                            port=port,
                            protocol="SMIME",
                            cert_pubkey_alg=info['key_alg'],
                            cert_pubkey_size=info['key_bits'],
                            cert_sig_alg=info['sig_alg'],
                            cert_subject=info['subject'],
                            cert_issuer=info['issuer'],
                            cert_not_before=info['not_before'].replace(tzinfo=None),
                            cert_not_after=info['not_after'].replace(tzinfo=None),
                            severity=severity,
                            service_detail="|".join(sd_parts),
                            smime_scan_json=json.dumps(scan_dict),
                            scanned_at=now,
                        )
                        results.append(ep)
        finally:
            try:
                conn.unbind()
            except Exception:
                pass

    return results
```

### `quantum-chaos-enterprise-lab/docker-compose.yml` additions

```yaml
  # =========================
  # Phase 79 — SMIME PROFILE (profile: smime)
  # OpenLDAP pre-seeded with 3 test users carrying weak/safe S/MIME certs.
  # No TLS — plain LDAP only on 38900. LDAPS deferred.
  # =========================
  openldap-smime:
    image: osixia/openldap:1.5.0
    profiles: ["smime"]
    environment:
      LDAP_ORGANISATION: "ChaosLab SMIME"
      LDAP_DOMAIN: "chaos.local"
      LDAP_ADMIN_PASSWORD: "admin"
    ports:
      - "38900:389"
    restart: unless-stopped

  openldap-smime-seed:
    image: osixia/openldap:1.5.0
    profiles: ["smime"]
    depends_on:
      - openldap-smime
    volumes:
      - ./smime/ldif/users.ldif:/ldif/users.ldif:ro
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        # Wait for openldap-smime to be ready
        for i in $$(seq 1 30); do
          ldapwhoami -x -H ldap://openldap-smime:389 \
            -D "cn=admin,dc=chaos,dc=local" -w admin >/dev/null 2>&1 \
            && break
          sleep 2
        done
        # -c = continue on AlreadyExists (idempotent re-up)
        ldapadd -x -H ldap://openldap-smime:389 \
          -D "cn=admin,dc=chaos,dc=local" -w admin \
          -c -f /ldif/users.ldif
        # Always exit 0 — idempotency contract
        exit 0
    restart: "no"
```

## State of the Art

| Old Approach | Current Approach | Why |
|--------------|------------------|-----|
| Custom LDAP socket protocol | `ldap3` library | Pure-Python, no OpenLDAP libldap required, handles AD quirks |
| Manual base64 + DER walk | `cryptography.x509.load_der_x509_certificate` | OID resolution, expiry helpers, attestation extraction |
| Per-scanner weak-token sets | `quirk/util/weak_crypto.is_weak_cipher` | Phase 73 INTEL-02 consolidation; single source of truth |
| `ldapsearch` CLI | `conn.extend.standard.paged_search` | Generator-based, RFC 2696 cookie loop handled |
| `xenial-image openldap` | `osixia/openldap:1.5.0` (pinned) | CHAOS-05 image-pinning gate; matches existing identity profile |

**Deprecated/outdated:**
- `python-ldap` library — C-extension based, builds against `libldap2-dev`; ldap3 is the modern pure-Python replacement [VERIFIED].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `tests/test_chaos_lab_idempotency.py` is created by Phase 82, not Phase 79 | Summary insight 2 | If it exists earlier, Phase 79 plan should add an entry for the smime profile to its parametrize list — minor edit |
| A2 | The `cfg.scan` config block already supports scanner-specific kwargs (precedent: `allow_internal_targets` for SAML) | Open Q1 | If config plumbing is missing, the `smime_search_base` kwarg can default-derive from realm and still work — config is convenience, not blocker |
| A3 | The `_realm_to_base_dn` helper is local to `smime_scanner.py` | Open Q2 | If a future scanner needs it, refactor into `quirk/util/ldap_dn.py` then — premature now |
| A4 | OpenSSL on the contributor's machine can produce SHA-1-signed certs without `-provider legacy` | Open Q4 | If OpenSSL 3 strict mode fails, add legacy provider flag — documented mitigation in cert README |
| A5 | The scanner can read `cfg.scan.smime_ldap_dialect` to switch AD vs OpenLDAP filter | Pitfall 7 | If config plumbing isn't extensible, hardcode to OpenLDAP-friendly `(|(objectClass=person)(objectClass=inetOrgPerson))` and accept slight AD inefficiency |

## Open Questions

1. **Should the scanner expose a CLI flag for an explicit base DN override?**
   - What we know: CONTEXT D-Area-1 says "configurable `smime_search_base`".
   - What's unclear: Whether this is a `cfg.scan.smime_search_base` config key, a CLI `--smime-base-dn DC=...` flag, or both.
   - Recommendation: Mirror the SAML `allow_internal_targets` pattern — config key, plumbed via the scan job dispatcher. CLI flag is nice-to-have for v4.11.

2. **Where should the smime cert generation script live?**
   - What we know: Certs are static, committed to repo.
   - What's unclear: Whether the openssl regeneration script lives in `quantum-chaos-enterprise-lab/smime/certs/regen.sh` (recommended) or in scripts/ at repo root.
   - Recommendation: `quantum-chaos-enterprise-lab/smime/certs/regen.sh` — co-located with what it produces.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `ldap3` Python pkg | Scanner runtime | ✓ (in `[identity]` extra) | `>=2.9.1` | Graceful: return [] if ImportError |
| `cryptography` Python pkg | Cert parsing | ✓ (transitive) | (existing) | None — hard requirement |
| `openssl` CLI | One-time cert baking | ✓ (assumed; standard dev tool) | 1.1+ | OpenSSL 3 needs `-provider legacy` for SHA-1 |
| Docker + Docker Compose | Chaos lab | ✓ (existing chaos lab dependency) | (existing) | None |
| `ldapadd` (in osixia image) | Seed container | ✓ (bundled in osixia/openldap) | (existing) | None |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in project) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_smime_scanner.py tests/test_smime_ast_gate.py tests/test_smime_no_envelope_leak.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SMIME-01 | LDAP search via ldap3 | unit | `pytest tests/test_smime_scanner.py::test_scan_returns_endpoints_for_each_cert -x` | ❌ Wave 0 |
| SMIME-02 | DER/PEM parse + weak-crypto classify | unit | `pytest tests/test_smime_scanner.py::test_weak_signing_classification -x` | ❌ Wave 0 |
| SMIME-03 | ORM column additive migration | unit | `pytest tests/test_init_db_idempotent.py -x` (existing — must continue to pass) | ✓ |
| SMIME-04 | Three counters in evidence + scoring | unit | `pytest tests/test_smime_scanner.py::test_evidence_counters_emit -x` | ❌ Wave 0 |
| SMIME-05 | `protocol="SMIME"` IdentityFinding | unit | `pytest tests/test_smime_scanner.py::test_identityfinding_emission -x` | ❌ Wave 0 |
| SMIME-06 | CBOM Pass-1 algorithm component | unit | `pytest tests/test_smime_scanner.py::test_cbom_algorithm_component -x` | ❌ Wave 0 |
| SMIME-07 | Chaos lab profile + oracle | smoke | Manual: `./lab.sh up --profile smime && quirk scan --targets ldap://localhost:38900` | ❌ Wave 0 |
| SMIME-08 | AST CI gate | unit | `pytest tests/test_smime_ast_gate.py -x` | ❌ Wave 0 |
| SMIME-04 privacy | No IMAP envelope field in output | unit | `pytest tests/test_smime_no_envelope_leak.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_smime_*.py -x` (~1 second)
- **Per wave merge:** `pytest tests/ -x` (full suite — note: SCORE_WEIGHTS invariant **expected to break** until Phase 83 — see Pitfall 3)
- **Phase gate:** Full suite green **except** `test_score_weights_invariant.py` (documented xfail until Phase 83)

### Wave 0 Gaps

- [ ] `tests/test_smime_scanner.py` — unit tests for the scanner module
- [ ] `tests/test_smime_no_envelope_leak.py` — SMIME-04 IMAP-envelope absence test
- [ ] `tests/test_smime_ast_gate.py` — SMIME-08 AST CI gate
- [ ] `quantum-chaos-enterprise-lab/smime/certs/{alice,bob,carol}.der` — fixture certs (one-time openssl bake)
- [ ] `quantum-chaos-enterprise-lab/smime/ldif/users.ldif` — generated from .der files

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Anonymous LDAP bind only — no credentials handled |
| V3 Session Management | no | No sessions — stateless scan |
| V4 Access Control | partial | Scanner respects target's anon-bind ACL; degrades gracefully on bind reject |
| V5 Input Validation | yes | DER bytes validated via `cryptography.x509.load_der_x509_certificate` (will raise on malformed input — graceful skip) |
| V6 Cryptography | yes | NO hand-rolled crypto. `cryptography` package + `weak_crypto.is_weak_cipher` reused |
| V9 Communications | partial | LDAP plaintext by default; LDAPS deferred. Acceptable: lab-only profile, no production traffic |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mailbox content leak (SMIME-04) | Information Disclosure | AST gate forbids `imaplib`/`email.*` imports; `test_smime_no_envelope_leak.py` asserts envelope fields absent from `smime_scan_json` |
| Malformed cert DoS | Denial of Service | `load_der_x509_certificate` raises on malformed; scanner catches and skips |
| LDAP injection in filter | Injection | Filter string is hardcoded; no user-controlled string interpolation |
| Credential leak via scan_error | Information Disclosure | Phase 59 LEAK-03 AST gate already enforces `safe_str()` on all `scan_error` writes — new scanner inherits the constraint |
| SSRF via target URL | SSRF | Anon-bind LDAP only; no follow-redirect surface |

## File Touch List

| File | Action | Rationale |
|------|--------|-----------|
| `quirk/models.py` | Add `smime_scan_json = Column(Text, nullable=True)` after line 70 (`dnssec_scan_json`) | SMIME-03 ORM column |
| `quirk/db.py` | Append `("smime_scan_json", "TEXT"),` to `_IDENTITY_COLUMNS` tuple at line 77 | SMIME-03 ALTER-TABLE-IF-MISSING |
| `quirk/scanner/smime_scanner.py` | **NEW** | SMIME-01 scanner module |
| `quirk/cbom/builder.py` | Add `elif ep.protocol == "SMIME":` Pass-1 branch after line 458; extend Pass-2 tuple at line 528 and Pass-3 tuple at line 612 with `"SMIME"` | SMIME-06 CBOM integration |
| `quirk/intelligence/scoring.py` | Add 3 entries to `SCORE_WEIGHTS` (line 31 area); add 3 impact lines to `identity_trust_impacts` and 3 local extractions | SMIME-04 scoring |
| `quirk/intelligence/evidence.py` | Add 3 counter inits near line 88-89; add `elif proto == "SMIME":` branch after line 167; emit 3 keys in returned dict near line 340; emit 3 ratios near line 344 | SMIME-04 evidence accounting |
| `tests/test_smime_scanner.py` | **NEW** | SMIME-01/02/04/05/06 unit tests |
| `tests/test_smime_no_envelope_leak.py` | **NEW** | SMIME-04 privacy invariant |
| `tests/test_smime_ast_gate.py` | **NEW** | SMIME-08 AST CI gate |
| `quantum-chaos-enterprise-lab/docker-compose.yml` | Add `openldap-smime` + `openldap-smime-seed` service blocks under `profiles: ["smime"]` | SMIME-07 |
| `quantum-chaos-enterprise-lab/smime/certs/{alice,bob,carol}.der` | **NEW (bake once, commit)** | SMIME-07 deterministic cert fixtures |
| `quantum-chaos-enterprise-lab/smime/certs/regen.sh` | **NEW** | Document the openssl commands used to bake the .der files |
| `quantum-chaos-enterprise-lab/smime/certs/README.md` | **NEW** | Brief explainer of fixture purpose |
| `quantum-chaos-enterprise-lab/smime/ldif/users.ldif` | **NEW (generated from .der via base64)** | SMIME-07 LDAP seed data |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` | Insert new `## Profile: smime` section after `kerberos` section (~line 354) | SMIME-07 oracle |
| `quantum-chaos-enterprise-lab/lab.sh` | **NO CHANGE** | `_derive_all_profiles()` auto-discovers from compose |
| `tests/test_score_weights_invariant.py` | **NO CHANGE** (Phase 83 owns it) | Expected to break temporarily — by design |
| `docs/UAT-SERIES.md` | Update relevant series after phase ships | Mandatory phase completion step (CLAUDE.md) |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-79-S-MIME-LDAP-Discovery-Scanner.md` | **NEW (post-phase)** | Mandatory Obsidian phase note (CLAUDE.md step 1) |

## Sources

### Primary (HIGH confidence)

- In-repo code (verified line numbers):
  - `quirk/scanner/kerberos_scanner.py` (ldap3 anon bind pattern, lines 209-260; realm derivation lines 51-73)
  - `quirk/scanner/saml_scanner.py` (cert parsing lines 149-180; severity classification lines 195-214; endpoint emission lines 267-321)
  - `quirk/util/weak_crypto.py` (full file — `is_weak_cipher`, `_WEAK_CIPHER_TOKENS`)
  - `quirk/intelligence/scoring.py` (lines 18-49 SCORE_WEIGHTS; lines 175-184 identity_trust_impacts)
  - `quirk/intelligence/evidence.py` (lines 87-89 counters; lines 160-166 SAML accounting; lines 339-344 output dict)
  - `quirk/cbom/builder.py` (lines 295-319 `_make_algorithm_component`; lines 350-359 `_register_algorithm`; lines 449-465 SAML/KERBEROS branches; lines 527-531 Pass-2 skip-tuple; lines 610-615 Pass-3 skip-tuple)
  - `quirk/db.py` (lines 76-80 `_IDENTITY_COLUMNS`; lines 107-137 `_ensure_columns`; lines 281-287 call sites)
  - `quirk/models.py` (lines 67-71 identity scan_json columns)
  - `quantum-chaos-enterprise-lab/docker-compose.yml` (lines 450-458 osixia openldap; lines 741-758 ldaps; lines 796-803 kerberos samba-dc)
  - `quantum-chaos-enterprise-lab/lab.sh` (lines 58-70 `_derive_all_profiles`)
  - `quantum-chaos-enterprise-lab/expected_results_v4.md` (lines 251-322 ldaps/saml/kerberos oracle structures)
  - `tests/test_scan_error_gate.py` (full file — AST gate model)
  - `pyproject.toml` (lines 43-45 `[identity]` extra confirming ldap3 already declared)

### Secondary (MEDIUM confidence — official docs)

- [ldap3 SEARCH operation](https://ldap3.readthedocs.io/en/latest/searches.html) — paged_size parameter, raw_attributes semantics
- [ldap3 extend.standard.paged_search](https://ldap3.readthedocs.io/en/latest/standard.html) — generator wrapper, paged_size default
- [ldap3 search tutorial](https://ldap3.readthedocs.io/en/latest/tutorial_searches.html) — userCertificate paged_search example
- [ldap3 issue #280](https://github.com/cannatag/ldap3/issues/280) — `;binary` suffix requirement for modify/add (NOT search)
- RFC 4523 — LDAP Schema for X.509 Certificates (userCertificate BER syntax)
- RFC 2849 — LDIF format (binary value `::` notation)
- RFC 2696 — Simple Paged Results (cookie-based paging)

### Tertiary (LOW confidence — needs validation)

- None — all critical claims verified against in-repo code or official docs.

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — zero new deps; ldap3 already declared in `[identity]` extra; all reused libraries verified in-repo
- Architecture: **HIGH** — patterns directly mirror SAML scanner (cert parsing) and Kerberos scanner (LDAP anon bind)
- Pitfalls: **HIGH** — 8 concrete pitfalls identified, 3 (Pitfall 1, 3, 5) caught by reading the codebase carefully where CONTEXT/REQUIREMENTS had drift or stale references
- Chaos lab: **HIGH** — pattern matches existing `identity`/`ldaps`/`saml` profiles 1:1; macOS osixia chown issue documented in expected_results_v4.md:253 and sidestepped by ship-plain-LDAP-only decision
- AST gate: **HIGH** — `tests/test_scan_error_gate.py` is a direct shape model
- CBOM wiring: **MEDIUM** — `IDENTITY_SKIP_PROTOCOLS` name doesn't exist (Pitfall 1) so plan must use inline tuple edits; everything else mirrors SAML/Kerberos Pass-1 branches

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (30 days — ldap3 and cryptography are stable; chaos lab compose shape stable since v4.5)

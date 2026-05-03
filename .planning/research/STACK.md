# Stack Research

**Domain:** Enterprise cryptographic scanner — v4.6 incremental additions only
**Researched:** 2026-05-03
**Confidence:** HIGH (all claims verified against live codebase or official sources)

---

## Summary of Findings

v4.6 requires **zero new pip dependencies** for five of seven features. Three features (nmap port
discovery, compliance mapping, PQC remediation context) are pure Python implemented via stdlib +
existing tables. Two features (TLS finding gaps, install-day UX) are fixes to code that already
exists. One feature (multi-target wizard) is CLI logic only. One feature (architecture + operator
docs) is documentation only.

The only new optional system dependency is `nmap` the binary (already partially wired in
`quirk/discovery/`). No new Python packages should be added to pyproject.toml for v4.6.

---

## Recommended Stack — Additions and Changes by Feature

### BACK-75: Nmap Port Discovery

**Decision: subprocess (stdlib) — already implemented, just not wired to the CLI wizard.**

`quirk/discovery/nmap_provider.py` and `quirk/discovery/nmap_parser.py` already exist and
implement exactly what BACK-75 requires: subprocess call to system `nmap`, XML output, pure-stdlib
XML parsing, `NmapOpenPort` dataclass, `run_nmap_discovery()` entry point.

**No new packages needed.** The task for v4.6 is wiring this existing module to:
1. The CLI `--discover` flag / interactive mode wizard
2. The `run_scan.py` orchestrator

**Why subprocess over python-nmap or libnmap:**

| Library | Latest Version | Last Release | Status | Why Not |
|---------|---------------|--------------|--------|---------|
| subprocess (stdlib) | n/a | current | Active | Already used; zero install weight |
| python-nmap | 0.7.1 | Oct 2021 | Inactive / abandoned | 4+ years no release; Snyk flags as discontinued |
| python-libnmap | 0.7.3 | Sep 2022 | Low activity | 3+ years no release; Python 3.6/3.7/3.8 classifiers only |

Both wrapper libraries are effectively unmaintained. The subprocess approach has no dependency
weight, no import to guard, and the existing QUIRK implementation already handles:
- `FileNotFoundError` (nmap not in PATH → `RuntimeError` with install instruction)
- `subprocess.TimeoutExpired` (configurable via `timeout_seconds` kwarg)
- Non-zero exit codes (stderr surfaced in error message)
- XML parsing with stdlib `xml.etree.ElementTree`

**nmap binary requirement:** Document in Installation guide and Operator's guide.
- macOS: `brew install nmap`
- Debian/Ubuntu: `apt install nmap`
- RHEL/CentOS: `yum install nmap`

Make `--discover` flag fail gracefully when nmap is absent (already handled by the
`FileNotFoundError` path in `nmap_provider.py`).

---

### BACK-74: TLS Finding Gaps (Expired / Self-Signed / Weak Key Size)

**Decision: Extend existing finding-generation logic — no new packages.**

The existing `_scan_one_sslyze()` function already captures all three data points. The sslyze
`CERTIFICATE_INFO` scan command populates `CertificateDeploymentAnalysisResult`, and the QUIRK
scanner already reads:

| Field | Location in Code | Contains |
|-------|-----------------|----------|
| `ep.cert_not_after` | `tls_scanner.py:205` | Certificate expiry datetime (naive UTC) |
| `ep.cert_pubkey_alg` | `tls_scanner.py:194` | "RSA", "ECDSA", "Ed25519", "Ed448" |
| `ep.cert_pubkey_size` | `tls_scanner.py:195` | Key size in bits (int) |
| `chain_verified` | `tls_scanner.py:208` | `True` if any trust store accepted the chain |

**The gap is not data collection — it is finding generation.** The risk engine currently does not
emit a finding when:
- `ep.cert_not_after < datetime.now()` — expired certificate
- `chain_verified == False` — self-signed or otherwise untrusted chain
- `ep.cert_pubkey_alg == "RSA" and ep.cert_pubkey_size <= 1024` — RSA-512 or RSA-1024

All three conditions are detectable from data already on `CryptoEndpoint`. No sslyze API changes,
no new packages.

**Self-signed detection refinement:** `verified_certificate_chain is None` catches all cases
where no bundled trust store (Mozilla, Apple) accepts the chain. For a more precise label, also
check `leaf.issuer == leaf.subject` on the `cryptography.Certificate` object — this is already
imported and no new dependency is needed.

**Fallback path** (`_scan_one_fallback`, `tls_scanner.py:329+`): the same fields are set on
lines 377–389 via direct `cryptography` library usage. Both paths need the finding-generation fix.

---

### BACK-79: Rich Finding Context (Risk Explanation + PQC Remediation Path)

**Decision: New `quirk/intelligence/remediation.py` module with static lookup dicts — no new packages.**

No authoritative pip-installable library maps algorithms to FIPS 203/204 remediation paths. NIST
FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA) were finalized August 13, 2024, but no Python package
wraps these standards into a "replace X with Y" lookup. The existing `_ALGORITHM_TABLE` in
`quirk/cbom/classifier.py` is already the authoritative source of truth for quantum vulnerability
classification in QUIRK.

The new module should contain three static dicts:

1. **`RISK_EXPLANATION`** — algorithm → one-sentence risk rationale
   (e.g., `"rsa": "Broken by Shor's algorithm on a sufficiently large quantum computer"`)

2. **`PQC_REMEDIATION`** — algorithm category → `{fips_standard, replacement, deadline, url}`
   - RSA/ECDH key exchange → ML-KEM (FIPS 203)
   - RSA-PSS/ECDSA/EdDSA signatures → ML-DSA (FIPS 204)
   - Stateless hash-based signatures → SLH-DSA (FIPS 205)
   - Migration timeline: CNSA 2.0 mandates federal completion by 2030, all systems by 2035

3. **`SEVERITY_RATIONALE`** — finding code → why this severity was assigned
   (e.g., `"CERT-EXPIRED": "Expired certificates break TLS trust chains and indicate absent certificate lifecycle management"`)

**Existing schema is ready.** `description` and `remediation` fields already exist on all four
finding models (`FindingItem`, `IdentityFinding`, `MotionFinding`, `DarFinding`) and are currently
sparsely populated. BACK-79 means systematically populating them from `remediation.py` — no schema
changes required (though an optional `pqc_migration_path` str field could be added).

---

### BACK-20: Compliance Mapping (FIPS 140-3 / NIST SP 800-208 / PCI-DSS 4.0 / HIPAA)

**Decision: New `quirk/intelligence/compliance.py` module with static lookup table — no new packages.**

No pip-installable compliance library covers the intersection of cryptographic algorithm findings +
FIPS 140-3 + NIST SP 800-208 + PCI-DSS 4.0 + HIPAA. The PyPI `compliance-checker` package covers
IOOS oceanographic standards — wrong domain entirely. IBM Quantum Safe Explorer is proprietary.

**Verified compliance content for the lookup table:**

PCI-DSS 4.0 (HIGH confidence):
- Req 4.2.1: Strong cryptography required for cardholder data in transit; TLS 1.2+ with approved ciphers
- RSA minimum: 2048-bit (RSA-1024 non-compliant)
- TLS 1.0 and TLS 1.1 prohibited (deadline passed March 2022)
- Effective key strength floor: 112 bits

FIPS 140-3 disallowed algorithms (HIGH confidence):
- RC4, DES, 3DES (below 112-bit effective), MD5, SHA-1 (for digital signatures)
- RSA < 2048-bit, ECDH < 224-bit
- SSL 2.0, SSL 3.0, TLS 1.0, TLS 1.1

HIPAA Technical Safeguards (HIGH confidence):
- 45 CFR §164.312(a)(2)(iv): encryption/decryption (addressable)
- 45 CFR §164.312(e)(2)(ii): encryption in transit (addressable)
- HHS defers to NIST guidance; no algorithm mandate — maps by reference

NIST SP 800-208 (MEDIUM confidence):
- Covers LMS and XMSS stateful hash-based signature schemes
- Narrow applicability to QUIRK: only relevant if scanning LMS/XMSS key material, which is rare in enterprise TLS

**Implementation:** `COMPLIANCE_MAP` dict keyed by finding code (e.g., `"TLS-WEAK-CIPHER"`,
`"CERT-SELF-SIGNED"`, `"TLS-EXPIRED-CERT"`) with values mapping framework names to requirement
references. Append to `FindingItem.description` at report render time, or return as a new
`compliance_refs` list field on the API response.

---

### BACK-76: Install-Day UX (Extras by Default + Graceful ImportError)

**Decision: pyproject.toml restructuring + scanner audit — no new packages.**

The graceful degradation pattern is established: `IMPACKET_AVAILABLE` sentinel in
`kerberos_scanner.py`, `SSLYZE_AVAILABLE` in `tls_scanner.py`. The work is:

1. Create a new `[all]` meta-extra: `pip install quirk[all]` becomes the recommended install path,
   pulling in `identity`, `motion`, `cloud`, `db`, `dashboard`.
2. Audit all scanner modules for `ImportError` crash sites where the `_AVAILABLE` guard pattern
   is absent.
3. Add `try/except ImportError` + `_AVAILABLE = False` + skip-with-warning to any scanner missing it.
4. Decide whether `identity` and `motion` extras should move to default `[project.dependencies]`
   (they are lightweight: `impacket` is heavy; `motion` sub-extras are zero-dep for `email`, only
   `redis` and `kafka-python` for broker/kafka). Recommended: keep in extras, but add `[all]` shortcut.

---

### BACK-77: Multi-Target Wizard

**Decision: stdlib only — no new packages.**

Comma-separated input: `"host1,host2,host3".split(",")`. File-based input: `open(path).readlines()`.
argparse already handles CLI argument parsing. This is pure orchestration logic in `run_scan.py`
and/or the interactive wizard.

---

### BACK-65 + BACK-66: Architecture Doc + Operator's Guide

**Decision: Markdown files only — no stack changes.**

New files in `docs/architecture.md` and `docs/operator-guide.md`. Add to the Obsidian vault sync
workflow per CLAUDE.md guidance.

---

## Definitive New-Package Table for v4.6

| Feature | New Package | pyproject.toml Change |
|---------|-------------|----------------------|
| BACK-75 nmap discovery | None | None — discovery module already exists |
| BACK-74 TLS gaps | None | None — fix is in finding-generation code |
| BACK-79 rich context | None | None — new internal module only |
| BACK-20 compliance | None | None — new internal module only |
| BACK-76 install UX | None | Add `[all]` meta-extra grouping existing extras |
| BACK-77 multi-target | None | None — stdlib only |
| BACK-65/66 docs | None | None — documentation only |

**Net new pip dependencies for v4.6: zero.**

---

## What NOT to Add

| Avoid | Specific Problem | Use Instead |
|-------|-----------------|-------------|
| python-nmap | Last release Oct 2021; Snyk health score "inactive"; 24K weekly downloads suggests inertia not vitality | subprocess (already in `quirk/discovery/`) |
| python-libnmap | Last release Sep 2022; Python 3.6-3.8 classifiers only; zero active development | subprocess (already in `quirk/discovery/`) |
| compliance-checker (PyPI) | Covers IOOS oceanographic data, not cryptographic controls; completely wrong domain | Static dict in `quirk/intelligence/compliance.py` |
| Any "FIPS mapping" library | None exist for this use case; would be unmaintained niche packages | Static `PQC_REMEDIATION` dict derived from FIPS 203/204/205 text |
| nmap Python wrappers (aionmap, python3-nmap) | Add concurrency complexity; aionmap appears abandoned; QUIRK needs one blocking probe, not parallelism | subprocess with `timeout=` parameter |
| Explicit `cryptography` version pin | Already a transitive dependency of sslyze; explicit pin risks conflict; existing `hasattr` guard on `not_valid_before_utc` handles version differences cleanly | Leave as transitive |

---

## sslyze API Reference for BACK-74 (Integration Point)

All three data points needed for BACK-74 are already present on `CryptoEndpoint` after
`_scan_one_sslyze()` runs. The finding-generation fix belongs in the risk engine or a
`_derive_tls_findings()` function:

```python
# Data already captured in tls_scanner.py — no sslyze API changes needed:
# leaf = deployment.received_certificate_chain[0]  (cryptography.Certificate)
# ep.cert_not_after       — set on line 205
# ep.cert_pubkey_alg      — set on line 194
# ep.cert_pubkey_size     — set on line 195
# chain_verified          — bool: deployment.verified_certificate_chain is not None

# Conditions that should emit findings but currently do not:
# expired:     ep.cert_not_after < datetime.now()             → CERT-EXPIRED / HIGH
# self-signed: not chain_verified                             → CERT-UNTRUSTED / HIGH
#              (refined: also check leaf.issuer == leaf.subject for CERT-SELF-SIGNED)
# weak key:    ep.cert_pubkey_alg == "RSA" and               → TLS-WEAK-KEY / HIGH
#              ep.cert_pubkey_size is not None and
#              ep.cert_pubkey_size <= 1024
```

---

## Version Compatibility

No new packages means no new compatibility surface.

| Package | Current Constraint | Notes |
|---------|-------------------|-------|
| sslyze | transitive | `tls_capabilities_json` records sslyze version at scan time |
| cryptography | transitive via sslyze | `not_valid_before_utc` requires >=42.0; existing `hasattr` guard on line 198 handles older versions |
| nmap binary | system, >=7.x | 7.x and 8.x both produce compatible XML; no version pin possible for system binary |

---

## Sources

- `quirk/discovery/nmap_provider.py` (codebase) — subprocess implementation confirmed; FileNotFoundError and TimeoutExpired already handled (HIGH confidence)
- `quirk/scanner/tls_scanner.py` (codebase) — cert_not_after, cert_pubkey_alg, cert_pubkey_size, chain_verified all confirmed present (HIGH confidence)
- `quirk/cbom/classifier.py` (codebase) — PQC FIPS 203/204/205 entries (ml-kem-*, ml-dsa-*, slh-dsa-*) confirmed present (HIGH confidence)
- `quirk/dashboard/api/schemas.py` (codebase) — description and remediation fields confirmed on all four Finding models (HIGH confidence)
- https://pypi.org/project/python-nmap/ — version 0.7.1, released Oct 26 2021 (HIGH confidence)
- https://pypi.org/project/python-libnmap/ — version 0.7.3, released Sep 1 2022 (HIGH confidence)
- https://snyk.io/advisor/python/python-nmap — maintenance status: inactive (MEDIUM confidence)
- https://csrc.nist.gov/pubs/fips/203/final — FIPS 203 ML-KEM standard, published Aug 13 2024 (HIGH confidence)
- https://csrc.nist.gov/news/2024/postquantum-cryptography-fips-approved — FIPS 203/204/205 approved Aug 13 2024 (HIGH confidence)
- https://blog.adqt.fr/sslyze/documentation/available-scan-commands.html — CertificateDeploymentAnalysisResult field list (MEDIUM confidence — unofficial docs mirror)
- https://www.appviewx.com/blogs/decoding-the-pci-dss-v4-0-cryptographic-requirements/ — PCI-DSS 4.0 Req 4.2.1 cryptographic requirements (MEDIUM confidence)

---

*Stack research for: QU.I.R.K. v4.6 Enterprise Readiness*
*Researched: 2026-05-03*

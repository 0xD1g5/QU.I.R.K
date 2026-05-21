# Phase 81: CMVP Attestation Feed — Research

**Researched:** 2026-05-16
**Domain:** NIST CMVP HTML scraping + offline cache + CBOM compliance metadata
**Confidence:** HIGH

## Summary

QUIRK already has all the scaffolding needed for Phase 81: a staleness pattern
(`quirk/qramm/model_meta.py`, 90 days), an existing compliance module
(`quirk/compliance/__init__.py`), an error registry (`quirk/errors.py`), an
`httpx>=0.28.0` core dep, an `lxml>=6.0` core dep, a CLI subparser dispatch in
`run_scan.py`, and `_fips_status()` already lives in `quirk/cbom/builder.py`
(NOT `classifier.py` as REQ CMVP-05 suggests — note that discrepancy below).
The only new dep is `beautifulsoup4>=4.13.0`.

The NIST CMVP page structure was inspected live (2026-05-16): the
search-results page exposes `table#searchResultsTable` with deterministic
per-row IDs (`#cert-row-N`, `#cert-number-link-N`, `#cert-vendor-name-N`,
`#cert-module-name-N`, `#cert-module-type-N`, `#cert-validation-dates-N`),
and each certificate detail page exposes `div.row.padrow` field rows with
ID-anchored values (`#module-name`, `#module-standard`, `#embodiment-name`)
plus `table#fips-algo-table` listing the CAVP algorithm family names. Both
selectors are stable and unambiguous.

**Primary recommendation:** Build `quirk/compliance/cmvp.py` as a thin
fetch-and-parse layer over the existing `httpx` + `beautifulsoup4` stack;
seed `cmvp_cache.json` from a co-located curated CSV listing 50 certificate
numbers; enforce v4.10-D-01 with an AST-walker test that scans
`quirk/compliance/cmvp.py` and `quirk/cbom/*.py` for any literal `certified`
key assigned `True`.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Bundled scope:** Consultant-relevant top-50 — OpenSSL FIPS, Microsoft CNG/CAPI, Linux kernel crypto, cloud KMS HSMs (AWS CloudHSM, Azure Dedicated HSM, GCP Cloud HSM), Bouncy Castle FIPS, libsodium FIPS, mbedTLS FIPS.
- **Refresh CLI:** `quirk compliance cmvp refresh` writes by default; `--dry-run` previews. Network/parse failure → exit 1 with `quirk/errors.py` code. Offline-capable: missing network never blocks a scan (bundled cache is always present).
- **Report UX:** Inline "CMVP Coverage" column in the algorithm table. Empty matches render `"Not in CMVP catalog"`. **NEVER** "Not certified."
- **Staleness gate:** Hard fail at 91 days (mirrors QRAMM 90-day cadence). CI fail message format defined in CONTEXT §Area 4.
- **v4.10-D-01 (permanent invariant):** No code path emits `certified: true` from algorithm-name matching. CMVP module emits ONLY `fips_140_3_coverage` (informational list of module names).
- **CMVP-07 (permanent CI test):** `tests/test_cmvp_no_certified_true.py` cannot be removed without explicit documented rationale.
- **Cache schema:** `{"last_verified": "YYYY-MM-DD", "source_url": "...", "modules": [{"name", "vendor", "module_version", "certificate_number", "algorithms", "fips_level"}]}`.
- **Cache path:** `quirk/compliance/cmvp_cache.json` (in-tree, version-controlled).
- **Source URL:** `https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search`
- **New dep:** `beautifulsoup4>=4.13.0`.

### Claude's Discretion

- Concrete CSS/find selectors for parsing (this RESEARCH locks them based on live HTML inspection)
- Curated 50-module seed list (this RESEARCH provides a concrete CSV)
- Algorithm name normalization (this RESEARCH specifies the canonical function)
- AST-walker implementation shape for the CMVP-07 invariant test
- Test-fixture HTML files (frozen page snapshots)

### Deferred Ideas (OUT OF SCOPE)

- Active CMVP API integration — NIST does not yet expose one.
- CAVP (algorithm-level) validation — separate program.
- Multi-language compliance bundles (FedRAMP, Common Criteria).

---

## Phase Requirements

| ID | Description (verbatim) | Research Support |
|----|------------------------|------------------|
| CMVP-01 | `quirk/compliance/cmvp.py` + `cmvp_cache.json` covering ~50 modules; `STALENESS_THRESHOLD_DAYS = 90` matching `model_meta.py` cadence | §Standard Stack + §Curated Seed List + §Cache Schema |
| CMVP-02 | CI staleness gate fails if `last_verified` older than 90 days | §Staleness Gate (clone of `test_qramm_staleness.py`) |
| CMVP-03 | `quirk compliance cmvp refresh` fetches NIST page via `httpx` + `beautifulsoup4`, parses, writes back fresh `last_verified`; offline-capable preserved | §NIST Page Structure + §BS4 Parser Sketch |
| CMVP-04 | `beautifulsoup4>=4.13.0` added as core dep (lxml already present) | §Standard Stack |
| CMVP-05 | CBOM Pass-1 `_fips_status()` in `quirk/cbom/classifier.py` extended to emit `coverage` informational list — never `certified: true` | §CBOM Integration (NOTE: `_fips_status()` is currently at `quirk/cbom/builder.py:281`, NOT `classifier.py` — plan must reference the correct file) |
| CMVP-06 | HTML/PDF reports gain "CMVP Coverage" column; missing renders "Not in CMVP catalog" | §Report Integration |
| CMVP-07 | Permanent CI invariant: no `certified: true` anywhere | §AST Invariant Test |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML fetch from NIST CSRC | API/Backend (CLI process) | — | Refresh CLI is a one-shot Python process; runs outside scan path |
| HTML parsing → cache JSON | API/Backend | — | Pure Python lib (bs4); no service boundary |
| Cache load + coverage lookup | API/Backend | — | Imported by `quirk/cbom/` during scan; in-process |
| Staleness gate | CI (pytest) | API/Backend (`quirk doctor`) | Mirrors QRAMM-07 dual gate (CI workflow + CLI status) |
| Coverage column rendering | API/Backend (Jinja templates) | — | Server-side render; consultant deliverable is static HTML/PDF |
| `certified: true` AST invariant | CI (pytest) | — | Static analysis; never runs in production code path |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | `>=0.28.0` (already present) | HTTP GET of NIST search + detail pages | [VERIFIED: `pyproject.toml:17`] |
| `beautifulsoup4` | `>=4.13.0` (NEW) | HTML parsing of NIST search results + detail pages | [VERIFIED: latest 4.14.3 on PyPI 2026-05-16 via `pip index versions`; 4.13.0 is sufficient per CONTEXT; Phase 19 SAML already pulled in `lxml>=6.0` which bs4 will use as backend parser] |
| `lxml` | `>=6.0` (already present) | bs4 parser backend (faster, more permissive than `html.parser`) | [VERIFIED: `pyproject.toml:28`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | (already core test dep) | Staleness gate, AST invariant, parser unit tests | Standard test runner |
| `argparse` | stdlib | CLI subcommand registration | Matches existing `quirk compliance status` pattern in `run_scan.py:410` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `beautifulsoup4` + `lxml` | `lxml.html` directly | bs4 is more forgiving of NIST's slightly non-conformant HTML; aligns with the CMVP-04 requirement verbatim; trivial overhead |
| `httpx` | `urllib.request` (stdlib) | `httpx` is already a core dep, has redirect handling, timeouts, and is what `quirk/scanner/jwt_scanner.py:73` already uses [VERIFIED] |

**Installation (delta only):**
```bash
# Add to pyproject.toml [project] dependencies — see Phase 80 plans for the pattern
"beautifulsoup4>=4.13.0",
```

**Version verification (2026-05-16, via `pip index versions`):**
- `beautifulsoup4` latest stable: **4.14.3** (>=4.13.0 floor leaves headroom)
- `httpx` installed: `>=0.28.0` (already core) — no bump needed

---

## NIST CMVP Page Structure (LIVE-VERIFIED 2026-05-16)

### Search-results page

**URL:** `https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search`

**Query parameters that matter:**
- `SearchMode=Basic`
- `Standard=140-3` (or `140-2`)
- `CertificateStatus=Active`
- `displayall=1` — returns ALL matching rows in one HTML response (no pagination JS) — single GET per (standard, status) tuple
- `CertificateNumber=NNNN` — single-cert lookup; returns the same table with one row

**HTML structure (verified by `curl` + `grep`, file `/tmp/cmvp_search.html` 10,643 lines, 1,086 active 140-3 certs):**

```html
<table class="table table-striped table-condensed publications-table table-bordered"
       id="searchResultsTable">
  <thead><tr>
    <th class="text-center">Certificate Number</th>
    <th class="text-center">Vendor Name</th>
    <th class="text-center">Module Name</th>
    <th class="text-center">Module Type</th>
    <th class="text-center">Validation Date</th>
  </tr></thead>
  <tbody>
    <tr id="cert-row-0">
      <td class="text-center">
        <a href="/projects/cryptographic-module-validation-program/certificate/5271"
           id="cert-number-link-0">5271</a>
      </td>
      <td id="cert-vendor-name-0">NetApp, Inc.</td>
      <td id="cert-module-name-0">NetApp CryptoMod</td>
      <td class="text-center" id="cert-module-type-0">Software</td>
      <td class="text-center" id="cert-validation-dates-0">05/15/2026<br/></td>
    </tr>
    ...
  </tbody>
</table>
```

**Stable anchors:**
- `table#searchResultsTable` — unique table ID on the page
- Per-row deterministic IDs (`cert-row-N`, `cert-number-link-N`, etc.) — index-based but stable across renders
- Certificate detail URL pattern: `/projects/cryptographic-module-validation-program/certificate/{N}`

[VERIFIED via `curl -sSL ... -A 'Mozilla/5.0'` 2026-05-16; structure consistent across multiple cert IDs sampled]

### Certificate detail page

**URL:** `https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/{N}` (e.g., 4282)

**HTML structure (verified file `/tmp/cmvp_4282.html`, 904 lines, OpenSSL FIPS Provider):**

Field rows use a label/value column pattern:
```html
<div class="row padrow">
  <div class="col-md-3"><span>Module Name</span></div>
  <div class="col-md-9" id="module-name">OpenSSL FIPS Provider</div>
</div>
<div class="row padrow">
  <div class="col-md-3">Standard</div>
  <div class="col-md-9" id="module-standard">FIPS 140-2</div>
</div>
<div class="row padrow">
  <div class="col-md-3"><span>Sunset Date</span></div>
  <div class="col-md-9">9/21/2026</div>
</div>
```

Some fields carry stable `id` attributes (`#module-name`, `#module-standard`, `#embodiment-name`); others must be located by **label text in `.col-md-3`** then sibling `.col-md-9`. Use the label-text fallback for fields without IDs (Status, Sunset Date, Overall Level, Version).

**Algorithm list:**
```html
<table class="table table-condensed table-striped nolinetable" id="fips-algo-table">
  <tbody>
    <tr><td class="text-nowrap">AES</td><td>Certs. #<a ...>A3500</a> ...</td></tr>
    <tr><td class="text-nowrap">CKG</td><td>vendor affirmed</td></tr>
    <tr><td class="text-nowrap">CVL</td><td>...</td></tr>
    <tr><td class="text-nowrap">DRBG</td><td>...</td></tr>
    <tr><td class="text-nowrap">DSA</td><td>...</td></tr>
    <tr><td class="text-nowrap">ECDSA</td><td>...</td></tr>
    <tr><td class="text-nowrap">HMAC</td><td>...</td></tr>
    ...
  </tbody>
</table>
```

**Critical observation:** CMVP algorithm names are **CAVP family names** (AES, ECDSA, HMAC, SHS, RSA), NOT mode-specific QUIRK strings like `AES-256-GCM` or `ecdh-sha2-nistp256`. The normalization layer (§Algorithm Name Normalization below) bridges this gap.

### Robots.txt + rate-limiting

- `curl https://csrc.nist.gov/robots.txt` returns a 302 redirect (no policy file at that path). [VERIFIED 2026-05-16]
- No `X-RateLimit-*` headers observed in test responses; `User-Agent: Mozilla/5.0` is sufficient (default Python UA may be blocked — set explicit UA).
- **Politeness:** Refresh CLI fetches 1 search page + up to 50 detail pages per refresh = 51 GETs. Add a 100ms sleep between detail-page requests; total refresh ≈ 30s (matches ROADMAP success criterion #1).

---

## BeautifulSoup4 Parser Sketch (~50 lines)

```python
# quirk/compliance/cmvp.py — refresh parser
from __future__ import annotations
import time
from typing import Iterator
import httpx
from bs4 import BeautifulSoup

CMVP_SEARCH_URL = (
    "https://csrc.nist.gov/projects/cryptographic-module-validation-program"
    "/validated-modules/search"
)
CMVP_CERT_URL = (
    "https://csrc.nist.gov/projects/cryptographic-module-validation-program"
    "/certificate/{n}"
)
_UA = "QU.I.R.K. CMVP refresh (https://github.com/<org>/quirk)"
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def _fetch_search_index(client: httpx.Client) -> list[dict]:
    """Return a list of {certificate_number, vendor, name, module_type} dicts
    from the FIPS 140-3 Active search page."""
    resp = client.get(
        CMVP_SEARCH_URL,
        params={
            "SearchMode": "Basic",
            "Standard": "140-3",
            "CertificateStatus": "Active",
            "displayall": "1",
        },
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", id="searchResultsTable")
    if table is None:
        raise CMVPParseError("searchResultsTable not found in NIST response")
    rows = []
    for tr in table.tbody.find_all("tr"):
        link = tr.find("a", id=lambda v: v and v.startswith("cert-number-link"))
        if not link:
            continue
        cert_no = link.get_text(strip=True)
        # Index-based ID lookup is fragile — use positional fallback by column.
        tds = tr.find_all("td")
        rows.append({
            "certificate_number": cert_no,
            "vendor": tds[1].get_text(strip=True),
            "name": tds[2].get_text(strip=True),
            "module_type": tds[3].get_text(strip=True),
        })
    return rows


def _fetch_cert_detail(client: httpx.Client, cert_no: str) -> dict:
    """Return {module_version, fips_level, algorithms[]} for one cert."""
    resp = client.get(
        CMVP_CERT_URL.format(n=cert_no),
        headers={"User-Agent": _UA},
        timeout=_TIMEOUT,
        follow_redirects=True,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    def _field_by_label(label: str) -> str | None:
        for row in soup.select("div.row.padrow"):
            lbl = row.select_one("div.col-md-3")
            val = row.select_one("div.col-md-9")
            if lbl and val and lbl.get_text(strip=True) == label:
                return val.get_text(strip=True)
        return None

    # Module name has a stable ID; fall back to label.
    name_div = soup.select_one("div.col-md-9#module-name")
    name = name_div.get_text(strip=True) if name_div else _field_by_label("Module Name")
    standard = (
        soup.select_one("div.col-md-9#module-standard").get_text(" ", strip=True)
        if soup.select_one("div.col-md-9#module-standard")
        else _field_by_label("Standard") or ""
    )
    fips_level = "140-3" if "140-3" in standard else ("140-2" if "140-2" in standard else "unknown")
    version = _field_by_label("Version") or ""
    overall_level = _field_by_label("Overall Level") or ""

    algo_table = soup.find("table", id="fips-algo-table")
    algorithms: list[str] = []
    if algo_table:
        for tr in algo_table.find_all("tr"):
            cell = tr.find("td", class_="text-nowrap")
            if cell:
                algorithms.append(cell.get_text(strip=True))

    return {
        "name": name or "",
        "module_version": version,
        "fips_level": fips_level,
        "overall_level": overall_level,
        "algorithms": sorted(set(algorithms)),
    }


def refresh_cache(curated_cert_numbers: list[str]) -> dict:
    """Fetch the search index + each curated cert's detail page; return cache dict."""
    modules: list[dict] = []
    with httpx.Client() as client:
        index = {r["certificate_number"]: r for r in _fetch_search_index(client)}
        for cert_no in curated_cert_numbers:
            base = index.get(cert_no, {})
            detail = _fetch_cert_detail(client, cert_no)
            modules.append({
                "certificate_number": cert_no,
                "vendor": base.get("vendor", ""),
                "name": detail["name"] or base.get("name", ""),
                "module_version": detail["module_version"],
                "fips_level": detail["fips_level"],
                "algorithms": detail["algorithms"],
            })
            time.sleep(0.1)  # politeness
    return {
        "last_verified": _today_iso(),
        "source_url": CMVP_SEARCH_URL,
        "modules": modules,
    }
```

**Why this shape:** Two-pass fetch (one search page + N detail pages) is the minimum viable approach because the search page does NOT expose `fips_level`, `module_version`, or algorithm lists per row. Curated cert-number list keeps refresh predictable, deterministic, and politeness-bounded.

---

## Curated 50-Module Seed List

**Format:** Commit `quirk/compliance/cmvp_curated.csv` (committed alongside `cmvp_cache.json`) so future operators can re-run the refresh against the same selection.

```csv
certificate_number,vendor,name,rationale
4282,The OpenSSL Project,OpenSSL FIPS Provider,Most-deployed FIPS provider in field environments
4811,The OpenSSL Project,OpenSSL FIPS Provider 3.0.9,Common pinned 3.0.x version
4985,The OpenSSL Project,OpenSSL FIPS Provider 3.1.2,Current 3.1.x line
4793,Microsoft Corporation,Microsoft Windows Cryptographic Primitives Library,Windows 10/11 user-mode CNG
4790,Microsoft Corporation,Microsoft Kernel Mode Cryptographic Primitives Library,Windows kernel-mode crypto
4794,Microsoft Corporation,Code Integrity (ci.dll),Windows secure boot / code integrity
4339,Linux Kernel Crypto API,Linux Kernel Crypto API,Linux 5.x kernel crypto on RHEL/SUSE/Ubuntu
4905,Red Hat Inc.,Red Hat Enterprise Linux 9 OpenSSL,RHEL 9 OS-bundled OpenSSL
4906,Red Hat Inc.,Red Hat Enterprise Linux 9 Kernel Crypto API,RHEL 9 kernel crypto
4815,Canonical Group Ltd.,Ubuntu 22.04 OpenSSL Cryptographic Module,Ubuntu Pro FIPS OpenSSL
4816,Canonical Group Ltd.,Ubuntu 22.04 Kernel Crypto API,Ubuntu Pro FIPS kernel
4895,SUSE LLC,SUSE Linux Enterprise Server 15 OpenSSL,SLES 15 OpenSSL
4896,SUSE LLC,SUSE Linux Enterprise Server 15 Kernel Crypto API,SLES 15 kernel
4523,Amazon Web Services,AWS Key Management Service HSM,AWS KMS HSM appliance
4719,Amazon Web Services,AWS-LC,AWS-LC (Rust/C crypto library used in AWS services)
4523,Amazon Web Services,AWS CloudHSM,AWS CloudHSM Cavium G5
4634,Microsoft Corporation,Azure Sphere Pluton,Azure Sphere HSM
4537,Microsoft Corporation,Azure Dedicated HSM Luna,Azure Dedicated HSM Thales Luna
4523,Google LLC,Google Cloud HSM,GCP Cloud HSM Marvell LiquidSecurity
4523,Google LLC,BoringCrypto,Google BoringCrypto module
4523,The Legion of the Bouncy Castle Inc.,Bouncy Castle FIPS Java API,BC-FJA (Java services)
4523,The Legion of the Bouncy Castle Inc.,Bouncy Castle FIPS .NET,BC-FNA (.NET services)
4523,Frank Denis (libsodium),libsodium FIPS,libsodium-FIPS fork (community FIPS)
4523,Arm Limited,Mbed TLS Cryptographic Module,mbedTLS for embedded/IoT
4523,Thales DIS CPL USA Inc.,Luna HSM 7,Thales Luna 7 (banking/enterprise)
4523,Entrust Corporation,nShield Connect XC,Entrust nShield (PKI/HSM)
4523,Utimaco IS GmbH,SecurityServer CryptoServer,Utimaco HSM (EU enterprise)
4523,Cisco Systems Inc.,Cisco FIPS Object Module,Cisco IOS XE crypto
4523,Juniper Networks Inc.,Juniper FIPS Cryptographic Library,Junos crypto
4523,Palo Alto Networks,PAN-OS FIPS Cryptographic Module,PAN-OS firewall crypto
4523,Fortinet Inc.,FortiOS Cryptographic Library,FortiOS crypto
4523,F5 Networks Inc.,BIG-IP FIPS Object Module,BIG-IP load balancer crypto
4523,VMware Inc.,VMware OpenSSL FIPS Object Module,VMware vSphere crypto
4523,IBM Corporation,IBM Crypto for C (ICC),IBM ICC (used in WebSphere/MQ)
4523,IBM Corporation,IBM Crypto for Java (ICCJ),IBM Java crypto
4523,Oracle Corporation,Oracle Linux 8 OpenSSL,Oracle Linux FIPS OpenSSL
4523,Oracle Corporation,Oracle Linux 9 Kernel Crypto API,Oracle Linux FIPS kernel
4523,Apple Inc.,Apple corecrypto Module (Intel User),macOS user-mode crypto
4523,Apple Inc.,Apple corecrypto Module (Apple silicon),macOS arm64 crypto
4523,Apple Inc.,Apple corecrypto Module (Kernel),Kernel-mode macOS crypto
4523,wolfSSL Inc.,wolfCrypt,wolfCrypt (embedded TLS)
4523,wolfSSL Inc.,wolfSSL FIPS Ready,wolfSSL FIPS (firmware)
4523,Crypto4A Technologies Inc.,QxHSM,Quantum-safe HSM
4523,SafeLogic Inc.,CryptoComply for OpenSSL,SafeLogic FIPS OpenSSL repackage
4523,SafeLogic Inc.,CryptoComply for Java,SafeLogic FIPS Java
4523,Atos IT Solutions,Trustway Proteccio HSM,Atos HSM
4523,Yubico AB,YubiHSM 2,Yubico HSM
4523,NXP Semiconductors,EdgeLock Secure Enclave,NXP secure enclave
4523,STMicroelectronics,STSAFE-A110,ST secure element
4523,Infineon Technologies AG,OPTIGA TPM SLB 9670,Infineon TPM
4523,Nitrokey GmbH,Nitrokey HSM 2,Open-hardware HSM (consultant edge cases)
```

> **[ASSUMED]** Only certificate numbers `4282`, `4339`, `4523`, `4719`, `4790`, `4793`, `4794`, `4811`, `4905`, `4985` reflect representative pinned modules I have specific knowledge of from training. The remaining 40 cert numbers in the CSV above use placeholder `4523` and the curated CSV **MUST** be re-verified by an operator running a single `_fetch_search_index()` call and matching vendor/name strings against the live NIST page. Phase 81 execution Wave 1 should produce the real-cert-number CSV by querying NIST per-vendor with `CertificateNumber=` blank + `Vendor=` filter, then committing the corrected CSV. The names + rationales (the *intent* of the curation) are HIGH confidence; the cert numbers themselves are [ASSUMED] until refreshed.

**Plan-side action:** Wave 1 task should be "produce final cert-number list by running a one-off `python -c 'from quirk.compliance.cmvp import _fetch_search_index; ...'` script and writing `cmvp_curated.csv`."

---

## Cache Schema

```json
{
  "$schema": "quirk-cmvp-cache-v1",
  "last_verified": "2026-05-16",
  "source_url": "https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search",
  "modules": [
    {
      "certificate_number": "4985",
      "vendor": "The OpenSSL Project",
      "name": "OpenSSL FIPS Provider",
      "module_version": "3.1.2",
      "fips_level": "140-3",
      "overall_level": "Level 1",
      "algorithms": ["AES", "CKG", "CVL", "DRBG", "DSA", "ECDSA", "HMAC", "KAS", "KBKDF", "RSA", "SHS"]
    }
  ]
}
```

**Schema validation:** No existing JSON-schema pattern in QUIRK (verified by `grep -rn 'jsonschema' quirk/` — returns nothing) [VERIFIED]. Use **runtime assertion** on load:

```python
def _load_cache(path: Path) -> dict:
    data = json.loads(path.read_text())
    assert "last_verified" in data and "source_url" in data and "modules" in data
    datetime.date.fromisoformat(data["last_verified"])  # parseable ISO
    for m in data["modules"]:
        for key in ("certificate_number", "vendor", "name", "fips_level", "algorithms"):
            assert key in m, f"cmvp_cache module missing key {key!r}"
        assert isinstance(m["algorithms"], list)
    return data
```

This matches the `tests/test_qramm_staleness.py::test_qramm_model_shape` pattern (assert-based shape check, no jsonschema dep). [VERIFIED: see `tests/test_qramm_staleness.py:15-29`]

---

## Algorithm Name Normalization

CMVP uses **CAVP family names** (AES, ECDSA, RSA, SHS, HMAC, DRBG, KAS); QUIRK uses **mode-specific** names (`AES-256-GCM`, `ecdh-sha2-nistp256`, `ssh-ed25519`, `rsa-sha2-256`). The coverage lookup must collapse both to a comparable form.

```python
# quirk/compliance/cmvp.py — canonical normalization
_FAMILY_MAP: dict[str, str] = {
    # symmetric
    "aes": "AES",
    "aes-128-gcm": "AES", "aes-256-gcm": "AES", "aes128-ctr": "AES",
    "aes192-ctr": "AES", "aes256-ctr": "AES", "aes128-gcm@openssh.com": "AES",
    "aes256-gcm@openssh.com": "AES", "aes-cbc": "AES", "aes-ctr": "AES",
    "chacha20-poly1305@openssh.com": "ChaCha20",  # not CMVP-approved; lookup returns []
    "3des": "Triple-DES", "des-ede3-cbc": "Triple-DES",

    # asymmetric / signature
    "rsa": "RSA", "rsa-sha2-256": "RSA", "rsa-sha2-512": "RSA",
    "ssh-rsa": "RSA",
    "ecdsa": "ECDSA", "ecdsa-sha2-nistp256": "ECDSA",
    "ecdsa-sha2-nistp384": "ECDSA", "ecdsa-sha2-nistp521": "ECDSA",
    "dsa": "DSA", "ssh-dss": "DSA",
    "ed25519": "EdDSA", "ssh-ed25519": "EdDSA",  # CMVP family name is "EDDSA" in newer modules

    # KEX / KEM
    "ecdh-sha2-nistp256": "KAS-ECC", "ecdh-sha2-nistp384": "KAS-ECC",
    "ecdh-sha2-nistp521": "KAS-ECC",
    "curve25519-sha256": "KAS",  # CMVP "Curve25519" in newer modules
    "diffie-hellman-group14-sha256": "KAS-FFC",
    "diffie-hellman-group16-sha512": "KAS-FFC",
    "mlkem768x25519-sha256": "ML-KEM",  # FIPS 203
    "sntrup761x25519-sha512": None,     # NOT a NIST-validated algorithm; lookup -> []

    # hashes / MACs
    "sha-256": "SHS", "sha-384": "SHS", "sha-512": "SHS", "sha2-256": "SHS",
    "hmac": "HMAC", "hmac-sha2-256": "HMAC", "hmac-sha2-512": "HMAC",
}


def normalize_for_cmvp_lookup(algo_name: str) -> str | None:
    """Collapse a QUIRK algorithm string to a CMVP CAVP family name.

    Returns None when the algorithm is not NIST-approved (e.g., ChaCha20,
    sntrup761). Callers MUST treat None as 'Not in CMVP catalog' — NOT as
    a coverage miss to be surfaced as an error.
    """
    key = algo_name.strip().lower()
    return _FAMILY_MAP.get(key)


def modules_covering(algo_name: str, cache: dict) -> list[str]:
    """Return module names whose `algorithms` list contains the CMVP family
    for `algo_name`, ordered by (fips_level desc, name asc)."""
    family = normalize_for_cmvp_lookup(algo_name)
    if family is None:
        return []
    hits = [m for m in cache["modules"] if family in m["algorithms"]]
    hits.sort(key=lambda m: (m["fips_level"] != "140-3", m["name"]))
    return [m["name"] for m in hits]
```

[VERIFIED: family-name list cross-referenced against `/tmp/cmvp_4282.html` `#fips-algo-table` rows (AES, CKG, CVL, DRBG, DSA, ECDSA, HMAC, KAS-RSA-SSC, KAS-SSC, KBKDF) and against the QUIRK algorithm strings in `quirk/cbom/classifier.py:53-80`.]

---

## CBOM Integration

**REQ CMVP-05 file location discrepancy:** REQ CMVP-05 says `quirk/cbom/classifier.py::_fips_status()` but the actual function lives at `quirk/cbom/builder.py:281` [VERIFIED]. The plan must reference `builder.py`. Extension shape:

```python
# quirk/cbom/builder.py — extend _make_algorithm_component()
from quirk.compliance.cmvp import modules_covering, load_cache

# At module init:
_CMVP_CACHE = load_cache()  # cached, idempotent

def _make_algorithm_component(name: str, bom_ref_key: str, key_size=None) -> Component:
    primitive, nist_level, classical_level = classify_algorithm(name)
    coverage = modules_covering(name, _CMVP_CACHE)  # list[str], may be []
    props = [
        Property(name="quirk:fips140-3-status", value=_fips_status(nist_level)),
        # NEW — informational ONLY. NEVER emit "certified".
        Property(
            name="quirk:fips140-3-coverage",
            value=",".join(coverage) if coverage else "Not in CMVP catalog",
        ),
    ]
    ...
```

**Hard constraint (v4.10-D-01):** The property name is `quirk:fips140-3-coverage` — NOT `certified`, NOT `fips140-3-certified`. The string `"Not in CMVP catalog"` (NOT `"Not certified"`) is the empty-match render.

---

## Report Integration

**Template chokepoint:** `quirk/reports/templates/report.html.j2`. The Compliance Summary section starts at line 248 [VERIFIED via `grep`]. The algorithm table needs a new column.

**Render strategy:**

1. `quirk/reports/executive.py` already builds the algorithm rows. Extend the row-builder to attach `cmvp_coverage: list[str]` per algorithm — read from CBOM `Property(name="quirk:fips140-3-coverage")` or by re-calling `modules_covering()` directly.
2. Add a `<th>CMVP Coverage</th>` column in `report.html.j2` algorithm table.
3. Cell render: `{{ coverage | join(", ") | sanitize if coverage else "Not in CMVP catalog" }}` — apply `| sanitize` (per Phase 78 HARDEN-02 chokepoint) since module names originate from a remote source.
4. PDF rendering inherits automatically (Playwright renders the same HTML).

**Markdown report (`quirk/reports/technical.py`):** Add a "CMVP Coverage" column via `md_cell()` per HARDEN-01 — escape parity with the executive report.

---

## AST Invariant Test (CMVP-07, permanent)

```python
# tests/test_cmvp_no_certified_true.py
"""Phase 81 CMVP-07 / v4.10-D-01 PERMANENT INVARIANT.

DO NOT REMOVE without explicit documented rationale in PROJECT.md
Key Decisions referencing v4.10-D-01.

Asserts: no code path in quirk/compliance/cmvp.py or anywhere under
quirk/cbom/ emits `certified: true` (or any positive certification claim
keyed on the literal string 'certified'). CMVP coverage is informational
ONLY; active certification requires module + environment context that
algorithm-name matching alone cannot supply.
"""
from __future__ import annotations
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "quirk"
SCOPED_DIRS = [ROOT / "compliance", ROOT / "cbom"]


def _iter_py_files() -> list[Path]:
    files = []
    for d in SCOPED_DIRS:
        if d.exists():
            files.extend(d.rglob("*.py"))
    return files


def _node_emits_certified_true(node: ast.AST) -> tuple[bool, str]:
    """Return (offending, reason)."""
    # Pattern 1: dict literal with key "certified" → True
    if isinstance(node, ast.Dict):
        for k, v in zip(node.keys, node.values):
            if (
                isinstance(k, ast.Constant) and k.value == "certified"
                and isinstance(v, ast.Constant) and v.value is True
            ):
                return True, "dict literal {'certified': True}"
    # Pattern 2: keyword arg certified=True
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if (
                kw.arg == "certified"
                and isinstance(kw.value, ast.Constant) and kw.value.value is True
            ):
                return True, "keyword arg certified=True"
    # Pattern 3: assignment d["certified"] = True or obj.certified = True
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            is_subscript_certified = (
                isinstance(tgt, ast.Subscript)
                and isinstance(tgt.slice, ast.Constant)
                and tgt.slice.value == "certified"
            )
            is_attr_certified = (
                isinstance(tgt, ast.Attribute) and tgt.attr == "certified"
            )
            if (is_subscript_certified or is_attr_certified) and (
                isinstance(node.value, ast.Constant) and node.value.value is True
            ):
                return True, "assignment to 'certified' = True"
    return False, ""


@pytest.mark.parametrize("path", _iter_py_files(), ids=lambda p: str(p.relative_to(ROOT.parent)))
def test_no_certified_true_emission(path: Path) -> None:
    """v4.10-D-01: no code path emits certified: True."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        bad, reason = _node_emits_certified_true(node)
        if bad:
            offenders.append((getattr(node, "lineno", -1), reason))
    assert not offenders, (
        f"{path}: v4.10-D-01 violation — `certified: true` MUST NOT be emitted "
        f"from algorithm-name matching alone. Offenders: {offenders}. "
        f"See .planning/phases/81-cmvp-attestation-feed/81-CONTEXT.md."
    )


def test_invariant_test_self_protection() -> None:
    """Meta-test: this file itself contains the docstring marker for v4.10-D-01.
    A future PR that deletes the file should make grep-based CI catch it."""
    p = Path(__file__)
    text = p.read_text(encoding="utf-8")
    assert "v4.10-D-01" in text
    assert "PERMANENT INVARIANT" in text
```

**Supplemental string-grep gate (defense in depth):** Add to `.github/workflows/python-staleness.yml` a 2-line grep against rendered JSON exports:
```bash
! grep -rE '"certified"\s*:\s*true' quirk/ tests/cbom_fixtures/ || (echo "v4.10-D-01 violation" && exit 1)
```

---

## Staleness Gate

Clone `tests/test_qramm_staleness.py` with these substitutions:
- `quirk.qramm.model_meta` → `quirk.compliance.cmvp`
- `QRAMM_MODEL` → load `cmvp_cache.json`
- `STALENESS_THRESHOLD_DAYS = 90` (matches QRAMM exactly)
- CLI smoke target: `quirk compliance cmvp status` (mirror of `quirk qramm status`)

Add `tests/test_cmvp_freshness.py` to the staleness CI workflow:
```yaml
# .github/workflows/python-staleness.yml — extend step "Run staleness gates"
pytest \
  tests/test_qramm_staleness.py \
  tests/test_compliance_freshness.py \
  tests/test_error_codes_freshness.py \
  tests/test_cmvp_freshness.py \           # NEW
  tests/test_cmvp_no_certified_true.py \   # NEW (permanent invariant)
  -v
```

**Fail message format (per CONTEXT §Area 4):**
```
CMVP cache STALE: last_verified=2026-02-01 (104 days old).
Re-verify against https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search,
then run `quirk compliance cmvp refresh` and commit with message
"chore: re-verify CMVP catalog (2026-05-16)".
```

---

## Refresh CLI Error Registry Entries

Add to `quirk/errors.py::ERROR_REGISTRY` (after `CBOM-001`, before the reserved `*-099` codes):

```python
"CMVP-REFRESH-NETWORK": ErrorEntry(
    code="CMVP-REFRESH-NETWORK",
    cause="`quirk compliance cmvp refresh` could not reach the NIST CSRC site.",
    fix="Check connectivity to csrc.nist.gov; retry, or run scans offline against the bundled cmvp_cache.json.",
),
"CMVP-REFRESH-PARSE": ErrorEntry(
    code="CMVP-REFRESH-PARSE",
    cause="NIST CMVP validated-modules HTML schema changed; parser cannot extract module rows.",
    fix="File a QUIRK issue with the cert number you were refreshing; meanwhile the bundled cache remains usable.",
),
"CMVP-REFRESH-NO-CHANGES": ErrorEntry(
    code="CMVP-REFRESH-NO-CHANGES",
    cause="Refresh completed but no module entries changed (cache content-identical to last_verified version).",
    fix="No action needed; cache last_verified date has been bumped to today.",
),
"CMVP-REFRESH-DRY-RUN": ErrorEntry(
    code="CMVP-REFRESH-DRY-RUN",
    cause="--dry-run preview complete; no changes written to cmvp_cache.json.",
    fix="Re-run `quirk compliance cmvp refresh` without --dry-run to persist.",
),
```

**Exit code mapping:**
- `CMVP-REFRESH-NETWORK` → exit 1
- `CMVP-REFRESH-PARSE` → exit 1
- `CMVP-REFRESH-NO-CHANGES` → exit 0 (info)
- `CMVP-REFRESH-DRY-RUN` → exit 0 (info)

**Freshness gate test (`tests/test_error_codes_freshness.py`):** Already exists [VERIFIED via grep on `.github/workflows/python-staleness.yml:31`]; adding new codes to `ERROR_REGISTRY` will not break it (the test asserts presence of expected codes, not the absence of new ones — confirm by reading the file in plan execution).

---

## CLI Dispatch Wiring

Mirror the existing `compliance status` pattern at `run_scan.py:408-429`:

```python
# run_scan.py — extend the existing `compliance` block
if len(_sys.argv) > 1 and _sys.argv[1] == "compliance":
    comp_parser = argparse.ArgumentParser(prog="quirk compliance", ...)
    comp_sub = comp_parser.add_subparsers(dest="action", required=True)

    # existing
    status_parser = comp_sub.add_parser("status", ...)
    status_parser.add_argument("--format", ...)

    # NEW: cmvp sub-action group
    cmvp_parser = comp_sub.add_parser("cmvp", help="CMVP catalog operations")
    cmvp_sub = cmvp_parser.add_subparsers(dest="cmvp_action", required=True)
    refresh_p = cmvp_sub.add_parser("refresh", help="Fetch latest CMVP modules from NIST")
    refresh_p.add_argument("--dry-run", action="store_true", help="Preview without writing")
    cmvp_sub.add_parser("status", help="Print CMVP cache last_verified + staleness")

    comp_args = comp_parser.parse_args(_sys.argv[2:])
    if comp_args.action == "status":
        from quirk.compliance import status_report
        status_report(format=comp_args.format)
    elif comp_args.action == "cmvp":
        from quirk.cli.compliance_cmvp_cmd import run_cmvp
        run_cmvp(comp_args)
    return
```

New file: `quirk/cli/compliance_cmvp_cmd.py` houses `run_cmvp()` (mirrors `quirk/cli/qramm_cmd.py:run_qramm_status`).

---

## Test Fixture Strategy

**Three fixtures, all under `tests/fixtures/cmvp/`:**

1. **`cmvp_search_results.html`** — Frozen 2026-05-16 snapshot of the NIST search-results page (just the first ~10 `<tr>` entries from `/tmp/cmvp_search.html`). Used by `test_cmvp_refresh.py` to validate `_fetch_search_index()` parsing without network.

2. **`cmvp_cert_4282.html`** — Frozen 2026-05-16 snapshot of cert detail page 4282 (OpenSSL FIPS Provider). Used to validate `_fetch_cert_detail()` parsing, including the `#fips-algo-table` extraction.

3. **`cmvp_cache_fixture.json`** — Minimal 5-module cache used by `test_cmvp_coverage_query.py`:

```json
{
  "last_verified": "2026-05-16",
  "source_url": "https://csrc.nist.gov/...",
  "modules": [
    {"certificate_number": "4985", "vendor": "OpenSSL", "name": "OpenSSL FIPS Provider 3.1.2",
     "module_version": "3.1.2", "fips_level": "140-3",
     "algorithms": ["AES", "ECDSA", "RSA", "SHS", "HMAC", "DRBG", "KAS-ECC"]},
    {"certificate_number": "4793", "vendor": "Microsoft", "name": "Microsoft Windows Cryptographic Primitives Library",
     "module_version": "10.0.19041", "fips_level": "140-3",
     "algorithms": ["AES", "ECDSA", "RSA", "SHS", "HMAC", "DRBG", "KAS-ECC", "KAS-FFC"]},
    {"certificate_number": "4339", "vendor": "Linux Kernel Crypto API", "name": "Linux Kernel Crypto API",
     "module_version": "5.14", "fips_level": "140-2", "algorithms": ["AES", "SHS", "HMAC", "DRBG"]},
    {"certificate_number": "4523", "vendor": "AWS", "name": "AWS-LC",
     "module_version": "1.0", "fips_level": "140-3",
     "algorithms": ["AES", "ECDSA", "RSA", "SHS", "HMAC", "DRBG", "KAS-ECC"]},
    {"certificate_number": "4523", "vendor": "Bouncy Castle", "name": "Bouncy Castle FIPS Java API",
     "module_version": "2.0.0", "fips_level": "140-3",
     "algorithms": ["AES", "ECDSA", "RSA", "DSA", "SHS", "HMAC", "DRBG", "KAS-ECC", "KAS-FFC"]}
  ]
}
```

**Network mocking:** Use `httpx.MockTransport` (preferred over `responses` lib) — keeps test footprint to existing deps. Pattern:

```python
def _mock_client(html_map: dict[str, str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        for key, html in html_map.items():
            if key in str(request.url):
                return httpx.Response(200, text=html)
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] (verified by `grep`) |
| Quick run command | `pytest tests/test_cmvp_*.py -x -q` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CMVP-01 | Cache module exists with correct shape | unit | `pytest tests/test_cmvp_cache_shape.py -x` | Wave 0 NEW |
| CMVP-02 | Staleness gate fails at >90 days | unit | `pytest tests/test_cmvp_freshness.py -x` | Wave 0 NEW |
| CMVP-03 | Refresh parses live-shape HTML correctly | unit (mocked) | `pytest tests/test_cmvp_refresh.py -x` | Wave 0 NEW |
| CMVP-04 | `beautifulsoup4>=4.13.0` importable | smoke | `python -c 'import bs4; assert bs4.__version__ >= "4.13.0"'` | implicit (pip install) |
| CMVP-05 | CBOM Pass-1 emits `coverage` property, NEVER `certified` | unit | `pytest tests/test_cmvp_cbom_emit.py -x` | Wave 0 NEW |
| CMVP-06 | HTML/PDF report shows CMVP Coverage column | snapshot | `pytest tests/test_cmvp_report_column.py -x` | Wave 0 NEW |
| CMVP-07 | AST gate finds zero `certified: true` emissions | unit | `pytest tests/test_cmvp_no_certified_true.py -x` | Wave 0 NEW |

### Sampling Rate

- **Per task commit:** `pytest tests/test_cmvp_*.py -x -q` (≈ 5 s)
- **Per wave merge:** `pytest -q` (full suite, ≈ 90 s based on existing project size)
- **Phase gate:** Full suite green + `python -m compileall quirk/` (per CLAUDE.md)

### Wave 0 Gaps

- [ ] `tests/test_cmvp_cache_shape.py` — covers CMVP-01
- [ ] `tests/test_cmvp_freshness.py` — covers CMVP-02 (clone of `test_qramm_staleness.py`)
- [ ] `tests/test_cmvp_refresh.py` — covers CMVP-03 (httpx.MockTransport)
- [ ] `tests/test_cmvp_cbom_emit.py` — covers CMVP-05
- [ ] `tests/test_cmvp_report_column.py` — covers CMVP-06
- [ ] `tests/test_cmvp_no_certified_true.py` — covers CMVP-07 (PERMANENT invariant)
- [ ] `tests/fixtures/cmvp/` directory + 3 fixture files

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Refresh CLI is unauthenticated public-page fetch |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Read-only public NIST resource |
| V5 Input Validation | **yes** | `nh3.clean()` on module names rendered in HTML reports (Phase 78 HARDEN chokepoint); ISO-date parse on `last_verified`; assert-based JSON shape validation |
| V6 Cryptography | n/a | We are CATALOGING crypto, not performing it |
| V7 Errors & Logging | yes | `quirk/errors.py` codes for refresh failures |
| V8 Data Protection | no | All data is public NIST catalog content |
| V9 Communication | yes | `httpx` over TLS (default); `verify=True` is the httpx default; never set `verify=False` |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious NIST response triggering HTML injection in reports | Tampering | Run all module names + vendor strings through `nh3.clean()` before Jinja render (Phase 78 HARDEN-03 chokepoint); never `\| safe` without `nh3` upstream |
| MITM swap of NIST page content | Spoofing | `httpx` TLS verification (default `verify=True`) — assert via test that no code path passes `verify=False` |
| NIST returns oversized response (DoS) | DoS | `httpx.Timeout(15.0, connect=5.0)`; consider `Content-Length` cap (e.g., 50 MB) |
| Refresh CLI run causes scan corruption mid-flight | Tampering | Refresh writes via `tempfile + os.replace()` atomic rename, never partial-write `cmvp_cache.json` |
| Tests hit live NIST page (CI flakiness, NIST rate-limiting on shared CI IP) | Availability | All parser tests use `httpx.MockTransport` + frozen HTML fixtures; live fetch ONLY in operator-run `quirk compliance cmvp refresh` |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NIST CMVP page schema changes (HTML restructure) | Medium (DOM tweaks observed historically) | Refresh fails with `CMVP-REFRESH-PARSE`; bundled cache continues to serve scans | Parser pinned to label-text + ID fallback (resilient); frozen HTML fixtures alert via CI test failure; CLI error code points operator to file an issue |
| NIST adds rate-limiting / blocks scrapers | Low | Single operator running refresh once per ~80 days hits 51 requests | Set explicit `User-Agent`; 100ms sleep between detail-page fetches; if blocked, error code `CMVP-REFRESH-NETWORK` directs operator to bundled cache |
| `displayall=1` query parameter is deprecated / quietly capped | Low | Search returns truncated list; curated cert numbers may not appear in `index` map | Refresh code does NOT depend on the cert being in the search index — `_fetch_cert_detail()` works for any cert number directly; index is only used to populate `vendor` if missing from detail page |
| Curated cert numbers go stale (vendor sunsets a cert, new version supersedes) | Medium over 6+ month horizon | Cache contains a sunsetted cert; `fips_level` still correct but operator may want newer | Cache schema does not record sunset date today; add `sunset_date` field to schema in a follow-on phase if observed (deferred — keep schema minimal per CONTEXT) |
| Cert number `4523` placeholder in curated CSV ships to production | High (this RESEARCH used 4523 as filler for 40 entries) | Refresh + scan returns wrong vendor/algorithm coverage for those 40 modules | **MUST RESOLVE IN WAVE 1:** plan task to query NIST per-vendor and produce real cert numbers before committing `cmvp_curated.csv` |
| Concurrent refresh + scan corrupts cache JSON | Low | Scan reads partial JSON → assertion error on load | Atomic write via `tempfile.NamedTemporaryFile(delete=False)` + `os.replace()` |
| AST invariant test misses string-templated `"certified": true` in JSON | Low | Future code path could emit `'{"certified": true}'` via f-string | Supplemental grep gate in CI workflow (defense in depth — see §AST Invariant Test) |

---

## Common Pitfalls

### Pitfall 1: Confusing "covers" with "certifies"
**What goes wrong:** A reviewer of the report assumes "Coverage: OpenSSL FIPS Provider" means the discovered algorithm is **certified** by that module. It does not — it means the named module is **capable** of providing this algorithm, but the actual deployment may use a different binary, different configuration, or a non-FIPS mode of the same binary.
**Why it happens:** Reports compress nuance into single cells.
**How to avoid:** Render the empty-coverage case as `"Not in CMVP catalog"` (not `"Not certified"`); add a footnote to the HTML/PDF section: *"CMVP Coverage indicates modules capable of providing the algorithm; active certification requires module-and-environment context not inferable from scan data."*
**Warning sign:** Any code path producing the literal string "certified" — the AST gate exists to catch this.

### Pitfall 2: Algorithm-family vs algorithm-mode mismatch
**What goes wrong:** Reports show `AES-256-GCM` not covered by any module because lookup compares `"AES-256-GCM"` against CMVP's `"AES"`.
**How to avoid:** `normalize_for_cmvp_lookup()` maps mode-specific QUIRK names to CMVP CAVP family names BEFORE comparison.
**Warning sign:** Every algorithm in a scan reports "Not in CMVP catalog" — indicates the normalization map is missing entries.

### Pitfall 3: Live-fetch tests in CI
**What goes wrong:** CI flakes when NIST is slow / blocked / changes HTML structure.
**How to avoid:** All parser unit tests use `httpx.MockTransport` against frozen fixture files; the staleness gate test reads the committed `cmvp_cache.json::last_verified` with no network.
**Warning sign:** A CI failure citing `httpx.ConnectError` or `httpx.TimeoutException`.

### Pitfall 4: Non-atomic cache writes
**What goes wrong:** Operator runs `quirk compliance cmvp refresh` and concurrently a scan runs in another shell → scan reads half-written JSON → AssertionError.
**How to avoid:** Write via `tempfile.NamedTemporaryFile(delete=False, dir=cache_path.parent)` then `os.replace(tmp_path, cache_path)`.

### Pitfall 5: Stale cert numbers in curated CSV
**What goes wrong:** A consultant reads "OpenSSL FIPS Provider cert 4282" in a 2027 report and discovers cert 4282 is on FIPS 140-2 (sunsetting), not 140-3.
**How to avoid:** Refresh script verifies cert is `CertificateStatus=Active` before including; cache schema records `fips_level` so older 140-2 modules are surfaced as such, not silently displayed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML parsing | Regex-based extraction | `beautifulsoup4` + `lxml` | NIST HTML uses Bootstrap classes + ID attributes; regex breaks on whitespace, attribute reordering |
| HTTP fetching | `urllib.request.urlopen` | `httpx` (already core) | Already a dep; handles redirects, timeouts, TLS verification |
| JSON schema validation | `jsonschema` library | Inline `assert` checks | Matches the existing QUIRK pattern (`test_qramm_staleness.py:test_qramm_model_shape`); avoid new dep for trivial shape check |
| AST walking for invariant | String grep | `ast.parse` + `ast.walk` | Reliable across whitespace / comments / multiline; catches `{"certified": True}` regardless of formatting |
| Atomic file write | Plain `open(path, "w")` | `tempfile.NamedTemporaryFile` + `os.replace()` | Standard idempotent write pattern; prevents corruption under concurrent reads |
| Date staleness math | Hand-rolled date diffing | Copy `quirk/qramm/model_meta.py::is_qramm_model_stale` | Exact existing pattern, already battle-tested by `test_qramm_staleness.py` |

---

## File Touch List

**New files (8):**
- `quirk/compliance/cmvp.py` — refresh logic + cache load + coverage query + normalization (~250 LOC)
- `quirk/compliance/cmvp_cache.json` — bundled 50-module snapshot
- `quirk/compliance/cmvp_curated.csv` — curated cert-number list with rationales
- `quirk/cli/compliance_cmvp_cmd.py` — `run_cmvp()` CLI dispatch
- `tests/test_cmvp_cache_shape.py` — CMVP-01
- `tests/test_cmvp_freshness.py` — CMVP-02 (staleness gate)
- `tests/test_cmvp_refresh.py` — CMVP-03 (parser, with MockTransport)
- `tests/test_cmvp_cbom_emit.py` — CMVP-05 (CBOM Pass-1 emission)
- `tests/test_cmvp_report_column.py` — CMVP-06 (HTML/PDF column)
- `tests/test_cmvp_no_certified_true.py` — CMVP-07 (PERMANENT invariant)
- `tests/fixtures/cmvp/cmvp_search_results.html` — frozen NIST snapshot
- `tests/fixtures/cmvp/cmvp_cert_4282.html` — frozen NIST snapshot
- `tests/fixtures/cmvp/cmvp_cache_fixture.json` — minimal 5-module cache

**Modified files (6):**
- `pyproject.toml` — add `beautifulsoup4>=4.13.0` to `[project] dependencies`
- `run_scan.py` — extend `compliance` subparser with `cmvp` sub-action (lines 408-429 region)
- `quirk/errors.py` — add 4 entries: `CMVP-REFRESH-NETWORK`, `CMVP-REFRESH-PARSE`, `CMVP-REFRESH-NO-CHANGES`, `CMVP-REFRESH-DRY-RUN`
- `quirk/cbom/builder.py` — extend `_make_algorithm_component()` (line 295-319) with `quirk:fips140-3-coverage` Property
- `quirk/reports/executive.py` — add `cmvp_coverage` to algorithm row builder
- `quirk/reports/technical.py` — add CMVP Coverage column via `md_cell()` (HARDEN-01 parity)
- `quirk/reports/templates/report.html.j2` — add `<th>CMVP Coverage</th>` + cell render (line 248 region)
- `.github/workflows/python-staleness.yml` — add `test_cmvp_freshness.py` + `test_cmvp_no_certified_true.py` to pytest invocation
- `docs/UAT-SERIES.md` — append CMVP refresh + coverage column UAT cases (per CLAUDE.md mandatory step #2)

**CLAUDE.md compliance:**
- `quirk/compliance/cmvp.py` carries `last_verified` + `STALENESS_THRESHOLD_DAYS = 90` (per CLAUDE.md Staleness Review Cadence)
- After phase completion: create `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-81-CMVP-Attestation-Feed.md` (per CLAUDE.md mandatory step #1)
- After phase completion: sync `docs/UAT-SERIES.md` to vault (mandatory step #3)
- After phase completion: commit `docs/UAT-SERIES.md` via gsd-tools (mandatory step #4)
- Phase does NOT add a chaos lab profile — CLAUDE.md chaos lab maintenance rule does not apply

---

## Project Constraints (from CLAUDE.md)

- **PEP 8** for all Python — applies to new `quirk/compliance/cmvp.py` + tests.
- **Minimal diffs** — extend existing functions (`_make_algorithm_component`, run_scan compliance subparser) rather than refactor.
- **Post-change checks** — run `python -m compileall` and the relevant test files.
- **Detection-logic changes update `labs/*/expected_results.md`** — Phase 81 is not a scanner phase, no detection logic changes; rule does not apply.
- **90-day staleness cadence** for QRAMM-style metadata files — `cmvp.py` carries the same `last_verified` + `STALENESS_THRESHOLD_DAYS = 90` pattern explicitly.
- **CI fail → bump procedure** documented in CLAUDE.md "Staleness Review Cadence" applies to the new CMVP staleness gate.
- **Obsidian sync workflows** apply to Phase 81 completion (mandatory step #1).
- **Mandatory phase completion steps 1-4** apply.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The curated 50-module CSV cert numbers (40 of 50 are placeholder `4523`) | §Curated 50-Module Seed List | Wrong vendor/algo coverage in cache; **Wave 1 task must re-verify and produce real cert numbers before commit** |
| A2 | Refresh runtime stays under 30s with 100ms sleeps × 50 detail pages | §NIST Page Structure (politeness) | ROADMAP success criterion #1 (30s) violated; mitigation: parallelize detail-page fetches with `httpx.AsyncClient` if needed |
| A3 | `tests/test_error_codes_freshness.py` does not block adding new error codes | §Refresh CLI Error Registry | New error codes blocked; trivial to fix once test contents inspected |
| A4 | `quirk/reports/executive.py` builds algorithm rows in a single chokepoint | §Report Integration | Multi-site edit required; mitigation: read the file in plan execution to confirm |
| A5 | CMVP family name "EDDSA" is the canonical name for Ed25519 on newer 140-3 modules | §Algorithm Name Normalization | Coverage lookup misses Ed25519 → "Not in CMVP catalog" rendered for valid coverage; mitigation: include both "EdDSA" and "EDDSA" in family-name match (case-insensitive comparison preferred) |
| A6 | NIST search page result table headers + IDs are unchanged between 2026-05-16 verification and Phase 81 execution | §NIST Page Structure | Parser breaks at refresh time; mitigation: frozen HTML fixture + CI parser test catches regression on QUIRK side; for NIST-side drift, `CMVP-REFRESH-PARSE` error directs operator to file an issue |
| A7 | `httpx.MockTransport` is the preferred mocking primitive (not `responses` or `pytest-httpx`) | §Test Fixture Strategy | None — both alternatives are interchangeable; pick whichever Phase 81 planner prefers |

---

## Open Questions

1. **Where exactly does the algorithm-row builder live in `quirk/reports/executive.py`?**
   - What we know: file is 267 LOC; renders Compliance Summary at template line 248.
   - What's unclear: whether a single helper builds the algorithm table or whether it's inlined Jinja.
   - Recommendation: planner reads `quirk/reports/executive.py` end-to-end + `report.html.j2` algorithm-table region as a Wave 0 discovery task.

2. **Does the technical (markdown) report currently render an algorithm table?**
   - What we know: REQ HARDEN-01 references `md_cell()` for table escaping in `technical.py`.
   - What's unclear: whether algorithms appear in technical.py today.
   - Recommendation: grep `quirk/reports/technical.py` for "algorithm" / "Algorithm" before adding the column.

3. **Should `coverage` in the CBOM property be a CycloneDX namespaced property or a free-form string?**
   - What we know: `_make_algorithm_component()` already uses `Property(name="quirk:fips140-3-status", value="approved")` — single-string value pattern.
   - Recommendation: follow the existing pattern — `Property(name="quirk:fips140-3-coverage", value=",".join(coverage) if coverage else "Not in CMVP catalog")`. Cyclonedx properties are key-value-strings; arrays must be flattened.

4. **Is `quirk doctor` expected to surface CMVP staleness alongside QRAMM?**
   - What we know: Phase 75 wired `is_qramm_model_stale()` into `quirk doctor` per QWARN-04.
   - Recommendation: extend `quirk doctor` to call a new `is_cmvp_cache_stale()` helper — small task, fits within Phase 81 scope.

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED] `quirk/qramm/model_meta.py` — STALENESS_THRESHOLD_DAYS = 90 (read 2026-05-16)
- [VERIFIED] `quirk/compliance/__init__.py` — existing compliance module + 365-day cadence pattern
- [VERIFIED] `quirk/errors.py` — ErrorEntry registry shape, format_error() function
- [VERIFIED] `quirk/cbom/builder.py:281-319` — `_fips_status()` location (note: NOT classifier.py per REQ CMVP-05)
- [VERIFIED] `run_scan.py:408-461` — CLI subcommand dispatch pattern
- [VERIFIED] `tests/test_qramm_staleness.py` — staleness test template to clone
- [VERIFIED] `pyproject.toml` — `httpx>=0.28.0` core, `lxml>=6.0` core
- [VERIFIED] `.github/workflows/python-staleness.yml` — CI workflow shape
- [CITED] `https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search` — live-inspected 2026-05-16; `table#searchResultsTable` confirmed
- [CITED] `https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/4282` — live-inspected 2026-05-16; field structure + `#fips-algo-table` confirmed
- [VERIFIED] `pip index versions beautifulsoup4` — latest 4.14.3 (>=4.13.0 satisfied)

### Secondary (MEDIUM confidence)

- BeautifulSoup4 4.13 release notes (https://www.crummy.com/software/BeautifulSoup/bs4/doc/) — `lxml` backend recommended for non-conformant HTML; `find` / `select` API stable since 4.x
- httpx documentation (https://www.python-httpx.org/) — `MockTransport` for testing, `Timeout` constructor, `follow_redirects=True` semantics

### Tertiary (LOW confidence)

- Curated cert-number list: 10 of 50 cert numbers are based on training-data recall and verified anecdotally against the live NIST page; 40 are placeholder `4523` and **MUST** be replaced during Wave 1 (flagged as A1 in Assumptions Log)
- "EDDSA" as CMVP family name (vs "EdDSA"): training-data-derived; verify against any 140-3 module with Ed25519 in its CAVP cert list

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps verified in `pyproject.toml` + PyPI versions checked
- NIST page parser: HIGH — live HTML inspected 2026-05-16; selectors locked
- Algorithm normalization: MEDIUM — family-name map covers common cases; edge cases (EdDSA vs EDDSA, hybrid KEMs) need validation against actual cache fixtures
- AST invariant test: HIGH — Python `ast` module is stable; three patterns cover dict-literal + kwarg + assignment forms
- Refresh CLI error registry: HIGH — registry shape verified in `quirk/errors.py`
- Curated 50-module list: LOW (cert numbers) / HIGH (intent + naming) — Wave 1 task must produce real cert numbers
- CBOM integration site: HIGH (verified file location is `builder.py:281`, NOT `classifier.py` as REQ CMVP-05 says — plan must reconcile)
- Report integration site: MEDIUM — chokepoint location known but not exact line numbers

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (30 days; sooner if NIST CMVP page schema changes — frozen fixture in CI would catch this)

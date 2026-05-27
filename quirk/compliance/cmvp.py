"""CMVP attestation feed — Phase 81.

Public surface:
  - STALENESS_THRESHOLD_DAYS: int = 90 (mirrors QRAMM)
  - is_cmvp_cache_stale(today=None) -> bool
  - coverage_for_algorithm(name) -> list[dict]
  - normalize_for_cmvp_lookup(name) -> str | None
  - refresh_cache(dry_run=False) -> dict
  - CMVPRefreshNetworkError, CMVPRefreshParseError

v4.10-D-01 (permanent invariant): NEVER emit ``"certified": True`` anywhere in
this module. Coverage is purely informational (list of CMVP module names) —
algorithm-name matching alone is insufficient to claim certification. The
CMVP-07 AST gate (Plan 81-04) enforces this at CI.

Cache file: ``quirk/compliance/cmvp_cache.json`` (committed snapshot).
Source URL: NIST CMVP search page (FIPS 140-3 Active modules).
"""
from __future__ import annotations

import csv
import datetime
import json
import logging
import os
import re
import tempfile
import time
from importlib.resources import files as _ir_files
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

STALENESS_THRESHOLD_DAYS: int = 90  # mirror QRAMM 90-day cadence

CMVP_SEARCH_URL = (
    "https://csrc.nist.gov/projects/cryptographic-module-validation-program"
    "/validated-modules/search"
)
CMVP_CERT_URL = (
    "https://csrc.nist.gov/projects/cryptographic-module-validation-program"
    "/certificate/{n}"
)

_UA = "QU.I.R.K. CMVP refresh (https://github.com/quirk-project/quirk)"
_CACHE_PATH = Path(__file__).parent / "cmvp_cache.json"
_CURATED_CSV_PATH = Path(__file__).parent / "cmvp_curated.csv"

# Module-level cache; populated lazily by _load_cache().
_CACHE: Optional[dict] = None


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class CMVPRefreshNetworkError(RuntimeError):
    """Raised when the CMVP refresh cannot reach csrc.nist.gov.
    Maps to error code CMVP-REFRESH-NETWORK."""


class CMVPRefreshParseError(RuntimeError):
    """Raised when the CMVP search/cert page does not match expected selectors.
    Maps to error code CMVP-REFRESH-PARSE."""


# ---------------------------------------------------------------------------
# Cache loader (runtime assertion validation, per RESEARCH §Cache Schema)
# ---------------------------------------------------------------------------

def _load_cache(force_reload: bool = False) -> dict:
    """Load and validate cmvp_cache.json. Cached at module scope after first call.

    Uses importlib.resources for the read path so the cache file is accessible
    from both source-checkout and wheel installs (STAB-02 / D-08).

    Override hook: if the module-level _CACHE_PATH has been replaced (e.g. by a
    test monkeypatch) we fall back to reading it directly so that unit tests can
    supply a temporary cache without touching the real package resource.
    The write path (refresh_cache) always uses _CACHE_PATH — refresh is a
    developer-only tool intended for source-checkout use (Pitfall 2).
    """
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE
    # Use _CACHE_PATH directly when it has been patched away from the package
    # default (e.g. in tests); otherwise prefer importlib.resources for
    # wheel-safe resource loading.
    _default_path = Path(__file__).parent / "cmvp_cache.json"
    if _CACHE_PATH != _default_path:
        # Monkeypatched path — must exist; if absent the patch is incorrect,
        # not a signal to fall through to the real production cache (IN-03).
        if not _CACHE_PATH.exists():
            raise FileNotFoundError(
                f"Monkeypatched _CACHE_PATH does not exist: {_CACHE_PATH}"
            )
        _text = _CACHE_PATH.read_text(encoding="utf-8")
    else:
        _text = (
            _ir_files("quirk.compliance")
            .joinpath("cmvp_cache.json")
            .read_text(encoding="utf-8")
        )
    data = json.loads(_text)
    assert "last_verified" in data, "cmvp_cache missing 'last_verified'"
    assert "source_url" in data, "cmvp_cache missing 'source_url'"
    assert "modules" in data, "cmvp_cache missing 'modules'"
    # parseable ISO date
    datetime.date.fromisoformat(data["last_verified"])
    for m in data["modules"]:
        for key in ("certificate_number", "vendor", "name", "fips_level", "algorithms"):
            assert key in m, f"cmvp_cache module missing key {key!r}"
        assert isinstance(m["algorithms"], list)
    _CACHE = data
    return _CACHE


def staleness_days(today: Optional[datetime.date] = None) -> int:
    """Return the age of the cache in days (today - last_verified)."""
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(_load_cache()["last_verified"])
    return (reference - last_verified).days


def is_cmvp_cache_stale(today: Optional[datetime.date] = None) -> bool:
    """Phase 81 CMVP-04: True when cache age > STALENESS_THRESHOLD_DAYS.

    Boundary: strict greater-than (matches QRAMM 90-day pattern). Exactly
    90 days is NOT stale.
    """
    return staleness_days(today) > STALENESS_THRESHOLD_DAYS


# ---------------------------------------------------------------------------
# Algorithm name normalization (D-81-R6 / RESEARCH §Algorithm Name Normalization)
# ---------------------------------------------------------------------------

# Map from lowercased QUIRK mode-specific names to CAVP family names used by CMVP.
# Names absent from this map (e.g. ChaCha20-Poly1305) intentionally yield None
# so coverage_for_algorithm() returns [] -> "Not in CMVP catalog".
_FAMILY_MAP: dict[str, Optional[str]] = {
    # symmetric — AES family
    "aes": "AES",
    "aes-128-gcm": "AES",
    "aes-192-gcm": "AES",
    "aes-256-gcm": "AES",
    "aes-128-cbc": "AES",
    "aes-192-cbc": "AES",
    "aes-256-cbc": "AES",
    "aes-128-ctr": "AES",
    "aes-192-ctr": "AES",
    "aes-256-ctr": "AES",
    "aes128-ctr": "AES",
    "aes192-ctr": "AES",
    "aes256-ctr": "AES",
    "aes128-cbc": "AES",
    "aes192-cbc": "AES",
    "aes256-cbc": "AES",
    "aes128-gcm@openssh.com": "AES",
    "aes256-gcm@openssh.com": "AES",
    "aes-cbc": "AES",
    "aes-ctr": "AES",
    "aes-gcm": "AES",

    # legacy symmetric
    "3des": "TripleDES",
    "triple-des": "TripleDES",
    "des-ede3-cbc": "TripleDES",

    # asymmetric / signature — RSA
    "rsa": "RSA",
    "rsa-sha2-256": "RSA",
    "rsa-sha2-512": "RSA",
    "ssh-rsa": "RSA",

    # asymmetric / signature — ECDSA
    "ecdsa": "ECDSA",
    "ecdsa-sha2-nistp256": "ECDSA",
    "ecdsa-sha2-nistp384": "ECDSA",
    "ecdsa-sha2-nistp521": "ECDSA",

    # asymmetric / signature — DSA (legacy)
    "dsa": "DSA",
    "ssh-dss": "DSA",

    # EdDSA
    "ed25519": "EdDSA",
    "ssh-ed25519": "EdDSA",
    "ed448": "EdDSA",

    # KEX / KAS
    "ecdh-sha2-nistp256": "KAS",
    "ecdh-sha2-nistp384": "KAS",
    "ecdh-sha2-nistp521": "KAS",
    "diffie-hellman-group14-sha256": "KAS",
    "diffie-hellman-group16-sha512": "KAS",
    "curve25519-sha256": "KAS",

    # PQC KEMs
    "mlkem768x25519-sha256": "ML-KEM",
    "ml-kem": "ML-KEM",
    "ml-kem-768": "ML-KEM",
    "ml-kem-1024": "ML-KEM",
    "sntrup761x25519-sha512": None,  # not NIST-validated -> []

    # hashes
    "sha-256": "SHS",
    "sha-384": "SHS",
    "sha-512": "SHS",
    "sha-224": "SHS",
    "sha2-256": "SHS",
    "sha2-384": "SHS",
    "sha2-512": "SHS",
    "sha256": "SHS",
    "sha384": "SHS",
    "sha512": "SHS",
    "sha3-256": "SHA-3",
    "sha3-384": "SHA-3",
    "sha3-512": "SHA-3",

    # MACs
    "hmac": "HMAC",
    "hmac-sha2-256": "HMAC",
    "hmac-sha2-512": "HMAC",
    "hmac-sha256": "HMAC",
    "hmac-sha512": "HMAC",

    # DRBG
    "drbg": "DRBG",
    "hash-drbg": "DRBG",
    "hmac-drbg": "DRBG",
    "ctr-drbg": "DRBG",

    # explicitly non-CMVP-approved -> None
    "chacha20-poly1305": None,
    "chacha20": None,
    "chacha20-poly1305@openssh.com": None,
}


def normalize_for_cmvp_lookup(name: str) -> Optional[str]:
    """Map a QU.I.R.K. mode-specific algorithm name to its CMVP CAVP family name.

    Returns None for algorithms not present in the CMVP catalog
    (e.g. ChaCha20-Poly1305, sntrup761). Caller renders "Not in CMVP catalog".
    """
    if not name:
        return None
    key = name.strip().lower()
    # Direct dict lookup first.
    if key in _FAMILY_MAP:
        return _FAMILY_MAP[key]

    # Regex fallbacks — order matters.
    if re.match(r"^aes[-_]?(\d+)?", key):
        return "AES"
    if re.match(r"^(rsa|ssh-rsa)", key):
        return "RSA"
    if re.match(r"^ecdsa", key):
        return "ECDSA"
    if re.match(r"^ecdh", key):
        return "KAS"
    if re.match(r"^(diffie-hellman|dh-group)", key):
        return "KAS"
    if re.match(r"^(ed25519|ed448|ssh-ed)", key):
        return "EdDSA"
    if re.match(r"^sha3[-_]", key):
        return "SHA-3"
    if re.match(r"^sha[-_]?\d+", key) or re.match(r"^sha2[-_]?\d+", key):
        return "SHS"
    if re.match(r"^hmac", key):
        return "HMAC"
    if re.match(r"^(3des|des-ede3|tripledes|triple-des)", key):
        return "TripleDES"
    if re.match(r"^(hash-|hmac-|ctr-)?drbg", key):
        return "DRBG"
    if re.match(r"^ml-?kem", key):
        return "ML-KEM"
    if re.match(r"^ml-?dsa", key):
        return "ML-DSA"
    if re.match(r"^slh-?dsa", key):
        return "SLH-DSA"

    return None


# ---------------------------------------------------------------------------
# Coverage query
# ---------------------------------------------------------------------------

def coverage_for_algorithm(name: str) -> list[dict]:
    """Return the list of CMVP modules whose algorithms include the CAVP family
    of ``name``. Ordered by:
      1. fips_level == "140-3" first
      2. module_version (descending lexicographic) as a recency proxy

    Returns [] for algorithm names absent from the CMVP catalog
    (e.g. ChaCha20-Poly1305) and for unknown names (never raises).

    The returned dicts contain ONLY informational fields (module name, vendor,
    cert number, fips_level, algorithms list). v4.10-D-01: this function NEVER
    returns a ``"certified"`` flag.
    """
    family = normalize_for_cmvp_lookup(name)
    if family is None:
        return []
    try:
        cache = _load_cache()
    except (FileNotFoundError, json.JSONDecodeError, AssertionError) as e:
        logger.warning("CMVP cache unavailable: %s", e)
        return []
    matches = [m for m in cache.get("modules", []) if family in m.get("algorithms", [])]
    matches.sort(
        key=lambda m: (
            m.get("fips_level") != "140-3",
            # Descending lexicographic by module_version: invert via tuple negation trick
            # using a sortable wrapper — simpler to sort then reverse on a secondary pass.
            -len(m.get("module_version", "")),
            m.get("module_version", ""),
        )
    )
    # Stable re-sort by module_version descending within fips tier.
    matches.sort(
        key=lambda m: (m.get("fips_level") != "140-3", m.get("module_version", "") or ""),
        reverse=False,
    )
    # Final ordering: fips=140-3 first (False<True), then by module_version desc.
    fips_first = [m for m in matches if m.get("fips_level") == "140-3"]
    fips_first.sort(key=lambda m: m.get("module_version", "") or "", reverse=True)
    others = [m for m in matches if m.get("fips_level") != "140-3"]
    others.sort(key=lambda m: m.get("module_version", "") or "", reverse=True)
    return fips_first + others


# ---------------------------------------------------------------------------
# Refresh logic
# ---------------------------------------------------------------------------

def _today_iso() -> str:
    return datetime.date.today().isoformat()


def _read_curated_cert_numbers() -> list[str]:
    """Read certificate numbers from cmvp_curated.csv (first column after header)."""
    if not _CURATED_CSV_PATH.exists():
        return []
    nums: list[str] = []
    with _CURATED_CSV_PATH.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            n = (row.get("certificate_number") or "").strip()
            if n:
                nums.append(n)
    return nums


def _fetch_search_index(client) -> list[dict]:
    """Fetch the CMVP search index page and return parsed rows.

    Raises CMVPRefreshParseError if the expected table is absent.
    """
    import httpx  # local import to keep module import cheap
    from bs4 import BeautifulSoup

    resp = client.get(
        CMVP_SEARCH_URL,
        params={
            "SearchMode": "Basic",
            "Standard": "140-3",
            "CertificateStatus": "Active",
            "displayall": "1",
        },
        headers={"User-Agent": _UA},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", id="searchResultsTable")
    if table is None:
        raise CMVPRefreshParseError(
            "searchResultsTable not found in NIST response — page structure may have changed"
        )
    rows: list[dict] = []
    if not table.tbody:
        return rows
    for tr in table.tbody.find_all("tr"):
        link = tr.find("a", id=lambda v: v and v.startswith("cert-number-link"))
        if not link:
            continue
        cert_no = link.get_text(strip=True)
        tds = tr.find_all("td")
        rows.append({
            "certificate_number": cert_no,
            "vendor": tds[1].get_text(strip=True) if len(tds) > 1 else "",
            "name": tds[2].get_text(strip=True) if len(tds) > 2 else "",
            "module_type": tds[3].get_text(strip=True) if len(tds) > 3 else "",
        })
    return rows


def _fetch_cert_detail(client, cert_no: str) -> dict:
    """Fetch a single certificate detail page and return the parsed module dict."""
    from bs4 import BeautifulSoup

    resp = client.get(
        CMVP_CERT_URL.format(n=cert_no),
        headers={"User-Agent": _UA},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    def _field_by_label(label: str) -> Optional[str]:
        for row in soup.select("div.row.padrow"):
            lbl = row.select_one("div.col-md-3")
            val = row.select_one("div.col-md-9")
            if lbl and val and lbl.get_text(strip=True) == label:
                return val.get_text(strip=True)
        return None

    name_div = soup.select_one("div.col-md-9#module-name")
    name = name_div.get_text(strip=True) if name_div else (_field_by_label("Module Name") or "")
    standard_div = soup.select_one("div.col-md-9#module-standard")
    standard = (
        standard_div.get_text(" ", strip=True) if standard_div
        else (_field_by_label("Standard") or "")
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
        "name": name,
        "module_version": version,
        "fips_level": fips_level,
        "overall_level": overall_level,
        "algorithms": sorted(set(algorithms)),
    }


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically: tempfile in same dir, then os.replace."""
    fd, tmp_name = tempfile.mkstemp(
        prefix=".cmvp_cache.", suffix=".json.tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=False)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _diff_caches(old: dict, new: dict) -> dict:
    """Compute added/removed/changed certificate numbers between two caches."""
    old_by_cert = {m["certificate_number"]: m for m in old.get("modules", [])}
    new_by_cert = {m["certificate_number"]: m for m in new.get("modules", [])}
    added = sorted(set(new_by_cert) - set(old_by_cert))
    removed = sorted(set(old_by_cert) - set(new_by_cert))
    changed = []
    for cert in sorted(set(old_by_cert) & set(new_by_cert)):
        if old_by_cert[cert].get("algorithms") != new_by_cert[cert].get("algorithms"):
            changed.append(cert)
    return {"added": added, "removed": removed, "changed": changed}


def refresh_cache(dry_run: bool = False) -> dict:
    """Fetch curated CMVP modules from NIST; write/preview cmvp_cache.json.

    Returns:
      - dry_run=True: a diff dict {'added': [...], 'removed': [...], 'changed': [...]}
        and writes nothing.
      - dry_run=False: the new cache dict; writes cmvp_cache.json atomically.

    Raises:
      CMVPRefreshNetworkError: any httpx transport / HTTP error.
      CMVPRefreshParseError:   expected page structure missing.
    """
    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        raise CMVPRefreshNetworkError(f"httpx not installed: {e}") from e

    curated = _read_curated_cert_numbers()
    if not curated:
        logger.warning("cmvp_curated.csv has no certificate numbers; refresh will be empty")

    modules: list[dict] = []
    timeout = httpx.Timeout(15.0, connect=5.0)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            index = {r["certificate_number"]: r for r in _fetch_search_index(client)}
            for cert_no in curated:
                base = index.get(cert_no, {})
                try:
                    detail = _fetch_cert_detail(client, cert_no)
                except CMVPRefreshParseError:
                    raise
                modules.append({
                    "certificate_number": cert_no,
                    "vendor": base.get("vendor", ""),
                    "name": detail.get("name") or base.get("name", ""),
                    "module_version": detail.get("module_version", ""),
                    "fips_level": detail.get("fips_level", "unknown"),
                    "overall_level": detail.get("overall_level", ""),
                    "algorithms": detail.get("algorithms", []),
                })
                time.sleep(0.1)  # politeness between detail-page requests
    except CMVPRefreshParseError:
        raise
    except httpx.HTTPError as e:
        raise CMVPRefreshNetworkError(
            f"CMVP refresh failed during HTTP fetch: {e}"
        ) from e
    except Exception as e:
        # Re-wrap any other transport-layer failure as a network error.
        if isinstance(e, CMVPRefreshNetworkError):
            raise
        raise CMVPRefreshNetworkError(
            f"Unexpected CMVP refresh failure: {e}"
        ) from e

    new_cache = {
        "schema_version": "1.0",
        "last_verified": _today_iso(),
        "source_url": CMVP_SEARCH_URL,
        "modules": modules,
    }

    if dry_run:
        try:
            old = _load_cache(force_reload=True)
        except (FileNotFoundError, json.JSONDecodeError, AssertionError):
            old = {"modules": []}
        return _diff_caches(old, new_cache)

    _atomic_write_json(_CACHE_PATH, new_cache)
    # Invalidate the in-memory cache so subsequent calls see the new data.
    global _CACHE
    _CACHE = None
    return new_cache

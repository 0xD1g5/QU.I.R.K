"""Container/binary scanner module (SCAN-04).

Uses syft to scan container images and returns one CryptoEndpoint per
crypto library found in the image. Degrades gracefully if syft is absent.
"""
import json
import shutil
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint
from quirk.util.subprocess_input import validate_image_ref

# Only these package names are considered crypto libraries.
# Checked against artifact["name"].lower().
CRYPTO_LIB_ALLOWLIST = frozenset({
    "openssl",
    "libssl",
    "libssl1.0",
    "libssl1.0.0",
    "libssl1.1",
    "libssl3",
    "libcrypto",
    "libcrypto3",
    "botan",
    "libgcrypt",
    "libgcrypt20",
    "nss",
    "libnss3",
    "mbedtls",
    "libmbedtls",
    "wolfssl",
    "gnutls",
    "libgnutls",
    "cryptography",
    "pyopenssl",
    "pycryptodome",
    "pycryptodomex",
    "bcrypt",
    "nacl",
    "pynacl",
})


def scan_container_image(
    image_ref: str,
    timeout: int = 120,
    logger=None,
) -> List[CryptoEndpoint]:
    """Scan a container image with syft and return CryptoEndpoints for crypto libraries.

    Returns empty list if syft is absent, subprocess fails, or JSON is invalid.
    Rejected inputs (argv injection, invalid OCI refs, etc.) return a single
    CryptoEndpoint with scan_error_category="invalid_input" and no subprocess call.
    """
    # Phase 57 / CR-03: reject argv-injection inputs before subprocess.run.
    _validation = validate_image_ref(image_ref)
    if not _validation.ok:
        if logger:
            logger.v(f"CONTAINER rejected {_validation.redacted_preview!r}: {_validation.reason}")
        return [CryptoEndpoint(
            host=_validation.redacted_preview,
            port=0,
            protocol="CONTAINER",
            scan_error=_validation.reason,
            scan_error_category="invalid_input",
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )]

    exe = shutil.which("syft")
    if not exe:
        if logger:
            logger.v(
                "syft is not installed — pip install 'quirk[cbom]' and "
                "`brew install syft` to enable container scanning"
            )
        return []

    try:
        proc = subprocess.run(
            [exe, "-o", "json", "--", image_ref],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        data = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return []

    endpoints: List[CryptoEndpoint] = []
    artifacts = data.get("artifacts", [])

    for artifact in artifacts:
        name = artifact.get("name", "")
        if name.lower() not in CRYPTO_LIB_ALLOWLIST:
            continue

        ep = CryptoEndpoint(
            host=image_ref,
            port=0,
            protocol="CONTAINER",
            cipher_suite=name,
            tls_version=artifact.get("version"),
            container_scan_json=json.dumps(artifact),
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        endpoints.append(ep)

        if logger:
            logger.v(f"CONTAINER {image_ref} {name}@{artifact.get('version')}")

    return endpoints


def scan_container_targets(
    targets: list,
    timeout: int = 120,
    logger=None,
) -> List[CryptoEndpoint]:
    """Scan a list of container image references and return all CryptoEndpoints found."""
    results: List[CryptoEndpoint] = []
    for image_ref in targets:
        try:
            eps = scan_container_image(image_ref, timeout=timeout, logger=logger)
            results.extend(eps)
        except Exception as exc:
            if logger:
                logger.v(f"Container scan error for {image_ref}: {exc}")
    return results

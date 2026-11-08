"""Container/binary scanner module (SCAN-04).

Uses syft to scan container images and returns one CryptoEndpoint per
crypto library found in the image. Degrades gracefully if syft is absent.

Phase 235.1 D-05: the defensive ``shutil.which`` fallback below stays (other
callers exist), but the engine gate in ``run_scan.py`` now records a
``missing-binary`` skip before this scanner is ever called, so a configured
container scan with syft absent never reads as "ran" with zero findings.
"""
import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint
from quirk.scanner.target_outcome import (
    OUTCOME_ANSWERED,
    OUTCOME_UNREACHABLE,
    TargetOutcomeContractError,
)
from quirk.util.safe_exc import safe_str
from quirk.util.subprocess_input import validate_image_ref

_LOG = logging.getLogger(__name__)

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
    *,
    _status=None,
) -> List[CryptoEndpoint]:
    """Scan a container image with syft and return CryptoEndpoints for crypto libraries.

    Returns empty list if syft is absent, subprocess fails, or JSON is invalid.
    Rejected inputs (argv injection, invalid OCI refs, etc.) return a single
    CryptoEndpoint with scan_error_category="invalid_input" and no subprocess call.

    ``_status`` (235.3 P-15, private): optional
    ``callable(kind, detail, row_emitted)`` told whether syft actually scanned
    the image (``answered``) or not (``unreachable``), and whether this call
    returned an in-band error row for it. Public return type is unchanged.
    """
    def _report(kind: str, detail: str = "", row_emitted: bool = False) -> None:
        if _status is not None:
            _status(kind, detail, row_emitted)

    # Phase 57 / CR-03: reject argv-injection inputs before subprocess.run.
    _validation = validate_image_ref(image_ref)
    if not _validation.ok:
        if logger:
            logger.v(f"CONTAINER rejected {_validation.redacted_preview!r}: {_validation.reason}")
        # 235.3 review A-IN-01: the reason is a fixed reason-code constant, not
        # an exception; safe_str() would render it as "str: <code>".
        _report(OUTCOME_UNREACHABLE, f"rejected: {_validation.reason}", row_emitted=True)
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
                "syft is not installed — pip install 'quirk-scanner[cbom]' and "
                "`brew install syft` to enable container scanning"
            )
        _report(OUTCOME_UNREACHABLE, "syft is not installed")
        return []

    try:
        proc = subprocess.run(
            [exe, "-o", "json", "--", image_ref],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        data = json.loads(proc.stdout)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("syft output is not an object", "", 0)
    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
        OSError,
        json.JSONDecodeError,
    ) as e:
        _LOG.warning(
            "subprocess failed in scan_container_image for %r: %s", image_ref, e
        )
        _report(OUTCOME_UNREACHABLE, safe_str(e))
        return []

    if proc.returncode != 0:
        # 235.3 review A-WR-07: a non-zero exit that still produced a parseable
        # SBOM (an ``artifacts`` list) scanned the image; keep the findings and
        # count it answered. Without artifacts there is nothing to return, so
        # never return findings under an ``unreachable`` outcome.
        if not isinstance(data.get("artifacts"), list):
            _LOG.warning(
                "syft exited with status %s for %r and produced no artifacts",
                proc.returncode, image_ref,
            )
            _report(OUTCOME_UNREACHABLE, f"syft exited with status {proc.returncode}")
            return []
        _LOG.warning(
            "syft exited with status %s for %r but produced a parseable SBOM; "
            "keeping its artifacts", proc.returncode, image_ref,
        )
    _report(OUTCOME_ANSWERED)

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
    *,
    outcomes=None,
) -> List[CryptoEndpoint]:
    """Scan a list of container image references and return all CryptoEndpoints found.

    235.3 P-15 / D-05: when ``outcomes`` (a TargetOutcomes sink) is supplied,
    one outcome is recorded per image against the raw image ref.
    """
    results: List[CryptoEndpoint] = []
    for image_ref in targets:
        status: list = []
        try:
            eps = scan_container_image(
                image_ref, timeout=timeout, logger=logger,
                _status=(lambda k, d="", r=False: status.append((k, d, r))),
            )
            results.extend(eps)
        except TargetOutcomeContractError:
            raise
        except Exception as exc:
            if logger:
                logger.v(f"Container scan error for {image_ref}: {safe_str(exc)}")
            if outcomes is not None:
                outcomes.record(image_ref, OUTCOME_UNREACHABLE, safe_str(exc))
            continue
        if outcomes is not None:
            kind, detail, row_emitted = (
                status[-1] if status else (OUTCOME_UNREACHABLE, "no status", False)
            )
            outcomes.record(image_ref, kind, detail, row_emitted=row_emitted)
    return results

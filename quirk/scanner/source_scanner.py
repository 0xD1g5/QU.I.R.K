"""Source code scanner module (SCAN-05).

Uses semgrep with the p/cryptography ruleset to find insecure cryptographic
usage in source repositories. Returns one CryptoEndpoint per finding.
Degrades gracefully if semgrep is absent.
"""
import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint
from quirk.util.subprocess_input import validate_repo_path

_LOG = logging.getLogger(__name__)


def scan_source_repo(
    repo_path: str,
    timeout: int = 300,
    logger=None,
) -> List[CryptoEndpoint]:
    """Scan a source repository with semgrep and return CryptoEndpoints for findings.

    Each finding maps to one CryptoEndpoint with:
    - protocol="SOURCE"
    - cipher_suite = semgrep check_id
    - service_detail = "file:line"
    - source_scan_json = full finding JSON

    Returns empty list if semgrep is absent, subprocess fails, or JSON is invalid.
    Rejected inputs (argv injection, path traversal, etc.) return a single
    CryptoEndpoint with scan_error_category="invalid_input" and no subprocess call.
    """
    # Phase 57 / CR-02: reject argv-injection inputs before subprocess.run.
    _validation = validate_repo_path(repo_path)
    if not _validation.ok:
        if logger:
            logger.v(f"SOURCE rejected {_validation.redacted_preview!r}: {_validation.reason}")
        return [CryptoEndpoint(
            host=_validation.redacted_preview,
            port=0,
            protocol="SOURCE",
            scan_error=_validation.reason,
            scan_error_category="invalid_input",
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )]

    exe = shutil.which("semgrep")
    if not exe:
        if logger:
            logger.v(
                "semgrep is not installed — pip install 'quirk[cbom]' and "
                "`pip install semgrep` to enable source code scanning"
            )
        return []

    try:
        proc = subprocess.run(
            [exe, "--json", "--config", "p/cryptography", "--", repo_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        data = json.loads(proc.stdout)
    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
        OSError,
        json.JSONDecodeError,
    ) as e:
        _LOG.warning(
            "subprocess failed in scan_source_repo for %r: %s", repo_path, e
        )
        return []

    endpoints: List[CryptoEndpoint] = []
    results = data.get("results", [])

    for result in results:
        check_id = result.get("check_id", "")
        path = result.get("path", "")
        line = result.get("start", {}).get("line", 0)
        service_detail = f"{path}:{line}"

        ep = CryptoEndpoint(
            host=repo_path,
            port=0,
            protocol="SOURCE",
            cipher_suite=check_id,
            service_detail=service_detail,
            source_scan_json=json.dumps(result),
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        endpoints.append(ep)

        if logger:
            logger.v(f"SOURCE {repo_path} {check_id} at {service_detail}")

    return endpoints


def scan_source_targets(
    targets: list,
    timeout: int = 300,
    logger=None,
) -> List[CryptoEndpoint]:
    """Scan a list of repository paths and return all CryptoEndpoints found."""
    results: List[CryptoEndpoint] = []
    for repo_path in targets:
        try:
            eps = scan_source_repo(repo_path, timeout=timeout, logger=logger)
            results.extend(eps)
        except Exception as exc:
            if logger:
                logger.v(f"Source scan error for {repo_path}: {exc}")
    return results

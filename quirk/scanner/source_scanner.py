"""Source code scanner module (SCAN-05).

Runs semgrep with the p/cryptography ruleset to find insecure cryptographic
usage in source repositories. Returns one CryptoEndpoint per finding.

Known defect (5.28.0): the p/cryptography ruleset is unavailable (the Semgrep
registry returns HTTP 404), so a run with semgrep present exits 7 with valid
JSON and ``results: []``. That is reported as "ruleset unavailable" and the
source domain reads Not assessed, never a clean repo. An absent semgrep binary
is still a graceful skip (empty list).
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

_MAX_DETAIL = 200


class SourceScanError(Exception):
    """A semgrep run failed. Messages are persisted and API-served, so they
    must not contain raw semgrep stdout or the repo path."""


class SourceRulesetUnavailable(SourceScanError):
    """The semgrep ruleset could not be loaded (404 / invalid configuration).
    Messages are persisted and API-served: no raw stdout, no repo path."""


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

    Returns empty list if semgrep is absent. Raises SourceScanError (or
    SourceRulesetUnavailable) if semgrep runs but fails or its output is invalid.
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
                "semgrep is not installed — pip install 'quirk-scanner[cbom]' and "
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
    except subprocess.TimeoutExpired as e:
        _LOG.warning("semgrep timed out in scan_source_repo for %r", repo_path)
        raise SourceScanError(
            f"source scan failed: TimeoutExpired: timed out after {timeout} s"
        ) from e
    except (
        subprocess.CalledProcessError,
        OSError,
        json.JSONDecodeError,
    ) as e:
        _LOG.warning(
            "subprocess failed in scan_source_repo for %r: %s", repo_path, e
        )
        raise SourceScanError(
            f"source scan failed: {e.__class__.__name__}"
        ) from e

    if not isinstance(data, dict):
        raise SourceScanError("source scan failed: unexpected semgrep output")

    error_entries = [
        e for e in (data.get("errors") or [])
        if isinstance(e, dict) and e.get("level") == "error"
    ]
    if proc.returncode not in (0, 1) or error_entries:
        first = str(error_entries[0].get("message", "")) if error_entries else ""
        first = first[:_MAX_DETAIL]
        _LOG.warning(
            "semgrep failed in scan_source_repo (exit %s): %s",
            proc.returncode, first,
        )
        is_ruleset = proc.returncode == 7 or any(
            "configuration" in str(e.get("message", "")).lower()
            for e in error_entries
        )
        if is_ruleset:
            raise SourceRulesetUnavailable(
                f"ruleset unavailable: semgrep exited {proc.returncode}: {first}"
            )
        raise SourceScanError(
            f"source scan failed: semgrep exited {proc.returncode}: {first}"
        )

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
        except SourceScanError:
            raise
        except Exception as exc:
            if logger:
                logger.v(f"Source scan error for {repo_path}: {exc}")
    return results

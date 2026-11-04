"""Source code scanner module (SCAN-05).

Runs semgrep with the p/cryptography ruleset to find insecure cryptographic
usage in source repositories. Returns one CryptoEndpoint per finding.

Known defect (5.28.0): the p/cryptography ruleset is unavailable (the Semgrep
registry returns HTTP 404), so a run with semgrep present exits 7 with valid
JSON and ``results: []``. That is reported as "ruleset unavailable" and the
source domain reads Not assessed, never a clean repo. An absent semgrep binary
returns an empty list at the scanner level; the engine gate in run_scan.py
records the missing-binary skip (235.1-01). Per-target failures are in-band
SOURCE error rows (235.1-03): one failing repo never discards the others, and
``scan_source_targets`` raises only when every target failed.
"""
import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str
from quirk.util.subprocess_input import validate_repo_path

_LOG = logging.getLogger(__name__)

_MAX_DETAIL = 200


class SourceScanError(Exception):
    """A semgrep run failed. Messages are persisted and API-served, so they
    must not contain raw semgrep stdout or the repo path."""

    category = "exception"


class SourceScanTimeout(SourceScanError):
    """A semgrep run exceeded its per-target timeout."""

    category = "timeout"


class SourceRulesetUnavailable(SourceScanError):
    """The semgrep ruleset could not be loaded (404 / invalid configuration).
    Messages are persisted and API-served: no raw stdout, no repo path."""


# A path character, and a single space that continues a path (WR-03): the next
# word holds a separator or starts uppercase/digit ("Acme Corp/src", "John Doe\\x").
_PATH_CH = r"[^\s'\"):,;]"
_PATH_BODY = rf"(?:{_PATH_CH}|[ ](?={_PATH_CH}*[\\/]|[A-Z0-9]))*"
_POSIX_PATH = re.compile(rf"(?<![\w<>])/{_PATH_BODY}")
_WIN_PATH = re.compile(rf"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{_PATH_BODY}")
_UNC_PATH = re.compile(rf"\\\\(?:{_PATH_CH}|[ ](?={_PATH_CH}*[\\/]|[A-Z0-9]))+")
_PATH_END = r"""(?=$|[/\\\s'":),;]|\.(?:\s|$))"""


def _repo_candidates(repo_path: str) -> list:
    """Spellings of the configured repo path worth replacing (WR-03/04/07)."""
    if not repo_path:  # IN-07: realpath("") is the CWD
        return []
    raw = {repo_path}
    try:
        raw.add(os.path.realpath(repo_path))
    except (OSError, ValueError):
        pass
    out = set()
    for c in raw:
        for v in (c, c.replace("\\", "/"), c.replace("/", "\\")):
            # WR-04: a bare relative token ("." / "src") is not a path to
            # replace; its realpath (absolute) spelling covers the real use.
            absolute = v.startswith(("/", "\\")) or re.match(r"[A-Za-z]:[\\/]", v)
            if len(v) < 3 or not (absolute or "/" in v or "\\" in v):
                continue
            out.add(v)
    return sorted(out, key=len, reverse=True)


def _redact(message: str, repo_path: str) -> str:
    """Strip the repo path and any absolute-path shape, then truncate (WR-02).

    The repo path is replaced only as a whole path (never inside a word), in
    its slash-normalised spellings; remaining POSIX / Windows / UNC absolute
    paths, including ones with spaces, collapse to ``<path>``.
    """
    msg = str(message)
    for cand in _repo_candidates(repo_path):
        flags = re.IGNORECASE if ("\\" in cand or re.match(r"[A-Za-z]:", cand)) else 0
        msg = re.sub(
            rf"(?<![\w.\-]){re.escape(cand)}{_PATH_END}", "<repo>", msg, flags=flags
        )
    msg = _UNC_PATH.sub("<path>", msg)
    msg = _WIN_PATH.sub("<path>", msg)
    msg = _POSIX_PATH.sub("<path>", msg)
    return msg[:_MAX_DETAIL]


def _repo_label(repo_path: str) -> str:
    """Redacted host label for an error row: the final path component only."""
    base = os.path.basename(str(repo_path).rstrip("/\\"))
    base = "".join(ch for ch in base if ch.isprintable())[:32]
    return base or "<repo>"


def _error_row(repo_path: str, message: str, category: str) -> CryptoEndpoint:
    return CryptoEndpoint(
        host=_repo_label(repo_path),
        port=0,
        protocol="SOURCE",
        scan_error=_redact(message, repo_path),
        scan_error_category=category,
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


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

    Returns empty list if semgrep is absent (the engine records missing-binary).
    Raises SourceScanError (or SourceRulesetUnavailable) if semgrep runs but
    fails or its output is invalid. When semgrep exits 0/1 with results AND
    level:error entries, the results are kept and one SOURCE error row is added.
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
        raise SourceScanTimeout(
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
    first = _redact(
        str(error_entries[0].get("message", "")) if error_entries else "",
        repo_path,
    )
    # IN-03: semgrep exit 7 / error code 7 = invalid or missing configuration.
    is_ruleset = proc.returncode == 7 or any(
        e.get("code") == 7 for e in error_entries
    )
    if is_ruleset:
        _LOG.warning("semgrep ruleset unavailable (exit %s)", proc.returncode)
        raise SourceRulesetUnavailable(
            f"ruleset unavailable: semgrep exited {proc.returncode}: {first}"
        )
    if proc.returncode not in (0, 1):
        _LOG.warning("semgrep failed in scan_source_repo (exit %s)", proc.returncode)
        raise SourceScanError(
            f"source scan failed: semgrep exited {proc.returncode}: {first}"
        )

    results = data.get("results", [])
    if not isinstance(results, list):
        raise SourceScanError("source scan failed: unexpected semgrep results")
    if any(not isinstance(r, dict) for r in results):
        raise SourceScanError("source scan failed: malformed semgrep result entry")

    endpoints: List[CryptoEndpoint] = []

    for result in results:
        check_id = result.get("check_id", "")
        path = result.get("path", "")
        start = result.get("start", {})
        line = start.get("line", 0) if isinstance(start, dict) else 0
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

    if error_entries:
        # WR-01: partial results are kept; the error is one visible row.
        _LOG.warning("semgrep reported %d error entries", len(error_entries))
        endpoints.append(_error_row(
            repo_path,
            f"source scan incomplete: semgrep reported "
            f"{len(error_entries)} error(s): {first}",
            "exception",
        ))

    return endpoints


def scan_source_targets(
    targets: list,
    timeout: int = 300,
    logger=None,
) -> List[CryptoEndpoint]:
    """Scan repository paths; return findings plus in-band SOURCE error rows.

    A failing target becomes one error row and never discards the other
    targets' results (WR-01). Raises only when EVERY target failed:
    SourceRulesetUnavailable if all failures were ruleset-unavailable, else
    SourceScanError with a redacted summary.
    """
    results: List[CryptoEndpoint] = []
    failures: List[BaseException] = []
    for repo_path in targets:
        try:
            eps = scan_source_repo(repo_path, timeout=timeout, logger=logger)
            results.extend(eps)
            # WR-02: a rejected target (invalid_input) returns a row instead of
            # raising, but it is not evidence -- it counts as a failure so a mix
            # of rejected + ruleset-unavailable targets cannot read as ``ran``.
            if eps and all(e.scan_error_category == "invalid_input" for e in eps):
                failures.append(SourceScanError(
                    f"invalid target rejected: {eps[0].scan_error}"
                ))
        except SourceScanError as exc:
            failures.append(exc)
            results.append(_error_row(repo_path, safe_str(exc), exc.category))
        except Exception as exc:  # unexpected: surfaced as a row, never swallowed
            failures.append(exc)
            results.append(_error_row(repo_path, safe_str(exc), "exception"))
    if targets and len(failures) == len(targets):
        if all(isinstance(f, SourceRulesetUnavailable) for f in failures):
            raise failures[0]
        summary = _redact(
            "; ".join(sorted({safe_str(f) for f in failures})), ""
        )
        raise SourceScanError(f"source scan failed for all targets: {summary}")
    return results

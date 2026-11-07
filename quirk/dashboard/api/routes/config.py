"""Runtime config endpoints.

GET /api/config — no auth required (frontend needs this before login). This
route and `get_config()` are intentionally left untouched by Phase 192 /
PARITY-01 (T-192-20): folding it together with the effective-config route
below would either leak config to unauthenticated callers or break the
pre-login vertical bootstrap.

GET /api/config/effective — Phase 192 / PARITY-01. Auth-gated (T-192-19).
Resolves the config a scan submission would actually run with (server config
plus the caller's scan-form selections), redacts every credential
server-side (T-192-18 / D-07), and badges each field's provenance (D-04).
"""
from __future__ import annotations

import ipaddress
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any, Dict, List, Literal, Optional, Tuple

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from quirk.config import get_vertical
from quirk.config_redaction import REDACTED_SET, REDACTED_UNSET, redact_config
from quirk.errors import format_error
from quirk.util.server_config import ServerConfigError, load_server_security
from quirk.util.url_allowlist import (
    RC_INTERNAL_IP,
    RC_LINK_LOCAL,
    RC_LOOPBACK,
    _redact_url_preview,
    validate_external_url,
)
from quirk.dashboard.api.config_preview import resolve_effective_config
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.middleware.csrf import require_csrf
from quirk.dashboard.api.routes.jobs import build_advanced_overlays
from quirk.dashboard.api.schemas import (
    AdvancedScanFields,
    ConfigEffectiveResponse,
    ConfigField,
    ConfigResponse,
    ConfigSection,
    InternalTargetCheckRequest,
    InternalTargetCheckResponse,
    InternalTargetEntry,
    validate_connectors_overlay,
    validate_credential_names,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """GET /api/config — returns active vertical setting."""
    return ConfigResponse(vertical=get_vertical())


# ---------------------------------------------------------------------------
# GET /api/config/effective (PARITY-01)
# ---------------------------------------------------------------------------

effective_router = APIRouter(dependencies=[Depends(require_auth)])

# Grouping order + display titles (plan-frozen). Timeout/retry values live
# under `scan` in the config tree (ScanCfg.timeouts / ScanCfg.retry) — they
# surface as `scan.timeouts.*` / `scan.retry.*` field names within the `scan`
# section rather than inventing a section the config does not have.
_SECTION_TITLES: tuple[tuple[str, str], ...] = (
    ("targets", "Targets"),
    ("scan", "Scan"),
    ("connectors", "Connectors"),
    ("output", "Output"),
    ("assessment", "Assessment"),
    ("intelligence", "Intelligence"),
    ("security", "Security"),
)


def _flatten_paths(value: Any, prefix: str = "") -> set[str]:
    """Recursively collect every dotted key path present in a nested dict.

    Used against the overlay dict `resolve_effective_config` returns to
    determine which field paths were explicitly present in the submission
    (D-04's "user"-provenance badge).
    """
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.add(path)
            paths |= _flatten_paths(sub, path)
    return paths


def _flatten_fields(section_dict: dict, prefix: str) -> list[tuple[str, Any]]:
    """Flatten a redacted section dict into (dotted_path, leaf_value) pairs.

    Nested dataclasses (e.g. `scan.timeouts` / `scan.retry`) are dicts in the
    redaction output and recurse into `scan.timeouts.*` /
    `scan.retry.*` field names — never a synthetic section. Credential leaves
    are already replaced with a placeholder STRING by the redaction call, so
    any dict value encountered here is a genuine nested structure to descend
    into, never a credential leaf.
    """
    out: list[tuple[str, Any]] = []
    for key, value in section_dict.items():
        path = f"{prefix}.{key}"
        if isinstance(value, dict):
            out.extend(_flatten_fields(value, path))
        else:
            out.append((path, value))
    return out


def _build_section_fields(
    section_name: str,
    section_dict: dict,
    user_paths: set[str],
    preset_paths: frozenset[str],
    connectors_user_set: set[str],
) -> list[ConfigField]:
    fields: list[ConfigField] = []
    for full_path, value in _flatten_fields(section_dict, section_name):
        rel_name = full_path[len(section_name) + 1:]
        redacted = value in (REDACTED_SET, REDACTED_UNSET)
        credential_status = None
        if redacted:
            credential_status = "set" if value == REDACTED_SET else "not set"

        # "user" wins over "preset" — an explicit operator value is the one
        # apply_profile was suppressed by (Phase 72 D-02/WR-11).
        if full_path in user_paths or (
            section_name == "connectors" and rel_name in connectors_user_set
        ):
            provenance: Literal["default", "user", "preset"] = "user"
        elif full_path in preset_paths:
            provenance = "preset"
        else:
            provenance = "default"

        fields.append(
            ConfigField(
                name=rel_name,
                value=value,
                provenance=provenance,
                redacted=redacted,
                credential_status=credential_status,
            )
        )
    return fields


@effective_router.get("/config/effective", response_model=ConfigEffectiveResponse)
def get_effective_config(
    targets: Optional[str] = Query(None),
    profile: Literal["quick", "standard", "deep"] = Query("standard"),
    calibration: Literal["strict", "balanced", "lenient"] = Query("balanced"),
    enable_nmap: bool = Query(False),
    port_scope: Literal["common", "top1000", "all", "custom"] = Query("top1000"),
    custom_ports: Optional[str] = Query(None),
    vertical: Optional[str] = Query(None),
    connectors: Optional[str] = Query(
        None,
        description=(
            "JSON-encoded dict of connector overlay values -- enable_* "
            "boolean toggles plus, since Phase 197 / PARITY-05 / PARITY-06 "
            "(D-09/D-11), the 37 residual connectors.* detail fields (target "
            "lists, endpoint/identifier strings, two timeouts, one boolean). "
            "Validated through the SAME validate_connectors_overlay() the "
            "submit path uses -- not duplicated here."
        ),
    ),
    advanced: Optional[str] = Query(
        None,
        description=(
            "JSON-encoded AdvancedScanFields object (Phase 194 / PARITY-04 "
            "D-01) -- validated through the SAME model POST /api/jobs uses, "
            "so preview and submit can never disagree on what is valid."
        ),
    ),
    credential_keys: Optional[str] = Query(
        None,
        description=(
            "JSON-encoded list of credential NAMES the New Scan form has "
            "filled; names only, never values. Validated by the same "
            "allow-list as job submission."
        ),
    ),
) -> ConfigEffectiveResponse:
    """GET /api/config/effective — resolved, redacted, provenance-badged config
    preview matching what a `POST /api/jobs` submission with these query
    params would actually run with (PARITY-01)."""
    # Phase 197 / PARITY-05 / PARITY-06 / D-09/D-10/D-11 (enforcement point c):
    # validate_connectors_overlay is the SAME function ScanSubmitRequest's
    # field_validator (enforcement point a) and build_job_config_dict's merge
    # gate (enforcement point b) call -- structurally identical to how
    # `advanced` below validates through AdvancedScanFields.model_validate.
    # No isinstance/allowlist logic against connector overlay values lives in
    # this file anymore (RESEARCH Pitfall 1).
    connectors_overlay: Optional[dict] = None
    if connectors is not None:
        try:
            connectors_overlay = json.loads(connectors)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="connectors must be a JSON object of connector overlay values",
            ) from exc
        if not isinstance(connectors_overlay, dict):
            raise HTTPException(
                status_code=422,
                detail="connectors must be a JSON object of connector overlay values",
            )
        try:
            connectors_overlay = validate_connectors_overlay(connectors_overlay)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 225.1 / D-09, D-24: names-only credential presence; same allow-list as submit.
    credential_names: set = set()
    if credential_keys is not None:
        _bad = "credential_keys must be a JSON list of credential name strings"
        try:
            _names = json.loads(credential_keys)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=_bad) from exc
        if not isinstance(_names, list) or not all(isinstance(n, str) for n in _names):
            raise HTTPException(status_code=422, detail=_bad)
        try:
            credential_names = set(validate_credential_names(_names))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Phase 194 / PARITY-04 / D-01: JSON-decode, then validate through the
    # SAME AdvancedScanFields model the submit path uses (never a second
    # ad hoc validator), then derive the two overlays via the shared helper.
    scan_overlay: Optional[dict] = None
    assessment_overlay: Optional[dict] = None
    if advanced is not None:
        try:
            advanced_raw = json.loads(advanced)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    "advanced must be a JSON object matching the "
                    "AdvancedScanFields shape"
                ),
            ) from exc
        try:
            advanced_model = AdvancedScanFields.model_validate(advanced_raw)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        # Phase 194 / PARITY-04 / D-03 / D-16: build_advanced_overlays calls
        # parse_port_spec, which raises ValueError on a malformed ports_tls
        # (AdvancedScanFields only bounds it by max_length, not numerically).
        # The submit path (jobs.py) converts that ValueError to 422; the GET
        # preview must do the same so preview/submit can never disagree on
        # what is valid -- otherwise a malformed advanced.ports_tls escapes as
        # an unhandled 500 here.
        try:
            scan_overlay, assessment_overlay = build_advanced_overlays(advanced_model)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        resolved_cfg, overlay_dict, preset_changed = resolve_effective_config(
            targets=targets,
            profile=profile,
            calibration=calibration,
            enable_nmap=enable_nmap,
            port_scope=port_scope,
            custom_ports=custom_ports,
            vertical=vertical,
            connectors_overlay=connectors_overlay,
            scan_overlay=scan_overlay,
            assessment_overlay=assessment_overlay,
        )
    except ServerConfigError as exc:
        logger.error("Server security configuration could not be read: %s", exc)
        raise HTTPException(status_code=503, detail=format_error("DASHBOARD-014")) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Single serialization path (D-07 / T-192-18): both the grouped view and
    # the raw view are built from this ONE redaction call — there is no
    # second, unredacted dump anywhere in this handler.
    redacted = redact_config(resolved_cfg)

    user_paths = _flatten_paths(overlay_dict)
    connectors_user_set = set(getattr(resolved_cfg.connectors, "_user_set_fields", frozenset()))

    sections: list[ConfigSection] = []
    redacted_field_count = 0
    raw: dict = {}
    for section_name, title in _SECTION_TITLES:
        section_dict = redacted.get(section_name) or {}
        raw[section_name] = section_dict
        fields = _build_section_fields(
            section_name, section_dict, user_paths, preset_changed, connectors_user_set,
        )
        if section_name == "connectors" and credential_names:
            for f in fields:
                if f.redacted and f.name in credential_names:
                    f.credential_status = "set"
        redacted_field_count += sum(1 for f in fields if f.redacted)
        sections.append(ConfigSection(name=section_name, title=title, fields=fields))

    return ConfigEffectiveResponse(
        vertical=vertical or get_vertical(),
        profile=profile,
        sections=sections,
        raw=raw,
        redacted_field_count=redacted_field_count,
    )


# ---------------------------------------------------------------------------
# POST /api/config/internal-target-check (235.3 / D-11 / P-12)
# ---------------------------------------------------------------------------

_INTERNAL_REASONS = frozenset({RC_LOOPBACK, RC_INTERNAL_IP, RC_LINK_LOCAL})
# C-WR-01: the connector URL lists the server's allow_internal_targets policy
# actually refuses. run_scan.py threads cfg.security.allow_internal_targets
# into the JWT and SAML scanners for these lists only. Plain scan targets are
# TLS / SSH, which ignore the policy, so they are never checked here: telling
# the operator "these connectors will be skipped" for them would be false.
_POLICY_GATED_FIELDS = ("jwt_targets", "saml_targets")
# C-WR-07: bounds on what one request can make the server do. Values beyond
# _INTERNAL_CHECK_LIMIT, hostnames beyond _INTERNAL_DNS_LIMIT, and lookups
# still running at the deadline are not checked, and the answer says
# truncated. Lookups run on a small dedicated pool, never inline on the
# shared AnyIO threadpool, so a slow resolver cannot starve the dashboard.
_INTERNAL_CHECK_LIMIT = 32
_INTERNAL_DNS_LIMIT = 16
_INTERNAL_CHECK_DEADLINE_S = 3.0
_DNS_WORKERS = 4
_dns_pool: Optional[ThreadPoolExecutor] = None
_dns_pool_lock = threading.Lock()
_HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _dns_executor() -> ThreadPoolExecutor:
    global _dns_pool
    with _dns_pool_lock:
        if _dns_pool is None:
            _dns_pool = ThreadPoolExecutor(
                max_workers=_DNS_WORKERS, thread_name_prefix="quirk-preflight-dns"
            )
        return _dns_pool


def _is_complete_hostname(host: str) -> bool:
    """True for a syntactically complete DNS name worth resolving.

    C-WR-07: the form fires the preflight on a typing pause, so a value typed
    half-way ("http://loc", "https://a.example.c") must not reach the
    resolver. ``localhost`` is accepted (a hosts-file answer); anything else
    needs at least two valid labels and an alphabetic TLD of 2+ characters.
    """
    if host == "localhost" or host.endswith(".localhost"):
        return True
    labels = host.split(".")
    if len(labels) < 2 or not all(_HOST_LABEL_RE.match(lb) for lb in labels):
        return False
    tld = labels[-1]
    return len(tld) >= 2 and tld.isalpha()


def _checked_url_for(value: str) -> Optional[Tuple[str, bool]]:
    """Return (url to classify, needs DNS) for *value*, or None to skip it."""
    value = value.strip()
    if not value:
        return None
    if "://" in value:
        url = value
    else:
        host = value
        if host.count(":") > 1 and not host.startswith("["):
            host = f"[{host}]"
        url = f"http://{host}/"
    try:
        host = (urlsplit(url).hostname or "").rstrip(".").lower()
    except ValueError:
        return None
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return (url, True) if _is_complete_hostname(host) else None
    return url, False


def _internal_reason_for(url: str) -> Optional[str]:
    """Return an internal-range reason code for *url*, or None.

    Uses the real SSRF guard (validate_external_url, DNS resolution only, no
    connection). Metadata / console / bad-scheme / DNS-failure verdicts are
    not "internal" -- flipping the policy would not help (P-04).
    """
    try:
        result = validate_external_url(url, allow_internal=False)
    except Exception:  # defensive: a malformed value is never an internal hit
        return None
    if not result.ok and result.reason in _INTERNAL_REASONS:
        return result.reason
    return None


def classify_internal_targets(
    values_by_field: Dict[str, List[str]],
    limit: int = _INTERNAL_CHECK_LIMIT,
    dns_limit: int = _INTERNAL_DNS_LIMIT,
    deadline: Optional[float] = None,
) -> Tuple[List[InternalTargetEntry], bool]:
    """Classify submitted values; return (internal entries, truncated).

    IP literals are classified inline (no DNS). Hostnames resolve on the
    dedicated pool under one wall-clock *deadline* (default
    _INTERNAL_CHECK_DEADLINE_S, read at call time); a lookup still running at
    the deadline is abandoned and marks the answer truncated.
    """
    if deadline is None:
        deadline = _INTERNAL_CHECK_DEADLINE_S
    planned: List[Tuple[str, str, bool]] = []
    truncated = False
    dns_count = 0
    for field, values in values_by_field.items():
        for value in values:
            plan = _checked_url_for(value)
            if plan is None:
                continue
            url, needs_dns = plan
            if len(planned) >= limit or (needs_dns and dns_count >= dns_limit):
                truncated = True
                continue
            dns_count += int(needs_dns)
            planned.append((field, url, needs_dns))

    reasons: Dict[int, Optional[str]] = {}
    futures = {}
    for idx, (_field, url, needs_dns) in enumerate(planned):
        if needs_dns:
            futures[_dns_executor().submit(_internal_reason_for, url)] = idx
        else:
            reasons[idx] = _internal_reason_for(url)
    if futures:
        done, not_done = wait(list(futures), timeout=deadline)
        for fut in not_done:
            fut.cancel()
            truncated = True
        for fut in done:
            reasons[futures[fut]] = fut.result()

    entries: List[InternalTargetEntry] = []
    for idx, (field, url, _needs_dns) in enumerate(planned):
        reason = reasons.get(idx)
        if reason:
            entries.append(
                InternalTargetEntry(
                    field=field,
                    preview=_redact_url_preview(url, max_len=64),
                    reason=reason,
                )
            )
    return entries, truncated


@effective_router.post(
    "/config/internal-target-check",
    response_model=InternalTargetCheckResponse,
    dependencies=[Depends(require_csrf)],
)
def post_internal_target_check(
    body: InternalTargetCheckRequest,
) -> InternalTargetCheckResponse:
    """POST /api/config/internal-target-check -- which submitted connector
    URLs the server's internal-target policy will refuse (235.3 D-11).

    Auth: inherited from router-level require_auth (do NOT add per-route).
    C-WR-07: POST + the X-Quirk-Request CSRF header, so a cross-site page
    cannot make the server resolve names it chooses (auth is a passthrough
    when no QUIRK_API_TOKEN is set). Read-only warning surface: the policy
    comes only from load_server_security(); a client-sent
    allow_internal_targets is ignored. DNS resolution only, never a
    connection, and bounded by the limits above.
    """
    overlay: dict = {}
    if body.connectors is not None:
        try:
            overlay = validate_connectors_overlay(body.connectors) or {}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    sec = load_server_security()
    if sec.error:
        logger.error("Server security configuration could not be read: %s", sec.error)
        return InternalTargetCheckResponse(
            allow_internal_targets=False,
            config_error=format_error("DASHBOARD-014"),
            internal=[],
        )
    if sec.allow_internal_targets:
        return InternalTargetCheckResponse(allow_internal_targets=True, internal=[])

    values: Dict[str, List[str]] = {
        field: [v for v in (overlay.get(field) or []) if isinstance(v, str)]
        for field in _POLICY_GATED_FIELDS
    }
    # C-WR-03: openapi_spec_path is a ScanCfg field, not a connector overlay
    # key; validate_connectors_overlay rejects it, so it is never checked here.
    internal, truncated = classify_internal_targets(values)
    return InternalTargetCheckResponse(
        allow_internal_targets=False, internal=internal, truncated=truncated
    )

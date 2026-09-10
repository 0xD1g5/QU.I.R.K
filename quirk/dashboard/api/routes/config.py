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

import json
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from quirk.config import get_vertical
from quirk.config_redaction import REDACTED_SET, REDACTED_UNSET, redact_config
from quirk.dashboard.api.config_preview import resolve_effective_config
from quirk.dashboard.api.middleware.auth import require_auth
from quirk.dashboard.api.routes.jobs import build_advanced_overlays
from quirk.dashboard.api.schemas import (
    AdvancedScanFields,
    ConfigEffectiveResponse,
    ConfigField,
    ConfigResponse,
    ConfigSection,
)

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
            "JSON-encoded dict[str, bool] of enable_* connector flags the "
            "operator has explicitly toggled (D-16 live preview). Unknown "
            "keys are rejected 422 by the same allowlist build_job_config_dict "
            "enforces on submit — not duplicated here."
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
) -> ConfigEffectiveResponse:
    """GET /api/config/effective — resolved, redacted, provenance-badged config
    preview matching what a `POST /api/jobs` submission with these query
    params would actually run with (PARITY-01)."""
    connectors_overlay: Optional[dict] = None
    if connectors is not None:
        try:
            connectors_overlay = json.loads(connectors)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="connectors must be a JSON object mapping enable_* flags to booleans",
            ) from exc
        if not isinstance(connectors_overlay, dict) or not all(
            isinstance(v, bool) for v in connectors_overlay.values()
        ):
            raise HTTPException(
                status_code=422,
                detail="connectors must be a JSON object mapping enable_* flags to booleans",
            )

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
        redacted_field_count += sum(1 for f in fields if f.redacted)
        sections.append(ConfigSection(name=section_name, title=title, fields=fields))

    return ConfigEffectiveResponse(
        vertical=vertical or get_vertical(),
        profile=profile,
        sections=sections,
        raw=raw,
        redacted_field_count=redacted_field_count,
    )

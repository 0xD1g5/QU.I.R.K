"""quirk.report_profiles — Phase 200 / RPT-04: named report branding/template
profiles.

An engagement's report branding + template settings (client_name,
engagement_name, prepared_by, cover_date, confidentiality_line, logo_path,
template_dir) repeat across consulting engagements that share a house style.
This module lets an operator save those values once under a name and re-apply
them on later engagements without re-entering them in every config.yaml.

Two invariants hold for every function in this module:

1. **Explicit config always wins.** ``apply_report_profile`` fills a field on
   ``cfg.report`` / ``cfg.report.branding`` ONLY when that field's flattened
   key is absent from ``cfg.report._user_set_fields`` (the frozenset stamped
   by ``quirk.config.config_from_dict``, plan 200-02). A profile can never
   override a value the operator wrote in their own engagement config.
2. **The profile name is a validated path component.** ``<name>.yaml`` is
   joined onto the profiles directory, so a name is a path-traversal vector
   even though it is not declared as a "path" field. Every function that
   touches the filesystem calls ``validate_profile_name`` BEFORE constructing
   any path from the caller-supplied name.

Only ``yaml.safe_load`` / ``yaml.safe_dump`` are used — ``yaml.load`` is an
RCE surface and is banned repo-wide.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from quirk.config import validate_report_path_field
from quirk.errors import format_error

_LOGGER = logging.getLogger(__name__)

# [A-Za-z0-9_-]{1,64} — a bare identifier, safe as a single path component.
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Flattened branding field names recognized inside a profile file's
# `branding:` sub-table. Mirrors quirk.config.ReportBrandingCfg's field set.
_BRANDING_FIELDS = frozenset(
    {
        "logo_path",
        "client_name",
        "engagement_name",
        "prepared_by",
        "cover_date",
        "confidentiality_line",
    }
)

# Top-level fields a profile file may carry outside `branding:`. `profile`
# itself is deliberately excluded — a profile file never names another
# profile, avoiding self-reference.
_REPORT_FIELDS = frozenset({"template_dir"})


def profiles_dir() -> Path:
    """Return the report-profiles directory.

    ``QUIRK_PROFILES_DIR`` env var wins over the default
    ``~/.quirk/report_profiles`` (mirrors the env-wins idiom in
    ``quirk.config.get_vertical()``). This is the ONE place the user's home
    directory is resolved in this module — every other function routes
    through here.
    """
    env_val = os.environ.get("QUIRK_PROFILES_DIR")
    if env_val:
        return Path(env_val)
    return Path.home() / ".quirk" / "report_profiles"


def validate_profile_name(name: str) -> str:
    """Validate a report-profile name as a safe bare path component.

    Accepts ``[A-Za-z0-9_-]{1,64}`` only. Raises ``ValueError`` (carrying the
    coded ``CONFIG-004`` message and the offending name) for anything else —
    including traversal-shaped names (``..``, ``../evil``), path-separator-
    bearing names (``a/b``), the empty string, and names over 64 characters.

    MUST be called before any path is constructed from ``name``.
    """
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError(
            f"{format_error('CONFIG-004')} (field='report.profile', value={name!r})"
        )
    return name


def _profile_path(name: str) -> Path:
    """Validate ``name`` then return its on-disk path. Name validation
    always precedes path construction."""
    validate_profile_name(name)
    return profiles_dir() / f"{name}.yaml"


def save_profile(name: str, cfg: Any) -> Path:
    """Save ``cfg.report``'s branding + template_dir fields as a named
    profile.

    Validates ``name`` (a path component) before touching the filesystem,
    creates the profiles directory if needed, and writes the set (non-None)
    branding fields plus ``template_dir`` (when set) as YAML via
    ``yaml.safe_dump``. ``profile`` is never written into a profile file — a
    profile does not name another profile.

    Overwrite semantics: saving over an existing profile name overwrites it.
    This is deliberate (T-200-19, accepted risk) — the CLI layer is
    responsible for reporting the overwrite explicitly on stdout, this
    function does not warn or refuse.

    Returns the path written.
    """
    path = _profile_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)

    report_cfg = getattr(cfg, "report", None)
    branding_cfg = getattr(report_cfg, "branding", None)

    payload: Dict[str, Any] = {}
    branding_payload: Dict[str, Any] = {}
    for field_name in _BRANDING_FIELDS:
        value = getattr(branding_cfg, field_name, None)
        if value is not None:
            branding_payload[field_name] = value
    if branding_payload:
        payload["branding"] = branding_payload

    template_dir = getattr(report_cfg, "template_dir", None)
    if template_dir is not None:
        payload["template_dir"] = template_dir

    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, default_flow_style=False, sort_keys=True)

    return path


def list_profiles() -> List[str]:
    """Return the sorted list of saved profile names. An absent profiles
    directory is not an error — it returns an empty list."""
    directory = profiles_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml"))


def load_profile(name: str) -> Dict[str, Any]:
    """Load a saved profile's raw dict via ``yaml.safe_load``.

    Validates ``name`` before constructing the path. Raises a coded
    ``CONFIG-004`` ``ValueError`` (naming the file) when the file does not
    exist, is not a mapping at the top level, or `branding:` is present but
    not a mapping. Unrecognized top-level or `branding.*` keys are logged as
    warnings and dropped rather than treated as fatal.
    """
    path = _profile_path(name)
    if not path.is_file():
        raise ValueError(
            f"{format_error('CONFIG-004')} (field='report.profile', value={name!r}) "
            f"— profile file not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(
            f"{format_error('CONFIG-004')} (field='report.profile', value={name!r}) "
            f"— profile file is not a mapping: {path}"
        )

    branding_raw = raw.get("branding", {}) or {}
    if not isinstance(branding_raw, dict):
        raise ValueError(
            f"{format_error('CONFIG-004')} (field='report.profile', value={name!r}) "
            f"— profile file's 'branding' key is not a mapping: {path}"
        )

    for unknown_key in sorted(set(raw.keys()) - _REPORT_FIELDS - {"branding"}):
        _LOGGER.warning(
            "%r is not a recognized report-profile option — ignored (%s)",
            unknown_key,
            path,
        )
    for unknown_key in sorted(set(branding_raw.keys()) - _BRANDING_FIELDS):
        _LOGGER.warning(
            "%r is not a recognized report-profile branding option — ignored (%s)",
            unknown_key,
            path,
        )

    result: Dict[str, Any] = {
        k: v for k, v in raw.items() if k in _REPORT_FIELDS
    }
    result["branding"] = {
        k: v for k, v in branding_raw.items() if k in _BRANDING_FIELDS
    }
    return result


def apply_report_profile(cfg: Any, name: str) -> None:
    """Apply a saved profile's values onto ``cfg.report`` / ``cfg.report.branding``.

    A profile-supplied value is applied ONLY when its flattened key
    (``template_dir``, ``branding.<field>``) is absent from
    ``cfg.report._user_set_fields`` — an explicit operator value is never
    overwritten (T-200-18). Every profile-supplied path-shaped value is
    routed through ``validate_report_path_field`` so a profile file cannot
    smuggle a traversal path past the config-load guard (T-200-17).
    """
    profile_data = load_profile(name)

    report_cfg = getattr(cfg, "report", None)
    if report_cfg is None:
        return
    branding_cfg = getattr(report_cfg, "branding", None)
    user_set = getattr(report_cfg, "_user_set_fields", frozenset())

    template_dir = profile_data.get("template_dir")
    if template_dir is not None and "template_dir" not in user_set:
        validate_report_path_field("report.template_dir", template_dir)
        report_cfg.template_dir = template_dir

    branding_data = profile_data.get("branding", {})
    for field_name, value in branding_data.items():
        if value is None:
            continue
        flattened_key = f"branding.{field_name}"
        if flattened_key in user_set:
            continue
        if field_name == "logo_path":
            validate_report_path_field("report.branding.logo_path", value)
        if branding_cfg is not None:
            setattr(branding_cfg, field_name, value)

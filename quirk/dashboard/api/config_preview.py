"""Overlay resolver for the config-preview surface.

Phase 192 / PARITY-01 / D-01 / D-03 / D-04.

`resolve_effective_config` resolves the config a scan submission would
*actually* run with — the same `build_job_config_dict` dict a real
`POST /api/jobs` call dumps, loaded through the real `load_config` +
`apply_profile` path — so the preview never disagrees with the scan. It is a
standalone, importable function (not route-private) because Phase 193's edit
form is specified to reuse it as its own preview mechanism.

Resolving through the real `load_config` + `apply_profile` path is required,
not incidental: `_user_set_fields` is populated from the raw YAML keys during
`load_config`, and `apply_profile` consults it to suppress mutation of
operator-explicit values (Phase 72 D-02 / WR-11). Re-deriving provenance any
other way would produce a preview that disagrees with the scan.
"""
from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path
from typing import Optional

import yaml

from quirk.config import AppConfig, load_config
from quirk.dashboard.api.deps import _default_db_path
from quirk.dashboard.api.routes.jobs import build_job_config_dict
from quirk.engine.profiles import apply_profile

# Nested dataclass fields on ScanCfg that are walked separately (never part of
# the shallow per-field snapshot below — apply_profile mutates their PARENT
# scalar fields, not these container fields themselves).
_SCAN_CONTAINER_FIELDS = ("timeouts", "retry")


def _snapshot_scalar_fields(instance) -> dict:
    """Shallow per-field snapshot of a dataclass instance's scalar fields.

    Deliberately NOT `copy.deepcopy` of the whole `AppConfig` — the config
    tree carries `frozenset` and nested-dataclass members and a deep copy is
    unnecessary work here; a shallow value snapshot is sufficient to detect
    which scalar fields `apply_profile` changed.
    """
    snapshot = {}
    for f in dataclasses.fields(instance):
        name = f.name
        if name.startswith("_") or name in _SCAN_CONTAINER_FIELDS:
            continue
        snapshot[name] = getattr(instance, name)
    return snapshot


def resolve_effective_config(
    *,
    targets: Optional[str] = None,
    profile: str = "standard",
    calibration: str = "balanced",
    enable_nmap: bool = False,
    port_scope: str = "top1000",
    custom_ports: Optional[str] = None,
    vertical: Optional[str] = None,
) -> tuple[AppConfig, dict, frozenset[str]]:
    """Resolve the config a `POST /api/jobs` submission with these selections
    would actually run with.

    Returns `(resolved_cfg, raw_yaml_dict, preset_changed_field_paths)`:
      - `resolved_cfg` — the loaded `AppConfig`, post-`apply_profile`.
      - `raw_yaml_dict` — the same dict `build_job_config_dict` produced (the
        overlay a real submission would dump); callers use this to determine
        which field paths were explicitly present in the submission (D-04's
        "user"-provenance badge).
      - `preset_changed_field_paths` — dotted `section.field` paths whose
        scalar value `apply_profile` changed (D-04's "preset"-provenance
        badge), e.g. `{"scan.tls_timeout_seconds", "connectors.enable_email"}`.

    `enable_nmap` is accepted for interface symmetry with `ScanSubmitRequest`
    but is not itself written into the job config dict — same as the real
    submission path, where it only affects `run_scan.py`'s `--discovery nmap`
    CLI flag, never a YAML key. `vertical` is likewise accepted for interface
    symmetry (`get_vertical()` resolves independently of `load_config`, and
    `AppConfig` has no `vertical` field); callers attach the caller-supplied
    or server-default vertical to their own response directly.
    """
    del vertical  # accepted for interface symmetry only; see docstring
    db_path = _default_db_path()

    # tempfile.TemporaryDirectory() guarantees cleanup on every path,
    # including the exception path (T-192-22).
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        config_dict = build_job_config_dict(
            output_dir,
            targets or "",
            db_path,
            calibration,
            allow_internal_targets=False,
            port_scope=port_scope,
            custom_ports=custom_ports,
        )
        config_path = output_dir / "preview-config.yaml"
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.dump(config_dict, fh, default_flow_style=False)
        cfg = load_config(str(config_path))
    # `tmp_dir` (and the temp YAML inside it) no longer exists past this point.

    scan_before = _snapshot_scalar_fields(cfg.scan)
    connectors_before = _snapshot_scalar_fields(cfg.connectors)

    apply_profile(cfg, profile)

    preset_changed_field_paths: set[str] = set()
    for name, before_value in scan_before.items():
        if getattr(cfg.scan, name) != before_value:
            preset_changed_field_paths.add(f"scan.{name}")
    for name, before_value in connectors_before.items():
        if getattr(cfg.connectors, name) != before_value:
            preset_changed_field_paths.add(f"connectors.{name}")

    return cfg, config_dict, frozenset(preset_changed_field_paths)

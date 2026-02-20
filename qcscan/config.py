from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class AssessmentCfg:
    name: str
    data_classification: str
    report_owner: str
    timezone: str


@dataclass
class ScanCfg:
    timeout_seconds: int
    concurrency: int
    ports_tls: List[int]
    include_sni: bool

    # v3.x additions (optional in YAML)
    tls_enum_mode: str = "fast"  # off|fast|deep

    fingerprint_timeout_seconds: int = 2
    fingerprint_concurrency: int = 200

    tls_timeout_seconds: int = 5
    tls_concurrency: int = 150

    ssh_timeout_seconds: int = 5
    ssh_concurrency: int = 100


@dataclass
class TargetsCfg:
    fqdns: List[str]
    cidrs: List[str]
    include_ips: List[str]
    exclude_ips: List[str]


@dataclass
class ConnectorsCfg:
    enable_aws: bool
    enable_azure: bool
    enable_windows_adcs: bool


@dataclass
class OutputCfg:
    directory: str
    db_path: str


@dataclass
class IntelligenceCfg:
    intelligence_version: str = "3.9.0"
    calibration_profile: str = "default"  # default|strict|lenient
    calibration_overrides: Optional[Dict[str, Any]] = None


@dataclass
class AppConfig:
    assessment: AssessmentCfg
    scan: ScanCfg
    targets: TargetsCfg
    connectors: ConnectorsCfg
    output: OutputCfg
    intelligence: IntelligenceCfg


def config_from_dict(raw: Dict[str, Any]) -> AppConfig:
    # Backward-compatible: if intelligence block missing, use defaults.
    intel_raw = raw.get("intelligence", {}) or {}
    overrides = intel_raw.get("calibration_overrides")
    if overrides is None:
        overrides = {}

    intelligence_cfg = IntelligenceCfg(
        intelligence_version=intel_raw.get("intelligence_version", "3.9.0"),
        calibration_profile=intel_raw.get("calibration_profile", "default"),
        calibration_overrides=overrides,
    )

    return AppConfig(
        assessment=AssessmentCfg(**raw["assessment"]),
        scan=ScanCfg(**raw["scan"]),
        targets=TargetsCfg(**raw["targets"]),
        connectors=ConnectorsCfg(**raw["connectors"]),
        output=OutputCfg(**raw["output"]),
        intelligence=intelligence_cfg,
    )


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return config_from_dict(raw)
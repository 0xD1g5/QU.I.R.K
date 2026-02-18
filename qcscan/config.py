from dataclasses import dataclass
from typing import List, Dict, Any
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

    # v3.6: TLS enum mode: "off" | "fast" | "deep"
    tls_enum_mode: str = "fast"

    # v3.7: phase-specific tuning (optional)
    fingerprint_timeout_seconds: int | None = None
    fingerprint_concurrency: int | None = None

    tls_timeout_seconds: int | None = None
    tls_concurrency: int | None = None

    ssh_timeout_seconds: int | None = None
    ssh_concurrency: int | None = None


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
class AppConfig:
    assessment: AssessmentCfg
    scan: ScanCfg
    targets: TargetsCfg
    connectors: ConnectorsCfg
    output: OutputCfg


def config_from_dict(raw: Dict[str, Any]) -> AppConfig:
    scan_raw = dict(raw["scan"])

    # defaults for new fields
    scan_raw.setdefault("tls_enum_mode", "fast")
    scan_raw.setdefault("fingerprint_timeout_seconds", None)
    scan_raw.setdefault("fingerprint_concurrency", None)
    scan_raw.setdefault("tls_timeout_seconds", None)
    scan_raw.setdefault("tls_concurrency", None)
    scan_raw.setdefault("ssh_timeout_seconds", None)
    scan_raw.setdefault("ssh_concurrency", None)

    return AppConfig(
        assessment=AssessmentCfg(**raw["assessment"]),
        scan=ScanCfg(**scan_raw),
        targets=TargetsCfg(**raw["targets"]),
        connectors=ConnectorsCfg(**raw["connectors"]),
        output=OutputCfg(**raw["output"]),
    )


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return config_from_dict(raw)

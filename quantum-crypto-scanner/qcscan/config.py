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
    return AppConfig(
        assessment=AssessmentCfg(**raw["assessment"]),
        scan=ScanCfg(**raw["scan"]),
        targets=TargetsCfg(**raw["targets"]),
        connectors=ConnectorsCfg(**raw["connectors"]),
        output=OutputCfg(**raw["output"]),
    )


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return config_from_dict(raw)

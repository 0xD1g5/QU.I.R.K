from dataclasses import dataclass, field
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
    include_sni: bool = True

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
    enable_aws: bool = False
    enable_azure: bool = False
    # Phase 3 scanner enable flags (per D-04)
    enable_jwt: bool = False
    enable_container: bool = False
    enable_source: bool = False
    # AWS connector config (per D-15)
    aws_region: str = "us-east-1"
    aws_profile: Optional[str] = None
    # Azure connector config (per D-16)
    azure_subscription_id: Optional[str] = None
    azure_keyvault_urls: list = field(default_factory=list)
    # Scanner target lists (per D-05)
    jwt_targets: list = field(default_factory=list)
    container_targets: list = field(default_factory=list)
    source_targets: list = field(default_factory=list)
    # Identity connector enable flags (v4.2, per D-04)
    enable_kerberos: bool = False
    enable_saml: bool = False
    enable_dnssec: bool = False
    # Identity connector target lists (v4.2, per D-05)
    kerberos_targets: list = field(default_factory=list)
    saml_targets: list = field(default_factory=list)
    dnssec_targets: list = field(default_factory=list)
    # GCP connector config (v4.3, Phase 26, per D-06)
    enable_gcp: bool = False
    gcp_project_id: Optional[str] = None
    # DB connector config (v4.3, Phase 27, per D-03)
    enable_db: bool = False
    pg_targets: list = field(default_factory=list)
    pg_scanner_user: Optional[str] = None
    pg_scanner_password: Optional[str] = None
    mysql_targets: list = field(default_factory=list)
    mysql_scanner_user: Optional[str] = None
    mysql_scanner_password: Optional[str] = None


@dataclass
class OutputCfg:
    directory: str
    db_path: str


@dataclass
class IntelligenceCfg:
    # Intelligence/scoring layer versioning
    intelligence_version: str = "4.2.0"

    # Score calibration profile used by scoring/reporting.
    # Supported: lenient|balanced|strict
    profile: str = "balanced"

    # Optional per-weight overrides (advanced tuning)
    calibration_overrides: Optional[Dict[str, Any]] = None


@dataclass
class AppConfig:
    assessment: AssessmentCfg
    scan: ScanCfg
    targets: TargetsCfg
    connectors: ConnectorsCfg
    output: OutputCfg
    intelligence: IntelligenceCfg


def _as_str_list(v: Any) -> List[str]:
    """Coerce a YAML value to List[str] — wraps a bare scalar in a list.

    Protects against a config.yaml that has `include_ips: 127.0.0.1` (scalar)
    instead of the correct `include_ips: ["127.0.0.1"]` (list).  Without this,
    Python's for-loop iterates the string character-by-character, producing
    single '.' values that crash socket.create_connection with an IDNA error.
    """
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def config_from_dict(raw: Dict[str, Any]) -> AppConfig:
    # Backward-compatible: if intelligence block missing, use defaults.
    intel_raw = raw.get("intelligence", {}) or {}

    # Advanced overrides are optional
    overrides = intel_raw.get("calibration_overrides")
    if overrides is None:
        overrides = {}

    # New key: intelligence.profile (lenient|balanced|strict)
    profile = intel_raw.get("profile")

    # Legacy key: intelligence.calibration_profile (default|lenient|strict)
    if not profile:
        legacy = str(intel_raw.get("calibration_profile", "default") or "default").strip().lower()
        if legacy == "default":
            profile = "balanced"
        elif legacy in ("lenient", "strict"):
            profile = legacy
        elif legacy == "balanced":
            profile = "balanced"
        else:
            profile = "balanced"

    # Normalize profile
    profile = str(profile or "balanced").strip().lower()
    if profile not in ("lenient", "balanced", "strict"):
        profile = "balanced"

    intelligence_cfg = IntelligenceCfg(
        intelligence_version=str(intel_raw.get("intelligence_version", "4.2.0") or "4.2.0"),
        profile=profile,
        calibration_overrides=overrides,
    )

    targets_raw = raw.get("targets") or {}
    targets = TargetsCfg(
        fqdns=_as_str_list(targets_raw.get("fqdns")),
        cidrs=_as_str_list(targets_raw.get("cidrs")),
        include_ips=_as_str_list(targets_raw.get("include_ips")),
        exclude_ips=_as_str_list(targets_raw.get("exclude_ips")),
    )

    return AppConfig(
        assessment=AssessmentCfg(**raw["assessment"]),
        scan=ScanCfg(**raw["scan"]),
        targets=targets,
        connectors=ConnectorsCfg(
            **{k: v for k, v in (raw.get("connectors") or {}).items() if k != "enable_windows_adcs"}
        ),
        output=OutputCfg(**raw["output"]),
        intelligence=intelligence_cfg,
    )


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return config_from_dict(raw)
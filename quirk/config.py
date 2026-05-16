import dataclasses
import os
import warnings
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
class TimeoutsCfg:
    """Phase 41 D-06: canonical [scan.timeouts] sub-table.

    Per-scanner timeout values, replacing the legacy flat
    ``*_timeout_seconds`` fields on ``ScanCfg``. Defaults match the
    documented effective post-profile values from RESEARCH §"Proposed
    [scan.timeouts] / [scan.retry] Shape".
    """
    default_seconds: int = 5
    fingerprint_seconds: int = 4
    tls_seconds: int = 6
    ssh_seconds: int = 6
    jwt_seconds: int = 10
    container_seconds: int = 120
    source_seconds: int = 300
    dnssec_seconds: int = 10
    saml_seconds: int = 10
    kerberos_seconds: int = 10
    vault_seconds: int = 10
    db_connect_seconds: int = 5
    broker_seconds: int = 10
    email_seconds: int = 10


@dataclass
class RetryCfg:
    """Phase 41 D-06: canonical [scan.retry] sub-table."""
    retry_count: int = 0
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 5.0


# Mapping of legacy ScanCfg flat kwargs → TimeoutsCfg field names.
# Used by ScanCfg.__init__ (kwarg routing) and the deprecation-alias
# properties (read-side warn-and-redirect).
_LEGACY_TIMEOUT_KWARG_MAP = {
    "timeout_seconds": "default_seconds",
    "fingerprint_timeout_seconds": "fingerprint_seconds",
    "tls_timeout_seconds": "tls_seconds",
    "ssh_timeout_seconds": "ssh_seconds",
}


@dataclass(init=False)
class ScanCfg:
    concurrency: int
    ports_tls: List[int]
    include_sni: bool = True

    # v3.x additions (optional in YAML)
    tls_enum_mode: str = "fast"  # off|fast|deep

    fingerprint_concurrency: int = 200
    tls_concurrency: int = 150
    ssh_concurrency: int = 100
    # Phase 71 / D-02 / WR-12: ThreadPool max_workers knob shared by email + broker
    # ("motion" subsystem) scanners. Default 50 preserves prior hardcoded behavior.
    motion_concurrency: int = 50

    # Phase 41 D-06: nested canonical sub-tables
    timeouts: TimeoutsCfg = field(default_factory=TimeoutsCfg)
    retry: RetryCfg = field(default_factory=RetryCfg)

    def __init__(
        self,
        concurrency: int,
        ports_tls: List[int],
        include_sni: bool = True,
        tls_enum_mode: str = "fast",
        fingerprint_concurrency: int = 200,
        tls_concurrency: int = 150,
        ssh_concurrency: int = 100,
        motion_concurrency: int = 50,
        timeouts: Optional[TimeoutsCfg] = None,
        retry: Optional[RetryCfg] = None,
        # Phase 41 D-07: legacy flat kwargs accepted for backward compat
        # (e.g. ``ScanCfg(timeout_seconds=5, ...)``). They are routed to
        # ``self.timeouts.*_seconds`` silently — the DeprecationWarning fires
        # on attribute READ, not construction.
        timeout_seconds: Optional[int] = None,
        fingerprint_timeout_seconds: Optional[int] = None,
        tls_timeout_seconds: Optional[int] = None,
        ssh_timeout_seconds: Optional[int] = None,
    ) -> None:
        self.concurrency = concurrency
        self.ports_tls = ports_tls
        self.include_sni = include_sni
        self.tls_enum_mode = tls_enum_mode
        self.fingerprint_concurrency = fingerprint_concurrency
        self.tls_concurrency = tls_concurrency
        self.ssh_concurrency = ssh_concurrency
        self.motion_concurrency = motion_concurrency
        self.timeouts = timeouts if timeouts is not None else TimeoutsCfg()
        self.retry = retry if retry is not None else RetryCfg()
        # Route legacy flat kwargs into the nested TimeoutsCfg
        legacy_values = {
            "timeout_seconds": timeout_seconds,
            "fingerprint_timeout_seconds": fingerprint_timeout_seconds,
            "tls_timeout_seconds": tls_timeout_seconds,
            "ssh_timeout_seconds": ssh_timeout_seconds,
        }
        for legacy_kw, value in legacy_values.items():
            if value is not None:
                setattr(self.timeouts, _LEGACY_TIMEOUT_KWARG_MAP[legacy_kw], int(value))

    # ---- Phase 41 D-07: deprecation-alias properties ------------------
    # Both read and write are supported for backward compat (apply_profile()
    # in quirk/engine/profiles.py still writes through the legacy names until
    # Plan 03 refactors it). Reads emit DeprecationWarning; writes route
    # silently to the corresponding TimeoutsCfg field (Plan 03 cleans the
    # remaining writers up).
    @property
    def timeout_seconds(self) -> int:
        warnings.warn(
            "ScanCfg.timeout_seconds is deprecated; use ScanCfg.timeouts.default_seconds",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.timeouts.default_seconds

    @timeout_seconds.setter
    def timeout_seconds(self, value: int) -> None:
        self.timeouts.default_seconds = int(value)

    @property
    def fingerprint_timeout_seconds(self) -> int:
        warnings.warn(
            "ScanCfg.fingerprint_timeout_seconds is deprecated; use ScanCfg.timeouts.fingerprint_seconds",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.timeouts.fingerprint_seconds

    @fingerprint_timeout_seconds.setter
    def fingerprint_timeout_seconds(self, value: int) -> None:
        self.timeouts.fingerprint_seconds = int(value)

    @property
    def tls_timeout_seconds(self) -> int:
        warnings.warn(
            "ScanCfg.tls_timeout_seconds is deprecated; use ScanCfg.timeouts.tls_seconds",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.timeouts.tls_seconds

    @tls_timeout_seconds.setter
    def tls_timeout_seconds(self, value: int) -> None:
        self.timeouts.tls_seconds = int(value)

    @property
    def ssh_timeout_seconds(self) -> int:
        warnings.warn(
            "ScanCfg.ssh_timeout_seconds is deprecated; use ScanCfg.timeouts.ssh_seconds",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.timeouts.ssh_seconds

    @ssh_timeout_seconds.setter
    def ssh_timeout_seconds(self, value: int) -> None:
        self.timeouts.ssh_seconds = int(value)


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
    # Phase 75 / APCL-04 / WR-12 (D-13): declared nmap toggle (replaces setattr injection)
    enable_nmap: bool = False
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
    # Phase 79 SMIME-01: S/MIME LDAP discovery scanner enable flag
    enable_smime: bool = False
    # Identity connector target lists (v4.2, per D-05)
    kerberos_targets: list = field(default_factory=list)
    saml_targets: list = field(default_factory=list)
    dnssec_targets: list = field(default_factory=list)
    # Phase 79 SMIME-01 / CONTEXT D-Area-1: S/MIME LDAP targets + optional
    # search-base override. Targets are LDAP URLs (ldap://host:port) or
    # bare host[:port] strings; search_base defaults to the Kerberos realm
    # derived DN.
    smime_targets: list = field(default_factory=list)
    smime_search_base: Optional[str] = None
    smime_timeout: int = 10
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
    # Object storage connector config (v4.3, Phase 28, per D-04)
    enable_s3: bool = False
    enable_blob: bool = False
    aws_endpoint_url: Optional[str] = None  # MinIO/LocalStack S3 endpoint override
    # K8S connector config (v4.3, Phase 29)
    enable_k8s: bool = False
    k8s_provider: Optional[str] = None    # "eks" | "gke" | "aks"
    k8s_cluster_name: Optional[str] = None
    k8s_namespace: str = "default"
    k8s_kubeconfig: Optional[str] = None
    k8s_context: Optional[str] = None
    gke_clusters: list = field(default_factory=list)   # [{name, location}]
    aks_clusters: list = field(default_factory=list)   # [{name, resource_group}]
    # Vault connector config (v4.3, Phase 30, per D-10)
    enable_vault: bool = False
    vault_addr: Optional[str] = None        # e.g. "http://localhost:8200"
    vault_token: Optional[str] = None       # if None, falls back to VAULT_TOKEN env var
    vault_transit_mount: str = "transit"    # default transit mount path (D-10)
    vault_tls_verify: bool = True           # passed to hvac.Client(verify=...) — D-09
    # Email scanner enable flag (v4.4, Phase 32)
    enable_email: bool = False
    # Broker scanner enable flag (v4.4 Phase 33 — D-10)
    enable_broker: bool = False
    # Cloud broker targets (D-01) — supplied via CLI/config only; no SDK enumeration (D-02)
    broker_azure_namespaces: List[str] = field(default_factory=list)
    broker_sqs_regions: List[str] = field(default_factory=list)
    # Phase 72 D-02 / WR-11: tracks which keys appeared in the raw YAML connectors block.
    # Used by quirk.engine.profiles to suppress mutation of user-explicit values.
    _user_set_fields: frozenset = field(default_factory=frozenset, repr=False, compare=False)


@dataclass
class OutputCfg:
    directory: str
    db_path: str


@dataclass
class IntelligenceCfg:
    # Intelligence/scoring layer versioning
    intelligence_version: str = "4.4.0"

    # Score calibration profile used by scoring/reporting.
    # Supported: lenient|balanced|strict
    profile: str = "balanced"

    # Optional per-weight overrides (advanced tuning)
    calibration_overrides: Optional[Dict[str, Any]] = None


@dataclass
class SecurityCfg:
    """Phase 57 / D-04: operator safety-override knobs. All default False.

    - allow_internal_targets: permit SAML/broker fetches to RFC1918, loopback,
      link-local IPs (CR-04). Metadata-service IPs remain blocked even when True.
    - allow_cleartext_broker_probe: permit broker mgmt API probes over HTTP /
      ssl_cert_reqs="none" Redis (CR-06).
    - allow_insecure_jwks: disable TLS certificate verification on JWKS fetches
      (CR-01).
    """
    allow_internal_targets: bool = False
    allow_cleartext_broker_probe: bool = False
    allow_insecure_jwks: bool = False
    api_token: str = ""  # Phase 58 / CR-03: bearer token for dashboard API; "" = auth disabled (D-02)
    cors_origins: list = dataclasses.field(default_factory=lambda: ["http://127.0.0.1", "http://localhost"])  # Phase 58 / HARDEN-API-02: CORS allowlist; overridden by QUIRK_CORS_ORIGINS env var (comma-separated)


@dataclass(frozen=True)
class BrokerCredential:
    """Phase 57 / D-05: per-host broker credential entry.

    `pass_env` is the NAME of the environment variable holding the password,
    NOT the password itself. Passwords MUST NOT appear inline in YAML.
    """
    user: str
    pass_env: str


@dataclass
class AppConfig:
    assessment: AssessmentCfg
    scan: ScanCfg
    targets: TargetsCfg
    connectors: ConnectorsCfg
    output: OutputCfg
    intelligence: IntelligenceCfg
    security: SecurityCfg = field(default_factory=SecurityCfg)             # Phase 57 / D-04
    broker_credentials: Dict[str, BrokerCredential] = field(default_factory=dict)  # Phase 57 / D-05


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


_KNOWN_CONNECTOR_KEYS = {f.name for f in dataclasses.fields(ConnectorsCfg)}


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

    conn_raw = {k: v for k, v in (raw.get("connectors") or {}).items()
                if k in _KNOWN_CONNECTOR_KEYS}
    # Coerce broker list fields through _as_str_list to guard against scalar YAML values
    # (T-33-03: user-supplied namespace/region strings must be proper lists before hostname construction)
    if "broker_azure_namespaces" in conn_raw:
        conn_raw["broker_azure_namespaces"] = _as_str_list(conn_raw["broker_azure_namespaces"])
    if "broker_sqs_regions" in conn_raw:
        conn_raw["broker_sqs_regions"] = _as_str_list(conn_raw["broker_sqs_regions"])

    # Phase 41 D-06/D-07: split [scan] into flat ScanCfg kwargs + nested
    # TimeoutsCfg / RetryCfg sub-tables, with backward-compat for the four
    # legacy flat ``*_timeout_seconds`` keys.
    scan_raw = dict(raw.get("scan") or {})
    timeouts_raw = scan_raw.pop("timeouts", None) or {}
    retry_raw = scan_raw.pop("retry", None) or {}

    timeouts_fields = {f.name for f in dataclasses.fields(TimeoutsCfg)}
    retry_fields = {f.name for f in dataclasses.fields(RetryCfg)}
    timeouts_cfg = TimeoutsCfg(
        **{k: v for k, v in timeouts_raw.items() if k in timeouts_fields}
    )
    retry_cfg = RetryCfg(
        **{k: v for k, v in retry_raw.items() if k in retry_fields}
    )

    # Legacy flat keys: only consulted when no [scan.timeouts] sub-table
    # was provided. Strip them from scan_raw so they don't get forwarded to
    # ScanCfg(**scan_raw); the constructor now treats them as deprecated
    # and we'd rather route them deterministically here.
    legacy_timeout_present = bool(timeouts_raw)
    for legacy_kw, target_field in _LEGACY_TIMEOUT_KWARG_MAP.items():
        if legacy_kw in scan_raw:
            value = scan_raw.pop(legacy_kw)
            if not legacy_timeout_present:
                setattr(timeouts_cfg, target_field, int(value))

    # Phase 57 / D-04: security hardening opt-out knobs
    security_raw = raw.get("security") or {}
    security_cfg = SecurityCfg(
        allow_internal_targets=bool(security_raw.get("allow_internal_targets", False)),
        allow_cleartext_broker_probe=bool(security_raw.get("allow_cleartext_broker_probe", False)),
        allow_insecure_jwks=bool(security_raw.get("allow_insecure_jwks", False)),
        api_token=str(security_raw.get("api_token", "") or ""),
        cors_origins=list(security_raw.get("cors_origins") or []),
    )

    # Phase 57 / D-05: per-host broker credentials (pass_env is env-var name, never inline password)
    broker_creds_raw = raw.get("broker_credentials") or {}
    broker_credentials: Dict[str, BrokerCredential] = {}
    for host_port, cred in broker_creds_raw.items():
        if not isinstance(cred, dict):
            continue
        broker_credentials[str(host_port)] = BrokerCredential(
            user=str(cred.get("user", "")),
            pass_env=str(cred.get("pass_env", "")),
        )

    # Phase 72 D-02 / WR-11: build connectors then stamp user-set field set so the
    # profile-application code can distinguish user-explicit values from defaults.
    connectors_cfg = ConnectorsCfg(**conn_raw)
    connectors_cfg._user_set_fields = frozenset(conn_raw.keys())

    return AppConfig(
        assessment=AssessmentCfg(**raw["assessment"]),
        scan=ScanCfg(timeouts=timeouts_cfg, retry=retry_cfg, **scan_raw),
        targets=targets,
        connectors=connectors_cfg,
        output=OutputCfg(**raw["output"]),
        intelligence=intelligence_cfg,
        security=security_cfg,
        broker_credentials=broker_credentials,
    )


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return config_from_dict(raw)


def get_cors_origins() -> list:
    """Return CORS allowlist: QUIRK_CORS_ORIGINS env var (comma-separated) wins over YAML.

    Default when neither is set: ["http://127.0.0.1", "http://localhost"].
    """
    if env_val := os.environ.get("QUIRK_CORS_ORIGINS"):
        return [o.strip() for o in env_val.split(",") if o.strip()]
    try:
        cfg = load_config()
        if cfg.security.cors_origins:
            return list(cfg.security.cors_origins)
    except Exception:
        pass
    return ["http://127.0.0.1", "http://localhost"]
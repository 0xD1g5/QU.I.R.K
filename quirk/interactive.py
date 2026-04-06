from __future__ import annotations

import datetime
from typing import List, Optional

from quirk.config import (
    AppConfig,
    AssessmentCfg,
    ScanCfg,
    TargetsCfg,
    ConnectorsCfg,
    OutputCfg,
    IntelligenceCfg,
)
from quirk.assessment.operator_context import OperatorContext, attach_context

DEFAULT_TIMEZONE = "America/New_York"

CONSULTING_TLS_PORTS = [
    443, 8443, 9443, 10443, 4433, 5001,
    636, 3269,
    993, 995, 465,
    6443, 2376,
    5432, 3306, 1433,
    8200,
]

_DATA_CLASS_MAP = {
    "1": ("public",       ["PUBLIC"],              "no sensitive data"),
    "2": ("internal",     ["GENERAL"],             "general internal data"),
    "3": ("confidential", ["FINANCIAL", "TRADE"],  "financial, trade secrets, or business-sensitive data"),
    "4": ("regulated",    ["PCI", "PHI"],          "PCI, PHI, or other regulated data types"),
}


def _prompt(text: str, default: Optional[str] = None) -> str:
    if default is None or default == "":
        val = input(f"{text}: ").strip()
        return val
    val = input(f"{text} [{default}]: ").strip()
    return val if val else default


def _prompt_int(text: str, default: int, minv: int = 1, maxv: int = 100000) -> int:
    while True:
        raw = _prompt(text, str(default))
        try:
            v = int(raw)
            if v < minv or v > maxv:
                print(f"  Enter a number between {minv} and {maxv}.")
                continue
            return v
        except ValueError:
            print("  Please enter a valid integer.")


def _prompt_bool(text: str, default: bool) -> bool:
    d = "Y" if default else "N"
    raw = _prompt(f"{text} (y/n)", d).lower()
    if raw in ("y", "yes"):
        return True
    if raw in ("n", "no"):
        return False
    return default


def _prompt_list(text: str, default: Optional[List[str]] = None) -> List[str]:
    d = ",".join(default) if default else ""
    raw = _prompt(f"{text} (comma-separated)", d)
    raw = raw.strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _prompt_ports(text: str, default_ports: List[int]) -> List[int]:
    raw = _prompt(
        f"{text} (comma-separated ints)",
        ",".join(str(p) for p in default_ports),
    )
    ports: List[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            p = int(token)
            if p < 1 or p > 65535:
                print(f"  Ignoring invalid port: {p}")
                continue
            ports.append(p)
        except ValueError:
            print(f"  Ignoring invalid token: {token}")
    return ports if ports else default_ports


def _prompt_profile(default: str = "standard") -> str:
    profiles = {
        "1": ("quick",    "fast sweep, lower accuracy"),
        "2": ("standard", "balanced, recommended for most engagements (default)"),
        "3": ("deep",     "thorough, use for high-value targets or regulated environments"),
    }
    default_num = "2"
    print(f"\nScan profile [{default}]:")
    for num, (name, desc) in profiles.items():
        print(f"  {num}) {name:<10} -- {desc}")
    raw = _prompt("Choice", default_num).strip()
    return profiles.get(raw, profiles[default_num])[0]


def _prompt_data_classification(default_num: str = "3") -> tuple[str, list[str]]:
    print("\nData classification:")
    for num, (label, _, desc) in _DATA_CLASS_MAP.items():
        print(f"  {num}) {label:<14} -- {desc}")
    raw = _prompt("Choice", default_num).strip()
    label, data_types, _ = _DATA_CLASS_MAP.get(raw, _DATA_CLASS_MAP[default_num])
    return label, data_types


def interactive_config() -> tuple[AppConfig, str]:
    print("\n=== QU.I.R.K. -- Interactive Setup ===\n")

    # --- 1. Targets (D-15) ---
    print("Targets")
    cidrs = _prompt_list("CIDR blocks", [])
    fqdns = _prompt_list("FQDNs", [])
    include_ips = _prompt_list("Specific IPs to include", [])
    exclude_ips = _prompt_list("IPs to exclude", [])

    # --- 2. Scan options (D-05/D-06) ---
    scan_profile = _prompt_profile()

    # --- 3. Additional scanners (D-16 -- preserve existing prompts) ---
    print("\nAdditional Scanners")
    enable_jwt = _prompt_bool("Enable JWT/API endpoint scanning", False)
    jwt_targets: list[str] = []
    if enable_jwt:
        jwt_targets = _prompt_list("JWT endpoint URLs (e.g., https://api.example.com)")

    enable_container = _prompt_bool("Enable container image scanning", False)
    container_targets: list[str] = []
    if enable_container:
        container_targets = _prompt_list("Container image references (e.g., nginx:latest)")

    enable_source = _prompt_bool("Enable source code scanning", False)
    source_targets: list[str] = []
    if enable_source:
        source_targets = _prompt_list("Source code paths or Git URLs")

    # --- 4. Cloud connectors (D-13/D-14) ---
    print("\nCloud Connectors")
    enable_aws = _prompt_bool("Enable AWS connector", False)
    if enable_aws:
        print("  \u26a0  Requires AWS credentials \u2014 set AWS_ACCESS_KEY_ID + "
              "AWS_SECRET_ACCESS_KEY, or configure an IAM role profile "
              "(aws_profile in config).")

    enable_azure = _prompt_bool("Enable Azure connector", False)
    if enable_azure:
        print("  \u26a0  Requires Azure credentials \u2014 run az login, or set "
              "AZURE_CLIENT_ID + AZURE_CLIENT_SECRET + AZURE_TENANT_ID.")

    # --- 5. Output ---
    print("\nOutput")
    out_dir = _prompt("Output directory", "output")
    db_path = _prompt("SQLite DB path", "output/quirk.db")

    # --- 6. Metadata (D-01 auto-detect timezone, D-10/D-11 unified classification) ---
    print("\nAssessment Metadata")
    name = _prompt("Assessment name", "Quantum Crypto Readiness - Interactive")
    data_classification, data_types = _prompt_data_classification()
    report_owner = _prompt("Report owner", "Security Team")

    # Auto-detect timezone (D-01) -- no prompt
    try:
        timezone = datetime.datetime.now().astimezone().tzname()
    except Exception:
        timezone = "UTC"

    # --- 7. Assessment context (D-12 remaining OperatorContext fields) ---
    print("\nAssessment Context")
    try:
        years_raw = input("Data longevity years [7]: ").strip()
        data_longevity_years = int(years_raw) if years_raw else 7
    except (ValueError, EOFError):
        data_longevity_years = 7

    print("\nExposure context:")
    print("  1) internal  (internal-only / segmented)")
    print("  2) mixed     (internal + some internet-facing)")
    print("  3) internet  (many internet-facing services)")
    exp_raw = _prompt("Choose 1/2/3", "2").strip()
    exposure = "mixed"
    if exp_raw == "1":
        exposure = "internal"
    elif exp_raw == "3":
        exposure = "internet"

    crown_jewels = _prompt_list("Crown jewels hosts/IPs/FQDNs (blank to skip)", [])

    # --- Build config (Pitfall 1: supply baseline ScanCfg values) ---
    cfg = AppConfig(
        assessment=AssessmentCfg(
            name=name,
            data_classification=data_classification,
            report_owner=report_owner,
            timezone=timezone,
        ),
        scan=ScanCfg(
            timeout_seconds=5,           # baseline; apply_profile() overrides
            concurrency=200,             # baseline; apply_profile() overrides
            ports_tls=CONSULTING_TLS_PORTS,  # D-03
            include_sni=True,            # D-02
        ),
        targets=TargetsCfg(
            fqdns=fqdns,
            cidrs=cidrs,
            include_ips=include_ips,
            exclude_ips=exclude_ips,
        ),
        connectors=ConnectorsCfg(
            enable_aws=enable_aws,
            enable_azure=enable_azure,
            enable_jwt=enable_jwt,
            jwt_targets=jwt_targets,
            enable_container=enable_container,
            container_targets=container_targets,
            enable_source=enable_source,
            source_targets=source_targets,
        ),
        output=OutputCfg(
            directory=out_dir,
            db_path=db_path,
        ),
        intelligence=IntelligenceCfg(),
    )

    # Attach OperatorContext directly (D-12, Option B from RESEARCH.md)
    ctx = OperatorContext(
        data_types=data_types,
        data_longevity_years=data_longevity_years,
        exposure=exposure,
        crown_jewels=crown_jewels,
    )
    attach_context(cfg, ctx)

    print("\nConfig captured.\n")
    return cfg, scan_profile   # D-07

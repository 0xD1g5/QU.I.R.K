from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from qcscan.config import (
    AppConfig,
    AssessmentCfg,
    ScanCfg,
    TargetsCfg,
    ConnectorsCfg,
    OutputCfg,
)

DEFAULT_TIMEZONE = "America/New_York"


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
                print(f"  ⚠️ Enter a number between {minv} and {maxv}.")
                continue
            return v
        except ValueError:
            print("  ⚠️ Please enter a valid integer.")


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
    raw = _prompt(f"{text} (comma-separated ints)", ",".join(str(p) for p in default_ports))
    ports: List[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            p = int(token)
            if p < 1 or p > 65535:
                print(f"  ⚠️ Ignoring invalid port: {p}")
                continue
            ports.append(p)
        except ValueError:
            print(f"  ⚠️ Ignoring invalid token: {token}")
    return ports if ports else default_ports


def interactive_config() -> AppConfig:
    print("\n🔐 Quantum Crypto Scanner — Interactive Setup\n")

    # Assessment
    name = _prompt("Assessment name", "Quantum Crypto Readiness - Interactive")
    data_classification = _prompt("Data classification (public|internal|confidential|regulated)", "confidential")
    report_owner = _prompt("Report owner", "Security Team")
    timezone = _prompt("Timezone", DEFAULT_TIMEZONE)

    # Scan
    timeout_seconds = _prompt_int("Socket/TLS timeout seconds", 4, 1, 60)
    concurrency = _prompt_int("Concurrency (threads)", 200, 1, 5000)
    ports_tls = _prompt_ports("TLS ports to probe", [443, 8443, 9443, 10443, 4433, 5001])
    include_sni = _prompt_bool("Use SNI for FQDN targets", True)

    # Targets
    print("\n🎯 Targets")
    cidrs = _prompt_list("CIDR blocks", [])
    fqdns = _prompt_list("FQDNs", [])
    include_ips = _prompt_list("Specific IPs to include", [])
    exclude_ips = _prompt_list("IPs to exclude", [])

    # Output
    print("\n📦 Output")
    out_dir = _prompt("Output directory", "output")
    db_path = _prompt("SQLite DB path", "data/qcscan.sqlite")

    # Connectors (stubs for now)
    print("\n🔌 Connectors (stubs in v2)")
    enable_aws = _prompt_bool("Enable AWS connector (stub)", False)
    enable_azure = _prompt_bool("Enable Azure connector (stub)", False)
    enable_windows_adcs = _prompt_bool("Enable Windows AD CS connector (stub)", False)

    cfg = AppConfig(
        assessment=AssessmentCfg(
            name=name,
            data_classification=data_classification,
            report_owner=report_owner,
            timezone=timezone,
        ),
        scan=ScanCfg(
            timeout_seconds=timeout_seconds,
            concurrency=concurrency,
            ports_tls=ports_tls,
            include_sni=include_sni,
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
            enable_windows_adcs=enable_windows_adcs,
        ),
        output=OutputCfg(
            directory=out_dir,
            db_path=db_path,
        ),
    )

    print("\n✅ Config captured.\n")
    return cfg

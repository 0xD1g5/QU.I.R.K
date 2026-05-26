"""Distributed topology static assertions — CI floor for LAB-01/02/03.

Asserts the structural invariants of the distributed chaos-lab compose file
without requiring a running Docker daemon (pure file parse + one optional
config-validate).  All ten behaviors are exercised as distinct test functions.

LAB-02 linchpin (confirmed in-code during planning):
  quirk/scanner/tls_scanner.py:188-189  CryptoEndpoint(host=host, ...)
  quirk/scanner/tls_scanner.py:351-352  fallback path — same pattern
  Both paths record the CONFIGURED scan-target string verbatim, not a
  resolved IP.  So two sensors both scanning "crypto.internal:443" record
  an identical host:port, differing only by sensor_id/segment — exactly the
  MERGE-03 reproduction scenario.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants — all paths rooted at the repo root via __file__ resolution.
# ---------------------------------------------------------------------------
LAB_DIR = Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"
DIST_COMPOSE = LAB_DIR / "docker-compose.distributed.yml"
SENSOR_DOCKERFILE = LAB_DIR / "sensor.Dockerfile"
E2E_SCRIPT = LAB_DIR / "scripts" / "distributed-e2e.sh"


# ---------------------------------------------------------------------------
# test_distributed_compose_file_exists
# ---------------------------------------------------------------------------
def test_distributed_compose_file_exists():
    assert DIST_COMPOSE.exists(), f"Distributed compose file not found: {DIST_COMPOSE}"


# ---------------------------------------------------------------------------
# test_config_validates
# Skipped on machines without the docker binary (live run is human-UAT).
# ---------------------------------------------------------------------------
def test_config_validates():
    if not shutil.which("docker"):
        import pytest
        pytest.skip("docker binary not available — skipping config validation")
    result = subprocess.run(
        ["docker", "compose", "-f", str(DIST_COMPOSE), "config"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"docker compose config failed:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# test_two_bridge_networks
# ---------------------------------------------------------------------------
def test_two_bridge_networks():
    data = yaml.safe_load(DIST_COMPOSE.read_text())
    networks = data.get("networks") or {}
    assert len(networks) >= 2, (
        f"Expected >= 2 networks, got {len(networks)}: {list(networks.keys())}"
    )


# ---------------------------------------------------------------------------
# test_segment_networks_have_distinct_subnets
# ---------------------------------------------------------------------------
def test_segment_networks_have_distinct_subnets():
    data = yaml.safe_load(DIST_COMPOSE.read_text())
    networks = data.get("networks") or {}

    def _subnet(net_cfg: dict) -> str | None:
        ipam = net_cfg.get("ipam") or {}
        configs = ipam.get("config") or []
        if configs:
            return configs[0].get("subnet")
        return None

    assert "segment-a" in networks, "segment-a network not found"
    assert "segment-b" in networks, "segment-b network not found"

    subnet_a = _subnet(networks["segment-a"])
    subnet_b = _subnet(networks["segment-b"])

    assert subnet_a is not None, "segment-a has no ipam.config subnet"
    assert subnet_b is not None, "segment-b has no ipam.config subnet"
    assert subnet_a == "10.10.0.0/24", f"Expected 10.10.0.0/24 for segment-a, got {subnet_a}"
    assert subnet_b == "10.20.0.0/24", f"Expected 10.20.0.0/24 for segment-b, got {subnet_b}"
    assert subnet_a != subnet_b, (
        f"segment-a and segment-b have the SAME subnet ({subnet_a}) — "
        "Docker forbids overlapping subnets on one daemon"
    )


# ---------------------------------------------------------------------------
# test_crypto_internal_alias_per_segment
# ---------------------------------------------------------------------------
def test_crypto_internal_alias_per_segment():
    data = yaml.safe_load(DIST_COMPOSE.read_text())
    services = data.get("services") or {}

    def _aliases_on_network(svc_cfg: dict, network_name: str) -> list[str]:
        """Return aliases list for a service on a specific network (long-form mapping)."""
        nets = svc_cfg.get("networks") or {}
        if isinstance(nets, list):
            return []
        net_entry = nets.get(network_name) or {}
        if isinstance(net_entry, dict):
            return net_entry.get("aliases") or []
        return []

    # tls-target-a must declare crypto.internal alias on segment-a
    assert "tls-target-a" in services, "tls-target-a service not found"
    aliases_a = _aliases_on_network(services["tls-target-a"], "segment-a")
    assert "crypto.internal" in aliases_a, (
        f"tls-target-a does not carry crypto.internal alias on segment-a; got {aliases_a}"
    )

    # tls-target-b must declare crypto.internal alias on segment-b
    assert "tls-target-b" in services, "tls-target-b service not found"
    aliases_b = _aliases_on_network(services["tls-target-b"], "segment-b")
    assert "crypto.internal" in aliases_b, (
        f"tls-target-b does not carry crypto.internal alias on segment-b; got {aliases_b}"
    )


# ---------------------------------------------------------------------------
# test_both_sensors_scan_crypto_internal
# ---------------------------------------------------------------------------
def test_both_sensors_scan_crypto_internal():
    data = yaml.safe_load(DIST_COMPOSE.read_text())
    services = data.get("services") or {}

    sensor_services = {
        name: svc for name, svc in services.items()
        if "sensor" in name and isinstance(svc, dict)
    }
    assert len(sensor_services) >= 2, (
        f"Expected >= 2 sensor services, found: {list(sensor_services.keys())}"
    )

    for name, svc in sensor_services.items():
        cmd = svc.get("command") or []
        # command may be a list or a string
        if isinstance(cmd, list):
            cmd_str = " ".join(cmd)
        else:
            cmd_str = str(cmd)

        # The scan target must reference crypto.internal:443
        assert "crypto.internal:443" in cmd_str, (
            f"Sensor '{name}' does not scan crypto.internal:443; command: {cmd}"
        )

        # Must NOT contain a literal IP address as the scan target
        import re
        # Look for 10.x.x.x patterns in the scan target portion
        ip_pattern = re.compile(r'10\.\d+\.\d+\.\d+:443')
        assert not ip_pattern.search(cmd_str), (
            f"Sensor '{name}' uses a literal IP scan target — must use crypto.internal:443"
        )


# ---------------------------------------------------------------------------
# test_one_sensor_service_per_segment
# ---------------------------------------------------------------------------
def test_one_sensor_service_per_segment():
    data = yaml.safe_load(DIST_COMPOSE.read_text())
    services = data.get("services") or {}

    sensor_services = {
        name: svc for name, svc in services.items()
        if "sensor" in name and isinstance(svc, dict)
    }
    assert len(sensor_services) >= 2, (
        f"Expected >= 2 sensor services (one per segment), found: {list(sensor_services.keys())}"
    )

    for name, svc in sensor_services.items():
        nets = svc.get("networks") or {}
        if isinstance(nets, list):
            net_names = set(nets)
        else:
            net_names = set(nets.keys())

        # Must be on console-net for push connectivity
        assert "console-net" in net_names, (
            f"Sensor '{name}' is not on console-net: {net_names}"
        )

        # Must be on exactly one segment network
        segment_nets = {n for n in net_names if n.startswith("segment-")}
        assert len(segment_nets) == 1, (
            f"Sensor '{name}' should be on exactly one segment network, "
            f"got: {segment_nets}"
        )

    # sensor-a must not be on segment-b and sensor-b must not be on segment-a
    def _networks(name: str) -> set[str]:
        nets = sensor_services.get(name, {}).get("networks") or {}
        if isinstance(nets, list):
            return set(nets)
        return set(nets.keys())

    if "sensor-a" in sensor_services:
        assert "segment-b" not in _networks("sensor-a"), (
            "sensor-a must NOT join segment-b (cross-segment isolation)"
        )
    if "sensor-b" in sensor_services:
        assert "segment-a" not in _networks("sensor-b"), (
            "sensor-b must NOT join segment-a (cross-segment isolation)"
        )


# ---------------------------------------------------------------------------
# test_one_console_service
# ---------------------------------------------------------------------------
def test_one_console_service():
    data = yaml.safe_load(DIST_COMPOSE.read_text())
    services = data.get("services") or {}

    console_services = [
        name for name in services
        if "console" in name
    ]
    assert len(console_services) >= 1, (
        f"Expected >= 1 console service, found none in: {list(services.keys())}"
    )


# ---------------------------------------------------------------------------
# test_sensor_dockerfile_base_pinned
# ---------------------------------------------------------------------------
def test_sensor_dockerfile_base_pinned():
    assert SENSOR_DOCKERFILE.exists(), f"sensor.Dockerfile not found: {SENSOR_DOCKERFILE}"
    content = SENSOR_DOCKERFILE.read_text()

    from_lines = [
        line.strip() for line in content.splitlines()
        if line.strip().upper().startswith("FROM")
    ]
    assert from_lines, "No FROM directive found in sensor.Dockerfile"

    # Must be patch-pinned: python:3.11.12-slim (not python:3.11-slim or :latest)
    from_line = from_lines[0]
    assert "python:3.11.12-slim" in from_line, (
        f"sensor.Dockerfile FROM must be python:3.11.12-slim (patch-pinned per CHAOS-05); "
        f"got: {from_line}"
    )


# ---------------------------------------------------------------------------
# test_e2e_script_enroll_push_merge_order
# ---------------------------------------------------------------------------
def test_e2e_script_enroll_push_merge_order():
    assert E2E_SCRIPT.exists(), f"distributed-e2e.sh not found: {E2E_SCRIPT}"
    text = E2E_SCRIPT.read_text()

    assert "enroll" in text, "distributed-e2e.sh must reference 'enroll'"
    assert "push" in text, "distributed-e2e.sh must reference 'push'"
    assert "merge" in text, "distributed-e2e.sh must reference 'merge'"

    ei = text.index("enroll")
    pi = text.index("push")
    mi = text.index("merge")

    assert ei < pi, (
        f"'enroll' (pos {ei}) must appear before 'push' (pos {pi}) in distributed-e2e.sh"
    )
    assert pi < mi, (
        f"'push' (pos {pi}) must appear before 'merge' (pos {mi}) in distributed-e2e.sh"
    )

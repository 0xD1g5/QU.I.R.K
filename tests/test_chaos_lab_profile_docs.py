"""CHAOS-07: chaos lab profile/port documentation coverage gate.

Regenerates the expected profile and port sets from
`quantum-chaos-enterprise-lab/docker-compose.yml` AT TEST RUN TIME (never a
hardcoded list — see CLAUDE.md's TOOL-04 lesson: a hand-derived enumeration
missed a real instance; a run-time source scan found it) and asserts that
every profile and every profile-gated published host port is documented in
`docs/chaos-lab.md`.

Pure file parse — no Docker daemon required; runs in the default pytest
suite. Mirrors the conventions of the sibling
`tests/test_chaos_lab_image_pinning.py`.
"""
import re
from pathlib import Path

import pytest  # noqa: F401  (kept: pytest.fail is used in the gate bodies below)
import yaml

COMPOSE_FILE = (
    Path(__file__).resolve().parent.parent
    / "quantum-chaos-enterprise-lab"
    / "docker-compose.yml"
)
DOCS_FILE = Path(__file__).resolve().parent.parent / "docs" / "chaos-lab.md"

# Matches section-3 headings of the shape:
#   ### 3.16 database Profile (v4.3 — DAR)
#   ### 3.20 tls-cert-defects Profile (v4.6)
# Captures the profile name token immediately preceding the literal word
# "Profile". Anchored to heading lines only (not free prose) to avoid the
# technology-name false positive documented in the plan's <audit_findings>
# (a substring match on "kafka"/"redis"/"postgres" would wrongly credit the
# `broker` and `database` sections, which cover different services/ports).
SECTION_HEADING_RE = re.compile(r"^###\s+3\.\d+\s+(\S+)\s+Profile\b", re.MULTILINE)


def _compose_data():
    return yaml.safe_load(COMPOSE_FILE.read_text())


def _all_compose_profiles():
    """Union of every service's `profiles:` entries, read at test run time."""
    data = _compose_data()
    profiles = set()
    for svc in (data.get("services") or {}).values():
        if not isinstance(svc, dict):
            continue
        for p in svc.get("profiles") or []:
            profiles.add(str(p))
    return profiles


def _documented_section3_profile_names():
    text = DOCS_FILE.read_text()
    return {m.group(1).strip() for m in SECTION_HEADING_RE.finditer(text)}


def _profile_gated_service_ports():
    """Map of service name -> set of published HOST ports (as strings).

    Only considers services that declare a `profiles:` list (i.e. are
    profile-gated), per this plan's scope. Handles both `"HOST:CONTAINER"`
    and `"127.0.0.1:HOST:CONTAINER"` string forms.
    """
    data = _compose_data()
    result = {}
    for name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        if not svc.get("profiles"):
            continue
        host_ports = set()
        for entry in svc.get("ports") or []:
            entry = str(entry)
            parts = entry.split(":")
            if len(parts) < 2:
                continue
            # "HOST:CONTAINER" -> parts[-2]; "127.0.0.1:HOST:CONTAINER" -> parts[-2]
            host_port = parts[-2]
            host_ports.add(host_port)
        if host_ports:
            result[name] = host_ports
    return result


def test_every_compose_profile_has_a_docs_section():
    profiles = _all_compose_profiles()
    documented = _documented_section3_profile_names()
    missing = sorted(p for p in profiles if p not in documented)
    assert not missing, (
        "Compose profiles in quantum-chaos-enterprise-lab/docker-compose.yml "
        "with no matching '### 3.N <profile> Profile' heading in "
        "docs/chaos-lab.md section 3:\n  " + "\n  ".join(missing)
    )


def test_every_published_profile_port_is_in_the_port_reference():
    ports_by_service = _profile_gated_service_ports()
    docs_text = DOCS_FILE.read_text()
    missing = []
    for svc, ports in sorted(ports_by_service.items()):
        for port in sorted(ports):
            if port not in docs_text:
                missing.append(f"{svc}:{port}")
    assert not missing, (
        "Published host ports for profile-gated services with no mention in "
        "docs/chaos-lab.md:\n  " + "\n  ".join(missing)
    )

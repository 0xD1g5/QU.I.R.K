"""CBOM-01: every shipped chaos lab profile must produce a CycloneDX 1.6
spec-valid JSON and XML CBOM.

Validator API note (RESEARCH Pitfall #2): `validate_str` RETURNS `None` on
valid and an error object on invalid — it does NOT raise. Always assert
`result is None`.

Drift-sentinel note: the live docker-compose.yml uses INLINE profile syntax
(`profiles: ["identity", "phaseA"]`), so we MUST use yaml.safe_load — a
regex over `profiles:\\n` would silently miss every inline-form entry.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.validation.xml import XmlValidator

from quirk.cbom.builder import build_cbom
from quirk.cbom.writer import write_cbom_files
from tests._cbom_profiles import PROFILE_ENDPOINTS


@pytest.mark.parametrize("profile", sorted(PROFILE_ENDPOINTS))
def test_cbom_validates_against_cyclonedx_1_6(profile, tmp_path):
    endpoints = PROFILE_ENDPOINTS[profile]()
    # Per user Option 1 (2026-04-30): every synthesizer returns at least one
    # representative endpoint, so the schema validator has a non-trivial Bom
    # to inspect for every profile (no `_empty` stubs).
    assert endpoints, (
        f"PROFILE_ENDPOINTS[{profile!r}]() returned empty list — synthesizer "
        f"must produce at least one representative endpoint per D-03."
    )
    bom = build_cbom(endpoints)
    json_path, xml_path = write_cbom_files(bom, str(tmp_path), "test")

    json_v = JsonStrictValidator(SchemaVersion.V1_6)
    xml_v = XmlValidator(SchemaVersion.V1_6)

    j_err = json_v.validate_str(Path(json_path).read_text())
    assert j_err is None, (
        f"[{profile}] JSON failed CycloneDX 1.6 schema validation: {j_err}"
    )

    x_err = xml_v.validate_str(Path(xml_path).read_text())
    assert x_err is None, (
        f"[{profile}] XML failed CycloneDX 1.6 schema validation: {x_err}"
    )


def _profiles_from_compose() -> set[str]:
    """Extract the union of profile names declared in docker-compose.yml.

    Uses yaml.safe_load — required because the live file uses INLINE form
    (`profiles: ["identity", "phaseA"]`). A regex over `profiles:\\n` would
    miss every inline entry. PyYAML is a transitive dep via cyclonedx-
    python-lib (verified `pip show pyyaml` returns 6.0.x on 2026-04-30).
    """
    path = Path("quantum-chaos-enterprise-lab/docker-compose.yml")
    data = yaml.safe_load(path.read_text())
    profiles: set[str] = set()
    for _svc, cfg in (data.get("services") or {}).items():
        for p in (cfg.get("profiles") or []):
            profiles.add(p)
    # Defensive guard: prevent silent false-positives from a parsing bug.
    assert len(profiles) >= 18, (
        f"Parser returned only {len(profiles)} profiles "
        f"({sorted(profiles)}) — likely a parsing bug, not real drift. "
        f"Check that docker-compose.yml structure has not changed."
    )
    return profiles


def test_parametrize_set_matches_docker_compose_profiles():
    """Drift sentinel: the parametrize set MUST equal the union of profiles
    declared in docker-compose.yml (per CLAUDE.md Chaos Lab Maintenance).
    """
    compose = _profiles_from_compose()
    test_set = set(PROFILE_ENDPOINTS)
    missing_in_test = compose - test_set
    extra_in_test = test_set - compose
    assert not missing_in_test and not extra_in_test, (
        f"Drift between docker-compose.yml profiles and "
        f"PROFILE_ENDPOINTS keys.\n"
        f"  In compose but not parametrize: {sorted(missing_in_test)}\n"
        f"  In parametrize but not compose: {sorted(extra_in_test)}\n"
        f"Update tests/_cbom_profiles.py — add or remove a synthesizer "
        f"in test_cbom_motion_endpoints.py if a real shape exists."
    )

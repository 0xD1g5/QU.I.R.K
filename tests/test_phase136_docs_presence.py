"""Phase 136 docs presence gate: enforce docs/operators-guide.md §9 Hardware
Scanning content (OPS-01/02/03) so this section cannot silently regress.

Pattern modelled on tests/test_phase135_docs_presence.py — read source file
from disk, substring-check the (lower-cased) contents. One additional test
cross-checks the §9.2 tier Severity/Deadline strings against the live
_TIER_SEVERITY / _CNSA_DEADLINE constants in
quirk/dashboard/api/routes/scan.py to guard against future doc drift.
"""
import os
import re

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_OPS_GUIDE = "docs/operators-guide.md"
_SCAN_ROUTES = "quirk/dashboard/api/routes/scan.py"

# OPS-01: §9.1 Enable SNMP Scanning
_OPS01_SECTIONS: tuple[str, ...] = (
    "## 9. hardware scanning",
    "### 9.1 enable snmp scanning",
    "pip install 'quirk-scanner[hw]'",
    "enable_snmp",
    "snmp_community",
    "sysdescr",
    "sysname",
    "sysobjectid",
    "vendor",
    "model",
    "tier",
)

# OPS-02: §9.2 CNSA 2.0 Remediation Tiers
_OPS02_SECTIONS: tuple[str, ...] = (
    "### 9.2 cnsa 2.0 remediation tiers",
    "tier 1",
    "tier 2",
    "tier 3",
    "tier n/a",
    "replace by 2030",
    "upgrade firmware 2030-2033",
    "accept + monitor, re-evaluate 2033+",
    "eol before pqc migration window",
    "cnsa 2.0",
    "do not affect the quantum-readiness score",
)

# OPS-03: §9.3 Crypto-Bridge Detection
_OPS03_SECTIONS: tuple[str, ...] = (
    "### 9.3 crypto-bridge detection",
    "partial_only",
    "/24",
    "upstream_mitigated",
    "reserved status",
    "does **not** reduce the device's remediation",
)

# Deferred topics that must NOT leak into §9 (Phase 137 scope).
_FORBIDDEN_SECTIONS: tuple[str, ...] = (
    "snmpv3",
    "udp-161",
    "udp/161",
)


def _read(rel: str) -> str:
    """Read a repo-relative file and return its lower-cased contents."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read().lower()


def _read_raw(rel: str) -> str:
    """Read a repo-relative file and return its contents unmodified."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read()


def test_operators_guide_resolves():
    """docs/operators-guide.md must exist on disk."""
    assert os.path.isfile(os.path.join(_REPO_ROOT, _OPS_GUIDE)), (
        f"Required Phase 136 doc missing: {_OPS_GUIDE}"
    )


def test_ops01_snmp_section_present():
    """§9.1 must document the [hw] install command, both config keys, all
    three OIDs, and a sample output block with vendor/model/tier fields."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _OPS01_SECTIONS if needle not in text]
    assert not missing, f"§9.1 SNMP section missing required substrings: {missing}"


def test_ops01_config_defaults_stated():
    """§9.1 must state the enable_snmp/snmp_community defaults (false/public)."""
    text = _read(_OPS_GUIDE)
    assert "default: false" in text or "default `false`" in text or "false — must be explicitly" in text, (
        "§9.1 does not state the enable_snmp default of false"
    )
    assert '"public"' in _read_raw(_OPS_GUIDE), (
        "§9.1 does not state the snmp_community default of \"public\""
    )


def test_ops02_tier_table_present():
    """§9.2 must present a 4-row CNSA 2.0 tier table with Tier/Severity/
    Deadline/Meaning columns, matching scan.py verbatim, plus the
    advisory-only note and CNSA 2.0 citation."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _OPS02_SECTIONS if needle not in text]
    assert not missing, f"§9.2 CNSA tier section missing required substrings: {missing}"


def test_ops02_no_implementation_detail_leaks():
    """§9.2 must be meaning-only — no HARDWARE_MATRIX / vendor-regex internals."""
    text = _read(_OPS_GUIDE)
    assert "hardware_matrix" not in text, (
        "§9.2 leaks tier-assignment implementation detail (HARDWARE_MATRIX)"
    )


def test_ops03_crypto_bridge_section_present():
    """§9.3 must define partial_only, explain the /24 heuristic, state
    upstream_mitigated is reserved and never auto-assigned, and close with
    the remediation-still-applies note."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _OPS03_SECTIONS if needle not in text]
    assert not missing, f"§9.3 crypto-bridge section missing required substrings: {missing}"


def test_ops03_upstream_mitigated_never_auto_assigned():
    """§9.3 must explicitly state QUIRK does not auto-assign upstream_mitigated."""
    text = _read(_OPS_GUIDE)
    assert (
        "does not auto-assign" in text
        or "quirk does not auto-assign it" in text
        or "never auto-assign" in text
    ), "§9.3 does not explicitly state upstream_mitigated is never auto-assigned"


def test_section9_deferred_topics_absent():
    """§9 must not leak SNMPv3 / firewall / troubleshooting content deferred
    to Phase 137's admin guide."""
    text = _read(_OPS_GUIDE)
    # Scope the check to the §9 section only (from '## 9. hardware scanning'
    # to end of file, since §9 is the final section in the guide).
    idx = text.find("## 9. hardware scanning")
    assert idx != -1, "§9 Hardware Scanning heading not found"
    section9 = text[idx:]
    present = [needle for needle in _FORBIDDEN_SECTIONS if needle in section9]
    assert not present, f"§9 leaks deferred Phase 137 content: {present}"


def test_tier_table_matches_live_scan_py_constants():
    """Cross-check: the §9.2 Severity/Deadline strings in the doc must match
    the live _TIER_SEVERITY / _CNSA_DEADLINE dicts in scan.py verbatim, so a
    future change to those constants is caught as doc drift here."""
    scan_py_src = _read_raw(_SCAN_ROUTES)

    severity_match = re.search(
        r"_TIER_SEVERITY\s*=\s*\{(.*?)\}", scan_py_src, re.DOTALL
    )
    deadline_match = re.search(
        r"_CNSA_DEADLINE\s*=\s*\{(.*?)\}", scan_py_src, re.DOTALL
    )
    assert severity_match, "_TIER_SEVERITY dict not found in scan.py — has it been renamed/removed?"
    assert deadline_match, "_CNSA_DEADLINE dict not found in scan.py — has it been renamed/removed?"

    # Extract "key": "value" pairs from each dict literal.
    pair_re = re.compile(r'"([^"]+)"\s*:\s*"([^"]+)"')
    severity_pairs = dict(pair_re.findall(severity_match.group(1)))
    deadline_pairs = dict(pair_re.findall(deadline_match.group(1)))

    expected_tiers = {"Tier 1", "Tier 2", "Tier 3", "Tier N/A"}
    assert set(severity_pairs.keys()) == expected_tiers, (
        f"_TIER_SEVERITY tiers changed: {set(severity_pairs.keys())}"
    )
    assert set(deadline_pairs.keys()) == expected_tiers, (
        f"_CNSA_DEADLINE tiers changed: {set(deadline_pairs.keys())}"
    )

    doc_text = _read_raw(_OPS_GUIDE)
    mismatches = []
    for tier in expected_tiers:
        severity = severity_pairs[tier]
        deadline = deadline_pairs[tier]
        if severity not in doc_text:
            mismatches.append((tier, "severity", severity))
        if deadline not in doc_text:
            mismatches.append((tier, "deadline", deadline))
    assert not mismatches, (
        f"docs/operators-guide.md §9.2 table drifted from scan.py constants: {mismatches}"
    )

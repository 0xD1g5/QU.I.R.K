"""Phase 202 (D-06/D-08): run-time source-scan gate over the finding-title bridge.

This is the safeguard `quirk/dashboard/api/finding_title_bridge.py` itself is NOT: the two
occurrence sets it checks against -- the dashboard's `_derive_findings()` title-emission sites and
the CLI's `evaluate_endpoints()` title-emission sites -- are regenerated from INSTALLED SOURCE at
every test run via `pathlib` + regex, never imported or hand-enumerated in this file. CLAUDE.md
records five prior instances in this repo of a hand-maintained list silently going stale as the
"safeguard" for exactly this defect class (the GSD `state.*` bold-field regex saga); the pattern
here follows the in-repo precedent at
`tests/test_gsd_state_patch.py::test_bold_field_regex_class_is_fully_dispositioned`.

Three groups of tests:
  1. Extraction correctness + vacuous-pass guards (minimum site counts).
  2. The bridge/ledger completeness gate (every dashboard site dispositioned; every bridge value
     present in the CLI vocabulary; no site in both/neither ledger).
  3. The constituency reachability census (Task 3, D-08/D-09) -- recomputed from
     REMEDIATION_CONSTITUENCY + dashboard severities, not asserted against hand-written strings.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from quirk.dashboard.api.finding_title_bridge import (
    BRIDGE_REACHABILITY,
    DASHBOARD_TITLE_BRIDGE,
    UNBRIDGED_DASHBOARD_TITLES,
    canonical_cli_title,
)
from quirk.intelligence.remediation import REMEDIATION_CONSTITUENCY

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCAN_PY = _REPO_ROOT / "quirk" / "dashboard" / "api" / "routes" / "scan.py"
_EVALUATOR_PY = _REPO_ROOT / "quirk" / "engine" / "findings_evaluator.py"

# Matches `title="literal"` or `title=f"literal{expr}..."` -- single-line only
# by construction (see _extract_dashboard_titles' loud-failure comment).
_TITLE_RE = re.compile(r'title\s*=\s*f?"((?:[^"\\]|\\.)*)"')


def _slice_function(source: str, func_name: str) -> Tuple[str, int]:
    """Return (body_text, start_line_number) for a top-level `def func_name`."""
    lines = source.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if re.match(rf"def {re.escape(func_name)}\(", line):
            start_idx = i
            break
    if start_idx is None:
        raise AssertionError(f"could not find `def {func_name}(` in source")
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if re.match(r"(async )?def \w", lines[i]):
            end_idx = i
            break
    body = "\n".join(lines[start_idx:end_idx])
    return body, start_idx + 1  # 1-indexed line number of the def itself


def _literal_prefix(title_literal: str) -> str:
    """Reduce a captured f-string literal to its leading text before the
    first `{` interpolation. Plain (non-f) titles have no `{` and are
    returned unchanged."""
    brace = title_literal.find("{")
    return title_literal if brace == -1 else title_literal[:brace]


def _extract_dashboard_titles() -> List[Tuple[int, str]]:
    """Scan `_derive_findings`' body for `title=`/`title=f"` sites.

    Returns a list of (absolute_line_number, literal_prefix) tuples. FAILS
    LOUDLY (raises) if any `title=` construct in the sliced body is not
    resolvable on a single line -- a skipped site is exactly the blindness
    this gate exists to prevent, so this extractor refuses to silently pass
    over one.
    """
    source = _SCAN_PY.read_text()
    body, base_line = _slice_function(source, "_derive_findings")
    results: List[Tuple[int, str]] = []
    for i, line in enumerate(body.splitlines()):
        if re.search(r"\btitle\s*=", line) and "title=idf.title" not in line:
            m = _TITLE_RE.search(line)
            if not m:
                raise AssertionError(
                    f"scan.py line {base_line + i}: found a `title=` construct "
                    f"that the single-line extractor could not parse: {line!r}. "
                    "The extractor must be fixed to handle it (multi-line "
                    "title constructs are NOT supported and must not be "
                    "silently skipped) -- see _extract_dashboard_titles."
                )
            results.append((base_line + i, _literal_prefix(m.group(1))))
    return results


def _extract_cli_titles() -> List[Tuple[int, str]]:
    """Scan the full findings_evaluator.py source for `title="..."` kwargs.

    Returns (absolute_line_number, literal_title) tuples. f-string titles in
    this file are reduced to their leading prefix the same way, though in
    practice every findings_evaluator.py title is a plain string literal.
    """
    source = _EVALUATOR_PY.read_text()
    results: List[Tuple[int, str]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        if re.search(r"\btitle\s*=", line):
            m = _TITLE_RE.search(line)
            if m:
                results.append((i, _literal_prefix(m.group(1))))
    return results


def _dashboard_disposition(prefix: str) -> str:
    """Return 'bridged' or 'unbridged' for a dashboard title/prefix, or
    raise with an actionable message if it is dispositioned nowhere (or in
    both places)."""
    in_bridge = prefix in DASHBOARD_TITLE_BRIDGE
    in_unbridged = prefix in UNBRIDGED_DASHBOARD_TITLES
    if in_bridge and in_unbridged:
        raise AssertionError(
            f"dashboard title/prefix {prefix!r} is dispositioned in BOTH "
            "DASHBOARD_TITLE_BRIDGE and UNBRIDGED_DASHBOARD_TITLES -- pick "
            "exactly one in quirk/dashboard/api/finding_title_bridge.py"
        )
    if not in_bridge and not in_unbridged:
        raise AssertionError(
            f"dashboard title/prefix {prefix!r} has NO disposition -- add "
            "an entry to DASHBOARD_TITLE_BRIDGE or "
            "UNBRIDGED_DASHBOARD_TITLES in "
            "quirk/dashboard/api/finding_title_bridge.py"
        )
    return "bridged" if in_bridge else "unbridged"


# ---------------------------------------------------------------------------
# Group 1: extraction sanity + vacuous-pass guards
# ---------------------------------------------------------------------------

def test_dashboard_extractor_finds_plausible_number_of_sites() -> None:
    sites = _extract_dashboard_titles()
    assert len(sites) >= 9, (
        f"dashboard title extractor found only {len(sites)} sites in "
        "_derive_findings -- expected >= 9. Either the regex is broken "
        "(vacuous pass) or a site was removed; investigate before trusting "
        "this gate."
    )


def test_cli_extractor_finds_plausible_number_of_sites() -> None:
    sites = _extract_cli_titles()
    assert len(sites) >= 10, (
        f"CLI title extractor found only {len(sites)} sites in "
        "findings_evaluator.py -- expected >= 10. Either the regex is "
        "broken (vacuous pass) or a site was removed; investigate before "
        "trusting this gate."
    )


# ---------------------------------------------------------------------------
# Group 2: ledger completeness gate
# ---------------------------------------------------------------------------

def test_every_dashboard_emission_site_is_dispositioned() -> None:
    sites = _extract_dashboard_titles()
    for line_no, prefix in sites:
        try:
            _dashboard_disposition(prefix)
        except AssertionError as exc:
            raise AssertionError(f"scan.py line {line_no}: {exc}") from exc


def test_every_bridge_value_exists_in_cli_vocabulary() -> None:
    cli_titles = {t for _, t in _extract_cli_titles()}
    for dashboard_key, cli_title in DASHBOARD_TITLE_BRIDGE.items():
        assert cli_title in cli_titles, (
            f"DASHBOARD_TITLE_BRIDGE[{dashboard_key!r}] = {cli_title!r} does "
            "not appear as a title= site in quirk/engine/findings_evaluator.py "
            "-- this is an orphaned/typo'd/renamed translation target. Fix "
            "the value in quirk/dashboard/api/finding_title_bridge.py."
        )


def test_no_unbridged_key_is_also_a_bridge_key() -> None:
    overlap = set(DASHBOARD_TITLE_BRIDGE) & set(UNBRIDGED_DASHBOARD_TITLES)
    assert not overlap, (
        f"keys present in BOTH ledgers: {overlap} -- each dashboard "
        "title/prefix must be dispositioned exactly once in "
        "quirk/dashboard/api/finding_title_bridge.py"
    )


def test_canonical_cli_title_resolves_interpolated_runtime_string() -> None:
    # Proves prefix matching fires on a runtime-SHAPED string (with the
    # interpolated value filled in), not only on the bare literal prefix.
    assert (
        canonical_cli_title("Legacy TLS version: TLSv1.1")
        == "Legacy TLS versions allowed (TLS 1.0/1.1)"
    )
    assert (
        canonical_cli_title("Certificate expiring in 12 day(s)")
        == "TLS certificate expiring within 30 days"
    )


def test_canonical_cli_title_returns_none_for_unbridged_and_unknown() -> None:
    for key in UNBRIDGED_DASHBOARD_TITLES:
        # Unbridged prefixes need a runtime-shaped probe, not the bare key,
        # for the interpolated ones -- exercise both forms.
        assert canonical_cli_title(key) is None
    assert canonical_cli_title("Weak cipher suites enabled") is None
    assert canonical_cli_title("Quantum-vulnerable algorithm: DSA") is None
    assert canonical_cli_title("this finding title does not exist anywhere") is None


def test_canonical_cli_title_never_falls_back_to_its_own_argument() -> None:
    probe = "a title guaranteed not to be in either ledger, ever"
    result = canonical_cli_title(probe)
    assert result is None
    assert result != probe


def test_longest_prefix_first_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    # Synthetic overlap: "Certificate expiring in " (production key) is a
    # prefix of the longer synthetic key below. Longest-prefix-first must
    # prefer the longer, more specific match.
    synthetic = dict(DASHBOARD_TITLE_BRIDGE)
    synthetic["Certificate expiring in 1 day(s)"] = "SHORT_WINDOW_SENTINEL"
    monkeypatch.setattr(
        "quirk.dashboard.api.finding_title_bridge.DASHBOARD_TITLE_BRIDGE",
        synthetic,
    )
    result = canonical_cli_title("Certificate expiring in 1 day(s)")
    assert result == "SHORT_WINDOW_SENTINEL", (
        "longest-prefix-first matching failed: the more specific (longer) "
        "prefix should win over the shorter, more general "
        "'Certificate expiring in ' prefix"
    )
    # And the shorter prefix still wins for an input it, but not the longer
    # key, matches.
    result2 = canonical_cli_title("Certificate expiring in 25 day(s)")
    assert result2 == "TLS certificate expiring within 30 days"


def test_identity_findings_family_is_out_of_derive_findings_scope() -> None:
    # D-06 interfaces note: the KERBEROS/SAML/DNSSEC identity-findings
    # family is emitted by _derive_identity_findings() and appended
    # separately at scan.py:1641 -- NOT emitted as title= sites inside
    # _derive_findings() itself, and those FindingItems carry no `id=` at
    # all. `_derive_findings` DOES reference the literal strings
    # "KERBEROS"/"SAML"/"DNSSEC" once, in its own skip-guard
    # (`if proto in {"KERBEROS", "SAML", "DNSSEC"}: continue`) -- that is
    # expected and is not a title= emission site. Assert the real scoping
    # boundary instead: no `title=` construct inside _derive_findings'
    # sliced body resolves to a Kerberos/SAML/DNSSEC title, so a future
    # refactor that merges the two loops doesn't silently escape this
    # gate's coverage without being noticed here.
    sites = _extract_dashboard_titles()
    for _line_no, prefix in sites:
        lowered = prefix.lower()
        assert not any(
            needle in lowered for needle in ("kerberos", "saml", "dnssec")
        ), (
            f"a title= site inside _derive_findings() now emits an "
            f"identity-family title ({prefix!r}) -- the identity-findings "
            "family has moved into the scope this gate scans; re-evaluate "
            "whether it needs explicit ledger entries."
        )


# ---------------------------------------------------------------------------
# Group 3: constituency reachability census (Task 3, D-08/D-09)
# ---------------------------------------------------------------------------

def _dashboard_severity_for_cli_title(cli_title: str) -> str:
    """Read the literal severity= the dashboard site emits for a given
    (bridged) CLI title, by locating the corresponding DASHBOARD_TITLE_BRIDGE
    key's emission site in scan.py and reading its severity="..." literal.

    This is intentionally a small, targeted re-scan (not a full-blown
    parser) — it only needs to answer "HIGH/CRITICAL or not" for the
    handful of already-verified bridged titles.
    """
    dashboard_key = next(
        k for k, v in DASHBOARD_TITLE_BRIDGE.items() if v == cli_title
    )
    source = _SCAN_PY.read_text()
    body, _ = _slice_function(source, "_derive_findings")
    lines = body.splitlines()
    for i, line in enumerate(lines):
        m = _TITLE_RE.search(line) if re.search(r"\btitle\s*=", line) else None
        if m and _literal_prefix(m.group(1)) == dashboard_key:
            # Severity is set on the `severity="..."` line inside the same
            # FindingItem(...) call, which precedes the title= line.
            for j in range(i, max(i - 6, -1), -1):
                sev_m = re.search(r'severity\s*=\s*"([A-Z]+)"', lines[j])
                if sev_m:
                    return sev_m.group(1)
    raise AssertionError(
        f"could not locate a severity= literal for dashboard title "
        f"{dashboard_key!r} near its title= site in scan.py"
    )


def _compute_reachability(cli_title: str) -> str:
    """Recompute D-08/D-09 reachability from REMEDIATION_CONSTITUENCY plus
    the dashboard site's own severity literal -- the ground truth this
    census is checked against."""
    for slug, (kind, titles) in REMEDIATION_CONSTITUENCY.items():
        if kind == "fingerprint" and cli_title in titles:
            return "specific"
    severity = _dashboard_severity_for_cli_title(cli_title)
    if severity in {"HIGH", "CRITICAL"}:
        return "catchall-only"
    return "unreachable"


def test_bridge_reachability_covers_every_bridge_value_no_gaps_no_extras() -> None:
    bridge_values = set(DASHBOARD_TITLE_BRIDGE.values())
    census_keys = set(BRIDGE_REACHABILITY)
    missing = bridge_values - census_keys
    extra = census_keys - bridge_values
    assert not missing, (
        f"BRIDGE_REACHABILITY is missing entries for: {missing} -- every "
        "DASHBOARD_TITLE_BRIDGE value needs a reachability disposition in "
        "quirk/dashboard/api/finding_title_bridge.py"
    )
    assert not extra, (
        f"BRIDGE_REACHABILITY has stale/extra entries not present in "
        f"DASHBOARD_TITLE_BRIDGE's values: {extra} -- remove them"
    )


def test_bridge_reachability_matches_recomputed_classification() -> None:
    for cli_title, recorded in BRIDGE_REACHABILITY.items():
        computed = _compute_reachability(cli_title)
        assert computed == recorded, (
            f"reachability disagreement for {cli_title!r}: recorded "
            f"disposition is {recorded!r} but recomputing from "
            "REMEDIATION_CONSTITUENCY + dashboard severity yields "
            f"{computed!r}. Update BRIDGE_REACHABILITY in "
            "quirk/dashboard/api/finding_title_bridge.py (or investigate "
            "whether REMEDIATION_CONSTITUENCY changed underneath this "
            "census)."
        )


def test_reachability_census_is_not_vacuous_all_three_classes_present() -> None:
    classes_present = set(BRIDGE_REACHABILITY.values())
    assert classes_present == {"specific", "catchall-only", "unreachable"}, (
        f"reachability census only exercises {classes_present} -- all three "
        "of specific/catchall-only/unreachable must be represented or this "
        "test proves nothing about the untested branches"
    )

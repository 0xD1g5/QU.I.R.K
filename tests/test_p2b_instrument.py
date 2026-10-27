"""SCORE-08 (Phase 233): contract for the third P2b measurement instrument.

WHAT THE INSTRUMENT IS
----------------------
``scripts/p2b_instrument.py`` measures how the readiness score responds when
an estate gains healthy endpoints and nothing else changes (P2b, todo
``r5-ladder-fixture-is-not-the-measurement-it-claims``, xfail
``tests/test_score_properties.py::test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints``).
It sweeps all five calibration rungs (R1..R5) at +0/+20/+100/+500 healthy
endpoints and records, at every point, three values: the EMITTED score, the
COMPUTED (pre-ceiling) score and WHICH CEILING WON (CONTEXT D-02, D-04).

WHY IT IS A THIRD, INDEPENDENT INSTRUMENT
-----------------------------------------
Phase 212's two instruments both mutated evidence DICTS and read only the
computed score. This one differs on three axes:

* D-01: it enters at the ROW layer. Each rung is rebuilt as synthetic endpoint
  rows plus finding dicts and assembled through
  ``quirk.intelligence.evidence.build_evidence_summary``, the only layer where
  the 228-230 evidence changes live. The 212 three-field dict mutator survives
  only as a labelled continuity reading (D-06), and the healthy row is
  decomposed into certless / RSA / ECDSA sub-readings (D-18).
* D-02: it records emitted + computed + the winning ceiling, so a
  ceiling-shaped fix candidate is visible instead of masked.
* D-03: ``scripts/p2b_closed_form.py`` re-derives the score from a WRITTEN
  SPEC without importing anything from ``quirk``. Every point is diffed
  against ``compute_readiness_score``; a disagreement is a finding recorded in
  ``KNOWN_DISAGREEMENTS``, never something to tune away. Independence is
  checked three ways here: an import allowlist, an AST ban on dynamic-import /
  exec routes and on non-docstring strings naming the audited code, and a
  fresh subprocess that proves no ``quirk`` module was loaded.

WHAT IS DELIBERATELY ABSENT
---------------------------
The real 2026-09-14 estate reading (D-08) needs the local, untracked
``quirk-output/`` directory (the canonical DB, read only through a sqlite
``.backup`` snapshot). It is a local-only phase-record observation, so no node
here reads ``quirk-output/`` or touches the network; the snapshot node uses
``tmp_path`` only.

This file carries NO skip, skipif, xfail or slow marker: every node runs in
the fast suite, so ``tests/test_skip_registry.py`` needs no registry entry
(D-14). The only literal sweep values asserted are 212's recorded R5 computed
pair 71 (+0) / 74 (+20) for the continuity reading (D-10). Every other number
is a measurement plan 233-04 records, not a target (D-12).

WHEN THIS FILE GOES RED ON PURPOSE
----------------------------------
When Phase 234 changes ``quirk/intelligence/scoring.py``, the closed-form
nodes are EXPECTED to go red until the written spec in
``scripts/p2b_closed_form.py`` is updated to the new model (D-10). That is the
cross-check working, not a flake; update the spec, never the comparison.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from tests.cli_helpers import run_fork_safe
from tests.test_score_properties import (
    _multihost_evidence,
    _r1_pristine_pqc_ready,
    _r2_well_run_no_pqc,
    _r3_typical_enterprise,
    _r4_neglected,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLOSED_FORM_PATH = REPO_ROOT / "scripts" / "p2b_closed_form.py"

# Numerator values for the one-field term probes on the R3 base (E = C = 40).
# Never above 40, so no ratio exceeds 1.
PROBE_VALUES = (1, 3, 7, 13, 20, 40)
# Same probes on the R5 base (E = 38, C = 17), where E != C, so a RATIO_TERMS
# row carrying the wrong denominator disagrees. Never above min(E, C) = 17.
PROBE_VALUES_E_NE_C = (1, 3, 7, 13, 17)

# Fields every measure_point() result must carry (the pinned contract).
POINT_KEYS = {
    "rung", "reading", "extra", "emitted", "computed", "ceiling_source",
    "ceiling_value", "losing_ceilings", "subscores", "closed_form", "agrees",
}
CLOSED_FORM_POINT_KEYS = {
    "emitted", "computed", "ceiling", "ceiling_source", "subscores",
}

# Static independence leg (D-03).
CLOSED_FORM_IMPORT_ALLOWLIST = {
    "__future__", "math", "typing", "collections", "dataclasses",
}
CLOSED_FORM_BANNED_NAMES = {
    "__import__", "importlib", "exec", "eval", "compile", "open",
    "__builtins__", "getattr", "globals", "vars", "__loader__", "__spec__",
}

# Dynamic independence leg: a fresh interpreter that reads the evidence as
# JSON on stdin, imports ONLY the closed form, and reports every quirk module
# that ended up loaded. It must not import this test module or anything under
# tests/ (they import quirk themselves).
CHILD = (
    "import json, sys\n"
    "evidence = json.loads(sys.stdin.read())\n"
    "from scripts.p2b_closed_form import closed_form\n"
    "result = closed_form(evidence)\n"
    "loaded = sorted(m for m in sys.modules"
    " if m == 'quirk' or m.startswith('quirk.'))\n"
    "print(json.dumps({'result': result, 'quirk_modules': loaded}))\n"
)

_COMPUTED_RE = re.compile(r"computed (\d+)")


# ---------------------------------------------------------------------------
# Fixtures. The two modules are imported inside fixtures, not at module
# level, so a missing module turns each node red on its own instead of
# erroring the whole file at collection.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cf():
    return importlib.import_module("scripts.p2b_closed_form")


@pytest.fixture(scope="module")
def inst():
    return importlib.import_module("scripts.p2b_instrument")


@pytest.fixture(scope="module")
def sweep_all(inst):
    return inst.run(points=inst.POINTS)


@pytest.fixture(scope="module")
def sweep_d10(inst):
    return inst.run(points=(0, 20))


# ---------------------------------------------------------------------------
# Helpers. These read compute_readiness_score's PUBLIC return directly, the
# same way tests/test_score_properties.py::_computed_score does, so the
# comparison does not depend on the instrument's own read_score().
# ---------------------------------------------------------------------------

def _code_reading(evidence: Dict[str, Any]) -> Dict[str, Any]:
    result = compute_readiness_score(evidence)
    assert result["score"] is not None, (
        "fixture assessed zero domains; the instrument is broken, not the "
        f"subject. coverage: {result['coverage_disclosure']}"
    )
    reason = result.get("rating_cap_reason") or ""
    match = _COMPUTED_RE.search(reason)
    computed = int(match.group(1)) if match else int(result["score"])
    if reason.startswith("no post-quantum"):
        source = "pqc_readiness"
    elif match:
        source = "consequence"
    else:
        source = "none"
    return {
        "emitted": int(result["score"]),
        "computed": computed,
        "ceiling_source": source,
        "subscores": dict(result["subscores"]),
    }


def _cf_reading(cf_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "emitted": cf_result["emitted"],
        "computed": cf_result["computed"],
        "ceiling_source": cf_result["ceiling_source"],
        "subscores": dict(cf_result["subscores"]),
    }


def _differs(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    return [k for k in ("emitted", "computed", "ceiling_source", "subscores")
            if a[k] != b[k]]


def _set_path(evidence: Dict[str, Any], path: Tuple[str, ...], value) -> None:
    node = evidence
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def _resolves(evidence: Dict[str, Any], path: Tuple[str, ...]) -> bool:
    node: Any = evidence
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True


def _severity(evidence: Dict[str, Any]) -> Dict[str, Any]:
    scored = evidence.get("scored_finding_severity_counts")
    if isinstance(scored, dict):
        return scored
    return evidence.get("finding_severity_counts", {})


def _weakness_inputs(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """The weakness counts a healthy row must never move.

    ``legacy_tls`` is read as scoring reads it: ``legacy_tls_count`` when
    present, else the LOW severity count (the dict ladder's fallback).
    """
    sev = _severity(evidence)
    legacy = evidence.get("legacy_tls_count")
    if legacy is None:
        legacy = int(sev.get("LOW", 0) or 0)
    certs = evidence.get("certificate_observations", {})
    return {
        "expired_count": certs.get("expired_count", 0),
        "expiring_count": certs.get("expiring_count", 0),
        "self_signed_count": certs.get("self_signed_count", 0),
        "legacy_tls": legacy,
        "plaintext_http_count": evidence.get("plaintext_http_count", 0),
        "http_on_tls_port_count": evidence.get("http_on_tls_port_count", 0),
        "CRITICAL": int(sev.get("CRITICAL", 0) or 0),
        "HIGH": int(sev.get("HIGH", 0) or 0),
    }


def _probe_paths(cf) -> List[Tuple[str, ...]]:
    paths: List[Tuple[str, ...]] = []
    for _domain, path, _denom, _weight, _sign in cf.RATIO_TERMS:
        if tuple(path) not in paths:
            paths.append(tuple(path))
    if ("motion_email_starttls_missing_count",) not in paths:
        paths.append(("motion_email_starttls_missing_count",))
    return paths


def _branch_probes(cf) -> Dict[str, Dict[str, Any]]:
    """Branches the ladder never exercises, each a one-edit copy of R3."""
    probes: Dict[str, Dict[str, Any]] = {}

    ev = _r3_typical_enterprise()
    ev["finding_severity_counts"]["HIGH"] = 1
    ev["finding_severity_counts"]["CRITICAL"] = 0
    probes["high1-crit0"] = ev

    ev = _r3_typical_enterprise()
    ev["finding_severity_counts"]["CRITICAL"] = 2
    probes["crit2"] = ev

    ev = _r3_typical_enterprise()
    ev["finding_severity_counts"]["CRITICAL"] = 5
    probes["crit5"] = ev

    ev = _r3_typical_enterprise()
    ev["pqc_hybrid_endpoint_count"] = 3
    probes["pqc-hybrid-3"] = ev

    ev = _r3_typical_enterprise()
    ev["scan_error"] = {"count": 16, "rate": 0.4}
    probes["scan-error-0.4"] = ev

    ev = _r3_typical_enterprise()
    ev["cert_key_type_counts"]["ECDSA"] = 1
    probes["ecdsa-1"] = ev

    ev = _r3_typical_enterprise()
    ev["cert_key_type_counts"] = {"RSA": 0, "ECDSA": 0}
    probes["keytype-unreported-with-certs"] = ev

    ev = _r3_typical_enterprise()
    for key in cf.DAR_KEYS:
        ev["protocol_counts"][key] = 0
    probes["dar-unassessed"] = ev

    ev = _r3_typical_enterprise()
    for key in cf.MOTION_KEYS:
        ev["protocol_counts"][key] = 0
    probes["motion-unassessed"] = ev

    ev = _r3_typical_enterprise()
    ev["legacy_tls_count"] = 4
    probes["legacy-tls-present"] = ev

    return probes


def _all_probes(cf) -> Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Every term and branch probe: id -> (closed-form reading, code reading)."""
    out: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    bases = (
        ("R3", _r3_typical_enterprise, PROBE_VALUES),
        ("R5", _multihost_evidence, PROBE_VALUES_E_NE_C),
    )
    for base_name, builder, values in bases:
        for path in _probe_paths(cf):
            for value in values:
                ev = copy.deepcopy(builder())
                _set_path(ev, path, value)
                probe_id = f"probe|{base_name}|{'.'.join(path)}|{value}"
                out[probe_id] = (
                    _cf_reading(cf.closed_form(copy.deepcopy(ev))),
                    _code_reading(ev),
                )
    for name, ev in _branch_probes(cf).items():
        probe_id = f"probe|R3|branch|{name}"
        out[probe_id] = (
            _cf_reading(cf.closed_form(copy.deepcopy(ev))),
            _code_reading(ev),
        )
    return out


# ---------------------------------------------------------------------------
# Nodes.
# ---------------------------------------------------------------------------

def test_emits_row_per_rung_per_point(inst, sweep_d10):
    """D-10: one result per (rung, reading, extra), with the full contract."""
    expected = {
        (rung, reading, extra)
        for rung in ("R1", "R2", "R3", "R4", "R5")
        for reading in ("rows_ecdsa", "rows_rsa", "rows_certless", "mutator_212")
        for extra in (0, 20)
    }
    assert tuple(inst.RUNGS) == ("R1", "R2", "R3", "R4", "R5")
    assert tuple(inst.READINGS) == (
        "rows_ecdsa", "rows_rsa", "rows_certless", "mutator_212")
    assert inst.PRIMARY_READING == "rows_ecdsa"
    assert inst.CONTINUITY_READING == "mutator_212"

    seen = [(p["rung"], p["reading"], p["extra"]) for p in sweep_d10]
    assert len(seen) == len(set(seen)), (
        f"duplicate sweep cells: {sorted(c for c in seen if seen.count(c) > 1)}"
    )
    assert set(seen) == expected, (
        f"missing cells {sorted(expected - set(seen))}; "
        f"unexpected cells {sorted(set(seen) - expected)}"
    )
    assert len(sweep_d10) == 40
    for point in sweep_d10:
        cell = f"{point['rung']}|{point['reading']}|{point['extra']}"
        missing = POINT_KEYS - set(point)
        assert not missing, f"{cell}: measure_point lacks keys {sorted(missing)}"
        cf_missing = CLOSED_FORM_POINT_KEYS - set(point["closed_form"])
        assert not cf_missing, (
            f"{cell}: closed_form sub-dict lacks keys {sorted(cf_missing)}"
        )


def test_rows_reproduce_dict_ladder_at_zero(inst):
    """D-01: at +0 the row rebuild of each rung scores exactly as the dict."""
    relevant = set(inst.SCORE_RELEVANT_PATHS)
    for rung in inst.RUNGS:
        row_ev = inst.row_evidence(rung, 0)
        dict_ev = inst.dict_rung(rung)

        row_proj = inst.projection(row_ev)
        dict_proj = inst.projection(dict_ev)
        diffs = {
            k: (dict_proj.get(k), row_proj.get(k))
            for k in set(row_proj) | set(dict_proj)
            if row_proj.get(k) != dict_proj.get(k)
        }
        assert not diffs, (
            f"{rung}|rows_ecdsa|0: score-relevant projection differs "
            f"(field: (dict, rows)): {diffs}"
        )

        row_score = inst.read_score(row_ev)
        dict_score = inst.read_score(dict_ev)
        for key in ("emitted", "computed", "subscores"):
            assert row_score[key] == dict_score[key], (
                f"{rung}|rows_ecdsa|0: {key} dict={dict_score[key]} "
                f"rows={row_score[key]}"
            )

        for gap in inst.projection_gaps(rung):
            assert len(gap) == 3, (
                f"{rung}: projection gap {gap!r} is not (field, dict, rows)"
            )
            field = gap[0]
            assert field not in relevant, (
                f"{rung}: projection gap on SCORE-RELEVANT field {field!r} "
                f"(dict={gap[1]!r}, rows={gap[2]!r}); a gap is only allowed "
                "on a field scoring does not read"
            )


def test_closed_form_agrees(cf, inst, sweep_all):
    """D-03: closed form == compute_readiness_score at every sweep point.

    All four points, not only D-10's +0/+20: integer rounding hides small
    spec errors at two points (RESEARCH Pitfall 3).
    """
    known = dict(inst.KNOWN_DISAGREEMENTS)
    disagreeing = set()
    for point in sweep_all:
        cell = f"{point['rung']}|{point['reading']}|{point['extra']}"
        evidence = inst.evidence_for(point["rung"], point["reading"], point["extra"])

        code = _code_reading(copy.deepcopy(evidence))
        spec = _cf_reading(cf.closed_form(copy.deepcopy(evidence)))

        # The instrument's own record must match a direct read of both sides.
        assert point["emitted"] == code["emitted"], (
            f"{cell}: instrument emitted {point['emitted']} != "
            f"compute_readiness_score {code['emitted']}"
        )
        assert point["computed"] == code["computed"], (
            f"{cell}: instrument computed {point['computed']} != "
            f"compute_readiness_score {code['computed']}"
        )
        assert point["ceiling_source"] == code["ceiling_source"], (
            f"{cell}: instrument ceiling_source {point['ceiling_source']!r} "
            f"!= parsed {code['ceiling_source']!r}"
        )
        assert _cf_reading(point["closed_form"]) == spec, (
            f"{cell}: instrument closed_form {point['closed_form']} != direct "
            f"closed_form {spec}"
        )

        mismatched = _differs(spec, code)
        assert point["agrees"] == (not mismatched), (
            f"{cell}: agrees={point['agrees']} but the fields that differ are "
            f"{mismatched}"
        )
        if mismatched:
            disagreeing.add(cell)
            assert cell in known, (
                f"{cell}: closed form and compute_readiness_score disagree on "
                f"{mismatched}: closed_form={spec} code={code}. Record the "
                "cause in KNOWN_DISAGREEMENTS; never tune it away."
            )

    sweep_keys = {k for k in known if not k.startswith("probe|")}
    stale = sorted(sweep_keys - disagreeing)
    assert not stale, (
        f"KNOWN_DISAGREEMENTS entries that no longer disagree (or name no "
        f"sweep cell): {stale}"
    )

    probe_keys = {k for k in known if k.startswith("probe|")}
    if probe_keys:
        probes = _all_probes(cf)
        stale_probes = sorted(
            k for k in probe_keys
            if k not in probes or not _differs(*probes[k])
        )
        assert not stale_probes, (
            f"KNOWN_DISAGREEMENTS probe entries that no longer disagree (or "
            f"name no probe): {stale_probes}"
        )


def test_closed_form_term_probes(cf):
    """D-03: every spec line the ladder never exercises, probed one at a time.

    Imports only the closed form and the dict ladder. The instrument is
    imported ONLY if a probe disagrees, to look up a KNOWN_DISAGREEMENTS
    excuse.
    """
    empty = build_evidence_summary([], [])
    unresolved = [
        ".".join(path) for _d, path, _den, _w, _s in cf.RATIO_TERMS
        if not _resolves(empty, tuple(path))
    ]
    assert not unresolved, (
        "RATIO_TERMS key paths absent from build_evidence_summary([], []) "
        f"output (a mistyped key hides behind a zero numerator): {unresolved}"
    )
    for _domain, _path, denom, _weight, _sign in cf.RATIO_TERMS:
        assert denom in ("E", "C"), f"RATIO_TERMS denominator {denom!r}"

    missing_e = copy.deepcopy(_r3_typical_enterprise())
    del missing_e["assessable_endpoint_count"]
    with pytest.raises(cf.UncoveredBranch):
        cf.closed_form(missing_e)
    with pytest.raises(cf.UncoveredBranch):
        cf.closed_form(_r3_typical_enterprise(), profile="conservative")

    r3 = _r3_typical_enterprise()
    assert r3["assessable_endpoint_count"] == 40
    assert r3["certificate_observations"]["certs_observed"] == 40
    r5 = _multihost_evidence()
    assert r5["assessable_endpoint_count"] == 38
    assert r5["certificate_observations"]["certs_observed"] == 17

    probes = _all_probes(cf)
    failures = {
        probe_id: (spec, code, _differs(spec, code))
        for probe_id, (spec, code) in probes.items()
        if _differs(spec, code)
    }
    if failures:
        known = importlib.import_module("scripts.p2b_instrument").KNOWN_DISAGREEMENTS
        unexcused = {k: v for k, v in failures.items() if k not in known}
        assert not unexcused, (
            f"{len(unexcused)} probe(s) disagree with no KNOWN_DISAGREEMENTS "
            "entry (id: (closed_form, code, fields)): "
            + "; ".join(f"{k}: {v}" for k, v in sorted(unexcused.items()))
        )


def test_closed_form_is_independent():
    """D-03: the closed form never reaches the code it audits."""
    assert CLOSED_FORM_PATH.is_file(), (
        f"{CLOSED_FORM_PATH} does not exist; the closed form is not written yet"
    )
    tree = ast.parse(CLOSED_FORM_PATH.read_text(encoding="utf-8"))

    # (a) import allowlist.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top in CLOSED_FORM_IMPORT_ALLOWLIST, (
                    f"line {node.lineno}: import {alias.name!r} is outside the "
                    f"allowlist {sorted(CLOSED_FORM_IMPORT_ALLOWLIST)}"
                )
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            assert node.level == 0 and top in CLOSED_FORM_IMPORT_ALLOWLIST, (
                f"line {node.lineno}: from {'.' * node.level}{node.module} "
                f"import ... is outside the allowlist "
                f"{sorted(CLOSED_FORM_IMPORT_ALLOWLIST)}"
            )

    # (b) no dynamic-import / exec / reflection route.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in CLOSED_FORM_BANNED_NAMES:
            raise AssertionError(
                f"line {node.lineno}: banned name {node.id!r} in the closed form"
            )
        if isinstance(node, ast.Attribute) and node.attr in CLOSED_FORM_BANNED_NAMES:
            raise AssertionError(
                f"line {node.lineno}: banned attribute {node.attr!r} in the "
                "closed form"
            )

    # (c) no non-docstring string naming the audited code.
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings):
            lowered = node.value.lower()
            assert "quirk" not in lowered and "scoring" not in lowered, (
                f"line {node.lineno}: non-docstring string {node.value!r} "
                "names the audited code"
            )

    # Dynamic leg: a fresh interpreter loads no quirk module at all.
    evidence = _r3_typical_enterprise()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = run_fork_safe(
        [sys.executable, "-c", CHILD],
        input=json.dumps(evidence),
        env=env,
    )
    assert proc.returncode == 0, (
        f"closed-form child exited {proc.returncode}: stderr={proc.stderr!r}"
    )
    payload = json.loads(proc.stdout)
    assert payload["quirk_modules"] == [], (
        f"importing and running the closed form loaded quirk modules: "
        f"{payload['quirk_modules']}"
    )
    child = _cf_reading(payload["result"])
    code = _code_reading(evidence)
    for key in ("emitted", "computed", "subscores"):
        assert child[key] == code[key], (
            f"R3 in a quirk-free child: closed_form {key}={child[key]} "
            f"compute_readiness_score {key}={code[key]}"
        )


def test_continuity_reproduces_212(inst):
    """D-06/D-10: 212's recorded R5 computed values, a record not a prediction."""
    at_zero = inst.measure_point("R5", "mutator_212", 0)["computed"]
    at_twenty = inst.measure_point("R5", "mutator_212", 20)["computed"]
    assert at_zero == 71, f"R5|mutator_212|0: computed {at_zero}, 212 recorded 71"
    assert at_twenty == 74, (
        f"R5|mutator_212|20: computed {at_twenty}, 212 recorded 74"
    )


def test_ceiling_identification_consistent(sweep_d10):
    """D-02: the winning ceiling explains the emitted score (linear squeeze)."""
    for point in sweep_d10:
        cell = f"{point['rung']}|{point['reading']}|{point['extra']}"
        if point["ceiling_source"] == "none":
            assert point["ceiling_value"] is None, (
                f"{cell}: no ceiling won but ceiling_value={point['ceiling_value']}"
            )
            assert point["emitted"] == point["computed"], (
                f"{cell}: no ceiling won but emitted {point['emitted']} != "
                f"computed {point['computed']}"
            )
        else:
            assert point["ceiling_source"] in ("consequence", "pqc_readiness"), (
                f"{cell}: unknown ceiling_source {point['ceiling_source']!r}"
            )
            squeezed = int(round(point["ceiling_value"] * point["computed"] / 100))
            assert point["emitted"] == squeezed, (
                f"{cell}: emitted {point['emitted']} != round("
                f"{point['ceiling_value']} x {point['computed']} / 100) = "
                f"{squeezed} ({point['ceiling_source']})"
            )


def test_healthy_rows_are_healthy(inst):
    """D-05/D-18/D-15: healthy rows add no weakness; no Kerberos placeholder."""
    for kind in ("ecdsa", "rsa", "certless"):
        rows = [inst.healthy_row(i, kind) for i in range(20)]
        findings = derive_report_findings(rows)
        bad = [
            (f.get("severity"), f.get("title"))
            for f in findings
            if str(f.get("severity", "")).upper() in ("CRITICAL", "HIGH")
        ]
        assert not bad, f"healthy {kind} rows derive CRITICAL/HIGH findings: {bad}"
        for row in rows:
            detail = getattr(row, "service_detail", "") or ""
            assert "pqc-hybrid-detected" not in detail, (
                f"healthy {kind} row {row.host} claims PQC hybrid: {detail!r}"
            )
            not_after = getattr(row, "cert_not_after", None)
            if kind == "certless":
                assert not_after is None, (
                    f"certless row {row.host} carries a certificate "
                    f"(cert_not_after={not_after!r})"
                )
            else:
                assert not_after is not None and not_after > inst.REF, (
                    f"healthy {kind} row {row.host} cert_not_after {not_after!r} "
                    f"is not after REF {inst.REF!r}"
                )

    for rung in inst.RUNGS:
        for kind in ("ecdsa", "rsa", "certless"):
            base = _weakness_inputs(inst.row_evidence(rung, 0, kind))
            wider = _weakness_inputs(inst.row_evidence(rung, 20, kind))
            assert base == wider, (
                f"{rung}|rows_{kind}: +20 healthy rows moved weakness inputs "
                f"from {base} to {wider}"
            )

    for rung in inst.RUNGS:
        rows, _findings = inst.rung_rows(rung)
        kerberos = [
            r for r in rows
            if str(getattr(r, "protocol", "") or "").upper() == "KERBEROS"
        ]
        # The dict ladder carries KERBEROS: 1 in every rung; without a row
        # this check would be vacuous.
        assert kerberos, f"{rung}: no KERBEROS row to check for a placeholder"
        for row in kerberos:
            detail = getattr(row, "service_detail", "") or ""
            assert "etype:" in detail, (
                f"{rung}: KERBEROS row {getattr(row, 'host', '?')} is a "
                f"placeholder (service_detail={detail!r}, no 'etype:')"
            )


def test_cli_outputs_json_and_markdown(inst, capsys):
    """D-09: the committed instrument emits JSON and a Markdown table."""
    assert inst.main(["--json", "--points", "0"]) == 0
    report = json.loads(capsys.readouterr().out)
    for key in ("provenance", "points", "readings", "results",
                "ladder_at_zero", "projection_gaps", "known_disagreements"):
        assert key in report, f"--json report lacks top-level key {key!r}"
    for key in ("head_sha", "scoring_blob", "evidence_blob", "python"):
        assert key in report["provenance"], f"provenance lacks {key!r}"

    assert inst.main(["--markdown", "--points", "0"]) == 0
    markdown = capsys.readouterr().out
    assert any(line.startswith("| R5 |") for line in markdown.splitlines()), (
        "--markdown output has no table row starting '| R5 |'"
    )


def test_real_db_snapshot_is_read_only(inst, tmp_path):
    """D-08: the snapshot path never modifies its source (tmp_path only)."""
    src = tmp_path / "source.db"
    conn = sqlite3.connect(str(src))
    try:
        conn.execute("CREATE TABLE endpoints (host TEXT, port INTEGER)")
        conn.execute("INSERT INTO endpoints VALUES ('h.p2b.example', 443)")
        conn.commit()
    finally:
        conn.close()
    before = hashlib.sha256(src.read_bytes()).hexdigest()

    snap = inst.snapshot_db(src, tmp_path / "snap")

    snap_conn = sqlite3.connect(str(snap))
    try:
        rows = snap_conn.execute("SELECT host, port FROM endpoints").fetchall()
    finally:
        snap_conn.close()
    assert rows == [("h.p2b.example", 443)], f"snapshot rows: {rows}"
    after = hashlib.sha256(src.read_bytes()).hexdigest()
    assert after == before, "snapshot_db modified its source database"

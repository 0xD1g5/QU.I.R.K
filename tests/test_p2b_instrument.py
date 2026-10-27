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
  SPEC without importing anything from ``quirk``. The spec was read from
  ``scoring.py`` at ``e0064b02`` (RESEARCH Q4), so the closed form is
  independent in mechanism, not in origin: agreement validates the
  instrument's reading of the scorer, not the scorer's intent. Every point is
  diffed against ``compute_readiness_score``; a disagreement is a finding
  recorded in ``KNOWN_DISAGREEMENTS``, never something to tune away.
  Mechanism independence is checked four ways here: an import allowlist, an
  AST ban on dynamic-import / exec / reflection names, an AST ban on
  non-docstring strings naming the audited code, and a fresh subprocess that
  proves no ``quirk`` module was loaded.

WHAT IS DELIBERATELY ABSENT
---------------------------
The real 2026-09-14 estate reading (D-08) needs the local, untracked
``quirk-output/`` directory (the canonical DB, read only through a sqlite
``.backup`` snapshot). It is a local-only phase-record observation, so no node
here reads ``quirk-output/`` or touches the network; the snapshot node uses
``tmp_path`` only.

This file carries NO skip, skipif, xfail or slow marker: every node runs in
the fast suite, so ``tests/test_skip_registry.py`` needs no registry entry
(D-14). No sweep value is asserted as a literal; the continuity reading is
asserted FLAT (Phase 234 D-08), and 212's 71/74/78/82 is kept as history in
that node's comment. Every number is a measurement the phase records, not a
target (D-12).

THE P2B GATE (Phase 234)
------------------------
Three gate nodes carry SCORE-09 (Phase 234 CONTEXT O-1: the gate is this
instrument across all rungs and readings, not only the property xfail):

* ``test_p2b_non_increase_all_rungs_all_readings`` (D-07(a)): over R1..R5 x
  the four readings x +0/+20/+100/+500, neither emitted nor computed ever
  rises. Red on scoring 3.0.
* ``test_p2b_weakness_rows_lower_the_score`` (D-07(b), D-22): the
  non-vacuity control. Adding weakness rows strictly lowers the score on
  R2..R5 and pulls R1 below 100. It is green on 3.0 too (3.0 also lowers the
  score when weakness is added), so its red proof is a mutation that zeroes
  every weight, recorded in the 234-01 SUMMARY.
* ``test_scan_error_rows_do_not_dilute`` (D-03): scan-error rows plus the
  healthy sweep never raise emitted, computed, hygiene or modern_tls. The
  scan-error rate sites are outside the ratio terms, so the sweep alone could
  not see them. Red on scoring 3.0.

WHEN THIS FILE GOES RED ON PURPOSE
----------------------------------
When ``quirk/intelligence/scoring.py`` changes, the closed-form nodes are
EXPECTED to go red until the written spec in ``scripts/p2b_closed_form.py``
matches the new model (D-10). That is the cross-check working, not a flake;
update the spec, never the comparison. Phase 234 ran this in the other order
(D-06, spec-first): the 4.0 spec was committed BEFORE the scorer changed, so
the closed-form nodes were red against 3.0 until plan 234-03 landed the
scorer.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
from datetime import timedelta
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

# Count values for the one-field term probes, used on BOTH bases (R3 and R5).
# 39/40/41/80 straddle the N_REF = 40 saturation knee of the 4.0 count curve.
# Denominators no longer exist (scoring 4.0, D-01), so the old E != C probe
# set is retired; the R5 base stays only as a second evidence context.
PROBE_VALUES = (1, 3, 7, 13, 20, 39, 40, 41, 80)

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


_ABSENT = object()


def _flatten(node: Any, prefix: str = "") -> Dict[str, Any]:
    """Every leaf of an evidence dict, keyed by its dotted path."""
    if not isinstance(node, dict):
        return {prefix: node}
    out: Dict[str, Any] = {}
    for key, value in node.items():
        out.update(_flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    return out


# WR-03: what +N healthy rows may move in the evidence summary, per kind.
# SCORED moves: E for every kind; C and the key-type counter for a row with
# a certificate. These are the effects the readings exist to measure.
HEALTHY_SCORED_MOVES = {
    "ecdsa": {"assessable_endpoint_count",
              "certificate_observations.certs_observed",
              "cert_key_type_counts.ECDSA"},
    "rsa": {"assessable_endpoint_count",
            "certificate_observations.certs_observed",
            "cert_key_type_counts.RSA"},
    "certless": {"assessable_endpoint_count"},
}
# UNSCORED moves (scoring never reads them): population counters, a ratio
# whose scored input is the count, and the MEDIUM "quantum-vulnerable key"
# finding a certificate-bearing row derives (scoring reads CRITICAL/HIGH
# only, and LOW only when legacy_tls_count is absent).
_UNSCORED_POPULATION = {
    "assessed_crypto_count", "protocol_counts.TLS", "totals.endpoints",
    "dar_db_plaintext_ratio",
}
_UNSCORED_CERT_FINDING = {
    "finding_severity_counts.MEDIUM",
    "scored_finding_severity_counts.MEDIUM", "totals.findings",
}
HEALTHY_ALLOWED_MOVES = {
    "ecdsa": HEALTHY_SCORED_MOVES["ecdsa"] | _UNSCORED_POPULATION
    | _UNSCORED_CERT_FINDING,
    "rsa": HEALTHY_SCORED_MOVES["rsa"] | _UNSCORED_POPULATION
    | _UNSCORED_CERT_FINDING,
    "certless": HEALTHY_SCORED_MOVES["certless"] | _UNSCORED_POPULATION,
}


def _probe_paths(cf) -> List[Tuple[str, ...]]:
    paths: List[Tuple[str, ...]] = []
    for _domain, path, _weight, _sign in cf.COUNT_TERMS:
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
    probes["scan-error-count-16"] = ev

    # A rate with no count: 4.0 reads the count only (D-03), so no penalty.
    ev = _r3_typical_enterprise()
    ev["scan_error"] = {"rate": 0.4}
    probes["scan-error-rate-only"] = ev

    ev = _r3_typical_enterprise()
    ev["cert_key_type_counts"]["ECDSA"] = 1
    probes["ecdsa-1"] = ev

    ev = _r3_typical_enterprise()
    ev["cert_key_type_counts"] = {"RSA": 0, "ECDSA": 0, "PQC": 1}
    probes["pqc-cert-1"] = ev

    ev = _r3_typical_enterprise()
    ev["cert_key_type_counts"]["PQC"] = 1
    probes["pqc-cert-with-rsa"] = ev

    # Only a placeholder Kerberos row: identity must be unassessed (D-11).
    ev = _r3_typical_enterprise()
    ev["certificate_observations"]["certs_observed"] = 0
    for key in cf.IDENTITY_KEYS:
        ev["protocol_counts"][key] = 0
    ev["protocol_counts"]["KERBEROS"] = 1
    ev["kerberos_placeholder_count"] = 1
    probes["kerberos-placeholder-only"] = ev

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
        ("R5", _multihost_evidence, PROBE_VALUES),
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
        ".".join(path) for _d, path, _w, _s in cf.COUNT_TERMS
        if not _resolves(empty, tuple(path))
    ]
    assert not unresolved, (
        "COUNT_TERMS key paths absent from build_evidence_summary([], []) "
        f"output (a mistyped key hides behind a zero count): {unresolved}"
    )
    assert len(cf.COUNT_TERMS) == 35, (
        f"COUNT_TERMS has {len(cf.COUNT_TERMS)} rows; the 35 ratio sites "
        "each become one count term (D-01)"
    )
    for row in cf.COUNT_TERMS:
        assert len(row) == 4, f"COUNT_TERMS row {row!r} is not 4 fields"
        _domain, _path, weight, sign = row
        assert weight > 0, f"COUNT_TERMS row {row!r}: weight {weight} <= 0"
        assert sign in (-1, 1), f"COUNT_TERMS row {row!r}: sign {sign}"
    # The 4.0 spec reads three keys the 3.0 evidence may not carry yet; a
    # mistyped or missing key would hide behind a zero read.
    extra_unresolved = [
        ".".join(path) for path in (
            ("scan_error", "count"),
            ("cert_key_type_counts", "PQC"),
            ("kerberos_placeholder_count",),
        )
        if not _resolves(empty, path)
    ]
    assert not extra_unresolved, (
        "4.0 spec key paths absent from build_evidence_summary([], []) "
        f"output: {extra_unresolved}"
    )

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
    """D-08: the 212 continuity reading is FLAT under scoring 4.0.

    The node name is kept because UAT-233-04 cites it. History, not an
    assertion: Phase 212 recorded R5 computed 71 (+0) -> 74 (+20) -> 78
    (+100) -> 82 (+500) under scoring 3.0. That rise WAS the P2b defect;
    4.0 makes the reading flat.
    """
    points = [inst.measure_point("R5", "mutator_212", extra)
              for extra in inst.POINTS]
    assert len(points) == 4, f"expected 4 points, got {len(points)}"
    for key in ("computed", "emitted"):
        seq = [p[key] for p in points]
        assert len(set(seq)) == 1, (
            f"R5|mutator_212|{key}: not flat over points "
            f"{list(inst.POINTS)}: {seq}"
        )


def test_p2b_non_increase_all_rungs_all_readings(sweep_all):
    """D-07(a): healthy endpoints never raise emitted or computed.

    Every rung x every reading x +0/+20/+100/+500.
    """
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for point in sweep_all:
        groups.setdefault((point["rung"], point["reading"]), []).append(point)
    # Non-vacuity: a zero-match grouping would pass every check below.
    assert len(groups) == 20, (
        f"expected 20 (rung, reading) groups: {sorted(groups)}"
    )
    for key, pts in groups.items():
        assert len(pts) == 4, f"{key}: expected 4 points, got {len(pts)}"

    rising = []
    for (rung, reading), pts in sorted(groups.items()):
        pts = sorted(pts, key=lambda p: p["extra"])
        for key in ("emitted", "computed"):
            seq = [(p["extra"], p[key]) for p in pts]
            for (x0, v0), (x1, v1) in zip(seq, seq[1:]):
                if v1 > v0:
                    rising.append(
                        f"{rung}|{reading}|{key}: +{x0}={v0} -> +{x1}={v1} "
                        f"(sequence {[v for _x, v in seq]})"
                    )
    assert not rising, (
        f"{len(rising)} rise(s) from adding healthy endpoints: "
        + "; ".join(rising)
    )


def _weak_row(inst, j: int):
    """TLSv1.1 + expired + self-signed + RSA (D-22: legacy TLS alone is not
    enough to move R5's emitted score)."""
    row = inst._row(
        host=f"weak-{j}.p2b.example", port=443, protocol="TLS",
        tls_version="TLSv1.1", tls_supported_versions="TLSv1.1,TLSv1.2",
        cipher_suite=inst.AEAD_CIPHER,
    )
    row.cert_not_after = inst.EXPIRED
    row.cert_subject = f"CN=w{j}"
    row.cert_issuer = f"CN=w{j}"
    row.cert_pubkey_alg = "RSA"
    return row


def test_p2b_weakness_rows_lower_the_score(inst):
    """D-07(b)/D-22: the non-vacuity control for the non-increase gate.

    Adding weakness rows strictly lowers emitted and computed on R2..R5; R1
    sits at the ceiling, where flat proves nothing, so it must drop below
    100. Green on 3.0 as well; its red proof is a zero-weights mutation.
    """
    weak_rows = [_weak_row(inst, j) for j in range(20)]
    for rung in inst.RUNGS:
        rows, findings = inst.rung_rows(rung)
        base = inst.read_score(build_evidence_summary(
            rows, findings, reference_utc=inst.REF))
        weak = inst.read_score(build_evidence_summary(
            rows + weak_rows, findings, reference_utc=inst.REF))
        if rung == "R1":
            assert weak["emitted"] < 100, (
                f"R1|+20 weak: emitted {weak['emitted']} (base "
                f"{base['emitted']}) did not drop below 100"
            )
            continue
        for key in ("emitted", "computed"):
            assert weak[key] < base[key], (
                f"{rung}|+20 weak: {key} {base[key]} -> {weak[key]}; adding "
                "weakness must strictly lower it"
            )


def test_scan_error_rows_do_not_dilute(inst):
    """D-03: scan-error rows plus healthy endpoints never raise the score.

    The two scan-error sites read a rate over all endpoints, outside the
    ratio terms, so the sweep alone cannot see them. Subscores are asserted
    too: a computed score can hide a single-domain rise.
    """
    err_rows = [
        inst._row(host=f"err-{j}.p2b.example", port=443, protocol="TLS",
                  scan_error="timeout")
        for j in range(4)
    ]
    rising = []
    for rung in inst.RUNGS:
        rows, findings = inst.rung_rows(rung)
        series: Dict[str, List[Tuple[int, Any]]] = {
            "emitted": [], "computed": [], "hygiene": [], "modern_tls": [],
        }
        for extra in inst.POINTS:
            h_rows, h_findings = inst._healthy(extra, "ecdsa")
            evidence = build_evidence_summary(
                rows + err_rows + h_rows, findings + h_findings,
                reference_utc=inst.REF)
            # Non-vacuity: the four error rows must reach the evidence.
            assert evidence["scan_error"]["count"] == 4, (
                f"{rung}|+{extra}: scan_error.count "
                f"{evidence['scan_error']['count']} != 4"
            )
            score = inst.read_score(evidence)
            series["emitted"].append((extra, score["emitted"]))
            series["computed"].append((extra, score["computed"]))
            series["hygiene"].append((extra, score["subscores"]["hygiene"]))
            series["modern_tls"].append(
                (extra, score["subscores"]["modern_tls"]))
        for key, seq in series.items():
            for (x0, v0), (x1, v1) in zip(seq, seq[1:]):
                if v1 > v0:
                    rising.append(
                        f"{rung}|scan_error+4|{key}: +{x0}={v0} -> +{x1}={v1} "
                        f"(sequence {[v for _x, v in seq]})"
                    )
    assert not rising, (
        f"{len(rising)} rise(s) with 4 scan-error rows plus healthy "
        "endpoints: " + "; ".join(rising)
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

    # WR-03: the WHOLE evidence summary, flattened, may move only where a
    # healthy row is expected to move it. Anything else that moves (e.g.
    # mtls_present_count, scan_error.count, protocol_counts.UNKNOWN) fails.
    relevant = set(inst.SCORE_RELEVANT_PATHS)
    for kind, allowed in HEALTHY_ALLOWED_MOVES.items():
        must_move = HEALTHY_SCORED_MOVES[kind]
        assert must_move <= allowed
        scored_allowed = allowed & relevant
        assert scored_allowed == must_move, (
            f"rows_{kind}: allowlist admits scored input(s) "
            f"{sorted(scored_allowed - must_move)} beyond E/C/key type"
        )
        for rung in inst.RUNGS:
            base = _flatten(inst.row_evidence(rung, 0, kind))
            wider = _flatten(inst.row_evidence(rung, 20, kind))
            moved = {k for k in set(base) | set(wider)
                     if base.get(k, _ABSENT) != wider.get(k, _ABSENT)}
            unexpected = moved - allowed
            assert not unexpected, (
                f"{rung}|rows_{kind}: +20 healthy rows moved "
                + "; ".join(f"{k}: {base.get(k, _ABSENT)!r} -> "
                            f"{wider.get(k, _ABSENT)!r}"
                            for k in sorted(unexpected))
            )
            assert must_move <= moved, (
                f"{rung}|rows_{kind}: expected {sorted(must_move - moved)} to "
                "move with +20 healthy rows; the check would be vacuous"
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


def test_healthy_rows_survive_a_later_clock(inst, monkeypatch):
    """CR-01: healthy rows stay healthy whatever today's date is.

    ``derive_report_findings`` checks certificate expiry against the wall
    clock, not against REF. A healthy notAfter tied to REF is a dated bomb:
    once real time passes it, every healthy row derives a CRITICAL and the
    instrument raises. Move the evaluator's clock 5+ years past REF and check
    that the instrument still runs and no healthy row derives an expiry
    finding of any severity.
    """
    fe = importlib.import_module("quirk.engine.findings_evaluator")
    real_dt = fe.datetime
    later = inst.REF + timedelta(days=5 * 366)

    class _Meta(type):
        def __instancecheck__(cls, obj):
            return isinstance(obj, real_dt)

    class _LaterClock(metaclass=_Meta):
        @classmethod
        def now(cls, tz=None):
            return later.replace(tzinfo=tz)

    monkeypatch.setattr(fe, "datetime", _LaterClock)

    for kind in inst.HEALTHY_KINDS:
        rows = [inst.healthy_row(i, kind) for i in range(20)]
        findings = fe.derive_report_findings(rows)
        bad = [
            (f.get("severity"), f.get("title")) for f in findings
            if str(f.get("severity", "")).upper() in ("CRITICAL", "HIGH")
            or "expir" in str(f.get("title", "")).lower()
        ]
        assert not bad, (
            f"clock {later.isoformat()}: healthy {kind} rows derive {bad}"
        )

    points = inst.run(points=(20,))
    assert len(points) == len(inst.RUNGS) * len(inst.READINGS)
    for point in points:
        assert point["agrees"], (
            f"clock {later.isoformat()}: {point['rung']}|{point['reading']}|20 "
            "closed form disagrees"
        )


def test_cli_outputs_json_and_markdown(inst, capsys):
    """D-09: the committed instrument emits JSON and a Markdown table."""
    assert inst.main(["--json", "--points", "0"]) == 0
    report = json.loads(capsys.readouterr().out)
    for key in ("provenance", "points", "readings", "results",
                "ladder_at_zero", "projection_gaps", "known_disagreements"):
        assert key in report, f"--json report lacks top-level key {key!r}"
    prov = report["provenance"]
    for key in ("head_sha", "scoring_blob", "evidence_blob", "dirty",
                "python"):
        assert key in prov, f"provenance lacks {key!r}"
    assert prov["python"], f"provenance python is empty: {prov['python']!r}"
    # IN-04: a crashed or failed git child surfaces as None, so require real
    # values whenever git and a checkout are present (CI clones have both).
    if shutil.which("git") and (REPO_ROOT / ".git").exists():
        for key in ("head_sha", "scoring_blob", "evidence_blob"):
            assert prov[key], f"git is available but provenance {key} is {prov[key]!r}"
        assert isinstance(prov["dirty"], bool), (
            f"git is available but provenance dirty is {prov['dirty']!r}"
        )

    assert inst.main(["--markdown", "--points", "0"]) == 0
    markdown = capsys.readouterr().out
    assert any(line.startswith("| R5 |") for line in markdown.splitlines()), (
        "--markdown output has no table row starting '| R5 |'"
    )


def test_real_db_snapshot_is_read_only(inst, tmp_path, monkeypatch):
    """D-08: the snapshot path never modifies its source (tmp_path only).

    An unchanged sha256 alone cannot tell ``mode=ro`` from a read-write
    connection that only reads (WR-04), so this also spies on
    ``sqlite3.connect`` and requires every open of the source to be a
    ``mode=ro`` URI, and checks that a missing source is not created.
    """
    src = tmp_path / "source.db"
    conn = sqlite3.connect(str(src))
    try:
        conn.execute("CREATE TABLE endpoints (host TEXT, port INTEGER)")
        conn.execute("INSERT INTO endpoints VALUES ('h.p2b.example', 443)")
        conn.commit()
    finally:
        conn.close()
    before = hashlib.sha256(src.read_bytes()).hexdigest()

    real_connect = sqlite3.connect
    opened: List[Tuple[str, bool]] = []

    def _spy(database, *args, **kwargs):
        opened.append((str(database), bool(kwargs.get("uri", False))))
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _spy)
    snap = inst.snapshot_db(src, tmp_path / "snap")
    source_opens = [(db, uri) for db, uri in opened if src.name in db]
    assert source_opens, f"snapshot_db never opened {src.name}: {opened}"
    for db, uri in source_opens:
        assert uri and db.startswith("file:") and "mode=ro" in db, (
            f"snapshot_db opened its source without a mode=ro URI: "
            f"database={db!r}, uri={uri}"
        )

    missing = tmp_path / "absent.db"
    with pytest.raises(sqlite3.OperationalError):
        inst.snapshot_db(missing, tmp_path / "snap-missing")
    assert not missing.exists(), (
        "snapshot_db created its missing source: it was not opened mode=ro"
    )
    monkeypatch.setattr(sqlite3, "connect", real_connect)

    snap_conn = sqlite3.connect(str(snap))
    try:
        rows = snap_conn.execute("SELECT host, port FROM endpoints").fetchall()
    finally:
        snap_conn.close()
    assert rows == [("h.p2b.example", 443)], f"snapshot rows: {rows}"
    after = hashlib.sha256(src.read_bytes()).hexdigest()
    assert after == before, "snapshot_db modified its source database"


def test_real_db_snapshot_fails_fast_on_a_locked_source(inst, tmp_path,
                                                        monkeypatch):
    """WR-02: a write-locked source fails promptly and leaves no snapshot.

    ``Connection.backup`` retries SQLITE_BUSY forever, so without a bound a
    running app or scan holding the canonical DB would hang ``--real-db``
    with no message. The call runs in a daemon thread so an unbounded
    implementation fails this node instead of hanging the suite.
    """
    src = tmp_path / "locked.db"
    holder = sqlite3.connect(str(src), isolation_level=None)
    holder.execute("CREATE TABLE t (x INTEGER)")
    holder.execute("INSERT INTO t VALUES (1)")
    monkeypatch.setattr(inst, "SNAPSHOT_LOCK_TIMEOUT_S", 0.5, raising=False)
    monkeypatch.setattr(inst, "SNAPSHOT_DEADLINE_S", 2.0, raising=False)
    snap_dir = tmp_path / "snap"
    outcome: Dict[str, Any] = {}

    def _call():
        try:
            outcome["returned"] = inst.snapshot_db(src, snap_dir)
        except BaseException as exc:  # recorded and asserted on below
            outcome["raised"] = exc

    holder.execute("BEGIN EXCLUSIVE")
    holder.execute("INSERT INTO t VALUES (2)")
    try:
        started = time.monotonic()
        worker = threading.Thread(target=_call, daemon=True)
        worker.start()
        worker.join(15)
        elapsed = time.monotonic() - started
        assert not worker.is_alive(), (
            f"snapshot_db still blocked after {elapsed:.1f}s on a write-locked "
            "source; it must fail fast"
        )
    finally:
        holder.execute("ROLLBACK")
        holder.close()

    assert "returned" not in outcome, (
        f"snapshot_db returned {outcome.get('returned')!r} from a locked source"
    )
    exc = outcome.get("raised")
    assert isinstance(exc, inst.SnapshotError), (
        f"expected SnapshotError, got {exc!r}"
    )
    assert "locked" in str(exc), f"error does not say the source is locked: {exc}"
    leftovers = sorted(p.name for p in snap_dir.glob("*")) if snap_dir.exists() else []
    assert not leftovers, f"partial snapshot left behind: {leftovers}"

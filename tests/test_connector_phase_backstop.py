"""COVTRUTH-03 backstop: no connector may regress to a silent ``ran``.

Phase 235.3 plan 15. The connector set is RE-DERIVED from ``run_scan.py`` and
``quirk/scanner/*.py`` on every run (CLAUDE.md: a hand-maintained list of
sites is not a safeguard). The only written data is the set of dicts below,
and every one of them is checked in BOTH directions against the source so it
cannot drift:

* ``NON_CONNECTOR``   phases that are not connectors (with the reason)
* ``EXEMPT``          connector phases exempt from the ran-vs-skipped rule
                      (decision id + reason; anchored by a ``# 235.3 <id>``
                      comment above the closure def in run_scan.py)
* ``ENTRYPOINT_EXEMPT`` ``scan_*`` callees that legitimately take no sink
* ``SAMPLES``         one sample value per derived target-field name
* ``LEG_NOT_APPLICABLE`` phases a leg does not exercise (with the reason)

Fast tests (not slow) run the enumeration and the cross-checks. The slow tests
drive every derived connector into a no-answer state through three in-process
``run_scan.main()`` legs and assert that no exercised phase reads ``ran``.

This file is self-contained: stdlib, pytest, yaml, run_scan and quirk modules
that exist at b6896416 only (so it can be dropped onto the pre-fix commit and
fail on its status assertions rather than on an import).
"""
from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
import math
import os
import re
import socket
import sqlite3
import sys
import textwrap
from collections import namedtuple
from pathlib import Path

import pytest
import yaml

import run_scan

_REPO = Path(__file__).resolve().parent.parent
_RUN_SCAN_SRC = Path(run_scan.__file__).read_text(encoding="utf-8")
_SCANNER_DIR = _REPO / "quirk" / "scanner"

# --------------------------------------------------------------------------
# Written data (every dict is checked both ways against source)
# --------------------------------------------------------------------------

NON_CONNECTOR = {
    "tls_scanning": "core TLS sweep over the scan targets, not an optional connector",
    "ssh_scanning": "core SSH sweep over the scan targets, not an optional connector",
    "pqc_probe": "post-quantum hybrid probe of already-found TLS endpoints, no connector config",
    "ot_ics_supplemental": (
        "module-level _wrapped_phase site (outside main), does not use _recorder; "
        "derived from discovery, not a cfg.connectors target list"
    ),
}

EXEMPT = {
    "fuzz_scanning": (
        "P-03", "interactive-only --fuzz, not a cfg.connectors flag; exempt from the D-03 rule",
    ),
    "email_scanning": (
        "P-03", "probes speculative default ports on TLS-derived hosts; nothing configured to answer",
    ),
    "source_scanning": (
        "P-15", "scan_source_targets raises when every target fails, so _wrapped_phase records it failed",
    ),
}

ENTRYPOINT_EXEMPT = {
    "quirk.scanner.broker_scanner.scan_kafka_targets": (
        "broker is classified in its closure from the unreached-target advisories (P-03)"
    ),
    "quirk.scanner.broker_scanner.scan_rabbitmq_targets": (
        "broker is classified in its closure from the unreached-target advisories (P-03)"
    ),
    "quirk.scanner.broker_scanner.scan_redis_targets": (
        "broker is classified in its closure from the unreached-target advisories (P-03)"
    ),
    "quirk.scanner.codesign_scanner.scan_codesign_from_tls_endpoints": (
        "in-process TLS-EKU check, no network I/O, records no outcomes (P-03)"
    ),
    "quirk.scanner.aws_connector._scan_eks_encryption": (
        "the k8s closure records the EKS outcome itself (extra=True), the helper takes no sink"
    ),
}

# One sample value per derived target-field name. Callables take a closed
# loopback port and return the value. Never port 88 (macOS answers Kerberos).
SAMPLES = {
    "jwt_targets": lambda p: [f"http://127.0.0.1:{p}"],
    "container_targets": lambda p: [f"127.0.0.1:{p}/quirk/none:latest"],
    "scan.openapi_spec_path": lambda p: f"http://127.0.0.1:{p}/openapi.json",
    "aws_region": lambda p: "us-east-1",
    "azure_subscription_id": lambda p: "00000000-0000-0000-0000-000000000000",
    "azure_keyvault_urls": lambda p: [f"https://127.0.0.1:{p}"],
    "gcp_project_id": lambda p: "quirk-backstop",
    "k8s_provider": lambda p: "eks",
    "pg_targets": lambda p: [f"127.0.0.1:{p}"],
    "mysql_targets": lambda p: [f"127.0.0.1:{p}"],
    "dnssec_targets": lambda p: ["quirk-backstop.test"],
    "saml_targets": lambda p: [f"http://127.0.0.1:{p}/metadata.xml"],
    "kerberos_targets": lambda p: [f"127.0.0.1:{p}"],
    "smime_targets": lambda p: [f"ldap://127.0.0.1:{p}"],
    "adcs_targets": lambda p: [f"ldap://127.0.0.1:{p}"],
    "codesign_targets": lambda p: [f"ldap://127.0.0.1:{p}"],
    "vault_addr": lambda p: f"http://127.0.0.1:{p}",
    "vault_token": lambda p: "x",
    "broker_targets": lambda p: [f"127.0.0.1:{p}"],
}

# Non-target settings a leg needs so nothing can reach beyond loopback. These
# are configuration, not derived from the guards, so they are not both-way
# checked; every key is asserted to be a real ConnectorsCfg field instead.
UNREACHABLE_EXTRAS = {
    "pg_scanner_user": lambda p: "x",
    "pg_scanner_password": lambda p: "x",
    "mysql_scanner_user": lambda p: "x",
    "mysql_scanner_password": lambda p: "x",
    "aws_endpoint_url": lambda p: "http://127.0.0.1:1",
    "adcs_user": lambda p: "x",
    "adcs_password": lambda p: "x",
}
COMMON_EXTRAS = {
    "dnssec_resolver": lambda p: f"127.0.0.1:{p}",
}

# Phases that read cloud credentials; the credentials leg enables only these.
CLOUD_PHASES = frozenset({
    "aws_scanning", "s3_scanning", "azure_scanning", "blob_scanning",
    "gcp_scanning", "k8s_scanning",
})

LEG_NOT_APPLICABLE = {
    "refused": {},
    "unreachable": {},
    "credentials": {
        # filled in from CLOUD_PHASES complement at collection time; see
        # _credentials_not_applicable(). Each carries the same written reason.
    },
}
_CREDENTIALS_NA_REASON = "no cloud credential involved; the credentials leg enables cloud connectors only"

SKIP_REASONS_NOT_EXERCISED = frozenset({
    "disabled-by-config", "no-eligible-targets", "missing-extra", "missing-binary",
})
ACCEPTED_NOT_EXERCISED_WITHOUT_ENTRY = frozenset({"missing-extra", "missing-binary"})

Site = namedtuple("Site", "phase label closure lineno")
Guard = namedtuple("Guard", "enable targets args_flags")


# --------------------------------------------------------------------------
# Source-derived helpers (pure: take a source string, so snippets can drive them)
# --------------------------------------------------------------------------


def enumerate_wrapped_sites(src: str):
    """Every ``_wrapped_phase(...)`` call in the whole module (not only main())."""
    tree = ast.parse(src)
    sites = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_wrapped_phase"
            and len(node.args) >= 4
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[3], ast.Name)
        ):
            sites.append(Site(
                node.args[1].value,
                node.args[2].value if isinstance(node.args[2], ast.Constant) else None,
                node.args[3].id,
                node.lineno,
            ))
    return sorted(sites, key=lambda s: s.lineno)


def _closure_defs(tree):
    defs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, node)
    return defs


def classification_problems(sites, non_connector, exempt):
    problems = []
    phases = [s.phase for s in sites]
    for key in non_connector:
        if key not in phases:
            problems.append(f"NON_CONNECTOR key {key} is not an enumerated _wrapped_phase site")
    connectors = [p for p in phases if p not in non_connector]
    for key in exempt:
        if key not in connectors:
            problems.append(f"EXEMPT key {key} is not an enumerated connector phase")
    return problems


def _is_cfg_connectors(node):
    return (
        isinstance(node, ast.Attribute) and node.attr == "connectors"
        and isinstance(node.value, ast.Name) and node.value.id == "cfg"
    )


def _refs_in(node):
    """cfg.connectors.X attrs, getattr(cfg.connectors, "X"), and CLI args flags."""
    conn, flags = [], []
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and _is_cfg_connectors(n.value):
            conn.append(n.attr)
        elif (
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr"
            and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant)
        ):
            if _is_cfg_connectors(n.args[0]):
                conn.append(n.args[1].value)
            elif isinstance(n.args[0], ast.Name) and n.args[0].id == "args":
                flags.append(n.args[1].value)
    return conn, flags


def _scan_fields_in(fn):
    out = []
    for n in ast.walk(fn):
        if (
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr"
            and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant)
            and isinstance(n.args[0], ast.Call) and isinstance(n.args[0].func, ast.Name)
            and n.args[0].func.id == "getattr" and len(n.args[0].args) >= 2
            and isinstance(n.args[0].args[0], ast.Name) and n.args[0].args[0].id == "cfg"
            and isinstance(n.args[0].args[1], ast.Constant) and n.args[0].args[1].value == "scan"
        ):
            out.append("scan." + n.args[1].value)
    return out


def derive_guard(fn):
    """Enable flag, target fields and CLI flags from the closure's guard clauses."""
    enables, targets, flags = [], [], []
    for n in ast.walk(fn):
        if isinstance(n, ast.If):
            conn, fl = _refs_in(n.test)
            for attr in conn:
                (enables if attr.startswith("enable_") else targets).append(attr)
            flags.extend(fl)
    conn_all, _ = _refs_in(fn)
    targets.extend(a for a in conn_all if a.endswith("_targets"))
    targets.extend(_scan_fields_in(fn))
    return Guard(
        enables[0] if enables else None,
        sorted(set(targets)),
        sorted(set(flags)),
    )


def sample_problems(guards, samples):
    derived = set()
    for g in guards.values():
        derived.update(g.targets)
    problems = [f"add a sample for connectors.{f}" for f in sorted(derived - set(samples))]
    problems += [f"SAMPLES entry {f} is not a derived target field" for f in sorted(set(samples) - derived)]
    return problems


def anchor_problems(src, sites, exempt):
    lines = src.splitlines()
    by_phase = {s.phase: s for s in sites}
    tree = ast.parse(src)
    defs = _closure_defs(tree)
    problems = []
    for phase, (decision, _reason) in exempt.items():
        site = by_phase.get(phase)
        fn = defs.get(site.closure) if site else None
        if fn is None:
            problems.append(f"EXEMPT {phase}: closure def not found")
            continue
        window = lines[max(0, fn.lineno - 4): fn.lineno - 1]
        if not any(f"# 235.3 {decision}" in ln for ln in window):
            problems.append(
                f"EXEMPT {phase}: no '# 235.3 {decision}' comment within 3 lines above def {fn.name}"
            )
    return problems


def _import_map(nodes):
    """name -> ('func', module, orig) for ``from quirk.scanner.X import a as b`` and
    name -> ('module', module) for ``from quirk.scanner import X as Y``."""
    out = {}
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.ImportFrom) and n.module:
                for alias in n.names:
                    bound = alias.asname or alias.name
                    if n.module == "quirk.scanner":
                        out[bound] = ("module", f"quirk.scanner.{alias.name}")
                    elif n.module.startswith("quirk.scanner."):
                        out[bound] = ("func", n.module, alias.name)
    return out


_SCAN_RE = re.compile(r"^_?scan_")


def closure_callees(tree, fn):
    """[(module, funcname, ast.Call)] for quirk.scanner ``^_?scan_`` calls in *fn*.

    Resolved from the closure's OWN ImportFrom nodes merged over the module's
    top-level imports, so a closure-local import can never be missed.
    """
    imports = _import_map(tree.body)          # module level only
    imports.update(_import_map([fn]))         # closure-local wins
    found = []
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id in imports and imports[f.id][0] == "func":
            _, mod, orig = imports[f.id]
            if _SCAN_RE.match(orig):
                found.append((mod, orig, n))
        elif (
            isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
            and f.value.id in imports and imports[f.value.id][0] == "module"
            and _SCAN_RE.match(f.attr)
        ):
            found.append((imports[f.value.id][1], f.attr, n))
    return found


def _accepts_outcomes(mod, name):
    obj = getattr(importlib.import_module(mod), name)
    return "outcomes" in inspect.signature(obj).parameters


def callee_problems(src, connector_closures, entrypoint_exempt):
    """Signature + call-site check for every non-exempt connector closure."""
    tree = ast.parse(src)
    problems = []
    seen_exempt = set()
    for phase, fn in connector_closures.items():
        callees = closure_callees(tree, fn)
        if not callees:
            problems.append(f"{phase}: closure {fn.name} resolves zero scanner callees")
            continue
        for mod, name, call in callees:
            qual = f"{mod}.{name}"
            if qual in entrypoint_exempt:
                seen_exempt.add(qual)
                if _accepts_outcomes(mod, name):
                    problems.append(f"ENTRYPOINT_EXEMPT {qual} now accepts outcomes; drop the exemption")
                continue
            if not _accepts_outcomes(mod, name):
                problems.append(f"{phase}: {qual} does not accept an `outcomes` parameter")
            if not any(kw.arg == "outcomes" for kw in call.keywords):
                problems.append(f"{phase}: {fn.name} calls {qual} without outcomes=")
    for qual in sorted(set(entrypoint_exempt) - seen_exempt):
        problems.append(f"ENTRYPOINT_EXEMPT {qual} is not called by any non-exempt connector closure")
    return problems


def dead_sink_problems(run_scan_src, scanner_sources):
    """Every function declaring an ``outcomes`` parameter is called with it somewhere."""
    declared = {}
    sources = {"run_scan": run_scan_src, **scanner_sources}
    trees = {k: ast.parse(v) for k, v in sources.items()}
    for key, tree in trees.items():
        if key == "run_scan":
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = [a.arg for a in n.args.posonlyargs + n.args.args + n.args.kwonlyargs]
                if "outcomes" in params:
                    declared[(key, n.name)] = params.index("outcomes")
    called_with = set()
    for tree in trees.values():
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            fname = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if fname is None:
                continue
            for (_key, dname), idx in declared.items():
                if dname != fname:
                    continue
                if any(kw.arg == "outcomes" for kw in n.keywords) or len(n.args) > idx:
                    called_with.add(dname)
    return [
        f"{key}.{name} declares an `outcomes` parameter that no call site passes (dead sink)"
        for (key, name) in sorted(declared) if name not in called_with
    ]


def _scanner_sources():
    return {
        p.stem: p.read_text(encoding="utf-8")
        for p in sorted(_SCANNER_DIR.glob("*.py"))
    }


def derive_everything(src, non_connector=None, exempt=None):
    non_connector = NON_CONNECTOR if non_connector is None else non_connector
    exempt = EXEMPT if exempt is None else exempt
    sites = enumerate_wrapped_sites(src)
    tree = ast.parse(src)
    defs = _closure_defs(tree)
    connector_sites = [s for s in sites if s.phase not in non_connector]
    non_exempt = {s.phase: defs[s.closure] for s in connector_sites
                  if s.phase not in exempt and s.closure in defs}
    guards = {p: derive_guard(fn) for p, fn in non_exempt.items()}
    return sites, connector_sites, non_exempt, guards


# --------------------------------------------------------------------------
# Fast tests
# --------------------------------------------------------------------------


def test_enumeration_and_both_way_classification():
    sites, connector_sites, non_exempt, _guards = derive_everything(_RUN_SCAN_SRC)
    print(f"[backstop] {len(sites)} _wrapped_phase sites: {[s.phase for s in sites]}")
    print(f"[backstop] {len(non_exempt)} non-exempt connectors: {sorted(non_exempt)}")
    assert len(sites) >= 25, f"only {len(sites)} sites enumerated"
    problems = classification_problems(sites, NON_CONNECTOR, EXEMPT)
    for s in sites:
        if s.phase not in NON_CONNECTOR and s.phase not in EXEMPT:
            assert s.closure in _closure_defs(ast.parse(_RUN_SCAN_SRC)), (
                f"{s.phase}: closure {s.closure} has no def"
            )
    assert not problems, "\n".join(problems)
    assert len(non_exempt) == len(connector_sites) - len(EXEMPT)


def test_ot_ics_supplemental_is_a_module_level_non_connector():
    tree = ast.parse(_RUN_SCAN_SRC)
    top_calls = [
        n for node in tree.body for n in ast.walk(node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_wrapped_phase"
        and len(n.args) > 1 and isinstance(n.args[1], ast.Constant) and n.args[1].value == "ot_ics_supplemental"
    ]
    assert top_calls, "ot_ics_supplemental _wrapped_phase site not found"
    assert "ot_ics_supplemental" in NON_CONNECTOR


def test_exemption_anchors_present_above_closure_defs():
    sites = enumerate_wrapped_sites(_RUN_SCAN_SRC)
    problems = anchor_problems(_RUN_SCAN_SRC, sites, EXEMPT)
    assert not problems, "\n".join(problems)


def test_scanner_callees_accept_and_receive_outcomes():
    _sites, _cs, non_exempt, _g = derive_everything(_RUN_SCAN_SRC)
    problems = callee_problems(_RUN_SCAN_SRC, non_exempt, ENTRYPOINT_EXEMPT)
    assert not problems, "\n".join(problems)


def test_every_declared_outcomes_parameter_is_passed_somewhere():
    problems = dead_sink_problems(_RUN_SCAN_SRC, _scanner_sources())
    assert not problems, "\n".join(problems)


def test_samples_cover_every_derived_target_field_both_ways():
    _s, _c, _n, guards = derive_everything(_RUN_SCAN_SRC)
    print(f"[backstop] derived guards: {dict(guards)}")
    problems = sample_problems(guards, SAMPLES)
    assert not problems, "\n".join(problems)


def test_every_connector_has_an_enable_flag_or_cli_flag():
    _s, _c, _n, guards = derive_everything(_RUN_SCAN_SRC)
    missing = [p for p, g in guards.items() if g.enable is None and not g.args_flags]
    # openapi is gated only by scan.openapi_spec_path (a target field).
    missing = [p for p in missing if "scan.openapi_spec_path" not in guards[p].targets]
    assert not missing, f"no enable flag / CLI flag derivable for {missing}"


def test_config_extras_are_real_connector_fields():
    from quirk.config import ConnectorsCfg

    fields = set(ConnectorsCfg.__dataclass_fields__)
    for table in (UNREACHABLE_EXTRAS, COMMON_EXTRAS):
        for key in table:
            assert key in fields, f"{key} is not a ConnectorsCfg field"
    for _p, g in derive_everything(_RUN_SCAN_SRC)[3].items():
        for t in g.targets:
            if not t.startswith("scan."):
                assert t in fields, f"derived target {t} is not a ConnectorsCfg field"
        if g.enable:
            assert g.enable in fields, f"derived enable flag {g.enable} is not a field"


# -- synthetic-source tests: the checks catch drift ------------------------

_SYNTH_NEW_PHASE = textwrap.dedent('''
    def main():
        def _run_foo_phase():
            _recorder = run_stats["phase_records"]
            if not cfg.connectors.enable_foo:
                return _recorder.skip("disabled-by-config", "x")
            if not cfg.connectors.foo_targets:
                return _recorder.skip("no-eligible-targets", "y")
        foo_endpoints = _wrapped_phase(
            run_stats, "foo_scanning", "foo_scanner",
            _run_foo_phase, error_endpoints, logger,
        )
''')


def test_synthetic_new_phase_is_reported_with_its_sample():
    sites = enumerate_wrapped_sites(_SYNTH_NEW_PHASE)
    assert [s.phase for s in sites] == ["foo_scanning"]
    problems = classification_problems(sites, {"tls_scanning": "x"}, {})
    # "neither connector nor NON_CONNECTOR": a stale key is reported, and the
    # new phase is a connector by construction that the sample check surfaces.
    assert any("tls_scanning" in p for p in problems)
    _s, _c, _n, guards = derive_everything(_SYNTH_NEW_PHASE, non_connector={}, exempt={})
    assert guards["foo_scanning"].enable == "enable_foo"
    assert guards["foo_scanning"].targets == ["foo_targets"]
    assert "add a sample for connectors.foo_targets" in sample_problems(guards, SAMPLES)


_SYNTH_LOCAL_IMPORT_NO_OUTCOMES = textwrap.dedent('''
    def main():
        def _run_vault_phase():
            from quirk.scanner.vault_connector import scan_vault_targets
            return scan_vault_targets(vault_addr="x", token="y", logger=None)
        v = _wrapped_phase(run_stats, "vault_scanning", "vault_connector",
                           _run_vault_phase, error_endpoints, logger)
''')


def test_synthetic_local_import_without_outcomes_is_reported():
    _s, _c, non_exempt, _g = derive_everything(
        _SYNTH_LOCAL_IMPORT_NO_OUTCOMES, non_connector={}, exempt={},
    )
    problems = callee_problems(_SYNTH_LOCAL_IMPORT_NO_OUTCOMES, non_exempt, {})
    assert any("vault_scanning" in p and "without outcomes=" in p for p in problems), problems


_SYNTH_ZERO_CALLEES = textwrap.dedent('''
    def main():
        def _run_bar_phase():
            return []
        v = _wrapped_phase(run_stats, "bar_scanning", "bar", _run_bar_phase,
                           error_endpoints, logger)
''')


def test_synthetic_closure_without_scanner_callees_is_reported():
    _s, _c, non_exempt, _g = derive_everything(_SYNTH_ZERO_CALLEES, non_connector={}, exempt={})
    problems = callee_problems(_SYNTH_ZERO_CALLEES, non_exempt, {})
    assert any("bar_scanning" in p and "resolves zero scanner callees" in p for p in problems), problems


def test_synthetic_missing_anchor_is_reported():
    sites = enumerate_wrapped_sites(_SYNTH_NEW_PHASE)
    problems = anchor_problems(_SYNTH_NEW_PHASE, sites, {"foo_scanning": ("P-03", "r")})
    assert any("foo_scanning" in p and "235.3 P-03" in p for p in problems)


def test_synthetic_dead_sink_is_reported():
    problems = dead_sink_problems("x = 1\n", {"m": "def scan_x(a, outcomes=None):\n    return a\n"})
    assert any("scan_x" in p for p in problems)
    ok = dead_sink_problems(
        "scan_x(1, outcomes=o)\n", {"m": "def scan_x(a, outcomes=None):\n    return a\n"},
    )
    assert not ok


def test_synthetic_stale_entrypoint_exemption_is_reported():
    _s, _c, non_exempt, _g = derive_everything(_SYNTH_LOCAL_IMPORT_NO_OUTCOMES, non_connector={}, exempt={})
    problems = callee_problems(
        _SYNTH_LOCAL_IMPORT_NO_OUTCOMES, non_exempt,
        {"quirk.scanner.vault_connector.scan_vault_targets": "r",
         "quirk.scanner.nowhere.scan_nothing": "r"},
    )
    assert any("now accepts outcomes" in p for p in problems)
    assert any("scan_nothing" in p and "not called" in p for p in problems)


# --------------------------------------------------------------------------
# Socket guard (hermeticity) - used by the slow legs, self-tested here
# --------------------------------------------------------------------------

_LOOPBACK_PREFIXES = ("127.", "::1", "localhost")


def _is_loopback(addr) -> bool:
    host = addr[0] if isinstance(addr, tuple) and addr else addr
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    return isinstance(host, str) and (host.startswith(_LOOPBACK_PREFIXES) or host == "")


@contextlib.contextmanager
def socket_guard():
    """Reject (and record) any non-loopback connect attempt."""
    violations = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_sendto = socket.socket.sendto
    real_create = socket.create_connection

    def _check(addr):
        if not _is_loopback(addr):
            violations.append(repr(addr))
            raise OSError(f"backstop socket guard: non-loopback connect to {addr!r}")

    def connect(self, addr):
        _check(addr)
        return real_connect(self, addr)

    def connect_ex(self, addr):
        _check(addr)
        return real_connect_ex(self, addr)

    def sendto(self, data, *args):
        if args:
            _check(args[-1])
        return real_sendto(self, data, *args)

    def create_connection(address, *a, **kw):
        _check(address)
        return real_create(address, *a, **kw)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.socket.sendto = sendto
    socket.create_connection = create_connection
    try:
        yield violations
    finally:
        socket.socket.connect = real_connect
        socket.socket.connect_ex = real_connect_ex
        socket.socket.sendto = real_sendto
        socket.create_connection = real_create


@pytest.mark.slow
def test_socket_guard_rejects_non_loopback_connect():
    with socket_guard() as violations:
        s = socket.socket()
        try:
            with pytest.raises(OSError, match="non-loopback"):
                s.connect(("93.184.216.34", 80))
        finally:
            s.close()
        with pytest.raises(OSError, match="non-loopback"):
            socket.create_connection(("93.184.216.34", 80), timeout=1)
    assert len(violations) == 2


# --------------------------------------------------------------------------
# Slow legs: every derived connector, three no-answer states
# --------------------------------------------------------------------------

_LEGS = ("refused", "unreachable", "credentials")
_SCRUB_PREFIXES = ("AWS_", "AZURE_", "GOOGLE_", "GCLOUD_", "CLOUDSDK_")


def _closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _credentials_not_applicable(connector_phases):
    return {p: _CREDENTIALS_NA_REASON for p in connector_phases if p not in CLOUD_PHASES}


def _build_leg_config(tmp: Path, leg: str, guards, port: int) -> Path:
    with open(_REPO / "quirk" / "config_template.yaml", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    data["output"] = {"directory": str(tmp / "out"), "db_path": str(tmp / "quirk.db")}
    data["targets"] = {"include_ips": ["127.0.0.1"], "fqdns": [], "cidrs": [], "exclude_ips": []}
    data["scan"]["ports_tls"] = [port]
    data["scan"]["timeout_seconds"] = 1
    data["scan"]["timeouts"] = {
        k: 1 for k in (
            "default_seconds", "fingerprint_seconds", "tls_seconds", "ssh_seconds",
            "jwt_seconds", "container_seconds", "source_seconds", "dnssec_seconds",
            "saml_seconds", "kerberos_seconds", "vault_seconds", "db_connect_seconds",
            "broker_seconds", "email_seconds",
        )
    }
    data["security"] = {"allow_internal_targets": leg != "refused"}
    conn = data["connectors"]
    for key in list(conn):
        if key.startswith("enable_"):
            conn[key] = False
    for key, mk in COMMON_EXTRAS.items():
        conn[key] = mk(port)
    if leg == "unreachable":
        for key, mk in UNREACHABLE_EXTRAS.items():
            conn[key] = mk(port)
    active = [
        p for p in guards
        if leg != "credentials" or p in CLOUD_PHASES
    ]
    for phase in active:
        g = guards[phase]
        if g.enable:
            conn[g.enable] = True
        for field in g.targets:
            value = SAMPLES[field](port)
            if field.startswith("scan."):
                data["scan"][field.split(".", 1)[1]] = value
            else:
                conn[field] = value
    path = tmp / "config.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _extra_argv(guards, leg):
    flags = set()
    for phase, g in guards.items():
        if leg == "credentials" and phase not in CLOUD_PHASES:
            continue
        flags.update(g.args_flags)
    return ["--" + f.replace("_", "-") for f in sorted(flags)]


def _read_phase_rows(db: Path):
    con = sqlite3.connect(str(db))
    try:
        run = con.execute(
            "select scan_run_id from scan_phase_records order by id desc limit 1"
        ).fetchone()
        if run is None:
            return {}
        rows = con.execute(
            "select phase_name, status, reason, detail from scan_phase_records "
            "where scan_run_id = ?", (run[0],),
        ).fetchall()
    finally:
        con.close()
    return {r[0]: {"status": r[1], "reason": r[2], "detail": r[3]} for r in rows}


class _AzureCredentialBlocked(Exception):
    pass


def _run_leg(tmp_path_factory, leg):
    tmp = tmp_path_factory.mktemp(f"backstop_{leg}")
    _s, _c, non_exempt, guards = derive_everything(_RUN_SCAN_SRC)
    port = _closed_port()
    cfg_path = _build_leg_config(tmp, leg, guards, port)
    db = tmp / "quirk.db"
    repo_out = _REPO / "quirk-output"
    before = sorted(os.listdir(repo_out)) if repo_out.is_dir() else None

    mp = pytest.MonkeyPatch()
    try:
        for name in list(os.environ):
            if name.startswith(_SCRUB_PREFIXES):
                mp.delenv(name, raising=False)
        nowhere = os.path.join(os.sep, "nonexistent-quirk-235-3")
        mp.setenv("AWS_EC2_METADATA_DISABLED", "true")
        mp.setenv("AWS_CONFIG_FILE", os.path.join(nowhere, "aws-config"))
        mp.setenv("AWS_SHARED_CREDENTIALS_FILE", os.path.join(nowhere, "aws-credentials"))
        mp.setenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.join(nowhere, "gcp.json"))
        mp.delenv("VAULT_ADDR", raising=False)
        mp.delenv("VAULT_TOKEN", raising=False)
        if leg == "unreachable":
            mp.setenv("AWS_ACCESS_KEY_ID", "x")
            mp.setenv("AWS_SECRET_ACCESS_KEY", "x")
            mp.setenv("AWS_ENDPOINT_URL", "http://127.0.0.1:1")
        try:
            from azure.core.exceptions import ClientAuthenticationError as _Err
        except Exception:  # azure extra absent
            _Err = _AzureCredentialBlocked

        def _blocked(*a, **kw):
            raise _Err("backstop: DefaultAzureCredential blocked")

        for modname in ("quirk.scanner.azure_connector",):
            mod = importlib.import_module(modname)
            mp.setattr(mod, "DefaultAzureCredential", _blocked, raising=False)
        mp.chdir(tmp)
        mp.setattr(sys, "argv", [
            "run_scan.py", "--config", str(cfg_path), "--db-path", str(db),
            *_extra_argv(guards, leg),
        ])
        print(f"[backstop:{leg}] run_scan.__file__={run_scan.__file__}")
        import quirk
        print(f"[backstop:{leg}] quirk.__file__={quirk.__file__}")
        with socket_guard() as violations:
            try:
                run_scan.main()
            except SystemExit as exc:  # a clean exit code is fine; anything else is a finding
                if exc.code not in (None, 0):
                    raise
    finally:
        mp.undo()
    after = sorted(os.listdir(repo_out)) if repo_out.is_dir() else None
    assert before == after, "backstop leg wrote into the repo's ./quirk-output/"
    return {
        "rows": _read_phase_rows(db),
        "violations": list(violations),
        "connectors": sorted(non_exempt),
        "guards": guards,
    }


@pytest.fixture(scope="module")
def leg_results(tmp_path_factory):
    cache = {}

    def get(leg):
        if leg not in cache:
            cache[leg] = _run_leg(tmp_path_factory, leg)
        return cache[leg]

    return get


def _account(leg, result):
    """Return (offenders, exercised, not_exercised, problems)."""
    rows = result["rows"]
    connectors = result["connectors"]
    na = LEG_NOT_APPLICABLE[leg] or (
        _credentials_not_applicable(connectors) if leg == "credentials" else {}
    )
    offenders, exercised, not_exercised, problems = [], [], {}, []
    for phase in connectors:
        row = rows.get(phase)
        if row is None:
            problems.append(f"{phase}: no scan_phase_records row")
            continue
        is_not_exercised = (
            row["status"] == "skipped" and row["reason"] in SKIP_REASONS_NOT_EXERCISED
        )
        if phase in na and not is_not_exercised:
            problems.append(f"LEG_NOT_APPLICABLE[{leg}][{phase}] is stale: phase was exercised "
                            f"({row['status']}/{row['reason']})")
        if is_not_exercised:
            if row["reason"] in ACCEPTED_NOT_EXERCISED_WITHOUT_ENTRY:
                not_exercised[phase] = f"{row['reason']}: {row['detail']}"
            elif phase in na:
                not_exercised[phase] = na[phase]
            else:
                problems.append(
                    f"{phase}: not exercised in the {leg} leg ({row['reason']}: {row['detail']}) "
                    f"and has no LEG_NOT_APPLICABLE entry"
                )
            continue
        exercised.append(phase)
        if row["status"] == "ran":
            offenders.append(phase)
    for phase in na:
        if phase not in connectors:
            problems.append(f"LEG_NOT_APPLICABLE[{leg}] key {phase} is not a connector phase")
    return offenders, exercised, not_exercised, problems


@pytest.mark.slow
@pytest.mark.parametrize("leg", _LEGS)
def test_no_exercised_connector_reads_ran(leg_results, leg):
    result = leg_results(leg)
    offenders, exercised, not_exercised, problems = _account(leg, result)
    print(f"[backstop:{leg}] exercised ({len(exercised)}): {exercised}")
    print(f"[backstop:{leg}] not exercised ({len(not_exercised)}): {not_exercised}")
    assert not offenders, (
        f"{leg} leg: these connector phases read status 'ran' with nothing to answer: "
        f"{offenders}"
    )
    assert not problems, "\n".join(problems)
    if leg != "credentials":
        floor = math.ceil(0.7 * len(result["connectors"]))
        assert len(exercised) >= floor, (
            f"only {len(exercised)} of {len(result['connectors'])} connectors exercised "
            f"(floor {floor}); not exercised: {not_exercised}"
        )
    else:
        assert exercised, "credentials leg exercised no cloud connector"


@pytest.mark.slow
@pytest.mark.parametrize("leg", _LEGS)
def test_leg_made_no_non_loopback_connect(leg_results, leg):
    assert leg_results(leg)["violations"] == [], (
        f"{leg} leg attempted non-loopback connects: {leg_results(leg)['violations']}"
    )

"""The LDAP and database connectors read a target's host and port with the
trust gate's own parser (``quirk.util.target_trust.parse_target``), and never
dial a value that parser rejects, whether or not ``trusted_targets`` is set.
"""
from __future__ import annotations

import importlib
import inspect
from types import SimpleNamespace

import pytest

from quirk.scanner.target_outcome import OUTCOME_UNREACHABLE, TargetOutcomes
from quirk.util import target_trust as _tt
from tests.test_connector_target_shape import PARSER_AGREEMENT_CORPUS

_IDS = [f"c{i:02d}" for i in range(len(PARSER_AGREEMENT_CORPUS))]

LDAP_CONSUMERS = {
    "adcs": ("quirk.scanner.adcs_scanner", "scan_adcs_targets"),
    "smime": ("quirk.scanner.smime_scanner", "scan_smime_targets"),
    "codesign": ("quirk.scanner.codesign_scanner", "scan_codesign_from_ldap"),
}
DB_CONSUMERS = {"pg": 5432, "mysql": 3306}


def _run_ldap(name, targets, mp):
    module_name, function_name = LDAP_CONSUMERS[name]
    mod = importlib.import_module(module_name)
    calls = []

    class _Server:
        def __init__(self, *a, **k):
            calls.append((a, k))

    class _Connection:
        def __init__(self, *a, **k):
            raise RuntimeError("stop before any network I/O")

    fake = SimpleNamespace(
        Server=_Server, Connection=_Connection, ALL="ALL", SIMPLE="SIMPLE",
        ANONYMOUS="ANONYMOUS", NONE="NONE", SUBTREE="SUBTREE",
    )
    mp.setattr(mod, "ldap3", fake, raising=False)
    mp.setattr(mod, "LDAP3_AVAILABLE", True, raising=False)
    outcomes = TargetOutcomes(targets)
    getattr(mod, function_name)(
        list(targets), 1, search_base="DC=a,DC=example", outcomes=outcomes,
    )
    return [(a[0], k.get("port")) for a, k in calls], outcomes


def _run_db(kind, targets, mp):
    from quirk.scanner import db_connector as mod

    calls = []

    def connect(**kw):
        calls.append((kw["host"], kw["port"]))
        raise RuntimeError("stop before any network I/O")

    outcomes = TargetOutcomes(targets)
    if kind == "pg":
        mp.setattr(mod, "PSYCOPG2_AVAILABLE", True)
        mp.setattr(mod, "psycopg2", SimpleNamespace(connect=connect), raising=False)
        mod.scan_pg_targets(list(targets), outcomes=outcomes)
    else:
        mp.setattr(mod, "PYMYSQL_AVAILABLE", True)
        mp.setattr(mod, "pymysql", SimpleNamespace(connect=connect), raising=False)
        mod.scan_mysql_targets(list(targets), outcomes=outcomes)
    return calls, outcomes


def _run(consumer, targets, mp):
    if consumer in LDAP_CONSUMERS:
        return _run_ldap(consumer, targets, mp)
    return _run_db(consumer, targets, mp)


def _expect(consumer, value):
    if consumer in LDAP_CONSUMERS:
        return _tt.parse_target(value, _tt.SHAPE_LDAP)
    return _tt.parse_target(
        value, _tt.SHAPE_HOST_PORT, default_port=DB_CONSUMERS[consumer]
    )


@pytest.mark.parametrize("value", PARSER_AGREEMENT_CORPUS, ids=_IDS)
@pytest.mark.parametrize("consumer", [*LDAP_CONSUMERS, *DB_CONSUMERS])
def test_consumer_reads_target_with_shared_parser(monkeypatch, consumer, value):
    try:
        parsed = _expect(consumer, value)
    except _tt.AmbiguousTargetError:
        parsed = None
    calls, outcomes = _run(consumer, [value], monkeypatch)
    if parsed is None:
        assert calls == [], "a rejected value was dialled"
        recorded = outcomes.items.get(value)
        assert recorded, "no outcome recorded for the rejected value"
        kind, detail, _row = recorded[0]
        assert kind == OUTCOME_UNREACHABLE
        assert detail.startswith("not-probed")
    else:
        assert calls == [(parsed.host, parsed.port)]


@pytest.mark.parametrize("consumer", [*LDAP_CONSUMERS, *DB_CONSUMERS])
def test_one_rejected_value_does_not_stop_the_loop(monkeypatch, consumer):
    good = "db.example:5432" if consumer in DB_CONSUMERS else "db.example:389"
    calls, outcomes = _run(consumer, ["a.example,b.example", good], monkeypatch)
    parsed = _expect(consumer, good)
    assert calls == [(parsed.host, parsed.port)]
    assert outcomes.items["a.example,b.example"][0][1].startswith("not-probed")


def test_no_hand_host_parsing_left():
    from quirk.scanner import (
        adcs_scanner, codesign_scanner, db_connector, smime_scanner,
    )

    sources = [
        inspect.getsource(m._parse_target)
        for m in (adcs_scanner, smime_scanner, codesign_scanner)
    ]
    sources += [
        inspect.getsource(db_connector.scan_pg_targets),
        inspect.getsource(db_connector.scan_mysql_targets),
    ]
    for src in sources:
        assert 'partition(":")' not in src
        assert "parse_target(" in src or "_db_host_port(" in src

"""TRUST-02 (Phase 239, SC#2, D-08..D-11, D-23, D-25): LDAP connectors follow no referral.

ldap3 follows a referral to any host by default and re-binds there. The AD CS,
S/MIME and code-signing connectors must pass ``allowed_referral_hosts=[]`` to
every ``ldap3.Server`` and ``auto_referrals=False`` to every
``ldap3.Connection``. Three layers:

* an AST gate over the BYTES of every ``quirk/**/*.py`` (alias-aware, with
  floors so it cannot pass vacuously);
* kwargs tests against a fake ldap3;
* a loopback test that serves a referral and asserts the referred port saw
  nothing. A kwargs check alone is not a claim about the wire (CLAUDE.md
  GSD state.* verb integrity (e): a green function test is not a command test).
"""

import ast
import socket  # noqa: F401
import textwrap
import types
from pathlib import Path

import pytest

from tests import kerberos_wire_helpers as kwh

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REQ = {"Server": "allowed_referral_hosts", "Connection": "auto_referrals"}


def _hardened(kind, call):
    kw = next((k.value for k in call.keywords if k.arg == _REQ[kind]), None)
    if kind == "Server":
        return isinstance(kw, ast.List) and not kw.elts
    return isinstance(kw, ast.Constant) and kw.value is False


def _collect(source: bytes, filename: str):
    tree = ast.parse(source, filename)
    mod_alias, name_alias = set(), {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "ldap3":
                    mod_alias.add(a.asname or "ldap3")
        elif isinstance(n, ast.ImportFrom) and n.module and (
            n.module == "ldap3" or n.module.startswith("ldap3.")
        ):
            for a in n.names:
                if a.name in _REQ:
                    name_alias[a.asname or a.name] = a.name
    found = {"Server": 0, "Connection": 0}
    bad = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f, kind = n.func, None
        if isinstance(f, ast.Attribute) and f.attr in _REQ:
            base = f.value
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name) and base.id in mod_alias:
                kind = f.attr
        elif isinstance(f, ast.Name) and f.id in name_alias:
            kind = name_alias[f.id]
        if kind is None:
            continue
        found[kind] += 1
        if any(k.arg is None for k in n.keywords) or not _hardened(kind, n):
            bad.append((filename, n.lineno, kind))
    return found, bad


def _scan_tree(root: Path):
    found = {"Server": 0, "Connection": 0}
    bad = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        f, b = _collect(path.read_bytes(), str(path.relative_to(PROJECT_ROOT)))
        for k in found:
            found[k] += f[k]
        bad.extend(b)
    return found, bad


def test_ast_gate_every_ldap3_constructor_is_hardened():
    found, bad = _scan_tree(PROJECT_ROOT / "quirk")
    print("found", found)
    assert found["Server"] >= 4 and found["Connection"] >= 5, found
    assert not bad, "unhardened ldap3 constructors:\n" + "\n".join(
        f"{f}:{ln}:{kind}" for f, ln, kind in bad
    )


@pytest.mark.parametrize("src", [
    "from ldap3 import Server as S\nS(h)",
    "import ldap3\nldap3.Connection(s, **kw)",
    "import ldap3\nldap3.Server(h, allowed_referral_hosts=[('*', True)])",
    "import ldap3\nldap3.core.server.Server(h)",
    "from ldap3.core.connection import Connection\nConnection(s, auto_referrals=True)",
    "import ldap3 as x\nx.Connection(s)",
])
def test_ast_gate_self_test_flags_every_unhardened_shape(src):
    _, bad = _collect(textwrap.dedent(src).encode(), "synthetic.py")
    assert len(bad) == 1


@pytest.mark.parametrize("src", [
    "import ldap3 as x\nx.Server(h, allowed_referral_hosts=[])\n"
    "x.Connection(s, auto_referrals=False)",
    "from ldap3 import Server as S, Connection as C\n"
    "S(h, allowed_referral_hosts=[])\nC(s, auto_referrals=False)",
])
def test_ast_gate_self_test_accepts_hardened_aliases(src):
    found, bad = _collect(src.encode(), "synthetic.py")
    assert bad == [] and found == {"Server": 1, "Connection": 1}


def test_ast_gate_ignores_unrelated_server_names():
    found, bad = _collect(b"def Server(h): pass\nServer(h)\n", "synthetic.py")
    assert found == {"Server": 0, "Connection": 0} and bad == []


def test_ast_gate_parses_bom_file():
    _, bad = _collect(b"\xef\xbb\xbfimport ldap3\nldap3.Server(h)\n", "bom.py")
    assert len(bad) == 1


def _fake_ldap3(calls):
    class Server:
        def __init__(self, *a, **k):
            calls["server"].append(k)

    class _Std:
        def paged_search(self, **k):
            return iter(())

    class Connection:
        def __init__(self, *a, **k):
            calls["conn"].append(k)
            self.last_error = None
            self.result = {"result": 0}
            self.entries = []
            self.extend = types.SimpleNamespace(standard=_Std())

        def bind(self):
            return True

        def search(self, *a, **k):
            return True

        def unbind(self):
            pass

    return types.SimpleNamespace(
        Server=Server, Connection=Connection, ALL="ALL", SIMPLE="SIMPLE",
        ANONYMOUS="ANONYMOUS", NONE="NONE", SUBTREE="SUBTREE",
    )


def _install(monkeypatch, mod):
    calls = {"server": [], "conn": []}
    monkeypatch.setattr(mod, "ldap3", _fake_ldap3(calls), raising=False)
    monkeypatch.setattr(mod, "LDAP3_AVAILABLE", True, raising=False)
    return calls


def test_kwargs_adcs_follows_no_referrals(monkeypatch):
    from quirk.scanner import adcs_scanner as mod
    calls = _install(monkeypatch, mod)
    mod._bind_and_query("h", 389, 3, user="u", password="p")
    mod._bind_and_query("h", 389, 3)
    assert len(calls["server"]) == 2 and len(calls["conn"]) == 2
    assert all(k["allowed_referral_hosts"] == [] for k in calls["server"])
    assert all(k["auto_referrals"] is False for k in calls["conn"])


def test_kwargs_smime_follows_no_referrals(monkeypatch):
    from quirk.scanner import smime_scanner as mod
    calls = _install(monkeypatch, mod)
    mod._bind_and_search("h", 389, "DC=a", 3)
    assert len(calls["server"]) == 1 and len(calls["conn"]) == 1
    assert calls["server"][0]["allowed_referral_hosts"] == []
    assert calls["conn"][0]["auto_referrals"] is False


def test_kwargs_codesign_follows_no_referrals(monkeypatch):
    from quirk.scanner import codesign_scanner as mod
    calls = _install(monkeypatch, mod)
    mod._bind_and_search_codesign("h", 389, "DC=a", 3)
    assert len(calls["server"]) == 1 and len(calls["conn"]) == 1
    assert calls["server"][0]["allowed_referral_hosts"] == []
    assert calls["conn"][0]["auto_referrals"] is False


def _adcs(p1):
    from quirk.scanner import adcs_scanner
    return adcs_scanner.scan_adcs_targets(
        [f"127.0.0.1:{p1}"], timeout=3, search_base="DC=corp,DC=local",
        user="CORP\\svc", password="s3cret-pw")


def _smime(p1):
    from quirk.scanner import smime_scanner
    return smime_scanner.scan_smime_targets(
        [f"127.0.0.1:{p1}"], timeout=3, search_base="DC=corp,DC=local")


def _codesign(p1):
    from quirk.scanner import codesign_scanner
    return codesign_scanner.scan_codesign_from_ldap(
        [f"127.0.0.1:{p1}"], timeout=3, search_base="DC=corp,DC=local")


@pytest.mark.parametrize("scan", [_adcs, _smime, _codesign],
                         ids=["adcs", "smime", "codesign"])
def test_loopback_referral_not_followed(scan):
    pytest.importorskip("ldap3")
    from tests import ldap_referral_responder as lrr

    referred = lrr.Responder()
    primary = lrr.Responder(
        referral_uri=f"ldap://127.0.0.1:{referred.port}/CN=Elsewhere,DC=corp,DC=local"
    )
    try:
        _, exc, _ = kwh.run_with_watchdog(lambda: scan(primary.port), 20)
        drained = referred.drain_backlog()
        print(f"RESULT {scan.__name__}: referrals_sent={primary.referrals_sent} "
              f"referred.accepts={referred.accepts} drained={drained} "
              f"referred.binds={referred.binds}")
        assert exc is None
        assert primary.referrals_sent >= 1
        assert referred.accepts == 0
        assert drained == 0
        assert primary.errors == []
        if scan is _adcs:
            assert referred.binds == []
            assert b"s3cret-pw" not in bytes(referred.received_bytes)
    finally:
        primary.close()
        referred.close()

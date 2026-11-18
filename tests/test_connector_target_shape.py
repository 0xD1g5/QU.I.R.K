"""Phase 239 TRUST-01 / SC#1 / D-07: one target shape for every list-typed connector field.

The field set is enumerated at run time from ``ConnectorsCfg`` with this
file's own walk, never by name, so a field added later is covered without
editing this test.  For every field a scalar value must load as a
one-element list, and the hosts the trust gate reads must equal the hosts of
the elements the scanner iterates.
"""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import io
import itertools
import os
import re
import shutil
import socket
import subprocess
import sys
import textwrap
import threading
import tokenize
import typing
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from quirk.config import ConnectorsCfg, config_from_dict, load_config
from quirk.util import target_trust as _tt


def _is_list_type(t) -> bool:
    if isinstance(t, str):
        return re.match(r"(typing\.)?(List|list)\b", t) is not None
    return t is list or typing.get_origin(t) is list


LIST_FIELDS = [f.name for f in dataclasses.fields(ConnectorsCfg) if _is_list_type(f.type)]
BROKER_FIELDS = {"broker_targets", "broker_azure_namespaces", "broker_sqs_regions"}

_MAPPING = {"dc01.example": 1}
SHAPES = [
    ("scalar", "h.example:443", ["h.example:443"]),
    ("int", 123, [123]),
    ("mapping", _MAPPING, [_MAPPING]),
    ("bool", True, [True]),
    ("none", None, []),
    ("empty", "", []),
    ("tuple", ("a.example", "b.example"), ["a.example", "b.example"]),
    ("frozenset", frozenset({"a.example"}), ["a.example"]),
]


def _write_cfg(tmp_path, connectors):
    p = tmp_path / "cfg.yaml"
    doc = {
        "assessment": {
            "name": "target-shape-test",
            "data_classification": "internal",
            "report_owner": "tester",
            "timezone": "UTC",
        },
        "scan": {"concurrency": 50, "ports_tls": [443]},
        "output": {
            "directory": str(tmp_path / "out"),
            "db_path": str(tmp_path / "out" / "quirk.db"),
        },
        "connectors": connectors,
    }
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return str(p)


def _raw(connectors):
    return {
        "assessment": {
            "name": "t",
            "data_classification": "internal",
            "report_owner": "t",
            "timezone": "UTC",
        },
        "scan": {"timeout_seconds": 5, "concurrency": 200, "ports_tls": [443]},
        "targets": {"fqdns": [], "cidrs": [], "include_ips": [], "exclude_ips": []},
        "output": {"directory": "/tmp/quirk-test", "db_path": "/tmp/quirk-test.db"},
        "connectors": connectors,
    }


def test_list_field_enumeration_is_not_vacuous():
    assert len(LIST_FIELDS) >= 17, LIST_FIELDS
    assert {"jwt_targets", "azure_keyvault_urls", "kerberos_targets", "broker_targets"} <= set(LIST_FIELDS)
    assert "_user_set_fields" not in LIST_FIELDS
    assert "snmp_v3_credentials" not in LIST_FIELDS


@pytest.mark.parametrize("field", LIST_FIELDS)
def test_scalar_loads_as_one_element_and_gate_sees_scanner_set(tmp_path, monkeypatch, field):
    disposition = _tt.CONNECTOR_HOST_FIELD_DISPOSITION.get(field)
    assert disposition is not None, f"{field} has no gate disposition"
    given = CONSUMERS[field][1] if disposition == "check" else "h.example:443"
    cfg = load_config(_write_cfg(tmp_path, {field: given}))
    value = getattr(cfg.connectors, field)
    assert value == [given]
    gate = [h for f, h in _tt.connector_host_values(cfg.connectors) if f == field]
    if disposition == "check":
        expected = CONSUMERS[field][2]
        assert gate == [expected]
        assert {_norm(c) for c in CONSUMERS[field][0](value[0], monkeypatch)} == {expected}
    elif disposition == "check-registry":
        assert gate == [h for h in (_tt._registry_host(e) for e in value) if h]


@pytest.mark.parametrize("field", LIST_FIELDS)
@pytest.mark.parametrize("shape", SHAPES, ids=[s[0] for s in SHAPES])
def test_direct_construction_coerces_shapes(field, shape):
    _, given, expected = shape
    value = getattr(ConnectorsCfg(**{field: given}), field)
    assert value == expected
    if shape[0] == "mapping":
        assert value[0] is given


def test_list_value_is_kept_as_same_object():
    v = ["a.example"]
    assert ConnectorsCfg(jwt_targets=v).jwt_targets is v


@pytest.mark.parametrize("field", [f for f in LIST_FIELDS if f not in BROKER_FIELDS])
@pytest.mark.parametrize("shape", SHAPES, ids=[s[0] for s in SHAPES])
def test_config_from_dict_coerces_shapes(field, shape):
    _, given, expected = shape
    cfg = config_from_dict(_raw({field: given}))
    assert getattr(cfg.connectors, field) == expected


def test_kerberos_coercion_block_removed():
    import quirk.config as qc

    assert 'conn_raw["kerberos_targets"]' not in inspect.getsource(qc.config_from_dict)


def test_code_and_test_enumerations_agree():
    from quirk.config import _is_list_annotation

    code = [f.name for f in dataclasses.fields(ConnectorsCfg) if _is_list_annotation(f.type)]
    assert sorted(code) == sorted(LIST_FIELDS)


def test_enforce_reads_scalar_trusted_targets_whole():
    from quirk.util.target_trust import enforce_trusted_targets

    cfg = SimpleNamespace(
        security=SimpleNamespace(trusted_targets="10.0.0.0/8", allow_internal_targets=False),
        targets=SimpleNamespace(fqdns=["10.1.2.3"], cidrs=[], include_ips=[], exclude_ips=[]),
        connectors=SimpleNamespace(),
    )
    enforce_trusted_targets(cfg)


PARSER_AGREEMENT_CORPUS = (
    "a.example",
    "a.example:389",
    "a.example:0",
    "a.example:65536",
    "a.example:99999",
    "a.example:abc",
    "a.example:",
    "a.example: 389",
    "a.example:+389",
    "a.example:\u0663\u0668\u0669",
    "a.example%2eb.example",
    "a.example%40b.example",
    "%61.example",
    "a.example%00",
    "ldap://a.example%2fb.example",
    "https://a.example%2fb.example",
    "b\u00fccher.example",
    "b\u00fccher.example:389",
    "ldap://b\u00fccher.example",
    "https://b\u00fccher.example/x",
    "A.EXAMPLE",
    "A.Example:389",
    "ldap://A.EXAMPLE",
    "https://A.EXAMPLE/",
    "a.example.",
    "a.example.:389",
    "ldap://a.example.",
    "https://a.example./",
    "a.example;b.example",
    "ldap://a.example;b.example",
    "https://a.example;b.example/",
    "ldap://a.example:389",
    "ldap://a.example",
    "ldaps://a.example",
    "ldaps://a.example:636",
    "ldap://:389",
    "ldap:///a.example",
    "https://a.example/x",
    "https://a.example:8443/x",
    "http://a.example",
    "[2001:db8::1]",
    "[2001:db8::1]:389",
    "[2001:db8::1",
    "[a.example]",
    "[a.example]:389",
    "ldap://[a.example]",
    "2001:db8::1",
    "192.0.2.1",
    "192.0.2.1:389",
    "ldap://192.0.2.1",
    "ldap://[2001:db8::1]:389",
    "https://[2001:db8::1]:8443/x",
    "user@a.example",
    "ldap://user@a.example",
    "ldap://user:pw@a.example",
    "ldap://b.example:389@a.example",
    "ldap://a.example:389@b.example",
    "https://user:pw@a.example/",
    "https://b.example:443@a.example/",
    "https://a.example:443@b.example/",
    "b.example:389@a.example",
    "a.example@b.example",
    "postgres://a.example",
    "postgres://b.example@a.example:5432",
    "mysql://a.example",
    "mysql://user:pw@a.example:3306",
    "a.example:389:extra",
    "a.example:389:b.example",
    " a.example",
    "a.example ",
    "a.example b.example",
    "a.example\tb.example",
    "a.example\nb.example",
    "a.example#b.example",
    "a.example?b.example",
    "a.example/b.example",
    "/var/run/a.example",
    "ldap://a.example#b.example",
    "ldap://a.example?b.example",
    "https://a.example#b.example",
    "https://a.example?x=b.example",
    "https://a.example\\@b.example",
    "ldap://a.example\\@b.example",
    "a.example\\@b.example",
    "a.example,b.example",
    "a.example:389,b.example:389",
    "a.example,b.example:5432",
    "a.example://b.example/x",
    "a.example/x:1",
    "a.example:5000/x",
    "[2001:db8::1]:5000/x",
    "registry:a.example/x",
    "oci-archive:a.example/x",
    "a.example:5000:6000/x",
)

_PARSER_AGREEMENT_IDS = [f"c{i:02d}" for i in range(len(PARSER_AGREEMENT_CORPUS))]

OUT_OF_AGREEMENT_SCOPE: dict = {}

CHECK_FIELDS = [
    f.name
    for f in dataclasses.fields(ConnectorsCfg)
    if _tt.CONNECTOR_HOST_FIELD_DISPOSITION.get(f.name) == "check"
]


AGREEMENT_FIELDS = [
    f.name
    for f in dataclasses.fields(ConnectorsCfg)
    if _tt.CONNECTOR_HOST_FIELD_DISPOSITION.get(f.name, "").startswith("check")
    and _tt.CONNECTOR_HOST_FIELD_DISPOSITION.get(f.name) not in OUT_OF_AGREEMENT_SCOPE
]


_KUBECONFIG_COUNTER = itertools.count()


def _write_kubeconfig(server, tmp_path):
    n = next(_KUBECONFIG_COUNTER)
    path = tmp_path / f"kubeconfig-{n}.yaml"
    doc = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": "c", "cluster": {"server": server}}],
        "users": [{"name": "u", "user": {"token": "t"}}],
        "contexts": [{"name": "x", "context": {"cluster": "c", "user": "u"}}],
        "current-context": "x",
    }
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return str(path)


GATE_INPUT = {"k8s_kubeconfig": _write_kubeconfig}


def _gate_input(field, value, tmp_path):
    adapter = GATE_INPUT.get(field)
    return adapter(value, tmp_path) if adapter else value


def _norm(host) -> str:
    text = str(host)
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    try:
        return text.lower().encode("idna").decode("ascii") if not text.isascii() else text.lower()
    except UnicodeError:
        return text.lower()


def _real_ldap3():
    import ldap3

    return ldap3


def _ldap_consumer(module_name, function_name):
    def run(value, mp):
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
        try:
            getattr(mod, function_name)([value], 1, search_base="DC=a,DC=example")
        except Exception:  # noqa: BLE001 - the consumer may refuse the value
            pass
        hosts = set()
        real = _real_ldap3()
        for args, kwargs in calls:
            try:
                server = real.Server(*args, port=kwargs.get("port"))
            except Exception:  # noqa: BLE001 - ldap3 refused the host string
                continue
            hosts.add(server.host)
        return hosts

    return run


def _libpq_hosts(host) -> set:
    """Endpoints libpq contacts for a ``host`` connection parameter.

    Per the libpq connection-string documentation (the ``host`` parameter): a
    comma separates several hosts, and a value starting with ``/`` names the
    directory of a Unix-domain socket.
    """
    if host.startswith("/"):
        return {host}
    return set(host.split(","))


def _pymysql_hosts(host, kwargs) -> set:
    """Endpoints PyMySQL contacts: the ``host`` argument of ``Connection`` verbatim.

    A socket is the separate ``unix_socket`` argument, which the scanner never
    sets.
    """
    assert "unix_socket" not in kwargs
    return {host}


def _db_consumer(kind):
    def run(value, mp):
        from quirk.scanner import db_connector as mod

        recorded = []

        def connect(**kw):
            recorded.append(kw)
            raise RuntimeError("stop before any network I/O")

        if kind == "pg":
            mp.setattr(mod, "PSYCOPG2_AVAILABLE", True)
            mp.setattr(mod, "psycopg2", SimpleNamespace(connect=connect), raising=False)
            mod.scan_pg_targets([value])
            return set().union(*[_libpq_hosts(kw["host"]) for kw in recorded]) if recorded else set()
        mp.setattr(mod, "PYMYSQL_AVAILABLE", True)
        mp.setattr(mod, "pymysql", SimpleNamespace(connect=connect), raising=False)
        mod.scan_mysql_targets([value])
        return set().union(*[_pymysql_hosts(kw["host"], kw) for kw in recorded]) if recorded else set()

    return run


def _kerberos_consumer(value, mp):
    from quirk.scanner import kerberos_scanner as mod

    if mod._invalid_target_reason(value) is not None:
        return set()
    try:
        return {mod._wire_name(value)}
    except UnicodeError:
        return set()


def _dnssec_consumer(value, mp):
    from quirk.scanner import dnssec_scanner as mod

    asked = []

    def resolve(domain, timeout, resolver=None, diag=None):
        asked.append(domain)
        return []

    mp.setattr(mod, "DNSPYTHON_AVAILABLE", True)
    mp.setattr(mod, "_resolve_ns", resolve)
    mod.scan_dnssec_targets([value], timeout=1)
    return set(asked)


def _broker_consumer(value, mp):
    from quirk.config import _parse_host_port

    try:
        return {_parse_host_port(value, field_name="connectors.broker_targets")[0]}
    except ValueError:
        return set()


def _http_consumer(kind):
    def run(value, mp):
        import httpx

        from quirk.util import url_allowlist

        seen = []

        def handler(request):
            seen.append(request.url.host)
            return httpx.Response(404)

        class _MockClient(httpx.Client):
            def __init__(self, *a, **k):
                k["transport"] = httpx.MockTransport(handler)
                super().__init__(*a, **k)

        shim = SimpleNamespace(
            getaddrinfo=lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 0))],
            gaierror=socket.gaierror,
            AF_UNSPEC=socket.AF_UNSPEC,
        )
        mp.setattr(url_allowlist, "socket", shim)
        mp.setattr(httpx._api, "Client", _MockClient)
        if kind == "jwt":
            from quirk.scanner import jwt_scanner

            jwt_scanner.scan_jwt_targets([value], timeout=1, allow_internal=True)
        else:
            from quirk.scanner import saml_scanner

            saml_scanner._fetch_metadata(value, 1, allow_internal=True)
        return set(seen)

    return run


def _urllib3_consumer(value, mp):
    """hvac/azure-core (through requests, models.py prepare_url) and botocore
    (httpsession.py send -> connection_from_url) all hand the URL to urllib3's
    ``parse_url``."""
    from urllib3.exceptions import LocationParseError
    from urllib3.util import parse_url

    try:
        host = parse_url(value).host
    except LocationParseError:
        return set()
    return {host} if host else set()


def _k8s_consumer(path, mp):
    """The Kubernetes connector loads the kubeconfig with the kubernetes client
    and urllib3 opens the connection; the spy records the host urllib3 is asked
    to dial."""
    import urllib3.util.connection

    from quirk.scanner import k8s_connector

    for name in (
        "HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy",
        "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
    ):
        mp.delenv(name, raising=False)
    dialled = []

    def spy(address, *a, **k):
        dialled.append(address[0])
        raise OSError("stop before any network I/O")

    mp.setattr(urllib3.util.connection, "create_connection", spy)
    try:
        k8s_connector.scan_k8s_targets(
            provider="eks", cluster_name="agreement", kubeconfig=path
        )
    except Exception:  # noqa: BLE001 - the connector may refuse the value
        pass
    return set(dialled)


_SYFT_REGISTRY_SCHEMES = ("registry:", "oci-model-registry:")
_SYFT_DAEMON_SCHEMES = ("docker:", "podman:", "containerd:", "docker-daemon:", "image:")
_SYFT_LOCAL_SCHEMES = (
    "docker-archive:", "oci-archive:", "oci-dir:", "singularity:", "dir:", "file:", "oci:", "snap:",
)
SYFT_MODEL_VERSION = "1.57.2"


def _parse_syft_version(text):
    match = re.search(r"^Version:[ \t]*(\S.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _syft_exe_or_skip() -> str:
    exe = shutil.which("syft")
    if exe is None:
        if os.environ.get("CI"):
            pytest.fail("syft is not on PATH; the Linux Full Suite job must install the pinned syft")
        pytest.skip("syft is not on PATH; the cross-check needs the real binary")
    proc = subprocess.run(
        [exe, "version"], capture_output=True, text=True, timeout=30, close_fds=False,
    )
    found = _parse_syft_version(proc.stdout + proc.stderr)
    if found != SYFT_MODEL_VERSION:
        message = (
            f"syft on PATH is {found}, the model cites {SYFT_MODEL_VERSION}; "
            "install the pinned version or bump SYFT_MODEL_VERSION with the model"
        )
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(message)
    return exe


def test_parse_syft_version_reads_the_version_line():
    sample = "Application:   syft\nVersion:           1.57.2\nBuildDate:     2026-11-16\n"
    assert _parse_syft_version(sample) == "1.57.2"
    assert _parse_syft_version("Application: syft\nBuildDate: x\n") is None


def test_syft_model_daemon_and_local_schemes_are_refused():
    from quirk.util.subprocess_input import RC_INVALID_IMAGE_REF, validate_image_ref

    schemes = _SYFT_DAEMON_SCHEMES + _SYFT_LOCAL_SCHEMES
    assert len(schemes) >= 10, schemes
    for scheme in schemes:
        for variant in (scheme, scheme.upper(), scheme.title()):
            res = validate_image_ref(variant + "a.example/x")
            assert not res.ok and res.reason == RC_INVALID_IMAGE_REF, variant


def test_syft_model_registry_schemes_are_not_refused():
    from quirk.util.subprocess_input import validate_image_ref

    assert _SYFT_REGISTRY_SCHEMES
    for scheme in _SYFT_REGISTRY_SCHEMES:
        assert validate_image_ref(scheme + "a.example/x").ok, scheme


def test_production_prefixes_are_classified_by_the_syft_model():
    from quirk.util import subprocess_input

    model = set(_SYFT_DAEMON_SCHEMES + _SYFT_LOCAL_SCHEMES)
    production = set(subprocess_input._LOCAL_REF_PREFIXES)
    assert production <= model, sorted(production - model)
    assert production == model, sorted(model - production)


def test_syft_model_schemes_cover_syft_help():
    exe = _syft_exe_or_skip()
    proc = subprocess.run(
        [exe, "scan", "--help"],
        capture_output=True, text=True, timeout=60, close_fds=False,
    )
    text = proc.stdout + proc.stderr
    marker = "explicitly specify the scheme"
    assert marker in text, text[:500]
    section = text.split(marker, 1)[1].split("Flags:", 1)[0]
    found = set(re.findall(r"^\s*syft scan ([a-z][a-z0-9-]*):", section, re.MULTILINE))
    assert len(found) >= 8, found
    model = set(
        s.rstrip(":")
        for s in _SYFT_REGISTRY_SCHEMES + _SYFT_DAEMON_SCHEMES + _SYFT_LOCAL_SCHEMES
    )
    assert found <= model, sorted(found - model)


_GO_HOST_CHARS = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=<>\"-]*$")
_GO_REPOSITORY_CHARS = re.compile(r"^[a-z0-9_./-]{1,255}$")
_GO_TAG_CHARS = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_GO_DIGEST_HEX = {"sha256": 64, "sha384": 96, "sha512": 128}


def _syft_authority_hostname(name):
    """Hostname of the URI authority ``name``, or None when it is not one."""
    if name.startswith("["):
        match = re.match(r"^\[([0-9A-Fa-f:.]+)\](?::[0-9]*)?$", name)
        return match.group(1) if match else None
    host = name
    if ":" in name:
        host, port = name.rsplit(":", 1)
        if not port.isascii() or not (port == "" or port.isdigit()):
            return None
    return host if _GO_HOST_CHARS.match(host) else None


def _syft_split_repository(name):
    """Split ``name`` into (registry, repository); None when it does not parse."""
    if not name:
        return None
    registry, repository = "", name
    parts = name.split("/", 1)
    if len(parts) == 2 and (parts[0] == "localhost" or "." in parts[0] or ":" in parts[0]):
        registry, repository = parts
    if not _GO_REPOSITORY_CHARS.match(repository):
        return None
    if registry and _syft_authority_hostname(registry) is None:
        return None
    return registry, repository


def _syft_split_tag(name):
    """Split ``name`` into (base, tag) as the upstream tag parser does; None on failure."""
    base, tag = name, ""
    pieces = name.split(":")
    if len(pieces) > 1 and "/" not in pieces[-1]:
        base, tag = ":".join(pieces[:-1]), pieces[-1]
        if tag == "":
            return None
    if tag and not _GO_TAG_CHARS.match(tag):
        return None
    return base, tag


def _syft_valid_digest(text):
    algorithm, _, encoded = text.partition(":")
    width = _GO_DIGEST_HEX.get(algorithm)
    return bool(width) and len(encoded) == width and all(c in "0123456789abcdef" for c in encoded)


def _syft_registry_hosts(ref) -> set:
    """Registry hosts syft contacts for the argv reference ``ref``.

    Written from the reference parser syft 1.57.2 (SYFT_MODEL_VERSION) uses for
    registry sources: stereoscope v0.4.2 calls ``name.ParseReference`` from
    github.com/google/go-containerregistry, version v0.22.1 (pinned by syft's
    go.mod at tag v1.57.2), package ``pkg/name``:
    https://github.com/google/go-containerregistry/blob/v0.22.1/pkg/name/repository.go
    (``NewRepository``), registry.go (``checkRegistry``, ``NewRegistry``),
    tag.go (``NewTag``), digest.go (``NewDigest``) and ref.go
    (``ParseReference``).  The rules, as that source states them:

    * ``ParseReference`` refuses a reference starting with ``http://`` or
      ``https://``; it tries ``NewTag`` first and ``NewDigest`` second.
    * ``NewTag`` splits on ``:``; the last piece is the tag when it contains
      no ``/``; the tag uses letters, digits and ``_-.`` (1-128).
    * ``NewDigest`` needs exactly one ``@``; the part before it goes through
      ``NewTag`` and then ``NewRepository``.
    * ``NewRepository`` splits once on ``/``; the first piece is the registry
      when it is ``localhost`` or contains ``.`` or ``:``, otherwise the whole
      name is the repository and the registry is the default.  The repository
      uses lowercase letters, digits and ``_-./`` (1-255).
    * ``checkRegistry`` accepts the registry when ``url.Parse`` of the name
      behind two slashes gives a host equal to the name: a URI authority with
      an optional, possibly empty, numeric port, a bracketed IPv6 form, and no
      case rule; the toolchain's URL parser behind it rejects a colon in an
      unbracketed host (observed with syft 1.57.2).
    * ``NewRegistry`` rewrites ``docker.io`` to ``index.docker.io``.

    Scheme handling is observed syft behaviour: ``scan --help`` lists the
    explicit schemes (matched in any letter case here); local-file and daemon
    sources contact no registry; a head of ``http:`` or ``https:`` is not
    resolved as a registry.  A reference with no explicit registry goes to the
    default registry, and syft also probes the snap store; the cross-check
    lists both separately.
    """
    lowered = ref.lower()
    rest = ref
    for scheme in _SYFT_REGISTRY_SCHEMES + _SYFT_DAEMON_SCHEMES + _SYFT_LOCAL_SCHEMES:
        if lowered.startswith(scheme):
            if scheme in _SYFT_LOCAL_SCHEMES:
                return set()
            rest = ref[len(scheme):]
            break
    if rest.startswith(("http://", "https://")) or rest.split("/", 1)[0].lower() in ("http:", "https:"):
        return set()
    split = None
    tagged = _syft_split_tag(rest)
    if tagged is not None:
        split = _syft_split_repository(tagged[0])
    if split is None:
        pieces = rest.split("@")
        if len(pieces) == 2 and _syft_valid_digest(pieces[1]):
            base = pieces[0]
            retagged = _syft_split_tag(base)
            if retagged is not None:
                base = retagged[0]
            split = _syft_split_repository(base)
    if split is None or not split[0]:
        return set()
    host = _syft_authority_hostname(split[0])
    if not host:
        return set()
    host = host.lower()
    return {"index.docker.io" if host == "docker.io" else host}


def _container_consumer(value, mp):
    from quirk.scanner import container_scanner as mod

    real_which = shutil.which
    mp.setattr(
        mod.shutil, "which",
        lambda name, *a, **k: "/nonexistent/syft" if name == "syft" else real_which(name, *a, **k),
    )
    recorded = []

    def fake(argv, *a, **k):
        recorded.append(list(argv))
        raise subprocess.TimeoutExpired(argv, 1)

    mp.setattr(mod.subprocess, "run", fake)
    mod.scan_container_targets([value], timeout=1)
    hosts = set()
    for argv in recorded:
        hosts |= _syft_registry_hosts(argv[-1])
    return hosts


CONSUMERS = {
    "adcs_targets": (_ldap_consumer("quirk.scanner.adcs_scanner", "scan_adcs_targets"), "ldap://dc.example:389", "dc.example"),
    "smime_targets": (_ldap_consumer("quirk.scanner.smime_scanner", "scan_smime_targets"), "ldap://dc.example:389", "dc.example"),
    "codesign_targets": (_ldap_consumer("quirk.scanner.codesign_scanner", "scan_codesign_from_ldap"), "ldap://dc.example:389", "dc.example"),
    "pg_targets": (_db_consumer("pg"), "db.example:5432", "db.example"),
    "mysql_targets": (_db_consumer("mysql"), "db.example:3306", "db.example"),
    "kerberos_targets": (_kerberos_consumer, "kdc.example", "kdc.example"),
    "dnssec_targets": (_dnssec_consumer, "zone.example", "zone.example"),
    "broker_targets": (_broker_consumer, "mq.example:9093", "mq.example"),
    "jwt_targets": (_http_consumer("jwt"), "https://svc.example/x", "svc.example"),
    "saml_targets": (_http_consumer("saml"), "https://svc.example/x", "svc.example"),
    "vault_addr": (_urllib3_consumer, "https://svc.example/x", "svc.example"),
    "aws_endpoint_url": (_urllib3_consumer, "https://svc.example/x", "svc.example"),
    "azure_keyvault_urls": (_urllib3_consumer, "https://svc.example/x", "svc.example"),
    "k8s_kubeconfig": (_k8s_consumer, "https://api.example:6443", "api.example"),
    "container_targets": (_container_consumer, "reg.example/app:1", "reg.example"),
}


def test_every_check_field_has_a_consumer():
    assert len(CHECK_FIELDS) >= 13, CHECK_FIELDS
    missing = sorted(set(AGREEMENT_FIELDS) - set(CONSUMERS))
    extra = sorted(set(CONSUMERS) - set(AGREEMENT_FIELDS))
    assert not missing, f"check field(s) with no registered consumer: {missing}"
    assert not extra, f"consumer registered for non-check field(s): {extra}"
    covered = {_tt.CONNECTOR_HOST_FIELD_DISPOSITION[f] for f in CONSUMERS}
    kinds = {
        d for d in _tt.CONNECTOR_HOST_FIELD_DISPOSITION.values()
        if d.startswith("check") and d != "check"
    }
    assert kinds <= covered | set(OUT_OF_AGREEMENT_SCOPE), kinds


def test_out_of_agreement_scope_entries_are_justified():
    ledger = (Path(__file__).resolve().parents[1] / ".planning" / "LEDGER.md").read_text(
        encoding="utf-8"
    )
    used = set(_tt.CONNECTOR_HOST_FIELD_DISPOSITION.values())
    for kind, reason in OUT_OF_AGREEMENT_SCOPE.items():
        assert kind in used, kind
        assert len(reason) >= 40, kind
        ids = re.findall(r"LEDGER (\d{6}-[a-z0-9-]+)", reason)
        assert ids, f"{kind}: reason names no LEDGER row"
        for row_id in ids:
            assert f"| {row_id} |" in ledger, f"{kind}: LEDGER row {row_id} not found"


@pytest.mark.parametrize("field", AGREEMENT_FIELDS)
def test_benign_targets_keep_their_host(monkeypatch, tmp_path, field):
    consumer, benign, expected = CONSUMERS[field]
    gate_input = _gate_input(field, benign, tmp_path)
    pairs = _tt.connector_host_values({field: [gate_input]})
    assert [h for _f, h in pairs] == [expected]
    assert _tt.is_target_trusted(expected, [expected]).ok
    contacted = {_norm(c) for c in consumer(gate_input, monkeypatch)}
    assert contacted == {expected}
    if field in ("jwt_targets", "saml_targets", "k8s_kubeconfig", "container_targets"):
        assert contacted


@pytest.mark.parametrize("value", PARSER_AGREEMENT_CORPUS, ids=_PARSER_AGREEMENT_IDS)
@pytest.mark.parametrize("field", AGREEMENT_FIELDS)
def test_gate_and_consumer_agree_on_host(monkeypatch, tmp_path, field, value):
    gate_input = _gate_input(field, value, tmp_path)
    pairs = _tt.connector_host_values({field: [gate_input]})
    gate_hosts = [h for _f, h in pairs if isinstance(h, str)]
    allow = gate_hosts or ["192.0.2.254"]
    gate_refuses = any(not _tt.is_target_trusted(h, allow).ok for _f, h in pairs)
    contacted = CONSUMERS[field][0](gate_input, monkeypatch)
    assert gate_refuses or {_norm(c) for c in contacted} <= {_norm(h) for h in gate_hosts}, (
        f"{field}: the gate and the consumer read the value differently "
        f"(corpus id c{PARSER_AGREEMENT_CORPUS.index(value):02d})"
    )


DEFAULT_REGISTRY_HOSTS = {"docker.io", "index.docker.io", "registry-1.docker.io", "auth.docker.io"}
SYFT_FIXED_PROBE_HOSTS = {"api.snapcraft.io"}


_SYFT_RULE_PROBES = (
    "regs.example:/app",
    "regs:5000/app",
    "UP.Example/app",
    "regs:/app",
    "reg.example:5000/app:1",
)


def _syft_observation_problems(ref, predicted, observed) -> list:
    allowed = set(predicted) | SYFT_FIXED_PROBE_HOSTS
    if not predicted:
        allowed |= DEFAULT_REGISTRY_HOSTS
    problems = []
    extra = sorted(set(observed) - allowed)
    if extra:
        problems.append(
            f"{ref!r}: syft contacted {extra}, the model allowed {sorted(allowed)}"
        )
    if predicted and not (set(predicted) & set(observed)):
        problems.append(
            f"{ref!r}: the model predicts {sorted(predicted)}, syft contacted {sorted(observed)}"
        )
    return problems


def _loopback_registry(ref) -> bool:
    first = ref.split("/", 1)[0].rsplit(":", 1)[0].lower() if "/" in ref else ""
    return first == "localhost" or first.startswith("127.") or first in ("[::1]", "::1")


def _observe_syft(exe, ref, base_env, work):
    """Run syft over ``ref`` behind a private recording proxy; return the CONNECT authorities."""
    seen = []
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(64)
    listener.settimeout(0.2)
    stop = threading.Event()

    def serve():
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except (socket.timeout, OSError):
                continue
            try:
                conn.settimeout(2)
                parts = conn.makefile("rb").readline().decode("latin-1", "replace").split()
                if len(parts) >= 2 and parts[0] == "CONNECT":
                    seen.append(parts[1])
            except OSError:
                pass
            finally:
                conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    proxy = f"http://127.0.0.1:{listener.getsockname()[1]}"
    absent = work / "absent.sock"
    env = dict(base_env)
    env.update(
        HTTPS_PROXY=proxy, HTTP_PROXY=proxy, https_proxy=proxy, http_proxy=proxy,
        HOME=str(work / "home"),
        XDG_CONFIG_HOME=str(work / "xdg-config"),
        XDG_CACHE_HOME=str(work / "xdg-cache"),
        SYFT_CHECK_FOR_APP_UPDATE="false",
        DOCKER_HOST=f"unix://{absent}",
        CONTAINER_HOST=f"unix://{absent}",
        CONTAINERD_ADDRESS=str(absent),
    )
    for sub in ("home", "xdg-config", "xdg-cache"):
        (work / sub).mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([exe, "-o", "json", "--", ref], env=env, capture_output=True, timeout=60,
                       close_fds=False)
    except subprocess.TimeoutExpired:
        pass
    finally:
        stop.set()
        thread.join(timeout=2)
        listener.close()
    return list(seen)


@pytest.mark.slow
def test_syft_registry_model_matches_real_syft(tmp_path):
    exe = _syft_exe_or_skip()
    from concurrent.futures import ThreadPoolExecutor

    from quirk.util.subprocess_input import validate_image_ref

    base_env = dict(os.environ)
    for name in ("NO_PROXY", "no_proxy", "ALL_PROXY", "all_proxy"):
        base_env.pop(name, None)
    version = subprocess.run(
        [exe, "version"], capture_output=True, text=True, timeout=30, close_fds=False,
    ).stdout
    refs = [
        r for r in PARSER_AGREEMENT_CORPUS
        if isinstance(r, str) and validate_image_ref(r).ok and not _loopback_registry(r)
    ]
    assert len(refs) >= 5, refs
    for probe in _SYFT_RULE_PROBES:
        assert validate_image_ref(probe).ok, probe
        refs.append(probe)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda item: _observe_syft(exe, item[1], base_env, tmp_path / f"w{item[0]}"),
                enumerate(refs),
            )
        )
    total = 0
    for ref, authorities in zip(refs, results):
        observed = {urllib.parse.urlsplit("//" + a).hostname or "" for a in authorities}
        total += len(authorities)
        problems = _syft_observation_problems(ref, _syft_registry_hosts(ref), observed)
        assert not problems, f"{problems} (syft version: {version.strip()!r})"
    assert total >= 1, "the proxy recorded no CONNECT: the cross-check is vacuous"


def _code_names_recursive(code) -> set:
    names = set(code.co_names)
    for const in code.co_consts:
        if inspect.iscode(const):
            names |= _code_names_recursive(const)
    return names


def _source_name_tokens(src) -> set:
    reader = io.StringIO(textwrap.dedent(src)).readline
    return {t.string for t in tokenize.generate_tokens(reader) if t.type == tokenize.NAME}


def _forbidden_gate_names(names) -> set:
    exact = {"_tt", "target_trust", "parse_target", "_registry_host"}
    return {n for n in names if n in exact or n.startswith("SHAPE_")}


def test_syft_observation_check_allows_default_registry_only_for_default_refs():
    problems = _syft_observation_problems
    assert problems("a.example/x", {"a.example"}, {"a.example", "registry-1.docker.io"})
    assert not problems("nginx:1", set(), {"registry-1.docker.io", "auth.docker.io"})
    assert not problems("a.example/x", {"a.example"}, {"a.example", "api.snapcraft.io"})
    assert problems("a.example/x", {"a.example"}, set())
    assert problems("nginx:1", set(), {"b.example"})


def test_syft_model_is_independent_of_the_gate():
    roots = (
        "_syft_registry_hosts",
        "_syft_observation_problems",
        "_observe_syft",
        "test_syft_registry_model_matches_real_syft",
    )
    module_globals = globals()
    missing = [r for r in roots if r not in module_globals]
    assert not missing, missing
    seen = {}
    queue = [module_globals[r] for r in roots]
    while queue:
        fn = queue.pop()
        if fn.__name__ in seen:
            continue
        seen[fn.__name__] = fn
        for name in _code_names_recursive(fn.__code__):
            target = module_globals.get(name)
            if inspect.isfunction(target) and target.__module__ == __name__:
                queue.append(target)
    assert len(seen) >= 3, sorted(seen)
    for name, fn in sorted(seen.items()):
        assert not _forbidden_gate_names(_code_names_recursive(fn.__code__)), name
        assert not _forbidden_gate_names(_source_name_tokens(inspect.getsource(fn))), name
    assert isinstance(module_globals.get("SYFT_MODEL_VERSION"), str)
    doc = _syft_registry_hosts.__doc__ or ""
    assert SYFT_MODEL_VERSION in doc
    assert "github.com/" in doc and "/v" in doc


@pytest.mark.parametrize(
    "body",
    ["return [_tt for _x in range(1)]", "return lambda: _tt"],
    ids=["comprehension", "lambda"],
)
def test_independence_walk_sees_nested_code_objects(body):
    ns: dict = {}
    exec("def f():\n    " + body, ns)
    code = ns["f"].__code__
    assert "_tt" in _code_names_recursive(code)
    if body.startswith("return lambda") or sys.version_info < (3, 12):
        assert "_tt" not in code.co_names


def test_independence_name_match_is_exact():
    assert _forbidden_gate_names(
        {"_syft_registry_hosts", "SHAPE", "NOT_SHAPE_X", "registry_host"}
    ) == set()
    everything = {"_registry_host", "SHAPE_HOST_PORT", "_tt", "target_trust", "parse_target"}
    assert _forbidden_gate_names(everything) == everything
    own = "def _syft_registry_hosts(ref):\n    return _syft_registry_hosts\n"
    assert _forbidden_gate_names(_source_name_tokens(own)) == set()


def test_ci_installs_the_syft_version_the_model_cites():
    workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "python-ci.yml"
    steps = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]["linux-full-suite"]["steps"]
    names = [st.get("name") for st in steps]
    assert "Run full test suite" in names
    run_at = names.index("Run full test suite")
    tarball = f"syft_{SYFT_MODEL_VERSION}_linux_amd64.tar.gz"
    hits = [
        i for i, st in enumerate(steps)
        if tarball in st.get("run", "") and "sha256sum -c" in st.get("run", "")
    ]
    assert hits and hits[0] < run_at, hits
    assert re.search(r"\b[0-9a-f]{64}\b", steps[hits[0]]["run"])

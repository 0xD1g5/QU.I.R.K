"""Tests for HashiCorp Vault connector — transit keys, PKI mounts, auth methods (VAULT-01/02/03).

Tests mock `hvac` to avoid network/Vault connections.
Scanner module: quirk/scanner/vault_connector.py (Plan 02 creates this file).

Decisions encoded in these tests (from .planning/phases/30-hashicorp-vault-connector/30-CONTEXT.md):
- D-01: Transit keys are classification-only (no severity unless exportable)
- D-02: Exportable transit keys → MEDIUM severity (does NOT increment dar_vault_weak_count)
- D-03: PKI scanner emits root + intermediate CA per mount; RSA<4096 or SHA-1 → HIGH
- D-04: Intermediate-chain failure swallowed silently (root-only result returned)
- D-05: Token auth method always HIGH unconditional (Vault cannot disable token auth)
- D-06: AUTH_RISK_MAP — token/ldap=HIGH, userpass=MEDIUM, approle/k8s/oidc=no finding
- D-09: vault_tls_verify config field default True
- D-17: session_start parameter mandatory (ISSUE-3 structural requirement)
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_pem_rsa(key_size: int, hash_alg: str = "SHA256") -> str:
    """Generate a real (ephemeral) self-signed PEM cert for PKI tests.

    Avoids embedding fixed PEMs (which would expire). Uses cryptography (already core dep).
    `hash_alg` accepts "SHA256" or "SHA1" to exercise the SHA-1 finding path.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "quirk-test-ca")])
    hash_cls = hashes.SHA1() if hash_alg.upper() == "SHA1" else hashes.SHA256()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
        .sign(key, hash_cls)
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def _build_mock_client(
    *,
    is_auth: bool = True,
    transit_keys: dict | None = None,  # {key_name: {"type": ..., "exportable": ..., "latest_version": ...}}
    pki_mounts: dict | None = None,    # {mount_path: {"root_pem": ..., "chain_pem": ... or Exception}}
    auth_methods: dict | None = None,  # {path: {"type": ...}}
):
    """Construct a MagicMock hvac.Client preloaded with the desired API responses.

    transit_keys is the dict form: {"my-rsa-key": {"type": "rsa-2048", "exportable": False, "latest_version": 1}}
    pki_mounts is: {"pki/": {"root_pem": "<PEM>", "chain_pem": "<PEM>" or RaisesException}}
    auth_methods is: {"token/": {"type": "token"}, "userpass/": {"type": "userpass"}}
    """
    client = MagicMock()
    client.url = "http://127.0.0.1:8200"
    client.is_authenticated.return_value = is_auth

    # Transit setup
    transit_keys = transit_keys if transit_keys is not None else {}
    client.secrets.transit.list_keys.return_value = {
        "data": {"keys": {name: {} for name in transit_keys}}
    }

    def _read_key(name, mount_point="transit"):
        return {"data": dict(transit_keys[name])}

    client.secrets.transit.read_key.side_effect = _read_key

    # PKI setup
    pki_mounts = pki_mounts if pki_mounts is not None else {}
    mounts_dict = {path: {"type": "pki"} for path in pki_mounts}
    client.sys.list_mounted_secrets_engines.return_value = {"data": mounts_dict}

    def _read_ca(mount_point):
        norm = mount_point.rstrip("/") + "/"
        return pki_mounts[norm]["root_pem"]

    def _read_chain(mount_point):
        norm = mount_point.rstrip("/") + "/"
        chain = pki_mounts[norm].get("chain_pem")
        if isinstance(chain, Exception):
            raise chain
        return chain or ""

    client.secrets.pki.read_ca_certificate.side_effect = _read_ca
    client.secrets.pki.read_ca_certificate_chain.side_effect = _read_chain

    # Auth methods
    auth_methods = auth_methods if auth_methods is not None else {}
    client.sys.list_auth_methods.return_value = {"data": auth_methods}

    return client


# ---------------------------------------------------------------------------
# ISSUE-2: pyproject.toml structural test (passes after Plan 01 Task 1)
# ---------------------------------------------------------------------------

def test_pyproject_has_hvac_in_cloud_extras():
    """ISSUE-2 (D-16): pyproject.toml [cloud] extras must list hvac>=2.4.0 with Phase 30 comment."""
    text = Path("pyproject.toml").read_text()
    # Must appear inside the cloud = [...] block
    cloud_block = re.search(r"cloud\s*=\s*\[(.*?)\]", text, re.DOTALL)
    assert cloud_block, "cloud extras block not found in pyproject.toml"
    block = cloud_block.group(1)
    assert "hvac>=2.4.0" in block, "hvac>=2.4.0 not in [cloud] extras"
    assert "Phase 30" in block, "Phase 30 marker comment missing on hvac line"
    assert "VAULT-01" in block, "VAULT-01 reference missing on hvac line"


# ---------------------------------------------------------------------------
# Import-guard / availability tests
# ---------------------------------------------------------------------------

def test_hvac_unavailable_returns_empty_list():
    """HVAC_AVAILABLE=False must produce empty list (no scan_error endpoint)."""
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", False):
        from quirk.scanner.vault_connector import scan_vault_targets
        assert scan_vault_targets("http://localhost:8200", token="root") == []


def test_no_token_produces_scan_error():
    """Missing token must produce single scan_error endpoint with vault-no-token prefix."""
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch.dict("os.environ", {}, clear=False):
        # Ensure VAULT_TOKEN env var is not set
        import os as _os
        _os.environ.pop("VAULT_TOKEN", None)
        from quirk.scanner.vault_connector import scan_vault_targets
        results = scan_vault_targets("http://localhost:8200", token=None)
    assert len(results) == 1
    assert results[0].protocol == "VAULT"
    assert results[0].port == 8200
    assert results[0].scan_error and "vault-no-token" in results[0].scan_error


def test_invalid_token_produces_scan_error():
    """is_authenticated() returning False must produce vault-auth-failed scan_error endpoint."""
    mock_client = _build_mock_client(is_auth=False)
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        results = scan_vault_targets("http://127.0.0.1:8200", token="bad-token")
    assert len(results) == 1
    assert results[0].protocol == "VAULT"
    assert results[0].scan_error and "vault-auth-failed" in results[0].scan_error


# ---------------------------------------------------------------------------
# ISSUE-3 / D-17: session_start parameter
# ---------------------------------------------------------------------------

def test_session_start_threaded_to_scanned_at():
    """ISSUE-3 (D-17): scan_vault_targets must accept session_start and stamp scanned_at."""
    session_start = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    mock_client = _build_mock_client(
        transit_keys={"k": {"type": "rsa-4096", "exportable": False, "latest_version": 1}},
    )
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        results = scan_vault_targets(
            "http://127.0.0.1:8200", token="root", session_start=session_start
        )
    assert results, "expected at least one transit endpoint"
    assert results[0].scanned_at == dt.datetime(2026, 1, 1, 12, 0, 0)  # tzinfo stripped


# ---------------------------------------------------------------------------
# VAULT-01: Transit key classification (D-01)
# ---------------------------------------------------------------------------

def _get_transit_endpoint(results, key_name):
    for ep in results:
        sd = str(getattr(ep, "service_detail", "") or "")
        if sd == f"transit/{key_name}":
            return ep
    raise AssertionError(f"no endpoint for transit/{key_name} in {[(e.service_detail, e.severity) for e in results]}")


def _scan_with_transit(transit_keys):
    mock_client = _build_mock_client(transit_keys=transit_keys)
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        return scan_vault_targets("http://127.0.0.1:8200", token="root")


def test_transit_key_rsa2048_no_severity():
    """D-01: RSA-2048 transit key has cert_pubkey_alg='RSA', size=2048, NO severity."""
    results = _scan_with_transit({"rsa-key": {"type": "rsa-2048", "exportable": False, "latest_version": 1}})
    ep = _get_transit_endpoint(results, "rsa-key")
    assert ep.protocol == "VAULT"
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.cert_pubkey_size == 2048
    assert ep.severity is None or ep.severity == ""


def test_transit_key_aes256_no_severity():
    """D-01: aes256-gcm96 transit key normalises to alg='AES', size=256, NO severity."""
    results = _scan_with_transit({"aes-key": {"type": "aes256-gcm96", "exportable": False, "latest_version": 1}})
    ep = _get_transit_endpoint(results, "aes-key")
    assert ep.cert_pubkey_alg == "AES"
    assert ep.cert_pubkey_size == 256
    assert ep.severity is None or ep.severity == ""


def test_transit_key_ecdsa_p256_no_severity():
    """D-01: ecdsa-p256 transit key normalises to alg='ECDSA', size=256, NO severity."""
    results = _scan_with_transit({"ec-key": {"type": "ecdsa-p256", "exportable": False, "latest_version": 1}})
    ep = _get_transit_endpoint(results, "ec-key")
    assert ep.cert_pubkey_alg == "ECDSA"
    assert ep.cert_pubkey_size == 256
    assert ep.severity is None or ep.severity == ""


def test_transit_key_ml_dsa_87_quantum_safe_alg_name():
    """VAULT-01: ml-dsa-87 transit key produces alg_name='ml-dsa-87' (matches classifier.py)."""
    results = _scan_with_transit({"pqc-key": {"type": "ml-dsa-87", "exportable": False, "latest_version": 1}})
    ep = _get_transit_endpoint(results, "pqc-key")
    assert ep.cert_pubkey_alg == "ml-dsa-87"
    assert ep.severity is None or ep.severity == ""


def test_transit_key_slh_dsa_128_quantum_safe_alg_name():
    """VAULT-01: slh-dsa-shake-128s transit key produces alg_name='slh-dsa-128' (matches classifier.py)."""
    results = _scan_with_transit(
        {"pqc-slh": {"type": "slh-dsa-shake-128s", "exportable": False, "latest_version": 1}}
    )
    ep = _get_transit_endpoint(results, "pqc-slh")
    assert ep.cert_pubkey_alg == "slh-dsa-128"


def test_transit_key_exportable_medium_severity():
    """D-02: exportable=True transit key gets MEDIUM severity (does NOT cap dar_vault_weak)."""
    results = _scan_with_transit(
        {"export-key": {"type": "rsa-2048", "exportable": True, "latest_version": 1}}
    )
    ep = _get_transit_endpoint(results, "export-key")
    assert ep.severity == "MEDIUM"
    # Must still classify the underlying algorithm
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.cert_pubkey_size == 2048


# ---------------------------------------------------------------------------
# VAULT-02: PKI mount CA certificate algorithm (D-03, D-04)
# ---------------------------------------------------------------------------

def _scan_with_pki(pki_mounts):
    mock_client = _build_mock_client(pki_mounts=pki_mounts)
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        return scan_vault_targets("http://127.0.0.1:8200", token="root")


def test_pki_rsa2048_root_ca_high_severity():
    """D-03: PKI mount with RSA-2048 root CA produces HIGH severity endpoint."""
    pem = _make_test_pem_rsa(2048, "SHA256")
    results = _scan_with_pki({"pki/": {"root_pem": pem, "chain_pem": ""}})
    pki_endpoints = [ep for ep in results if str(ep.service_detail or "").startswith("PKI/")]
    assert pki_endpoints, "no PKI endpoint produced"
    root = pki_endpoints[0]
    assert root.protocol == "VAULT"
    assert root.severity == "HIGH"
    assert root.cert_pubkey_size == 2048


def test_pki_rsa4096_root_ca_no_severity():
    """D-03: RSA-4096 SHA-256 root CA produces no severity (baseline ok)."""
    pem = _make_test_pem_rsa(4096, "SHA256")
    results = _scan_with_pki({"pki/": {"root_pem": pem, "chain_pem": ""}})
    pki_endpoints = [ep for ep in results if str(ep.service_detail or "").startswith("PKI/")]
    assert pki_endpoints
    root = pki_endpoints[0]
    assert root.severity is None or root.severity == ""
    assert root.cert_pubkey_size == 4096


def test_pki_sha1_signed_ca_high_severity():
    """D-03: SHA-1 signing algorithm on PKI CA cert produces HIGH severity."""
    pem = _make_test_pem_rsa(4096, "SHA1")
    results = _scan_with_pki({"pki/": {"root_pem": pem, "chain_pem": ""}})
    pki_endpoints = [ep for ep in results if str(ep.service_detail or "").startswith("PKI/")]
    assert pki_endpoints
    root = pki_endpoints[0]
    assert root.severity == "HIGH"


def test_pki_intermediate_chain_emits_separate_endpoints():
    """D-03: PKI mount with intermediate chain produces ROOT + INTERMEDIATE endpoints (>=2)."""
    root_pem = _make_test_pem_rsa(4096, "SHA256")
    int_pem = _make_test_pem_rsa(2048, "SHA256")  # intermediate is RSA-2048 → HIGH
    results = _scan_with_pki({"pki/": {"root_pem": root_pem, "chain_pem": int_pem}})
    pki_endpoints = [ep for ep in results if str(ep.service_detail or "").startswith("PKI/")]
    # At least one root + one intermediate endpoint
    assert len(pki_endpoints) >= 2, f"expected root + intermediate, got {[ep.service_detail for ep in pki_endpoints]}"
    # One must be intermediate (severity HIGH due to RSA-2048)
    intermediates = [ep for ep in pki_endpoints if "intermediate" in str(ep.service_detail or "").lower()]
    assert intermediates, "no intermediate endpoint emitted"
    assert intermediates[0].severity == "HIGH"


def test_pki_intermediate_failure_swallowed_returns_root_only():
    """D-04: read_ca_certificate_chain raising → only root endpoint returned, no scan_error."""
    root_pem = _make_test_pem_rsa(4096, "SHA256")
    results = _scan_with_pki(
        {"pki/": {"root_pem": root_pem, "chain_pem": RuntimeError("no intermediate configured")}}
    )
    pki_endpoints = [ep for ep in results if str(ep.service_detail or "").startswith("PKI/")]
    # Exactly one PKI endpoint (root). No vault-no-intermediate-ca scan_error per D-04.
    assert len(pki_endpoints) == 1
    assert pki_endpoints[0].severity is None or pki_endpoints[0].severity == ""
    # No scan_error endpoints from the swallowed intermediate failure
    pki_errors = [ep for ep in pki_endpoints if ep.scan_error]
    assert pki_errors == []


def test_pki_endpoint_strips_trailing_slash_in_mount_path():
    """Pitfall 3: list_mounted_secrets_engines returns 'pki/' — mount_point passed without trailing slash."""
    pem = _make_test_pem_rsa(4096, "SHA256")
    mock_client = _build_mock_client(pki_mounts={"pki/": {"root_pem": pem, "chain_pem": ""}})
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        scan_vault_targets("http://127.0.0.1:8200", token="root")
    # read_ca_certificate must have been called with mount_point='pki' (no trailing slash)
    call_args = mock_client.secrets.pki.read_ca_certificate.call_args
    mount_arg = call_args.kwargs.get("mount_point") or (call_args.args[0] if call_args.args else "")
    assert not str(mount_arg).endswith("/"), f"mount_point must strip trailing slash, got {mount_arg!r}"


# ---------------------------------------------------------------------------
# VAULT-03: Auth method risk tiering (D-05, D-06)
# ---------------------------------------------------------------------------

def _scan_with_auth(auth_methods):
    mock_client = _build_mock_client(auth_methods=auth_methods)
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        return scan_vault_targets("http://127.0.0.1:8200", token="root")


def _auth_endpoint(results, path):
    for ep in results:
        if str(ep.service_detail or "") == f"auth/{path}":
            return ep
    return None


def test_auth_token_unconditional_high():
    """D-05: token auth always HIGH (even when other safe methods are present)."""
    results = _scan_with_auth({
        "token/": {"type": "token"},
        "approle/": {"type": "approle"},
        "kubernetes/": {"type": "kubernetes"},
    })
    ep = _auth_endpoint(results, "token/")
    assert ep is not None, "token endpoint must be emitted unconditionally"
    assert ep.severity == "HIGH"


def test_auth_ldap_high_severity():
    """D-06: ldap auth → HIGH (LDAP root bind risk)."""
    results = _scan_with_auth({"ldap/": {"type": "ldap"}})
    ep = _auth_endpoint(results, "ldap/")
    assert ep is not None
    assert ep.severity == "HIGH"


def test_auth_userpass_medium_severity():
    """D-06: userpass auth → MEDIUM."""
    results = _scan_with_auth({"userpass/": {"type": "userpass"}})
    ep = _auth_endpoint(results, "userpass/")
    assert ep is not None
    assert ep.severity == "MEDIUM"


def test_auth_approle_kubernetes_oidc_no_finding():
    """D-06: approle, kubernetes, oidc → NO endpoint emitted (positive posture)."""
    results = _scan_with_auth({
        "approle/": {"type": "approle"},
        "k8s/": {"type": "kubernetes"},
        "oidc/": {"type": "oidc"},
    })
    auth_eps = [ep for ep in results if str(ep.service_detail or "").startswith("auth/")]
    assert auth_eps == [], f"expected no auth endpoints, got {[e.service_detail for e in auth_eps]}"


# ---------------------------------------------------------------------------
# VAULT-01/02/03 invariant: dat_scan_json populated
# ---------------------------------------------------------------------------

def test_dat_scan_json_populated_on_every_vault_endpoint():
    """Every VAULT endpoint (transit, PKI, auth) must have non-empty dat_scan_json."""
    pem = _make_test_pem_rsa(4096, "SHA256")
    mock_client = _build_mock_client(
        transit_keys={"k1": {"type": "rsa-4096", "exportable": False, "latest_version": 1}},
        pki_mounts={"pki/": {"root_pem": pem, "chain_pem": ""}},
        auth_methods={"token/": {"type": "token"}, "userpass/": {"type": "userpass"}},
    )
    with patch("quirk.scanner.vault_connector.HVAC_AVAILABLE", True), \
         patch("quirk.scanner.vault_connector.hvac") as mock_hvac:
        mock_hvac.Client.return_value = mock_client
        from quirk.scanner.vault_connector import scan_vault_targets
        results = scan_vault_targets("http://127.0.0.1:8200", token="root")
    # At least 4 endpoints: 1 transit + 1 PKI root + 2 auth (token, userpass)
    assert len(results) >= 4
    for ep in results:
        if ep.scan_error:
            continue
        assert ep.dat_scan_json, f"empty dat_scan_json on {ep.protocol} ep service_detail={ep.service_detail!r}"
        # Must be valid JSON
        import json as _json
        _json.loads(ep.dat_scan_json)


# ---------------------------------------------------------------------------
# Section: Phase 30 / UAT-30-01 Live Integration (SKIPPED unless env var set)
# ---------------------------------------------------------------------------
# Closes Phase 30 HUMAN-UAT (1 pending) — see .planning/STATE.md Deferred Items.
# Run locally with:
#   cd quantum-chaos-enterprise-lab && ./lab.sh up vault
#   QUIRK_VAULT_INTEGRATION=1 python -m pytest tests/test_vault_connector.py::test_vault_live_uat_30_01_five_findings -v

import os as _os_uat
import pytest as _pytest_uat


@_pytest_uat.mark.slow
@_pytest_uat.mark.skipif(
    not _os_uat.environ.get("QUIRK_VAULT_INTEGRATION"),
    reason="Set QUIRK_VAULT_INTEGRATION=1 and start `docker compose --profile vault up -d`",
)
def test_vault_live_uat_30_01_five_findings():
    """UAT-30-01: vault-30 chaos lab (port 28200, root token) produces 5 expected findings.

    Pitfall 3: this test MUST point at port 28200 (vault-30, image 1.17), NOT
    20009 (legacy storage-profile vault, image 1.15) — the seeded state differs.
    """
    from quirk.scanner.vault_connector import scan_vault_targets

    results = scan_vault_targets(
        vault_addr="http://localhost:28200",
        token="root",
    )

    assert len(results) >= 5, (
        f"Expected >=5 vault findings (UAT-30-01); got {len(results)}: "
        f"{[(r.service_detail, r.severity) for r in results]}"
    )

    details = [(r.service_detail or "", r.severity) for r in results]

    # Finding 2: transit exportable RSA-2048 -> MEDIUM
    assert any("transit" in d.lower() and "exportable" in d.lower() and sev == "MEDIUM"
               for d, sev in details), (
        f"Missing transit/rsa-2048-exportable MEDIUM finding; got: {details}"
    )

    # Finding 3: PKI RSA-2048 root CA -> HIGH
    assert any("pki" in d.lower() and sev == "HIGH" for d, sev in details), (
        f"Missing PKI HIGH finding; got: {details}"
    )

    # Finding 4: auth/token -> HIGH
    assert any("token" in d.lower() and sev == "HIGH" for d, sev in details), (
        f"Missing auth/token HIGH finding; got: {details}"
    )

    # Finding 5: auth/userpass -> MEDIUM
    assert any("userpass" in d.lower() and sev == "MEDIUM" for d, sev in details), (
        f"Missing auth/userpass MEDIUM finding; got: {details}"
    )

    # dar_vault_weak_count == 2 (HIGH-only) per expected_results_v4.md
    high_count = sum(1 for _, sev in details if sev == "HIGH")
    assert high_count >= 2, (
        f"Expected >=2 HIGH vault findings (dar_vault_weak_count==2); got {high_count}: {details}"
    )

"""Single source of truth for the per-profile CBOM endpoint synthesizer map.

Created by Phase 42 / Plan 03 to eliminate duplication between Plan 02
(schema validation harness) and Plan 04 (classifier coverage gate).

Every entry MUST resolve to a callable that returns a NON-EMPTY
list[CryptoEndpoint] with at least one real algorithm name observed by
the scanner for that profile (per D-03 + user Option 1, 2026-04-30).

Drift between this map and docker-compose.yml is enforced by
``tests/test_cbom_schema_validation.py::test_parametrize_set_matches_docker_compose_profiles``
(added in Plan 02).
"""
from __future__ import annotations

from typing import Callable

from quirk.models import CryptoEndpoint

# The 2 already-shipped Phase 35 synthesizers live in test_cbom_motion_golden.py
from tests.test_cbom_motion_golden import (
    _build_broker_lab_endpoints,
    _build_email_lab_endpoints,
)

# The Phase 42 + later synthesizers live in test_cbom_motion_endpoints.py
from tests.test_cbom_motion_endpoints import (
    _build_adcs_lab_endpoints,
    _build_cloud_lab_endpoints,
    _build_database_lab_endpoints,
    _build_dnssec_lab_endpoints,
    _build_fuzz_target_lab_endpoints,
    _build_grpc_tls_lab_endpoints,
    _build_hwcompat_lab_endpoints,
    _build_identity_lab_endpoints,
    _build_jwt_lab_endpoints,
    _build_kafka_tls_lab_endpoints,
    _build_kerberos_lab_endpoints,
    _build_ldaps_lab_endpoints,
    _build_oqs_nginx_lab_endpoints,
    _build_phaseA_lab_endpoints,
    _build_pki_lab_endpoints,
    _build_postgres_tls_lab_endpoints,
    _build_redis_tls_lab_endpoints,
    _build_registry_lab_endpoints,
    _build_saml_lab_endpoints,
    _build_smime_lab_endpoints,
    _build_source_lab_endpoints,
    _build_ssh_weak_lab_endpoints,
    _build_storage_s3_lab_endpoints,
    _build_tls_cert_defects_lab_endpoints,
    _build_vault_lab_endpoints,
)

PROFILE_ENDPOINTS: dict[str, Callable[[], list[CryptoEndpoint]]] = {
    # Every profile declared in quantum-chaos-enterprise-lab/docker-compose.yml
    # (drift-enforced by test_parametrize_set_matches_docker_compose_profiles).
    # Every entry returns >=1 representative endpoint.
    "adcs":             _build_adcs_lab_endpoints,
    "broker":           _build_broker_lab_endpoints,
    "cloud":            _build_cloud_lab_endpoints,
    "database":         _build_database_lab_endpoints,
    "dnssec":           _build_dnssec_lab_endpoints,
    "email":            _build_email_lab_endpoints,
    "fuzz-target":      _build_fuzz_target_lab_endpoints,
    "grpc-tls":         _build_grpc_tls_lab_endpoints,
    "hwcompat":         _build_hwcompat_lab_endpoints,
    "identity":         _build_identity_lab_endpoints,
    "jwt":              _build_jwt_lab_endpoints,
    "kafka-tls":        _build_kafka_tls_lab_endpoints,
    "kerberos":         _build_kerberos_lab_endpoints,
    "ldaps":            _build_ldaps_lab_endpoints,
    "oqs-nginx":        _build_oqs_nginx_lab_endpoints,
    "phaseA":           _build_phaseA_lab_endpoints,
    "pki":              _build_pki_lab_endpoints,
    "postgres-tls":     _build_postgres_tls_lab_endpoints,
    "redis-tls":        _build_redis_tls_lab_endpoints,
    "registry":         _build_registry_lab_endpoints,
    "saml":             _build_saml_lab_endpoints,
    "smime":            _build_smime_lab_endpoints,
    "source":           _build_source_lab_endpoints,
    "ssh-weak":         _build_ssh_weak_lab_endpoints,
    "storage-s3":       _build_storage_s3_lab_endpoints,
    "tls-cert-defects": _build_tls_cert_defects_lab_endpoints,
    "vault":            _build_vault_lab_endpoints,
}

# Sanity guard at import time -- a missing/empty entry is a synthesizer bug.
assert len(PROFILE_ENDPOINTS) == 27, (
    f"Expected 27 profiles in PROFILE_ENDPOINTS; got {len(PROFILE_ENDPOINTS)}"
)

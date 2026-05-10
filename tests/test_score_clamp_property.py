"""Property test: compute_readiness_score() always returns score in [0, 100].

Uses seeded random.Random(42) for 1,000 randomised evidence dicts.
Per CONTEXT.md D-03.
"""
from __future__ import annotations

import random

import pytest

from quirk.intelligence.scoring import compute_readiness_score

_EVIDENCE_KEYS = [
    "plaintext_http_count",
    "http_on_tls_port_count",
    "mtls_present_count",
    "identity_weak_etype_count",
    "saml_weak_signing_count",
    "dnssec_weak_algo_count",
    "dar_db_plaintext_count",
    "dar_db_weak_ssl_count",
    "dar_storage_unencrypted_count",
    "dar_storage_aws_managed_count",
    "dar_k8s_unencrypted_count",
    "dar_k8s_inaccessible_count",
    "dar_vault_weak_count",
    "motion_email_plaintext_count",
    "motion_email_starttls_missing_count",
    "motion_email_weak_cipher_count",
    "motion_broker_plaintext_count",
    "motion_broker_weak_tls_count",
    "motion_broker_weak_cipher_count",
]


def _random_evidence(rng: random.Random) -> dict:
    endpoints = rng.randint(0, 200)
    findings = rng.randint(0, 500)
    protocol_counts = {
        "TLS": rng.randint(0, endpoints),
        "SSH": rng.randint(0, max(0, endpoints - 10)),
        "UNKNOWN": rng.randint(0, 50),
        "LOW": rng.randint(0, findings),
    }
    sev = {
        "HIGH": rng.randint(0, findings),
        "CRITICAL": rng.randint(0, findings // 2 if findings else 0),
        "LOW": rng.randint(0, findings),
    }
    ev: dict = {
        "totals": {"endpoints": endpoints, "findings": findings},
        "protocol_counts": protocol_counts,
        "finding_severity_counts": sev,
        "scan_error": {"rate": rng.uniform(0.0, 1.0)},
        "certificate_observations": {
            "expired_count": rng.randint(0, 50),
            "expiring_count": rng.randint(0, 50),
            "self_signed_count": rng.randint(0, 50),
        },
        "cert_key_type_counts": {
            "RSA": rng.randint(0, 100),
            "ECDSA": rng.randint(0, 100),
        },
    }
    for key in _EVIDENCE_KEYS:
        ev[key] = rng.randint(0, max(1, endpoints))
    return ev


def test_score_always_bounded_1000_iterations():
    rng = random.Random(42)
    for i in range(1_000):
        ev = _random_evidence(rng)
        result = compute_readiness_score(ev)
        score = result["score"]
        assert 0 <= score <= 100, (
            f"Iteration {i}: score={score} out of bounds. "
            f"evidence snapshot: endpoints={ev['totals']['endpoints']}"
        )

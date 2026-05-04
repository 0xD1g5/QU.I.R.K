"""Phase 47 / Plan 03 (TDD RED): post-write CBOM JSON schema validation hook.

Covers decisions D-14, D-15, D-16 from 47-CONTEXT.md:
- D-14: CBOM file is NOT deleted on validation failure.
- D-15: schema-violation → one coverage_gap WARN advisory; scan continues.
- D-16: missing jsonschema/referencing → MissingOptionalDependencyException caught
        silently; registry probe in run_scan.py emits the INFO advisory (no double-emit).

RESEARCH F6 (critical anti-pattern to avoid):
MissingOptionalDependencyException can fire at BOTH JsonStrictValidator(SchemaVersion.V1_6)
constructor AND at .validate_str(). BOTH are wrapped in a single try-except block.

Test decision: test_cbom_schema_validation.py covers chaos-lab-profile-level schema
validity (a different concern). This new file covers the writer-level soft-fail mechanism
and backward-compat of the new keyword-only error_endpoints param.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tls_endpoint(**overrides):
    """Create a TLS CryptoEndpoint with sensible defaults."""
    from quirk.models import CryptoEndpoint

    defaults = dict(
        host="example.com",
        port=443,
        protocol=None,
        tls_version="TLSv1.2",
        cipher_suite="TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        cert_pubkey_alg="RSA",
        cert_pubkey_size=2048,
        cert_sig_alg="sha256WithRSAEncryption",
        cert_subject="CN=example.com",
        cert_issuer="CN=Example CA",
        cert_not_before=None,
        cert_not_after=None,
        tls_capabilities_json=None,
        ssh_audit_json=None,
    )
    defaults.update(overrides)
    return CryptoEndpoint(**defaults)


def _build_test_bom():
    """Build a Bom from a TLS endpoint."""
    from quirk.cbom.builder import build_cbom

    ep = _tls_endpoint()
    return build_cbom([ep])


# ---------------------------------------------------------------------------
# Test 1: Valid CBOM passes validation — no finding emitted (D-14, D-15)
# ---------------------------------------------------------------------------

def test_valid_cbom_passes_validation_no_finding(tmp_path):
    """Happy path: a valid Bom produces a schema-valid CBOM JSON; no advisory appended."""
    from quirk.cbom.writer import write_cbom_files

    bom = _build_test_bom()
    eps = []

    json_path, xml_path = write_cbom_files(bom, str(tmp_path), "stamp", error_endpoints=eps)

    assert os.path.exists(json_path), "JSON CBOM file must exist after write"
    assert len(eps) == 0, f"Expected no advisories for valid CBOM, got {eps}"


# ---------------------------------------------------------------------------
# Test 2: Invalid CBOM → WARN finding emitted; file NOT deleted (D-14, D-15)
# ---------------------------------------------------------------------------

def test_invalid_cbom_emits_warn_finding_and_preserves_file(tmp_path):
    """D-14 + D-15: schema violation → one coverage_gap WARN advisory; file is preserved."""
    from quirk.cbom.writer import write_cbom_files

    bom = _build_test_bom()
    eps = []

    # Mock JsonStrictValidator to return a fake validation error.
    fake_error = MagicMock()
    fake_error.__str__ = lambda self: "property 'invalid_prop' is not valid"

    with patch("quirk.cbom.writer.JsonStrictValidator") as mock_validator_cls:
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_str.return_value = fake_error
        mock_validator_cls.return_value = mock_validator_instance

        json_path, xml_path = write_cbom_files(bom, str(tmp_path), "stamp", error_endpoints=eps)

    # D-14: file must NOT be deleted on failure.
    assert os.path.exists(json_path), "D-14: JSON CBOM file must be preserved on schema failure"

    # D-15: exactly one coverage_gap WARN advisory.
    assert len(eps) == 1, f"Expected exactly 1 advisory on schema failure, got {len(eps)}"
    ep = eps[0]
    assert ep.scan_error_category == "coverage_gap", (
        f"Expected scan_error_category='coverage_gap', got {ep.scan_error_category!r}"
    )
    assert ep.scan_error.startswith("CBOM JSON failed schema validation:"), (
        f"scan_error must start with the canonical prefix: {ep.scan_error!r}"
    )
    # Error summary must appear in the message.
    assert "invalid_prop" in ep.scan_error, (
        f"Validator error summary must be included in the finding: {ep.scan_error!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: Missing jsonschema/referencing → silent skip; no advisory (D-16)
# ---------------------------------------------------------------------------

def test_missing_jsonschema_emits_no_finding_from_writer(tmp_path):
    """D-16: when MissingOptionalDependencyException fires (deps absent),
    the writer catches it and returns normally — no exception escapes, no advisory
    appended. The registry probe (run_scan.py) handles the INFO advisory; writer
    does NOT double-emit."""
    from quirk.cbom.writer import write_cbom_files

    bom = _build_test_bom()
    eps = []

    # Simulate MissingOptionalDependencyException at validate_str() time.
    from cyclonedx.validation.json import MissingOptionalDependencyException

    with patch("quirk.cbom.writer.JsonStrictValidator") as mock_validator_cls:
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_str.side_effect = MissingOptionalDependencyException(
            "jsonschema"
        )
        mock_validator_cls.return_value = mock_validator_instance

        # Must not raise; must return paths normally.
        json_path, xml_path = write_cbom_files(bom, str(tmp_path), "stamp", error_endpoints=eps)

    assert os.path.exists(json_path), "JSON CBOM file must exist even when validation skipped"
    # D-16: writer does NOT emit a double advisory; the registry probe does.
    assert len(eps) == 0, (
        f"Writer must not emit advisory on MissingOptionalDependencyException (registry handles it): {eps}"
    )


def test_missing_jsonschema_at_constructor_silent(tmp_path):
    """D-16 / RESEARCH F6: MissingOptionalDependencyException raised at the
    JsonStrictValidator() constructor (before validate_str) is also caught silently."""
    from quirk.cbom.writer import write_cbom_files
    from cyclonedx.validation.json import MissingOptionalDependencyException

    bom = _build_test_bom()
    eps = []

    # Simulate constructor raising MissingOptionalDependencyException.
    with patch("quirk.cbom.writer.JsonStrictValidator",
               side_effect=MissingOptionalDependencyException("jsonschema")):
        json_path, xml_path = write_cbom_files(bom, str(tmp_path), "stamp", error_endpoints=eps)

    assert os.path.exists(json_path)
    assert len(eps) == 0, (
        "Constructor-time MissingOptionalDependencyException must be caught silently"
    )


# ---------------------------------------------------------------------------
# Test 4: Backward compat — positional callers with no error_endpoints kwarg (D-15 Risks #2)
# ---------------------------------------------------------------------------

def test_error_endpoints_default_none_no_emit(tmp_path):
    """Backward compat: write_cbom_files(bom, outdir, stamp) without the error_endpoints
    kwarg must not raise — preserves all existing test_cbom_writer.py call sites."""
    from quirk.cbom.writer import write_cbom_files

    bom = _build_test_bom()

    # No error_endpoints kwarg — should succeed without exception.
    json_path, xml_path = write_cbom_files(bom, str(tmp_path), "stamp")

    assert os.path.exists(json_path)
    assert os.path.exists(xml_path)

"""Tests for quirk.scanner.pqc_probe — PQC-02 detection via raw openssl subprocess.

All tests use mocked subprocess output — no live network required (Phase 90 plan 02).
"""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from quirk.cbom.classifier import classify_algorithm, CryptoPrimitive


# ---------------------------------------------------------------------------
# Classifier alias tests (D-02)
# ---------------------------------------------------------------------------

class TestClassifierAlias:
    """classify_algorithm must map X25519MLKEM768 -> (KEM, 3, 192)."""

    def test_x25519mlkem768_returns_kem(self):
        prim, level, bits = classify_algorithm("X25519MLKEM768")
        assert prim == CryptoPrimitive.KEM

    def test_x25519mlkem768_returns_nist_level_3(self):
        prim, level, bits = classify_algorithm("X25519MLKEM768")
        assert level == 3

    def test_x25519mlkem768_returns_192_bits(self):
        prim, level, bits = classify_algorithm("X25519MLKEM768")
        assert bits == 192

    def test_lowercase_x25519mlkem768(self):
        """classify_algorithm lowercases input before lookup."""
        prim, level, bits = classify_algorithm("x25519mlkem768")
        assert prim == CryptoPrimitive.KEM
        assert level == 3
        assert bits == 192


# ---------------------------------------------------------------------------
# Capability gate tests
# ---------------------------------------------------------------------------

class TestHostSupportsMlkem:
    """host_supports_mlkem() returns True/False based on openssl kem-algorithms output."""

    def test_returns_true_when_mlkem_listed(self):
        from quirk.scanner.pqc_probe import host_supports_mlkem
        ml_kem_output = (
            "Available KEM algorithms:\n"
            "  X25519MLKEM768\n"
            "  ML-KEM-512\n"
            "  ML-KEM-768\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = ml_kem_output
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert host_supports_mlkem() is True

    def test_returns_false_when_mlkem_absent(self):
        from quirk.scanner.pqc_probe import host_supports_mlkem
        mock_result = MagicMock()
        mock_result.stdout = "Available KEM algorithms:\n  Classic-McEliece\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert host_supports_mlkem() is False

    def test_returns_false_on_subprocess_error(self):
        from quirk.scanner.pqc_probe import host_supports_mlkem
        with patch("subprocess.run", side_effect=Exception("openssl not found")):
            assert host_supports_mlkem() is False

    def test_capability_gate_uses_argv_list(self):
        """host_supports_mlkem must not use shell=True."""
        from quirk.scanner.pqc_probe import host_supports_mlkem
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            host_supports_mlkem()
        call_kwargs = mock_run.call_args
        # shell=True must not appear
        assert call_kwargs.kwargs.get("shell", False) is False
        # first arg must be a list
        assert isinstance(call_kwargs.args[0], list)


# ---------------------------------------------------------------------------
# Probe function tests
# ---------------------------------------------------------------------------

class TestProbePqcHybrid:
    """probe_pqc_hybrid() — argv-list safety, parse, timeout, validation."""

    def test_detected_true_on_negotiated_group(self):
        """Successful hybrid handshake with the expected output line."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        output = (
            "CONNECTED(00000003)\n"
            "Negotiated TLS1.3 group: X25519MLKEM768\n"
            "---\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = output
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = probe_pqc_hybrid("pqc.example.com", 443)
        assert result["detected"] is True
        assert result["negotiated_group"] == "X25519MLKEM768"

    def test_detected_false_on_classical_server(self):
        """Classical TLS endpoint — no X25519MLKEM768 in output."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        mock_result = MagicMock()
        mock_result.stdout = "CONNECTED(00000003)\nSSL handshake has read 4096 bytes\n---\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = probe_pqc_hybrid("classical.example.com", 443)
        assert result["detected"] is False
        assert result["negotiated_group"] is None

    def test_no_shell_true(self):
        """subprocess must be called without shell=True (T-90-03)."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            probe_pqc_hybrid("host.example.com", 443)
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("shell", False) is False
        # Command is an argv list, not a string
        assert isinstance(call_kwargs.args[0], list)

    def test_argv_list_contains_connect_host_port(self):
        """Probe command includes -connect host:port in the argv list."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            probe_pqc_hybrid("myhost.example.com", 25443)
        cmd = mock_run.call_args.args[0]
        assert isinstance(cmd, list)
        # The connect string must appear as a single argv element
        assert "myhost.example.com:25443" in cmd

    def test_argv_list_contains_groups_flag(self):
        """Probe command includes -groups X25519MLKEM768."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            probe_pqc_hybrid("host.example.com", 443)
        cmd = mock_run.call_args.args[0]
        assert "X25519MLKEM768" in cmd

    def test_timeout_expired_returns_not_detected(self):
        """TimeoutExpired must be caught; probe returns detected=False (T-90-04)."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        with patch("subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd=["openssl"], timeout=8)):
            result = probe_pqc_hybrid("slow.example.com", 443)
        assert result["detected"] is False
        assert result["negotiated_group"] is None

    def test_timeout_expired_does_not_raise(self):
        """No exception escapes from probe_pqc_hybrid on TimeoutExpired."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        with patch("subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd=["openssl"], timeout=8)):
            # Should not raise
            probe_pqc_hybrid("slow.example.com", 443)

    def test_invalid_host_empty_returns_not_detected(self):
        """Empty host is rejected — returns detected=False without calling subprocess."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        with patch("subprocess.run") as mock_run:
            result = probe_pqc_hybrid("", 443)
        assert result["detected"] is False
        mock_run.assert_not_called()

    def test_invalid_host_metachar_returns_not_detected(self):
        """Host containing shell metacharacter is rejected (T-90-03)."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        with patch("subprocess.run") as mock_run:
            result = probe_pqc_hybrid("host;rm -rf /", 443)
        assert result["detected"] is False
        mock_run.assert_not_called()

    def test_port_coerced_to_int(self):
        """Port string is coerced to int in the connect argument."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            probe_pqc_hybrid("host.example.com", "443")
        cmd = mock_run.call_args.args[0]
        assert "host.example.com:443" in cmd

    def test_result_contains_capability_ok_field(self):
        """Result dict always has a capability_ok field."""
        from quirk.scanner.pqc_probe import probe_pqc_hybrid
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            result = probe_pqc_hybrid("host.example.com", 443)
        assert "capability_ok" in result

"""PQC discriminator regression test — Phase 90 Plan 04.

Proves the false-positive-free property of the X25519MLKEM768 hybrid-only probe:

- **Positive arm (oqs-nginx, live):** probe_pqc_hybrid() returns detected=True
  against ``127.0.0.1:39444`` when the ``oqs-nginx`` chaos-lab profile is running.
  Skipped cleanly when the profile is not up.

- **Negative arm (mocked classical TLS):** uses ``unittest.mock.patch`` to inject
  classical-server output (TLS alert / no hybrid group line) into the probe and
  asserts detected=False.  Always runs — no live lab dependency.

  Rationale: the negative arm cannot use a real Python ssl.SSLContext server on
  this host because the host's OpenSSL 3.6.2 supports X25519MLKEM768 natively and
  will complete the hybrid handshake even for a "plain" Python TLS server — making
  the mock server behaviorally identical to a PQC server.  Mocking subprocess.run
  to return classical output (no "Negotiated TLS1.3 group:" line, or a TLS alert)
  is the correct way to exercise the probe's parser in the classical case.

Discriminator rationale (D-01 / spike-verified 2026-05-22):
  Offering ONLY ``-groups X25519MLKEM768`` to a classical TLS server that does not
  support the group causes the handshake to fail — the server sends a TLS Alert and
  the openssl s_client output never contains the
  "Negotiated TLS1.3 group: X25519MLKEM768" line.
  The probe returns detected=False whenever that line is absent → zero false
  positives against a genuine classical endpoint.
"""
from __future__ import annotations

import socket
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from quirk.scanner.pqc_probe import probe_pqc_hybrid

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OQS_NGINX_HOST = "127.0.0.1"
OQS_NGINX_PORT = 39444

# Typical openssl s_client stdout when a classical server rejects X25519MLKEM768
# (handshake fails; server sends handshake_failure alert; no group negotiated).
_CLASSICAL_HANDSHAKE_FAILURE_OUTPUT = b"""\
CONNECTED(00000005)
write:errno=0
140736050948928:error:141A318A:SSL routines:tls1_process_ks_point:no shared groups
---
no peer certificate available
---
No client certificate CA names sent
---
SSL handshake has read 7 bytes and written 302 bytes
Verification: OK
---
New, (NONE), Cipher is (NONE)
Secure Renegotiation IS NOT supported
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 0 (ok)
---
"""

# Typical openssl s_client stdout when a PQC-hybrid server negotiates the group.
_PQC_HANDSHAKE_SUCCESS_OUTPUT = b"""\
CONNECTED(00000005)
Can't use SSL_get_servername
depth=0 CN=oqs-nginx
verify error:num=18:self-signed certificate
verify return:1
---
Certificate chain
 0 s:CN=oqs-nginx
   i:CN=oqs-nginx
---
Server certificate
...
Peer signature type: mldsa65
---
SSL handshake has read 1234 bytes and written 567 bytes
Verification: OK
---
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
Secure Renegotiation IS NOT supported
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 18 (self signed certificate)
---
Negotiated TLS1.3 group: X25519MLKEM768
---
"""


def _oqs_nginx_up() -> bool:
    """Return True when the oqs-nginx chaos-lab port is reachable."""
    try:
        with socket.create_connection((OQS_NGINX_HOST, OQS_NGINX_PORT), timeout=2):
            return True
    except OSError:
        return False


def _make_completed_process(stdout: bytes, returncode: int = 0) -> MagicMock:
    """Return a mock subprocess.CompletedProcess-like object."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.stdout = stdout
    mock.returncode = returncode
    return mock


# ---------------------------------------------------------------------------
# Positive arm — live oqs-nginx (skipped when lab down)
# ---------------------------------------------------------------------------


class TestPqcDiscriminatorPositive:
    """Positive arm: oqs-nginx probe detects X25519MLKEM768 (skipped when lab down)."""

    @pytest.mark.skipif(
        not _oqs_nginx_up(),
        reason="oqs-nginx chaos-lab profile is not running (PROFILE_ARGS='--profile oqs-nginx' ./lab.sh up)",
    )
    def test_probe_detects_oqs_nginx(self):
        """Positive arm: probe returns detected=True against the live oqs-nginx endpoint."""
        result = probe_pqc_hybrid(OQS_NGINX_HOST, OQS_NGINX_PORT, timeout=15)
        assert result["detected"] is True, (
            f"Expected detected=True against oqs-nginx:{OQS_NGINX_PORT}; "
            f"got {result}"
        )
        assert result["negotiated_group"] == "X25519MLKEM768", (
            f"Expected negotiated_group='X25519MLKEM768'; got {result.get('negotiated_group')!r}"
        )

    @pytest.mark.skipif(
        not _oqs_nginx_up(),
        reason="oqs-nginx chaos-lab profile is not running",
    )
    def test_probe_detects_negotiated_group_string(self):
        """Probe parses 'Negotiated TLS1.3 group: X25519MLKEM768' from oqs-nginx output."""
        result = probe_pqc_hybrid(OQS_NGINX_HOST, OQS_NGINX_PORT, timeout=15)
        assert result.get("negotiated_group") == "X25519MLKEM768"


# ---------------------------------------------------------------------------
# Negative arm — mocked classical TLS (always runs)
# ---------------------------------------------------------------------------


class TestPqcDiscriminatorNegative:
    """Negative arm: probe returns detected=False for classical-only output.

    These tests use ``subprocess.run`` mocking to inject realistic openssl
    output from a classical TLS server (no "Negotiated TLS1.3 group:" line).
    They prove the false-positive-free guarantee without requiring any live
    classical endpoint or a Python ssl.SSLContext server (which would use the
    host's OpenSSL 3.6.2 and *also* support X25519MLKEM768).
    """

    def test_probe_does_not_false_positive_against_classical_handshake_failure(self):
        """No false positive: openssl output with no group negotiation → detected=False."""
        with patch("quirk.scanner.pqc_probe.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                _CLASSICAL_HANDSHAKE_FAILURE_OUTPUT
            )
            result = probe_pqc_hybrid("127.0.0.1", 443, timeout=8)

        assert result["detected"] is False, (
            f"False positive! Classical handshake output returned detected=True; result={result}"
        )
        assert result["negotiated_group"] is None, (
            f"Classical output should not produce a negotiated_group; got {result.get('negotiated_group')!r}"
        )

    def test_probe_does_not_false_positive_against_empty_output(self):
        """No false positive when subprocess returns empty stdout → detected=False."""
        with patch("quirk.scanner.pqc_probe.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(b"")
            result = probe_pqc_hybrid("127.0.0.1", 443, timeout=8)

        assert result["detected"] is False

    def test_probe_does_not_false_positive_different_group_name(self):
        """No false positive when a different group (e.g. x25519) is negotiated → detected=False."""
        output = b"...\nNegotiated TLS1.3 group: x25519\n..."
        with patch("quirk.scanner.pqc_probe.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(output)
            result = probe_pqc_hybrid("127.0.0.1", 443, timeout=8)

        assert result["detected"] is False, (
            "A classical group (x25519) must not trigger the PQC detector"
        )
        # negotiated_group is None because the group name did not match the hybrid group.
        assert result["negotiated_group"] is None

    def test_probe_returns_false_for_invalid_host(self):
        """Invalid host (empty string) → detected=False, no exception escapes."""
        result = probe_pqc_hybrid("", 39444)
        assert result["detected"] is False

    def test_probe_returns_false_for_shell_metachar_host(self):
        """Host with shell metacharacters → detected=False (T-90-03 host validation)."""
        result = probe_pqc_hybrid("127.0.0.1; id", 39444)
        assert result["detected"] is False


# ---------------------------------------------------------------------------
# Mocked positive arm — confirms the parse path (always runs)
# ---------------------------------------------------------------------------


class TestPqcDiscriminatorMockedPositive:
    """Mocked positive arm: probe parses PQC output correctly even without live lab."""

    def test_probe_detects_x25519mlkem768_from_mocked_output(self):
        """Probe parses the 'Negotiated TLS1.3 group: X25519MLKEM768' sentinel correctly."""
        with patch("quirk.scanner.pqc_probe.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(
                _PQC_HANDSHAKE_SUCCESS_OUTPUT
            )
            result = probe_pqc_hybrid(OQS_NGINX_HOST, OQS_NGINX_PORT, timeout=15)

        assert result["detected"] is True, (
            f"Mocked PQC output should produce detected=True; got {result}"
        )
        assert result["negotiated_group"] == "X25519MLKEM768"

    def test_mocked_pqc_and_classical_differ(self):
        """Mocked PQC output → detected=True; mocked classical → detected=False (discriminator)."""
        with patch("quirk.scanner.pqc_probe.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_PQC_HANDSHAKE_SUCCESS_OUTPUT)
            pqc_result = probe_pqc_hybrid("127.0.0.1", 39444, timeout=8)

        with patch("quirk.scanner.pqc_probe.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(_CLASSICAL_HANDSHAKE_FAILURE_OUTPUT)
            classical_result = probe_pqc_hybrid("127.0.0.1", 443, timeout=8)

        assert pqc_result["detected"] is True
        assert classical_result["detected"] is False
        assert pqc_result["detected"] != classical_result["detected"], (
            "Discriminator: PQC and classical outputs must produce different detected values"
        )

"""Tests for SSH scanner — threaded execution and ssh-audit integration.

TDD RED phase: These tests are written before the implementation.
They test the behaviors required by Plan 02 (D-04, D-05, D-06, D-07).
"""

import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from qcscan.models import CryptoEndpoint
from qcscan.scanner.ssh_scanner import scan_ssh_one, scan_ssh_targets


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SSH_AUDIT_JSON = {
    "target": "10.0.0.1:22",
    "banner": {"raw": "SSH-2.0-OpenSSH_8.9p1", "protocol": "2.0", "software": "OpenSSH_8.9p1"},
    "kex": [
        {"algorithm": "curve25519-sha256", "keysize": None, "notes": {}},
        {"algorithm": "diffie-hellman-group14-sha256", "keysize": 2048, "notes": {}},
    ],
    "key": [
        {"algorithm": "ssh-rsa", "keysize": 3072, "notes": {}},
        {"algorithm": "ecdsa-sha2-nistp256", "keysize": 256, "notes": {}},
    ],
    "enc": [
        {"algorithm": "aes128-ctr", "notes": {}},
        {"algorithm": "chacha20-poly1305@openssh.com", "notes": {}},
    ],
    "mac": [
        {"algorithm": "hmac-sha2-256", "notes": {}},
    ],
    "fingerprints": [
        {"hash_alg": "SHA256", "hash": "SHA256:abc123"},
    ],
}


def _make_cfg(concurrency=4, timeout=5):
    """Return a minimal config object matching what run_scan.py passes."""
    cfg = SimpleNamespace()
    cfg.scan = SimpleNamespace()
    cfg.scan.concurrency = concurrency
    cfg.scan.timeout_seconds = timeout
    return cfg


# ---------------------------------------------------------------------------
# scan_ssh_one tests
# ---------------------------------------------------------------------------


class TestScanSshOneWithSshAudit(unittest.TestCase):
    """ssh-audit is available and returns valid JSON."""

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run")
    def test_ssh_audit_json_populated(self, mock_run, mock_which):
        """CryptoEndpoint.ssh_audit_json is set to the JSON string from ssh-audit."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(SSH_AUDIT_JSON),
            returncode=0,
        )

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNotNone(ep.ssh_audit_json, "ssh_audit_json must be set when ssh-audit succeeds")
        parsed = json.loads(ep.ssh_audit_json)
        self.assertEqual(parsed["banner"]["raw"], "SSH-2.0-OpenSSH_8.9p1")

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run")
    def test_tls_version_not_set(self, mock_run, mock_which):
        """tls_version must NOT be set for SSH endpoints (D-06)."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(SSH_AUDIT_JSON),
            returncode=0,
        )

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNone(ep.tls_version, "tls_version must not be used for SSH data (D-06)")

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run")
    def test_cipher_suite_ssh_marker(self, mock_run, mock_which):
        """cipher_suite is set to 'SSH' as per D-06 marker."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(SSH_AUDIT_JSON),
            returncode=0,
        )

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertEqual(ep.cipher_suite, "SSH", "cipher_suite must be 'SSH' marker for SSH endpoints")

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run")
    def test_banner_stored_in_service_detail(self, mock_run, mock_which):
        """Banner from ssh-audit JSON is stored in service_detail, not tls_version."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(SSH_AUDIT_JSON),
            returncode=0,
        )

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIn("SSH-2.0-OpenSSH_8.9p1", ep.service_detail or "")

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run")
    def test_protocol_is_ssh(self, mock_run, mock_which):
        """protocol field is set to 'SSH'."""
        mock_run.return_value = MagicMock(
            stdout=json.dumps(SSH_AUDIT_JSON),
            returncode=0,
        )

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertEqual(ep.protocol, "SSH")


class TestScanSshOneWithoutSshAudit(unittest.TestCase):
    """ssh-audit is NOT available — fallback to socket banner grab."""

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value=None)
    @patch("qcscan.scanner.ssh_scanner.socket.create_connection")
    def test_banner_fallback_works(self, mock_conn, mock_which):
        """When ssh-audit is absent, banner is captured via socket."""
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9p1\r\n"
        mock_conn.return_value = mock_sock

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNone(ep.ssh_audit_json, "ssh_audit_json must be None when ssh-audit unavailable")
        # Banner should be stored somewhere (service_detail)
        self.assertIsNotNone(ep.service_detail)

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value=None)
    @patch("qcscan.scanner.ssh_scanner.socket.create_connection")
    def test_tls_version_not_set_in_fallback(self, mock_conn, mock_which):
        """tls_version is NOT set even in fallback mode (D-06)."""
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9p1\r\n"
        mock_conn.return_value = mock_sock

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNone(ep.tls_version, "tls_version must not be used for SSH data (D-06)")


class TestScanSshOneSshAuditTimeout(unittest.TestCase):
    """ssh-audit subprocess raises TimeoutExpired — fallback to banner."""

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh-audit", timeout=10))
    @patch("qcscan.scanner.ssh_scanner.socket.create_connection")
    def test_no_crash_on_timeout(self, mock_conn, mock_run, mock_which):
        """TimeoutExpired from ssh-audit does not crash; fallback runs cleanly."""
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9p1\r\n"
        mock_conn.return_value = mock_sock

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        # Should have fallen back — no exception propagated
        self.assertIsInstance(ep, CryptoEndpoint)
        self.assertIsNone(ep.ssh_audit_json)

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh-audit", timeout=10))
    @patch("qcscan.scanner.ssh_scanner.socket.create_connection")
    def test_tls_version_not_set_on_timeout(self, mock_conn, mock_run, mock_which):
        """tls_version is NOT set even after ssh-audit timeout + banner fallback."""
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9p1\r\n"
        mock_conn.return_value = mock_sock

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNone(ep.tls_version)


class TestScanSshOneDoesNotSetTlsVersion(unittest.TestCase):
    """Comprehensive check: tls_version is never set by scan_ssh_one."""

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value="/usr/local/bin/ssh-audit")
    @patch("qcscan.scanner.ssh_scanner.subprocess.run")
    def test_tls_version_never_set(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(stdout=json.dumps(SSH_AUDIT_JSON), returncode=0)

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNone(ep.tls_version)

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value=None)
    @patch("qcscan.scanner.ssh_scanner.socket.create_connection")
    def test_tls_version_never_set_fallback(self, mock_conn, mock_which):
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9p1\r\n"
        mock_conn.return_value = mock_sock

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertIsNone(ep.tls_version)


class TestScanSshOneCipherSuiteSsh(unittest.TestCase):
    """cipher_suite is always 'SSH' for SSH endpoints (D-06)."""

    @patch("qcscan.scanner.ssh_scanner.shutil.which", return_value=None)
    @patch("qcscan.scanner.ssh_scanner.socket.create_connection")
    def test_cipher_suite_ssh_in_fallback(self, mock_conn, mock_which):
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.recv.return_value = b"SSH-2.0-OpenSSH_8.9p1\r\n"
        mock_conn.return_value = mock_sock

        ep = scan_ssh_one("10.0.0.1", 22, timeout=5)

        self.assertEqual(ep.cipher_suite, "SSH")


# ---------------------------------------------------------------------------
# scan_ssh_targets tests
# ---------------------------------------------------------------------------


class TestScanSshTargetsUsesThreadPool(unittest.TestCase):
    """scan_ssh_targets uses ThreadPoolExecutor and returns all results."""

    def test_all_results_returned(self):
        """All 5 targets return a CryptoEndpoint."""
        targets = [("10.0.0." + str(i), 22) for i in range(1, 6)]
        cfg = _make_cfg(concurrency=4, timeout=5)

        with patch("qcscan.scanner.ssh_scanner.scan_ssh_one") as mock_one:
            mock_one.side_effect = lambda host, port, timeout, logger=None: CryptoEndpoint(
                host=host, port=port, protocol="SSH", cipher_suite="SSH"
            )

            results = scan_ssh_targets(cfg, targets)

        self.assertEqual(len(results), 5, "All 5 targets must produce a result")

    def test_results_are_crypto_endpoints(self):
        """Each result is a CryptoEndpoint instance."""
        targets = [("10.0.0.1", 22), ("10.0.0.2", 22)]
        cfg = _make_cfg()

        with patch("qcscan.scanner.ssh_scanner.scan_ssh_one") as mock_one:
            mock_one.side_effect = lambda host, port, timeout, logger=None: CryptoEndpoint(
                host=host, port=port, protocol="SSH", cipher_suite="SSH"
            )

            results = scan_ssh_targets(cfg, targets)

        for ep in results:
            self.assertIsInstance(ep, CryptoEndpoint)

    def test_progress_cb_called_per_target(self):
        """progress_cb is called once per completed target."""
        targets = [("10.0.0." + str(i), 22) for i in range(1, 4)]
        cfg = _make_cfg()
        progress_calls = []

        with patch("qcscan.scanner.ssh_scanner.scan_ssh_one") as mock_one:
            mock_one.side_effect = lambda host, port, timeout, logger=None: CryptoEndpoint(
                host=host, port=port, protocol="SSH", cipher_suite="SSH"
            )

            scan_ssh_targets(cfg, targets, progress_cb=lambda n: progress_calls.append(n))

        self.assertEqual(len(progress_calls), 3, "progress_cb must be called once per target")

    def test_empty_targets_returns_empty_list(self):
        """Empty target list returns empty results without error."""
        cfg = _make_cfg()
        results = scan_ssh_targets(cfg, [])
        self.assertEqual(results, [])

    def test_threadpoolexecutor_used(self):
        """ThreadPoolExecutor is actually used (not a sequential loop)."""
        targets = [("10.0.0.1", 22), ("10.0.0.2", 22)]
        cfg = _make_cfg(concurrency=2)

        with patch("qcscan.scanner.ssh_scanner.ThreadPoolExecutor") as mock_executor_cls:
            # Set up the mock context manager
            mock_executor = MagicMock()
            mock_executor.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor.__exit__ = MagicMock(return_value=False)
            mock_executor_cls.return_value = mock_executor

            mock_future1 = MagicMock()
            mock_future1.result.return_value = CryptoEndpoint(host="10.0.0.1", port=22, protocol="SSH", cipher_suite="SSH")
            mock_future2 = MagicMock()
            mock_future2.result.return_value = CryptoEndpoint(host="10.0.0.2", port=22, protocol="SSH", cipher_suite="SSH")

            mock_executor.submit.side_effect = [mock_future1, mock_future2]

            with patch("qcscan.scanner.ssh_scanner.as_completed", return_value=[mock_future1, mock_future2]):
                scan_ssh_targets(cfg, targets)

            mock_executor_cls.assert_called_once_with(max_workers=2)


if __name__ == "__main__":
    unittest.main()

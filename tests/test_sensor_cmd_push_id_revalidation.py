"""RED test for AUDIT-10: CLI sensor-push sensor_id shape re-validation.

Asserts that quirk.cli.sensor_cmd._cmd_push exits non-zero (or raises SystemExit)
WITHOUT reaching the network (_do_push sentinel) when sensor.yaml contains a
malformed sensor_id (path-traversal string instead of a UUID).

TODAY (current main): _cmd_push reads sensor_id but does NOT apply _UUID_RE on the
push network path (the guard exists only in _cmd_export_results at ~L743-745, CR-02).
As a result, _cmd_push will proceed past the sensor_id check and call _do_push with
the bad id — so the sentinel-not-called assertion FAILS.  This is the RED signal.

WAVE 2 (plan 131-02) adds the _UUID_RE guard to _cmd_push before _do_push, making
this test GREEN.

pytest -q tests/test_sensor_cmd_push_id_revalidation.py
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_sensor_yaml(tmp_path: Path, sensor_id: str) -> Path:
    """Write a minimal sensor.yaml with the given sensor_id to tmp_path."""
    config = textwrap.dedent(f"""\
        sensor_id: "{sensor_id}"
        console_url: "https://console.example.com"
        hmac_key: "{'a' * 64}"
        console_api_token: "tok_test_abc123"
        segment: "dmz"
        scan_config: "config.yaml"
        allow_internal_console: false
        sensor_version: "5.8.0"
    """)
    yaml_path = tmp_path / "sensor.yaml"
    yaml_path.write_text(config, encoding="utf-8")
    return yaml_path


def _build_args(sensor_yaml: Path, scan_config: str = "config.yaml") -> argparse.Namespace:
    """Return a minimal argparse.Namespace that _cmd_push expects."""
    return argparse.Namespace(
        config=str(sensor_yaml),
        scan_config=scan_config,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSensorPushSensorIdRevalidation:
    """AUDIT-10: _cmd_push must reject a malformed sensor_id before network contact."""

    def test_path_traversal_sensor_id_rejected_before_network(self, tmp_path):
        """AUDIT-10 RED: sensor_id with path-traversal chars must exit non-zero WITHOUT
        invoking _do_push (no network contact).

        TODAY this test FAILS because _cmd_push does not validate sensor_id shape on
        the push path — with console_url SSRF check stubbed out, it will fall through
        to _run_local_scan and then call _do_push with the bad id, triggering the
        sentinel and causing the "not sentinel_called" assertion to fail.

        Implementation note: validate_external_url is stubbed to return OK so that
        the unrelated console_url SSRF guard does not interfere with testing the
        sensor_id guard specifically.
        """
        yaml_path = _write_sensor_yaml(tmp_path, sensor_id="../etc/evil")
        args = _build_args(yaml_path)

        sentinel_called = []

        def _do_push_sentinel(client, url, headers, content):
            sentinel_called.append(True)
            raise AssertionError("_do_push must NOT be reached for a malformed sensor_id")

        def _run_local_scan_noop(scan_config, output_dir, allow_internal=False):
            return 0

        # Stub ValidationResult so the unrelated console_url SSRF check passes
        class _OkResult:
            ok = True
            allowed = True
            reason = "stubbed"

        with patch("quirk.cli.sensor_cmd._do_push", side_effect=_do_push_sentinel), \
             patch("quirk.cli.sensor_cmd._run_local_scan", side_effect=_run_local_scan_noop), \
             patch("quirk.cli.sensor_cmd.validate_external_url", return_value=_OkResult()):
            # _cmd_push calls sys.exit() on early-rejection paths
            with pytest.raises(SystemExit) as exc_info:
                from quirk.cli.sensor_cmd import _cmd_push
                _cmd_push(args)

        # Assertions that define the GREEN contract:
        # 1) Exited non-zero (rejected by sensor_id guard)
        assert exc_info.value.code != 0, (
            f"Expected non-zero exit for malformed sensor_id, got: {exc_info.value.code}"
        )
        # 2) Network was never contacted (guard fired BEFORE _do_push)
        assert not sentinel_called, (
            "_do_push was called despite malformed sensor_id — "
            "AUDIT-10 guard is missing from _cmd_push push path"
        )

    def test_slash_in_sensor_id_rejected_before_network(self, tmp_path):
        """AUDIT-10 RED: sensor_id containing a slash is rejected without network contact."""
        yaml_path = _write_sensor_yaml(tmp_path, sensor_id="evil/path")
        args = _build_args(yaml_path)

        sentinel_called = []

        def _do_push_sentinel(client, url, headers, content):
            sentinel_called.append(True)
            raise AssertionError("_do_push must NOT be reached for malformed sensor_id")

        def _run_local_scan_noop(scan_config, output_dir, allow_internal=False):
            return 0

        class _OkResult:
            ok = True
            allowed = True
            reason = "stubbed"

        with patch("quirk.cli.sensor_cmd._do_push", side_effect=_do_push_sentinel), \
             patch("quirk.cli.sensor_cmd._run_local_scan", side_effect=_run_local_scan_noop), \
             patch("quirk.cli.sensor_cmd.validate_external_url", return_value=_OkResult()):
            with pytest.raises(SystemExit) as exc_info:
                from quirk.cli.sensor_cmd import _cmd_push
                _cmd_push(args)

        assert exc_info.value.code != 0, (
            f"Expected non-zero exit for slash sensor_id, got: {exc_info.value.code}"
        )
        assert not sentinel_called, (
            "_do_push was called despite slash in sensor_id"
        )

    def test_valid_uuid_sensor_id_reaches_push(self, tmp_path):
        """AUDIT-10 positive case: a valid UUID sensor_id passes the sensor_id guard.

        The test verifies that a conforming sensor_id does NOT trigger the early
        exit added by AUDIT-10 (guard is UUID-shape-only).  We mock validate_external_url
        to return a passing result (so the unrelated SSRF/console_url guard does not
        interfere) and mock _run_local_scan so no subprocess is spawned.  The key
        invariant is that _run_local_scan is reached — proving the valid UUID was not
        rejected by the sensor_id shape guard.

        Note: This positive case is expected to PASS both before and after AUDIT-10.
        """
        import uuid as _uuid
        valid_uuid = str(_uuid.uuid4())
        yaml_path = _write_sensor_yaml(tmp_path, sensor_id=valid_uuid)
        args = _build_args(yaml_path)

        scan_reached = []

        def _run_local_scan_sentinel(scan_config, output_dir, allow_internal=False):
            scan_reached.append(True)
            return 0

        def _do_push_sentinel(client, url, headers, content):
            raise RuntimeError("stub: network not available in test")

        # Stub ValidationResult so the unrelated console_url SSRF check passes
        class _OkResult:
            ok = True
            allowed = True
            reason = "stubbed"

        with patch("quirk.cli.sensor_cmd._run_local_scan", side_effect=_run_local_scan_sentinel), \
             patch("quirk.cli.sensor_cmd._do_push", side_effect=_do_push_sentinel), \
             patch("quirk.cli.sensor_cmd.validate_external_url", return_value=_OkResult()):
            with pytest.raises(SystemExit):
                from quirk.cli.sensor_cmd import _cmd_push
                _cmd_push(args)

        # The key assertion: scan was reached, meaning the UUID passed the guard.
        assert scan_reached, (
            "Valid UUID sensor_id was incorrectly rejected before _run_local_scan"
        )

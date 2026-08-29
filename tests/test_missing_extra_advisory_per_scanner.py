"""Phase 173 D-03/D-04 (SCOPE-03): per-scanner missing-extra advisory tests.

`tests/test_scan_robustness.py::test_missing_extra_advisory_stderr` and
`::test_missing_extra_exit_code_zero` do an `inspect.getsource(run_scan)` string
grep for "INSTALL-001" / "missing_extra" appearing ANYWHERE in the file. They
stay green even if broker/smime/adcs never fire their gate, as long as some
OTHER scanner's advisory strings are present elsewhere in run_scan.py. They are
not coverage of this defect and are explicitly left byte-untouched here
(supersede by addition, not replacement) -- see 173-03-SUMMARY.md for the
falsification proof recording the exact evidence.

Phase 173 WR-02: `_broker_missing_extra` / `_smime_missing_extra` /
`_adcs_missing_extra` are extracted, importable, module-level predicates in
run_scan.py (they no longer live only inline inside `main()`'s closure), so
these tests import and exercise the REAL gates directly rather than a
hand-mirrored copy of the conditional. A future divergence between the real
gate and what these tests expect will show up as this file failing, not as a
silently-stale mirror.

Each test monkeypatches the scanner modules' `_AVAILABLE` flags rather than
uninstalling real packages, and asserts BOTH halves of the documented signal:
the QRK-INSTALL-001 stderr line (via capsys) AND an appended `CryptoEndpoint`
row with `scan_error_category == "missing_extra"` and the correct `host`.
"""
from __future__ import annotations

from run_scan import (
    _broker_missing_extra as _broker_gate,
    _smime_missing_extra as _smime_gate,
    _adcs_missing_extra as _adcs_gate,
)
from quirk.scanner import broker_scanner, smime_scanner, adcs_scanner


def _assert_both_halves(capsys, error_endpoints, host: str) -> None:
    captured = capsys.readouterr()
    assert "INSTALL-001" in captured.err
    matching = [ep for ep in error_endpoints if ep.host == host]
    assert len(matching) == 1
    assert matching[0].scan_error_category == "missing_extra"
    assert matching[0].protocol == "ADVISORY"


# ---------------------------------------------------------------------------
# Broker -- three sub-cases, each individually driving the regression
# ---------------------------------------------------------------------------
def test_broker_sslyze_missing_emits_both_halves(monkeypatch, capsys):
    """Fails if broker's gate stops consulting SSLYZE_AVAILABLE."""
    monkeypatch.setattr(broker_scanner, "SSLYZE_AVAILABLE", False)
    monkeypatch.setattr(broker_scanner, "KAFKA_AVAILABLE", True)
    monkeypatch.setattr(broker_scanner, "REDIS_AVAILABLE", True)
    error_endpoints: list = []
    skip = _broker_gate(True, error_endpoints)
    assert skip is True
    _assert_both_halves(capsys, error_endpoints, "broker_scanner")


def test_broker_kafka_missing_emits_both_halves(monkeypatch, capsys):
    """Fails if broker's gate reverts to checking only SSLYZE_AVAILABLE (kafka
    absence would then be silently ignored, exactly the pre-173-03 defect)."""
    monkeypatch.setattr(broker_scanner, "SSLYZE_AVAILABLE", True)
    monkeypatch.setattr(broker_scanner, "KAFKA_AVAILABLE", False)
    monkeypatch.setattr(broker_scanner, "REDIS_AVAILABLE", True)
    error_endpoints: list = []
    skip = _broker_gate(True, error_endpoints)
    assert skip is True
    _assert_both_halves(capsys, error_endpoints, "broker_scanner")


def test_broker_redis_missing_emits_both_halves(monkeypatch, capsys):
    """Fails if broker's gate reverts to checking only SSLYZE_AVAILABLE (redis
    absence would then be silently ignored, exactly the pre-173-03 defect)."""
    monkeypatch.setattr(broker_scanner, "SSLYZE_AVAILABLE", True)
    monkeypatch.setattr(broker_scanner, "KAFKA_AVAILABLE", True)
    monkeypatch.setattr(broker_scanner, "REDIS_AVAILABLE", False)
    error_endpoints: list = []
    skip = _broker_gate(True, error_endpoints)
    assert skip is True
    _assert_both_halves(capsys, error_endpoints, "broker_scanner")


def test_broker_all_three_missing_emits_exactly_one_row(monkeypatch, capsys):
    """Fails if the gate emits more than one advisory row when multiple flags
    are missing simultaneously (Phase 173 D-03 decision record: one row per
    scanner invocation, never per missing module)."""
    monkeypatch.setattr(broker_scanner, "SSLYZE_AVAILABLE", False)
    monkeypatch.setattr(broker_scanner, "KAFKA_AVAILABLE", False)
    monkeypatch.setattr(broker_scanner, "REDIS_AVAILABLE", False)
    error_endpoints: list = []
    skip = _broker_gate(True, error_endpoints)
    assert skip is True
    captured = capsys.readouterr()
    assert captured.err.count("INSTALL-001") == 1
    matching = [ep for ep in error_endpoints if ep.host == "broker_scanner"]
    assert len(matching) == 1


def test_broker_all_available_emits_no_advisory(monkeypatch, capsys):
    """Fails if the gate fires an advisory even when all three deps are
    present -- a false positive would corrupt the report with a bogus row."""
    monkeypatch.setattr(broker_scanner, "SSLYZE_AVAILABLE", True)
    monkeypatch.setattr(broker_scanner, "KAFKA_AVAILABLE", True)
    monkeypatch.setattr(broker_scanner, "REDIS_AVAILABLE", True)
    error_endpoints: list = []
    skip = _broker_gate(True, error_endpoints)
    assert skip is False
    captured = capsys.readouterr()
    assert "INSTALL-001" not in captured.err
    assert error_endpoints == []


def test_broker_disabled_emits_no_advisory_regardless_of_flags(monkeypatch, capsys):
    """Fails if the gate advises even when enable_broker is False -- the
    connector-disabled scanners must stay silent (matches optional_extra.py's
    D-08 config-disabled contract)."""
    monkeypatch.setattr(broker_scanner, "SSLYZE_AVAILABLE", False)
    monkeypatch.setattr(broker_scanner, "KAFKA_AVAILABLE", False)
    monkeypatch.setattr(broker_scanner, "REDIS_AVAILABLE", False)
    error_endpoints: list = []
    skip = _broker_gate(False, error_endpoints)
    assert skip is True
    captured = capsys.readouterr()
    assert "INSTALL-001" not in captured.err
    assert error_endpoints == []


# ---------------------------------------------------------------------------
# smime / adcs
# ---------------------------------------------------------------------------
def test_smime_ldap3_missing_emits_both_halves(monkeypatch, capsys):
    """Fails if smime's advisory call is removed -- pre-173-03 smime only
    logged a warning with zero machine-readable/stderr signal."""
    monkeypatch.setattr(smime_scanner, "LDAP3_AVAILABLE", False)
    error_endpoints: list = []
    skip = _smime_gate(True, error_endpoints)
    assert skip is True
    _assert_both_halves(capsys, error_endpoints, "smime_scanner")


def test_smime_ldap3_available_emits_no_advisory(monkeypatch, capsys):
    monkeypatch.setattr(smime_scanner, "LDAP3_AVAILABLE", True)
    error_endpoints: list = []
    skip = _smime_gate(True, error_endpoints)
    assert skip is False
    captured = capsys.readouterr()
    assert "INSTALL-001" not in captured.err
    assert error_endpoints == []


def test_smime_disabled_emits_no_advisory_regardless_of_flag(monkeypatch, capsys):
    monkeypatch.setattr(smime_scanner, "LDAP3_AVAILABLE", False)
    error_endpoints: list = []
    skip = _smime_gate(False, error_endpoints)
    assert skip is True
    captured = capsys.readouterr()
    assert "INSTALL-001" not in captured.err
    assert error_endpoints == []


def test_adcs_ldap3_missing_emits_both_halves(monkeypatch, capsys):
    """Fails if adcs's advisory call is removed -- pre-173-03 adcs only
    logged a warning with zero machine-readable/stderr signal."""
    monkeypatch.setattr(adcs_scanner, "LDAP3_AVAILABLE", False)
    error_endpoints: list = []
    skip = _adcs_gate(True, error_endpoints)
    assert skip is True
    _assert_both_halves(capsys, error_endpoints, "adcs_scanner")


def test_adcs_ldap3_available_emits_no_advisory(monkeypatch, capsys):
    monkeypatch.setattr(adcs_scanner, "LDAP3_AVAILABLE", True)
    error_endpoints: list = []
    skip = _adcs_gate(True, error_endpoints)
    assert skip is False
    captured = capsys.readouterr()
    assert "INSTALL-001" not in captured.err
    assert error_endpoints == []


def test_adcs_disabled_emits_no_advisory_regardless_of_flag(monkeypatch, capsys):
    monkeypatch.setattr(adcs_scanner, "LDAP3_AVAILABLE", False)
    error_endpoints: list = []
    skip = _adcs_gate(False, error_endpoints)
    assert skip is True
    captured = capsys.readouterr()
    assert "INSTALL-001" not in captured.err
    assert error_endpoints == []

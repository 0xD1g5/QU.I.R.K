"""RED contract tests for AUDIT-04: DOCX renderer must log warnings with exc_info on bad-data injection.

AUDIT-04 success criterion: When a guarded ``except`` block in ``docx_renderer`` catches an
exception during rendering (e.g., from a style assignment error), it must emit a WARNING-level
log record with ``exc_info=True`` rather than swallowing it silently with bare ``pass``.

Currently all guarded except blocks in quirk/reports/docx_renderer.py use bare ``pass``
(at lines ~44-45, ~65-66, ~153-154), meaning exceptions are completely silent — no logging,
no diagnostic information for operators.

These tests FAIL against the current codebase (v5.7) because:
- _set_table_style swallows (KeyError, Exception) with no log record.
- No WARNING log record is emitted when the guarded exception is caught.

Wave 2 Plan 130-02 makes them pass.
"""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_minimal_cfg():
    """Minimal cfg object matching the test pattern from test_docx_report.py."""
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="TestOrg",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
            logo_path=None,
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_docx_exc"),
    )


def _make_exploding_table():
    """Return a table mock whose .style setter raises KeyError (the documented error case)."""
    tbl = MagicMock()
    type(tbl).style = PropertyMock(
        side_effect=KeyError("Table Grid"),
    )
    return tbl


# ---------------------------------------------------------------------------
# Test A: guarded except emits WARNING with exc_info (RED — currently fails)
# ---------------------------------------------------------------------------

class TestDocxExceptionLogging:
    """AUDIT-04: guarded except blocks in docx_renderer must log WARNING with exc_info."""

    def test_set_table_style_exception_emits_warning_with_exc_info(
        self, tmp_path, caplog
    ) -> None:
        """When tbl.style assignment raises KeyError, a WARNING is logged with exc_info (AUDIT-04).

        Injects a table mock whose ``.style`` setter raises a KeyError (the documented
        failure mode from the Research note in _set_table_style's docstring). Asserts:
        1. A WARNING-level log record is captured from the docx_renderer logger.
        2. The record has exc_info populated (not None) — logged with exc_info=True.

        Currently FAILS because _set_table_style swallows the exception with bare ``pass``,
        producing zero WARNING log records.
        """
        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "exc_test.docx")

        exploding_table = _make_exploding_table()

        with caplog.at_level(logging.WARNING, logger="quirk.reports.docx_renderer"):
            # Patch doc.add_table so every table returned triggers the KeyError in _set_table_style
            with patch("docx.document.Document.add_table", return_value=exploding_table):
                # render_docx_report calls _set_table_style(tbl) for every table;
                # each call hits `tbl.style = style_name` which now raises KeyError.
                # The except block currently swallows with `pass` — AUDIT-04 requires logging.
                result = render_docx_report(
                    path=path,
                    cfg=_make_minimal_cfg(),
                    findings=[],
                )

        # AUDIT-04 assertion: at least one WARNING-level record must exist
        warning_records = [
            r for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert len(warning_records) >= 1, (
            f"AUDIT-04 VIOLATED: No WARNING log record was emitted when tbl.style raised KeyError. "
            f"Current code in _set_table_style swallows the exception with bare 'pass'. "
            f"Post-fix, the renderer must call logger.warning(..., exc_info=True) so operators "
            f"can diagnose rendering failures. "
            f"Log records captured: {[r.getMessage() for r in caplog.records]}"
        )

        # AUDIT-04 assertion: the WARNING must carry exc_info
        exc_info_records = [
            r for r in warning_records if r.exc_info is not None
        ]
        assert len(exc_info_records) >= 1, (
            f"AUDIT-04 VIOLATED: WARNING was emitted but without exc_info. "
            f"Found {len(warning_records)} WARNING records, none with exc_info set. "
            f"The logger call must use exc_info=True to capture the stack trace."
        )

    def test_set_table_style_directly_emits_warning_with_exc_info(
        self, caplog
    ) -> None:
        """Directly calling _set_table_style with a bad table emits WARNING with exc_info (AUDIT-04).

        This exercises the except block in _set_table_style in isolation (no render cycle).
        The table mock's .style setter raises KeyError. Post-fix code must log WARNING;
        current code silently passes.
        """
        from quirk.reports.docx_renderer import _set_table_style

        exploding_table = _make_exploding_table()

        with caplog.at_level(logging.WARNING, logger="quirk.reports.docx_renderer"):
            # Call the function directly — current code: except (KeyError, Exception): pass
            # Post-fix code: except (KeyError, Exception): logger.warning(..., exc_info=True)
            _set_table_style(exploding_table, "Table Grid")

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1, (
            f"AUDIT-04 VIOLATED: _set_table_style swallowed a KeyError with bare 'pass'. "
            f"Post-fix, it must call logger.warning(..., exc_info=True). "
            f"Log records captured: {[r.getMessage() for r in caplog.records]}"
        )
        exc_info_records = [r for r in warning_records if r.exc_info is not None]
        assert len(exc_info_records) >= 1, (
            "AUDIT-04 VIOLATED: WARNING emitted without exc_info=True."
        )


# ---------------------------------------------------------------------------
# Test B: normal data does NOT emit a warning (regression guard)
# ---------------------------------------------------------------------------

class TestDocxNoSpuriousWarning:
    """Normal docx renders must not emit WARNING records (AUDIT-04 regression guard)."""

    def test_normal_render_no_warning(self, tmp_path, caplog) -> None:
        """A successful render with no findings emits no WARNING-level records."""
        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "normal.docx")

        with caplog.at_level(logging.WARNING, logger="quirk.reports.docx_renderer"):
            render_docx_report(
                path=path,
                cfg=_make_minimal_cfg(),
                findings=[],
            )

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 0, (
            f"Spurious WARNING records emitted during a clean render: "
            f"{[r.getMessage() for r in warning_records]}. "
            "WARNING logging must only fire when an exception is actually caught."
        )

    def test_normal_render_with_findings_no_warning(self, tmp_path, caplog) -> None:
        """A successful render with typical findings produces no WARNING records."""
        from quirk.reports.docx_renderer import render_docx_report

        path = str(tmp_path / "with_findings.docx")
        findings = [
            {
                "severity": "HIGH",
                "title": "Test Finding",
                "host": "10.0.0.1",
                "port": "443",
                "description": "Test description",
                "recommendation": "Test recommendation",
                "quantum_risk": "High PQC risk",
                "category": "tls",
            }
        ]

        with caplog.at_level(logging.WARNING, logger="quirk.reports.docx_renderer"):
            render_docx_report(
                path=path,
                cfg=_make_minimal_cfg(),
                findings=findings,
            )

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 0, (
            f"Spurious WARNING records during render with findings: "
            f"{[r.getMessage() for r in warning_records]}"
        )

"""Phase 7 — BRAND-02: rich summary table in write_reports()."""
import inspect
import ast


def test_scan_summary_uses_rich():
    """write_reports() must import and use rich Console/Table for the scan summary."""
    import quirk.reports.writer as writer_mod
    source = inspect.getsource(writer_mod)
    assert "from rich" in source or "import rich" in source, (
        "writer.py must import rich — plain print() calls should be replaced"
    )
    assert "Console" in source or "Table" in source, (
        "writer.py must use rich Console or Table for the scan summary block"
    )


def test_no_bare_summary_prints():
    """The '✅ Wrote reports:' block must be replaced — no bare print() for summary output."""
    import quirk.reports.writer as writer_mod
    source = inspect.getsource(writer_mod)
    # The old emoji-print pattern should be gone
    assert 'print("\\n✅ Wrote reports:' not in source and "print('\\n✅ Wrote reports:" not in source, (
        "Old bare print() summary block still present in writer.py — must be replaced by rich"
    )

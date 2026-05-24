"""Phase 100 — FMT-01 / D-01: AssessmentCfg.logo_path backward-compat tests."""


def test_assessment_cfg_logo_path():
    """AssessmentCfg accepts logo_path as an optional kwarg without raising."""
    from quirk.config import AssessmentCfg
    cfg = AssessmentCfg(
        name="Test Org",
        data_classification="CONFIDENTIAL",
        report_owner="Security Team",
        timezone="UTC",
        logo_path="/tmp/x.png",
    )
    assert cfg.logo_path == "/tmp/x.png"


def test_backward_compat_config():
    """AssessmentCfg constructed without logo_path must not raise; .logo_path is None."""
    from quirk.config import AssessmentCfg
    cfg = AssessmentCfg(
        name="Test Org",
        data_classification="CONFIDENTIAL",
        report_owner="Security Team",
        timezone="UTC",
    )
    assert cfg.logo_path is None

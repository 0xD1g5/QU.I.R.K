"""Deprecated alias for quirk.engine.findings_evaluator. Removed in v5.0."""
from quirk.engine.findings_evaluator import *  # noqa: F401, F403
from quirk.engine.findings_evaluator import (  # noqa: F401
    _SEVERITY_RANK,
    _build_finding,
    _chain_verified,
    _dedupe_findings,
    _normalize_finding,
    _postprocess_findings,
)

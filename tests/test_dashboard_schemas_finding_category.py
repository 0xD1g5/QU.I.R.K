"""Phase 45 / Plan 03 / Task 4 — FindingItem.category field (Q2)."""
from __future__ import annotations

from quirk.dashboard.api.schemas import FindingItem


def _dump(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()  # pydantic v1 fallback


def test_finding_item_default_category_is_none():
    f = FindingItem(host="x", port=0, severity="INFO", title="y")
    assert f.category is None


def test_finding_item_accepts_explicit_category():
    f = FindingItem(
        host="x", port=0, severity="INFO", title="y", category="coverage_gap"
    )
    dumped = _dump(f)
    assert dumped.get("category") == "coverage_gap"

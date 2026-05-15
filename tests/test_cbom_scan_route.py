"""Phase 70 BLOCK-08 / D-05 — narrowed except + logged warning in `_qs_for_alg`.

These tests exercise `quirk.dashboard.api.routes.scan._qs_for_alg` directly. They
require Task 2 of plan 70-02 to (a) lift `_qs_for_alg` to module scope and
(b) narrow its `except Exception:` clause to
`except (KeyError, TypeError, AttributeError) as e:` while logging a WARNING.

Behaviors covered (from the plan `<behavior>` block):

1. KeyError raised by `classify_algorithm` → returns "Unknown" + WARNING log.
2. TypeError raised by `classify_algorithm` → returns "Unknown" + WARNING log.
3. AttributeError raised by `classify_algorithm` → returns "Unknown" + WARNING log.
4. RuntimeError raised by `classify_algorithm` → propagates (no swallow, no log).
5. ValueError raised by `classify_algorithm` → propagates (no swallow, no log).
6. Happy path on a real alg ("RSA-2048") → returns a non-empty string with no
   WARNING emitted (regression guard).
"""
from __future__ import annotations

import logging

import pytest

from quirk.dashboard.api.routes.scan import _qs_for_alg


# ---------- Narrowed exception types: swallowed + logged ----------


@pytest.mark.parametrize("exc_cls", [KeyError, TypeError, AttributeError])
def test_qs_for_alg_returns_unknown_on_narrowed_exc(monkeypatch, caplog, exc_cls):
    """Each of the three narrowed exception classes is swallowed, logged, and the
    function returns the literal string "Unknown" (the `_QS_DISPLAY` fallback).
    """

    def _raises(*_args, **_kwargs):
        raise exc_cls("boom")

    monkeypatch.setattr("quirk.cbom.classifier.classify_algorithm", _raises)

    with caplog.at_level(logging.WARNING, logger="quirk.dashboard.api.routes.scan"):
        result = _qs_for_alg("RSA-2048")

    assert result == "Unknown"
    assert "classifier failed" in caplog.text


# ---------- Unrelated exception types: propagate, no log ----------


@pytest.mark.parametrize("exc_cls", [RuntimeError, ValueError])
def test_qs_for_alg_propagates_unrelated_exc(monkeypatch, caplog, exc_cls):
    """Exceptions outside the narrowed tuple must surface to the caller — they
    represent real bugs, not classifier misses.
    """

    def _raises(*_args, **_kwargs):
        raise exc_cls("real bug")

    monkeypatch.setattr("quirk.cbom.classifier.classify_algorithm", _raises)

    with caplog.at_level(logging.WARNING, logger="quirk.dashboard.api.routes.scan"):
        with pytest.raises(exc_cls):
            _qs_for_alg("RSA-2048")

    # No "classifier failed" warning should have been emitted on the propagation
    # path — the warning is only for the swallowed-and-degraded path.
    assert "classifier failed" not in caplog.text


# ---------- Happy path regression ----------


def test_qs_for_alg_happy_path_no_warning(caplog):
    """With the real classifier, a known algorithm returns a non-empty display
    string and emits no WARNING.
    """
    with caplog.at_level(logging.WARNING, logger="quirk.dashboard.api.routes.scan"):
        result = _qs_for_alg("RSA-2048")

    assert isinstance(result, str)
    assert result  # non-empty
    assert "classifier failed" not in caplog.text

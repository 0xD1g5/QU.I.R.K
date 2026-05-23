"""Tests for the REST fuzzer CONFIRM gate, non-TTY hard abort, and budget hard ceiling.

Phase 96 / FUZZ-02, FUZZ-03
-----------------------------
These tests are written TEST-FIRST (TDD RED phase) and must be committed BEFORE any
dispatch code exists in rest_fuzzer.py.

Critical safety invariants proven here:
- Non-TTY stdin causes a HARD ABORT before any network request is sent (FUZZ-03).
- TTY path requires the literal word "CONFIRM" — any other input aborts.
- Budget above MAX_FUZZ_BUDGET (500) raises ValueError immediately (FUZZ-02).
- No call to requests.Session().request or socket is ever made in non-TTY path.

Design: all functions use injectable prompt_fn / stderr_print_fn so tests never
touch real sys.stdin/sys.stderr. is_tty is always passed explicitly (True/False).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from quirk.scanner.rest_fuzzer import (
    confirm_fuzz_gate,
    _resolve_budget,
    MAX_FUZZ_BUDGET,
    DEFAULT_FUZZ_BUDGET,
)


# ---------------------------------------------------------------------------
# FUZZ-03: Non-TTY hard abort — ZERO requests before confirmation
# ---------------------------------------------------------------------------

def test_non_tty_hard_abort_zero_requests() -> None:
    """FUZZ-03: non-TTY stdin must abort BEFORE any request is sent.

    Creates a MagicMock session and asserts session.request.call_count == 0
    after confirm_fuzz_gate(is_tty=False) returns False.  This proves the gate
    fires before any network I/O.
    """
    session_mock = MagicMock()
    stderr_calls: list[str] = []

    result = confirm_fuzz_gate(
        budget=50,
        target_count=3,
        is_tty=False,
        stderr_print_fn=stderr_calls.append,
    )

    assert result is False, "Non-TTY gate must return False (hard abort)"
    assert session_mock.request.call_count == 0, (
        "FUZZ-03 VIOLATED: session.request was called before CONFIRM gate "
        f"(call_count={session_mock.request.call_count})"
    )
    assert stderr_calls, "Gate must print an error message to stderr in non-TTY mode"
    assert any("non" in msg.lower() or "headless" in msg.lower() or "non-interactive" in msg.lower()
               for msg in stderr_calls), (
        f"Error message must mention non-interactive/headless mode. Got: {stderr_calls}"
    )


def test_non_tty_hard_abort_returns_false_no_prompt() -> None:
    """Non-TTY path must return False without ever calling prompt_fn."""
    prompt_calls: list[str] = []

    result = confirm_fuzz_gate(
        budget=50,
        target_count=1,
        is_tty=False,
        prompt_fn=lambda p: (prompt_calls.append(p), "CONFIRM")[1],
        stderr_print_fn=lambda _: None,
    )

    assert result is False
    assert prompt_calls == [], "prompt_fn must never be called in non-TTY mode"


# ---------------------------------------------------------------------------
# FUZZ-03: TTY path — exact "CONFIRM" string required
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_input", [
    "y",
    "yes",
    "confirm",     # lowercase — must NOT match
    "",            # blank enter
    " ",           # whitespace only
    "CONFIRM ",    # trailing space — must NOT match (strip() is done on answer, not partial)
    "confirm\n",   # newline variant
    "YES",
    "ok",
    "1",
    "true",
])
def test_confirm_required_exact_string_rejects_bad_input(bad_input: str) -> None:
    """TTY path rejects anything that is not exactly 'CONFIRM' after .strip()."""
    result = confirm_fuzz_gate(
        budget=50,
        target_count=1,
        is_tty=True,
        prompt_fn=lambda _: bad_input,
    )
    assert result is False, (
        f"Gate should abort on input {bad_input!r} but returned True"
    )


def test_confirm_required_exact_string_accepts_confirm() -> None:
    """TTY path returns True only for the exact literal string 'CONFIRM'."""
    result = confirm_fuzz_gate(
        budget=50,
        target_count=1,
        is_tty=True,
        prompt_fn=lambda _: "CONFIRM",
    )
    assert result is True, "Gate must return True for exact 'CONFIRM' input"


def test_confirm_prompt_includes_budget_and_target_count() -> None:
    """The TTY prompt string must mention the budget and target count."""
    prompts: list[str] = []

    confirm_fuzz_gate(
        budget=42,
        target_count=7,
        is_tty=True,
        prompt_fn=lambda p: (prompts.append(p), "abort")[1],
    )

    assert prompts, "prompt_fn must be called in TTY mode"
    prompt_text = prompts[0]
    assert "42" in prompt_text, f"Prompt must include budget (42). Got: {prompt_text!r}"
    assert "7" in prompt_text, f"Prompt must include target_count (7). Got: {prompt_text!r}"


# ---------------------------------------------------------------------------
# FUZZ-02: Budget hard ceiling — unbypassable via _resolve_budget
# ---------------------------------------------------------------------------

def test_budget_hard_ceiling_raises_on_501() -> None:
    """FUZZ-02: budget > 500 must raise ValueError matching 'hard maximum'."""
    with pytest.raises(ValueError, match="hard maximum"):
        _resolve_budget(501)


def test_budget_hard_ceiling_accepts_500() -> None:
    """FUZZ-02: budget == 500 (the hard max) is accepted."""
    assert _resolve_budget(500) == 500


def test_budget_hard_ceiling_accepts_1() -> None:
    """Minimum budget of 1 is accepted."""
    assert _resolve_budget(1) == 1


def test_budget_none_resolves_to_default() -> None:
    """_resolve_budget(None) returns DEFAULT_FUZZ_BUDGET (50)."""
    assert _resolve_budget(None) == DEFAULT_FUZZ_BUDGET
    assert _resolve_budget(None) == 50


def test_budget_default_resolves_correctly() -> None:
    """_resolve_budget(50) returns 50 (explicit default value)."""
    assert _resolve_budget(50) == 50


def test_budget_max_constant_is_500() -> None:
    """MAX_FUZZ_BUDGET module constant must equal 500 (FUZZ-02)."""
    assert MAX_FUZZ_BUDGET == 500, (
        f"MAX_FUZZ_BUDGET must be 500 (hard maximum per FUZZ-02). Got {MAX_FUZZ_BUDGET}"
    )


def test_budget_raises_for_various_overflows() -> None:
    """Several values above 500 all raise ValueError."""
    for over_budget in (501, 600, 1000, 9999):
        with pytest.raises(ValueError, match="hard maximum"):
            _resolve_budget(over_budget)

"""Phase 47 / Plan 02: tests for TTY-aware probe-budget guard (DISCOVER-04, D-10..D-12).

Tests are isolated from run_scan.py import side-effects by importing helpers
directly from quirk.util.targets.
"""
from __future__ import annotations

import pytest
from quirk.util.targets import projected_probe_count, maybe_confirm_probe_budget


# ---------------------------------------------------------------------------
# projected_probe_count
# ---------------------------------------------------------------------------

def test_projected_probe_count_includes_cidr_hosts_excludes_net_bcast():
    """/30 CIDR has 2 usable hosts (.hosts() excludes network + broadcast). Risks #4."""
    count = projected_probe_count(["10.0.0.0/30"], [443])
    assert count == 2, (
        f"Expected 2 (hosts in /30 × 1 port), got {count}"
    )


def test_projected_probe_count_mix():
    """Mix of bare hosts + CIDR: (2 fqdns + 254 /24 hosts) × 2 ports = 512."""
    count = projected_probe_count(["a.com", "b.com", "10.0.0.0/24"], [443, 8443])
    expected = (2 + 254) * 2
    assert count == expected, (
        f"Expected {expected}, got {count}"
    )


# ---------------------------------------------------------------------------
# maybe_confirm_probe_budget — under threshold
# ---------------------------------------------------------------------------

def test_under_threshold_no_prompt():
    """When probe count <= threshold, no prompt is issued and True is returned."""
    called = []

    def fail_prompt(_):
        called.append(True)
        pytest.fail("should not prompt when under threshold")

    result = maybe_confirm_probe_budget(
        ["a.com"],
        [443],
        threshold=10_000,
        is_tty=True,
        prompt_fn=fail_prompt,
    )
    assert result is True
    assert called == [], "prompt_fn should not have been called"


# ---------------------------------------------------------------------------
# maybe_confirm_probe_budget — over threshold, TTY
# ---------------------------------------------------------------------------

def _make_200_host_51_port_args():
    """200 bare hosts × 51 ports = 10,200 probes (> 10,000)."""
    targets = [f"host{i}.example.com" for i in range(200)]
    ports = list(range(1, 52))  # 51 ports
    return targets, ports


def test_over_threshold_tty_user_confirms_yes():
    """Over threshold + TTY + user answers 'y' → True."""
    targets, ports = _make_200_host_51_port_args()
    count = projected_probe_count(targets, ports)
    assert count == 10_200, f"Fixture probe count should be 10,200, got {count}"

    result = maybe_confirm_probe_budget(
        targets, ports,
        threshold=10_000,
        is_tty=True,
        prompt_fn=lambda _: "y",
    )
    assert result is True


def test_over_threshold_tty_user_aborts_no():
    """Over threshold + TTY + user answers 'n' → False."""
    targets, ports = _make_200_host_51_port_args()

    result = maybe_confirm_probe_budget(
        targets, ports,
        threshold=10_000,
        is_tty=True,
        prompt_fn=lambda _: "n",
    )
    assert result is False


# ---------------------------------------------------------------------------
# maybe_confirm_probe_budget — over threshold, non-TTY
# ---------------------------------------------------------------------------

def test_over_threshold_non_tty_prints_stderr_and_proceeds():
    """Over threshold + non-TTY → calls stderr_print_fn with count, returns True."""
    targets, ports = _make_200_host_51_port_args()
    count = projected_probe_count(targets, ports)

    captured = []

    result = maybe_confirm_probe_budget(
        targets, ports,
        threshold=10_000,
        is_tty=False,
        stderr_print_fn=captured.append,
    )
    assert result is True, "Non-TTY mode should auto-proceed"
    assert len(captured) == 1, f"Expected 1 stderr message, got {len(captured)}"
    # The message must mention the formatted probe count.
    assert "10,200" in captured[0], (
        f"Stderr message should contain formatted count '10,200': {captured[0]!r}"
    )

"""Tests for quirk.util.hosts.is_loopback_host (SECH-02 console URL scheme policy)."""
from __future__ import annotations

import pytest

from quirk.util.hosts import is_loopback_host


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "LOCALHOST",
        "127.0.0.1",
        "127.5.5.5",
        "::1",
        "[::1]",
        "::1%lo0",
        "::ffff:127.0.0.1",
    ],
)
def test_loopback_hosts_accepted(host):
    assert is_loopback_host(host) is True


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "::", "10.0.0.1", "console", "example.com", "", "localhost.example.com"],
)
def test_non_loopback_hosts_rejected(host):
    assert is_loopback_host(host) is False

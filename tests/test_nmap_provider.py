"""Phase 47 / Plan 02: tests for nmap_provider._default_nmap_args.

Tests lock in the D-07 requirement that --max-parallelism 100 is always
included in the default nmap argument list.
"""
from __future__ import annotations


def test_default_args_includes_max_parallelism():
    """_default_nmap_args must include '--max-parallelism' followed by '100' (D-07)."""
    from quirk.discovery.nmap_provider import _default_nmap_args

    args = _default_nmap_args("443,8443")
    # Must contain the flag and value as consecutive elements.
    assert "--max-parallelism" in args, (
        "--max-parallelism flag missing from default nmap args"
    )
    idx = args.index("--max-parallelism")
    assert args[idx + 1] == "100", (
        f"Expected '100' after --max-parallelism, got {args[idx + 1]!r}"
    )

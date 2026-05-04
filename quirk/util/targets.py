"""Multi-target parser for QUIRK — Phase 47 / MULTI-01..05.

Decision enforcement:
  D-01: One smart wizard prompt, syntax-routed per token.
        Tokens split on ',' first; each trimmed token is routed:
          - starts with '@' (top-level only) → load file via load_targets_file,
            then recursively parse the joined CSV with nested @-routing suppressed.
          - contains '/' → validate via ipaddress.ip_network; append to cidrs.
          - else → append to fqdns_or_ips (bare host, FQDN, or IP).

  D-02: Targets file grammar is permissive — one token per line; non-blank,
        non-'#'-prefixed lines only; NO nested @file references. A line that
        begins with '@' inside a file is treated as a bare-host token (the
        leading '@' character is part of the host string). This is enforced by
        the ``_in_file=True`` guard that suppresses @-routing for tokens
        originating from a file.

  D-05: Malformed input is a hard error, not a silent skip.
        - Bad CIDR   → ValueError("Invalid target: '<token>'") raised from
          ipaddress.ip_network's ValueError.
        - Missing @file → FileNotFoundError("Targets file not found: <path>")
          raised from the OS-level FileNotFoundError.

Public surface:
  parse_target_tokens(raw: str) -> tuple[list[str], list[str]]
  load_targets_file(path: str) -> str
  apply_targets_file_override(cfg, targets_file_path: str) -> None
"""
from __future__ import annotations

import ipaddress
import sys
from typing import Callable, Optional


def load_targets_file(path: str) -> str:
    """Read a targets file; strip blank lines and lines starting with '#'.

    Returns the surviving lines joined by ',' so the result can be passed
    directly to parse_target_tokens.

    Raises:
        FileNotFoundError: with the supplied path embedded in the message (D-05).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Targets file not found: {path}") from e

    tokens = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    return ",".join(tokens)


def parse_target_tokens(
    raw: str,
    _in_file: bool = False,
) -> tuple[list[str], list[str]]:
    """Route each comma-separated token to fqdns_or_ips or cidrs.

    Per-token routing (D-01):
      - starts with '@' AND _in_file is False (top-level only):
          load file via load_targets_file; recursively call parse_target_tokens
          on the joined result with _in_file=True to suppress further @-routing.
          # D-02: no nested @file — tokens from inside a file are NEVER
          # re-routed through @-prefix loading.
      - contains '/':
          validate via ipaddress.ip_network(token, strict=False).
          On success → append to cidrs.
          On ValueError → re-raise as ValueError with the offending token (D-05).
      - else (bare host, FQDN, or plain IP):
          append to fqdns_or_ips.

    Whitespace-only tokens are silently skipped.

    Args:
        raw: Comma-separated string of targets (may include @file tokens and CIDRs).
        _in_file: Internal flag; True when tokens originated from a file so
            @-prefix loading is suppressed (D-02). Callers must NOT pass this.

    Returns:
        (fqdns_or_ips, cidrs) — two lists; each token appears in exactly one.

    Raises:
        ValueError: If a CIDR token fails ipaddress validation (D-05).
        FileNotFoundError: If an @file token points at a missing file (D-05).
    """
    fqdns: list[str] = []
    cidrs: list[str] = []

    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue

        if token.startswith("@") and not _in_file:
            # D-01: @-prefix → file load; D-02: suppress nested @-routing
            file_path = token[1:]
            file_raw = load_targets_file(file_path)
            file_fqdns, file_cidrs = parse_target_tokens(file_raw, _in_file=True)
            fqdns.extend(file_fqdns)
            cidrs.extend(file_cidrs)

        elif "/" in token and not token.startswith("@"):
            # D-01: CIDR token — validate via stdlib
            try:
                ipaddress.ip_network(token, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid target: {token!r}") from e
            cidrs.append(token)

        else:
            # D-01: bare host, FQDN, or IP (including @-prefixed tokens from files)
            fqdns.append(token)

    return fqdns, cidrs


def projected_probe_count(targets: list, ports: list) -> int:
    """Count the total number of probes: hosts × ports.

    For CIDR tokens (containing '/'), count live hosts via .hosts() (excludes
    network/broadcast addresses for IPv4). For bare hosts/FQDNs/IPs, count 1
    each. Risks #4: uses .hosts() NOT .num_addresses to avoid off-by-2 on IPv4
    /24.

    Args:
        targets: List of target tokens (CIDR strings or bare hosts/FQDNs/IPs).
        ports: List of port integers.

    Returns:
        Total probe count (host_count × port_count).
    """
    host_count = 0
    for t in targets:
        if "/" in t:
            try:
                network = ipaddress.ip_network(t, strict=False)
                host_count += len(list(network.hosts()))
            except ValueError:
                host_count += 1  # treat malformed CIDRs as single host
        else:
            host_count += 1
    return host_count * len(ports)


def maybe_confirm_probe_budget(
    targets: list,
    ports: list,
    threshold: int = 10_000,
    is_tty: Optional[bool] = None,
    prompt_fn: Callable = input,
    stderr_print_fn: Optional[Callable] = None,
) -> bool:
    """TTY-aware probe-budget guard; returns True if scan should proceed.

    D-10: When probe count exceeds threshold:
      - TTY mode → print projection and require y/N confirm (returns False on 'n').
      - Non-TTY mode → print warning to stderr and auto-proceed (returns True).
    D-12: threshold default is 10,000 (kwarg exists for testability; run_scan.py
    MUST pass the literal 10_000 at the call site, not rely on the default).

    Args:
        targets: Target list passed to projected_probe_count.
        ports: Port list passed to projected_probe_count.
        threshold: Budget limit (default 10,000; D-12 — not configurable in prod).
        is_tty: Override for sys.stdout.isatty(); None means auto-detect.
        prompt_fn: Callable used to ask y/N (injectable for tests).
        stderr_print_fn: Callable used for stderr warning (injectable for tests).

    Returns:
        True if scan should proceed, False if user aborted.
    """
    count = projected_probe_count(targets, ports)
    if count <= threshold:
        return True

    if is_tty is None:
        is_tty = sys.stdout.isatty()  # D-10

    formatted = f"{count:,}"
    if is_tty:
        answer = prompt_fn(
            f"⚠️  Projected probe count ({formatted}) exceeds {threshold:,}. "
            "Proceed? [y/N]: "
        ).strip().lower()
        return answer in ("y", "yes")
    else:
        # Non-TTY: warn to stderr, auto-proceed (D-10)
        warn_msg = (
            f"WARNING: Projected probe count ({formatted}) exceeds {threshold:,}. "
            "Auto-proceeding in non-TTY mode."
        )
        if stderr_print_fn is not None:
            stderr_print_fn(warn_msg)
        else:
            print(warn_msg, file=sys.stderr)
        return True


def apply_targets_file_override(cfg, targets_file_path: str) -> None:
    """D-03: replace cfg.targets.fqdns and cfg.targets.cidrs with parsed file contents.

    Loads the file via load_targets_file, parses the result, and REPLACES
    (does NOT merge) the two lists on cfg.targets. This is the canonical
    --targets-file override path.

    Args:
        cfg: AppConfig instance whose .targets.fqdns and .targets.cidrs will
            be replaced in-place.
        targets_file_path: Path to the targets file (forwarded to load_targets_file).

    Raises:
        FileNotFoundError: If targets_file_path does not exist (D-05).
        ValueError: If any token in the file is a malformed CIDR (D-05).
    """
    raw = load_targets_file(targets_file_path)
    fqdns, cidrs = parse_target_tokens(raw)
    cfg.targets.fqdns = fqdns  # D-03: REPLACES, does not merge
    cfg.targets.cidrs = cidrs  # D-03: REPLACES, does not merge

"""quirk serve — launches uvicorn dashboard server and optionally opens browser."""
from __future__ import annotations

import ipaddress
import os
import sys
import webbrowser

from quirk.errors import format_error

# Hosts that are always safe to bind without operator auth — traffic cannot
# arrive from another machine. ``0.0.0.0`` / ``::`` (all interfaces) and any
# routable address are treated as remotely reachable.
_LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "::1", "localhost"})

# uvicorn's default trusted-proxy set. When the console runs behind a
# TLS-terminating reverse proxy on the same host (the recommended topology),
# loopback is the proxy's source address, so trusting loopback is correct and
# safe. Operators can widen this via QUIRK_TRUST_PROXY when the proxy lives on
# a different host.
_DEFAULT_TRUSTED_PROXIES = "127.0.0.1"


def _is_loopback_host(host: str) -> bool:
    """Return True when *host* can only be reached from the local machine.

    Accepts the textual aliases in ``_LOOPBACK_HOSTS`` and any address that
    ``ipaddress`` classifies as loopback. ``0.0.0.0`` / ``::`` (bind-all) and
    every routable address return False — they are reachable from the network.
    """
    h = host.strip().lower()
    if h in _LOOPBACK_HOSTS:
        return True
    # Strip an IPv6 zone-id (e.g. "::1%lo0") before classification.
    pct = h.find("%")
    if pct >= 0:
        h = h[:pct]
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        # Unknown hostname — treat as potentially remote (fail closed).
        return False


def _operator_token_configured() -> bool:
    """True when an operator API token is set (env var or config.yaml).

    Mirrors the resolution used by the dashboard auth dependency so the
    startup guardrail and the runtime auth check agree on whether the
    operator/dashboard surface is protected.
    """
    try:
        from quirk.dashboard.api.middleware.auth import _get_configured_token
        return bool(_get_configured_token())
    except Exception:
        # Be conservative: if we cannot prove a token is configured, treat it
        # as absent so the guardrail errs toward refusing an exposed bind.
        return bool(os.environ.get("QUIRK_API_TOKEN"))


def _forwarded_allow_ips() -> str:
    """Trusted-proxy source IPs for uvicorn's X-Forwarded-* handling.

    QUIRK_TRUST_PROXY (comma-separated IPs, or "*" to trust all upstreams)
    overrides the loopback default. When set, uvicorn rewrites the request's
    client address from X-Forwarded-For, so the rate limiter and audit log see
    the real sensor IP rather than the proxy's loopback address.
    """
    val = os.environ.get("QUIRK_TRUST_PROXY", "").strip()
    return val or _DEFAULT_TRUSTED_PROXIES


def _print_startup_summary(host: str, port: int, *, auth_on: bool, trust_proxy: str) -> None:
    """Emit a one-glance security summary so operators can spot misconfig."""
    loopback = _is_loopback_host(host)
    exposure = "loopback only" if loopback else "REACHABLE FROM NETWORK"
    print("QU.I.R.K. Dashboard security summary:")
    print(f"  bind            : {host}:{port}  ({exposure})")
    print(f"  operator auth   : {'ENABLED' if auth_on else 'DISABLED — no QUIRK_API_TOKEN set'}")
    print(f"  trusted proxies : {trust_proxy}")


def serve(
    port: int = 8512,
    host: str = "127.0.0.1",
    no_open: bool = False,
    insecure: bool = False,
) -> None:
    """Start the QU.I.R.K. dashboard server.

    Args:
        port: Port to bind uvicorn on. Default 8512 (per D-06).
        host: Host to bind. Default 127.0.0.1 (local only).
        no_open: If True, suppresses auto-opening the browser.
        insecure: If True, allow binding a network-reachable interface with no
            operator API token configured. Off by default — the server refuses
            such a bind so a public/cloud console cannot be left auth-disabled
            by accident. The escape hatch exists for intentionally token-less
            binds on trusted, firewalled segments.
    """
    try:
        import uvicorn
    except ImportError:
        print(format_error("INSTALL-002"), file=sys.stderr)
        sys.exit(1)

    auth_on = _operator_token_configured()
    loopback = _is_loopback_host(host)
    trust_proxy = _forwarded_allow_ips()

    # ------------------------------------------------------------------
    # Startup guardrail: refuse a network-reachable bind with no operator
    # token unless the operator explicitly opts in with --insecure.
    # Fails closed so a cloud console cannot silently run auth-disabled.
    # ------------------------------------------------------------------
    if not loopback and not auth_on and not insecure:
        print(
            "REFUSING to start: binding a network-reachable interface "
            f"({host}) with operator authentication DISABLED.\n"
            "\n"
            "Anyone who can reach this port would get full dashboard and "
            "operator-API access.\n"
            "\n"
            "Fix one of the following:\n"
            "  1. Set a strong token before starting:\n"
            "       export QUIRK_API_TOKEN=\"$(python -c 'import secrets;print(secrets.token_urlsafe(32))')\"\n"
            "  2. Bind loopback only and put a TLS reverse proxy in front:\n"
            "       quirk serve --host 127.0.0.1\n"
            "  3. Intentionally running token-less on a trusted, firewalled\n"
            "     segment? Re-run with --insecure to acknowledge the risk.\n"
            "\n"
            "See docs/deployment-cloud-console.md for the hardened topology.",
            file=sys.stderr,
        )
        sys.exit(2)

    _print_startup_summary(host, port, auth_on=auth_on, trust_proxy=trust_proxy)
    if not loopback and not auth_on and insecure:
        print(
            "WARNING: --insecure set — serving a network-reachable interface "
            "with operator auth DISABLED. Ensure this segment is firewalled.",
            file=sys.stderr,
        )

    # Browser auto-open target: never point at a bind-all address (0.0.0.0/::),
    # which is not a connectable host. Fall back to loopback for the local UI.
    open_host = host if _is_loopback_host(host) else "127.0.0.1"
    url = f"http://{host}:{port}"
    print(f"QU.I.R.K. Dashboard starting at {url}")
    print("Press Ctrl+C to stop.")

    if not no_open:
        # Open browser after a brief delay to allow uvicorn to bind
        import threading
        def _open():
            import time
            time.sleep(1.2)
            webbrowser.open(f"http://{open_host}:{port}")
        threading.Thread(target=_open, daemon=True).start()

    os.environ["QUIRK_SERVE_PORT"] = str(port)
    try:
        uvicorn.run(
            "quirk.dashboard.api.app:app",
            host=host,
            port=port,
            log_level="info",
            # Honour X-Forwarded-* from trusted proxies so request.client.host
            # is the real sensor IP behind a reverse proxy (correct rate-limit
            # bucketing + audit). forwarded_allow_ips restricts which upstream
            # source addresses are allowed to set those headers.
            proxy_headers=True,
            forwarded_allow_ips=trust_proxy,
        )
    except OSError as exc:
        if "address already in use" in str(exc).lower():
            print(format_error("INSTALL-004").replace("<port>", str(port)), file=sys.stderr)
            sys.exit(1)
        raise

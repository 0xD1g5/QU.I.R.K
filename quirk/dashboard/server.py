"""quirk serve — launches uvicorn dashboard server and optionally opens browser."""
from __future__ import annotations

import os
import sys
import webbrowser


def serve(port: int = 8512, host: str = "127.0.0.1", no_open: bool = False) -> None:
    """Start the QU.I.R.K. dashboard server.

    Args:
        port: Port to bind uvicorn on. Default 8512 (per D-06).
        host: Host to bind. Default 127.0.0.1 (local only).
        no_open: If True, suppresses auto-opening the browser.
    """
    try:
        import uvicorn
    except ImportError:
        print(format_error("INSTALL-002"), file=sys.stderr)
        sys.exit(1)

    url = f"http://{host}:{port}"
    print(f"QU.I.R.K. Dashboard starting at {url}")
    print("Press Ctrl+C to stop.")

    if not no_open:
        # Open browser after a brief delay to allow uvicorn to bind
        import threading
        def _open():
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    os.environ["QUIRK_SERVE_PORT"] = str(port)
    try:
        uvicorn.run(
            "quirk.dashboard.api.app:app",
            host=host,
            port=port,
            log_level="info",
        )
    except OSError as exc:
        if "address already in use" in str(exc).lower():
            print(
                f"[QRK-INSTALL-004] Port {port} is already in use. "
                f"Fix: Run `lsof -i :{port}` to find the conflicting process, "
                "or use `quirk serve --port <other>` to bind a different port.",
                file=sys.stderr,
            )
            sys.exit(1)
        raise

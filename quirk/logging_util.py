from __future__ import annotations
import threading
from datetime import datetime, timezone
from typing import Optional

_PRINT_LOCK = threading.Lock()


class Logger:
    """
    Simple logger that can play nicely with tqdm progress bars.
    If tqdm is enabled, we use tqdm.write() so the bar isn't mangled.
    """
    def __init__(self, verbose: bool = False, use_tqdm: bool = False):
        self.verbose = verbose
        self.use_tqdm = use_tqdm
        self._tqdm = None  # late import handle

        if use_tqdm:
            try:
                from tqdm import tqdm  # type: ignore
                self._tqdm = tqdm
            except Exception:
                self.use_tqdm = False
                self._tqdm = None

    def _write(self, msg: str) -> None:
        with _PRINT_LOCK:
            if self.use_tqdm and self._tqdm is not None:
                self._tqdm.write(msg)
            else:
                print(msg)

    @staticmethod
    def _fmt(msg: object, args: tuple) -> str:
        """Render a message the way stdlib logging does: lazy %-substitution.

        The scanner layer passes this Logger wherever a stdlib logger would go
        (run_scan.py phase wrappers, kerberos/saml/dnssec scanners, etc.) and
        calls it with printf-style args, e.g. ``logger.info("scan: %d", n)``.
        Support that idiom so those call sites don't blow up at runtime.
        """
        text = str(msg)
        if args:
            try:
                text = text % args
            except (TypeError, ValueError):
                # Mirror stdlib's resilience: fall back to a readable join
                text = " ".join([text, *(str(a) for a in args)])
        return text

    def info(self, msg: object, *args) -> None:
        self._write(self._fmt(msg, args))

    def v(self, msg: object, *args) -> None:
        if not self.verbose:
            return
        self._write(self._fmt(msg, args))

    # stdlib-compatible level methods. The scanner layer treats this object as a
    # stdlib logger, so honor warning/error/debug/exception/critical too.
    def warning(self, msg: object, *args) -> None:
        self._write("WARNING: " + self._fmt(msg, args))

    warn = warning

    def error(self, msg: object, *args) -> None:
        self._write("ERROR: " + self._fmt(msg, args))

    def critical(self, msg: object, *args) -> None:
        self._write("CRITICAL: " + self._fmt(msg, args))

    def exception(self, msg: object, *args) -> None:
        self._write("ERROR: " + self._fmt(msg, args))

    def debug(self, msg: object, *args) -> None:
        # Debug is verbose-gated, matching the spirit of .v()
        if not self.verbose:
            return
        self._write("DEBUG: " + self._fmt(msg, args))

    def stamp(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.info(f"[{ts}Z] {msg}")

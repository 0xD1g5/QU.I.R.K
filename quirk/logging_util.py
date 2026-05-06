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

    def info(self, msg: str) -> None:
        self._write(msg)

    def v(self, msg: str) -> None:
        if not self.verbose:
            return
        self._write(msg)

    def stamp(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.info(f"[{ts}Z] {msg}")

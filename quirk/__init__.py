"""QU.I.R.K. -- Quantum Infrastructure Readiness Kit

Version resolution (D-84-R1 / v4.10 D-02):
``pyproject.toml [project.version]`` is the canonical source of truth. The
``__version__`` attribute below derives from installed package metadata via
``importlib.metadata.version`` so there is no second literal to keep in sync.

For unpackaged dev runs (fresh checkout, never ``pip install -e .``-d), the
``PackageNotFoundError`` fallback parses ``pyproject.toml`` directly via
``tomllib`` so importing the package never fails on a bare clone.
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

_DIST_NAME = "quirk-scanner"

try:
    __version__ = _pkg_version(_DIST_NAME)
except PackageNotFoundError:
    # Unpackaged dev run — parse pyproject.toml at the repo root.
    import tomllib
    from pathlib import Path

    _pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        _pyproject = tomllib.loads(_pyproject_path.read_text(encoding="utf-8"))
        __version__ = _pyproject["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        # Last-resort sentinel — keeps imports safe even in pathological envs.
        __version__ = "0.0.0+unknown"

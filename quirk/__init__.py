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
    # Unpackaged dev run — parse pyproject.toml at the repo root. ``tomllib``
    # only exists from 3.11 and a bare 3.10 clone may lack the ``tomli``
    # backport, so fall back to a strict regex on the [project] table
    # (Phase 235.1 D-04) rather than failing the import.
    import re as _re
    from pathlib import Path

    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            tomllib = None  # type: ignore[assignment]

    _TOML_ERRORS = (OSError, KeyError, ValueError)
    if tomllib is not None:
        _TOML_ERRORS = (OSError, KeyError, tomllib.TOMLDecodeError)

    def _version_from_text(text):
        m = _re.search(r"^\[project\]\s*$", text, _re.M)
        if not m:
            raise KeyError("project")
        body = text[m.end():]
        nxt = _re.search(r"^\[", body, _re.M)
        table = body[: nxt.start()] if nxt else body
        v = _re.search(r'^version\s*=\s*"([^"]+)"\s*$', table, _re.M)
        if not v:
            raise KeyError("version")
        return v.group(1)

    _pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        _text = _pyproject_path.read_text(encoding="utf-8")
        if tomllib is not None:
            __version__ = tomllib.loads(_text)["project"]["version"]
        else:
            __version__ = _version_from_text(_text)
    except _TOML_ERRORS:
        # Last-resort sentinel — keeps imports safe even in pathological envs.
        __version__ = "0.0.0+unknown"

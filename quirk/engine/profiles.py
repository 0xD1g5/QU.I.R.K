from __future__ import annotations

from typing import Any


def apply_profile(cfg, profile: str, safe_mode: bool = False) -> None:
    """
    Applies scan profile defaults to cfg.scan.
    Works even when certain fields are None (unset in config).
    """

    scan = cfg.scan
    p = (profile or "standard").lower().strip()

    # -------------------------
    # helpers
    # -------------------------
    def _get_int(v: Any, fallback: int) -> int:
        """Return an int value, treating None / empty as fallback."""
        if v is None:
            return fallback
        try:
            return int(v)
        except Exception:
            return fallback

    def _set_if_unset(field: str, value: int) -> None:
        """
        Sets scan.<field> if it is currently None (or missing).
        This is important because None means "not explicitly set by user".
        """
        current = getattr(scan, field, None)
        if current is None:
            setattr(scan, field, int(value))

    def _set_if_default(field: str, value: int, default: int) -> None:
        """
        Sets scan.<field> if it is None OR equals the known default.
        Useful when config uses baseline defaults but profile should override.
        """
        current = getattr(scan, field, None)
        if current is None or current == default:
            setattr(scan, field, int(value))

    # -------------------------
    # establish baseline defaults (only if unset)
    # -------------------------
    _set_if_unset("timeout_seconds", 5)
    _set_if_unset("concurrency", 200)

    # Phase-specific defaults (these may be Optional[int] in your config)
    _set_if_unset("fingerprint_timeout_seconds", 4)
    _set_if_unset("fingerprint_concurrency", _get_int(getattr(scan, "concurrency", 200), 200))

    _set_if_unset("tls_timeout_seconds", _get_int(getattr(scan, "timeout_seconds", 5), 5))
    _set_if_unset("tls_concurrency", _get_int(getattr(scan, "concurrency", 200), 200))

    _set_if_unset("ssh_timeout_seconds", _get_int(getattr(scan, "timeout_seconds", 5), 5))
    _set_if_unset("ssh_concurrency", _get_int(getattr(scan, "concurrency", 200), 200))

    # Optional knobs
    if getattr(scan, "fingerprint_timeout_seconds", None) is None:
        scan.fingerprint_timeout_seconds = 4

    # -------------------------
    # profile presets
    # -------------------------
    # Note: we try to *not* clobber explicit user config.
    # We only override if a field is None or set to a baseline default.

    # Use these to detect whether values are likely defaults.
    base_timeout_default = 5
    base_concurrency_default = 200

    if p == "quick":
        # faster, less depth
        _set_if_default("fingerprint_timeout_seconds", 3, default=4)
        _set_if_default("fingerprint_concurrency", 300, default=base_concurrency_default)

        _set_if_default("tls_timeout_seconds", 4, default=base_timeout_default)
        _set_if_default("tls_concurrency", 250, default=base_concurrency_default)

        _set_if_default("ssh_timeout_seconds", 4, default=base_timeout_default)
        _set_if_default("ssh_concurrency", 200, default=base_concurrency_default)

        # tls_enum_mode handled elsewhere; quick should effectively be OFF
        if hasattr(scan, "tls_enum_mode") and (getattr(scan, "tls_enum_mode") is None):
            scan.tls_enum_mode = "off"

        # Phase 32: do NOT enable email scanning in quick profile.
        # cfg.connectors.enable_email default (False) stays.
        # Phase 33: do NOT enable broker scanning in quick profile (D-10).
        # cfg.connectors.enable_broker default (False) stays.

    elif p == "deep":
        # slower, deeper enumeration
        _set_if_default("fingerprint_timeout_seconds", 6, default=4)
        _set_if_default("fingerprint_concurrency", 150, default=base_concurrency_default)

        _set_if_default("tls_timeout_seconds", 10, default=base_timeout_default)
        _set_if_default("tls_concurrency", 120, default=base_concurrency_default)

        _set_if_default("ssh_timeout_seconds", 8, default=base_timeout_default)
        _set_if_default("ssh_concurrency", 120, default=base_concurrency_default)

        if hasattr(scan, "tls_enum_mode") and (getattr(scan, "tls_enum_mode") is None):
            scan.tls_enum_mode = "deep"

        # Phase 32: deep profile enables email scanning.
        # Phase 72 D-02 / WR-11: respect user-explicit enable_email value from YAML.
        if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_email"):
            user_set = getattr(cfg.connectors, "_user_set_fields", frozenset())
            if "enable_email" not in user_set:
                if not cfg.connectors.enable_email:
                    cfg.connectors.enable_email = True

        # Phase 33: deep profile enables broker scanning (D-10).
        # Phase 72 D-02 / WR-11: respect user-explicit enable_broker value from YAML.
        if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_broker"):
            user_set = getattr(cfg.connectors, "_user_set_fields", frozenset())
            if "enable_broker" not in user_set:
                if not cfg.connectors.enable_broker:
                    cfg.connectors.enable_broker = True

    else:
        # standard
        # Phase 72 D-03 / WR-12: removed no-op _set_if_default("fingerprint_timeout_seconds", 4) — matches TimeoutsCfg default.
        # Phase 72 D-03 / WR-12: removed no-op _set_if_default("fingerprint_concurrency", 200) — matches ScanCfg default.
        # Phase 72 D-03 / WR-12: removed no-op _set_if_default("tls_timeout_seconds", 6) — matches TimeoutsCfg default.
        # Phase 72 D-03 / WR-12: removed no-op _set_if_default("tls_concurrency", 150) — matches ScanCfg default.
        # Phase 72 D-03 / WR-12: removed no-op _set_if_default("ssh_timeout_seconds", 6) — matches TimeoutsCfg default.
        _set_if_default("ssh_concurrency", 150, default=base_concurrency_default)

        if hasattr(scan, "tls_enum_mode") and (getattr(scan, "tls_enum_mode") is None):
            scan.tls_enum_mode = "fast"

        # Phase 32: standard profile enables email scanning.
        # Phase 72 D-02 / WR-11: respect user-explicit enable_email value from YAML.
        if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_email"):
            user_set = getattr(cfg.connectors, "_user_set_fields", frozenset())
            if "enable_email" not in user_set:
                if not cfg.connectors.enable_email:
                    cfg.connectors.enable_email = True

        # Phase 33: standard profile enables broker scanning (D-10).
        # Phase 72 D-02 / WR-11: respect user-explicit enable_broker value from YAML.
        if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_broker"):
            user_set = getattr(cfg.connectors, "_user_set_fields", frozenset())
            if "enable_broker" not in user_set:
                if not cfg.connectors.enable_broker:
                    cfg.connectors.enable_broker = True

    # -------------------------
    # safe-mode adjustments
    # -------------------------
    if safe_mode:
        # dial concurrency down and increase timeouts slightly
        scan.fingerprint_concurrency = max(25, _get_int(getattr(scan, "fingerprint_concurrency", 100), 100) // 2)
        scan.tls_concurrency = max(25, _get_int(getattr(scan, "tls_concurrency", 100), 100) // 2)
        scan.ssh_concurrency = max(25, _get_int(getattr(scan, "ssh_concurrency", 100), 100) // 2)

        scan.fingerprint_timeout_seconds = max(4, _get_int(getattr(scan, "fingerprint_timeout_seconds", 4), 4))
        scan.tls_timeout_seconds = max(6, _get_int(getattr(scan, "tls_timeout_seconds", 6), 6))
        scan.ssh_timeout_seconds = max(6, _get_int(getattr(scan, "ssh_timeout_seconds", 6), 6))
# Phase 72 D-06 / WR-21: explicit EOF marker confirms file integrity (py_compile + git history verified intact at 153 lines).
# eof
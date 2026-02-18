from __future__ import annotations

def apply_profile(cfg, profile: str, safe_mode: bool = False) -> None:
    """
    Apply opinionated defaults for scan behavior. Users can still override via config.yaml.
    Profiles should change *defaults* only.

    quick:
      - faster: lower timeouts, higher concurrency, skip TLS enum
    standard:
      - balanced: tls_enum fast
    deep:
      - thorough: tls_enum deep, more conservative concurrency
    safe_mode:
      - reduce concurrency + add more timeouts (intended to avoid tripping IDS/fragile hosts)
    """
    profile = (profile or "standard").lower()
    scan = cfg.scan

    # Ensure optional fields exist (config.py adds defaults, but be defensive)
    if not hasattr(scan, "tls_enum_mode"):
        scan.tls_enum_mode = "fast"

    if not hasattr(scan, "fingerprint_timeout_seconds"):
        scan.fingerprint_timeout_seconds = scan.timeout_seconds
    if not hasattr(scan, "fingerprint_concurrency"):
        scan.fingerprint_concurrency = max(20, min(200, scan.concurrency))

    if not hasattr(scan, "tls_timeout_seconds"):
        scan.tls_timeout_seconds = scan.timeout_seconds
    if not hasattr(scan, "tls_concurrency"):
        scan.tls_concurrency = scan.concurrency

    if not hasattr(scan, "ssh_timeout_seconds"):
        scan.ssh_timeout_seconds = scan.timeout_seconds
    if not hasattr(scan, "ssh_concurrency"):
        scan.ssh_concurrency = max(20, min(scan.concurrency, 200))

    # ---- Apply profile defaults (only if user didn't already set explicit values) ----
    # We'll treat "explicit" as: field exists in cfg and is not None.
    def _set_if_default(attr: str, value):
        # if config.py always sets these, we still allow profile to overwrite as baseline
        setattr(scan, attr, value)

    if profile == "quick":
        _set_if_default("fingerprint_timeout_seconds", max(1, min(scan.fingerprint_timeout_seconds, 2)))
        _set_if_default("tls_timeout_seconds", max(2, min(scan.tls_timeout_seconds, 3)))
        _set_if_default("ssh_timeout_seconds", max(2, min(scan.ssh_timeout_seconds, 3)))

        _set_if_default("fingerprint_concurrency", max(50, scan.fingerprint_concurrency))
        _set_if_default("tls_concurrency", max(100, scan.tls_concurrency))
        _set_if_default("ssh_concurrency", max(50, scan.ssh_concurrency))

        _set_if_default("tls_enum_mode", "off")

    elif profile == "deep":
        _set_if_default("fingerprint_timeout_seconds", max(scan.fingerprint_timeout_seconds, 4))
        _set_if_default("tls_timeout_seconds", max(scan.tls_timeout_seconds, 5))
        _set_if_default("ssh_timeout_seconds", max(scan.ssh_timeout_seconds, 5))

        # conservative concurrency
        _set_if_default("fingerprint_concurrency", min(scan.fingerprint_concurrency, 150))
        _set_if_default("tls_concurrency", min(scan.tls_concurrency, 120))
        _set_if_default("ssh_concurrency", min(scan.ssh_concurrency, 120))

        _set_if_default("tls_enum_mode", "deep")

    else:
        # standard
        _set_if_default("tls_enum_mode", getattr(scan, "tls_enum_mode", "fast") or "fast")
        if scan.tls_enum_mode == "off":
            scan.tls_enum_mode = "fast"

    # ---- Safe mode overrides ----
    if safe_mode:
        scan.fingerprint_concurrency = max(10, min(scan.fingerprint_concurrency, 60))
        scan.tls_concurrency = max(10, min(scan.tls_concurrency, 60))
        scan.ssh_concurrency = max(10, min(scan.ssh_concurrency, 60))

        scan.fingerprint_timeout_seconds = max(scan.fingerprint_timeout_seconds, 4)
        scan.tls_timeout_seconds = max(scan.tls_timeout_seconds, 6)
        scan.ssh_timeout_seconds = max(scan.ssh_timeout_seconds, 6)
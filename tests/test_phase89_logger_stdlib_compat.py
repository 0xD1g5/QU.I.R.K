"""Phase 89 LAB-06: regression guard for the custom Logger's stdlib-compat API.

The scanner layer (run_scan.py phase wrappers, kerberos/saml/dnssec scanners)
passes ``quirk.logging_util.Logger`` wherever a stdlib logger is expected and
calls it with printf-style args and stdlib level methods. Before this fix the
custom Logger only implemented ``info/v/stamp(msg)``, so the live identity
connectors crashed end-to-end with:

  - ``Logger.info() takes 2 positional arguments but 4 were given`` (dnssec, saml)
  - ``'Logger' object has no attribute 'warning'`` (kerberos, impacket-missing path)

This silently zeroed identity_weak_etype_count / saml_weak_signing_count /
dnssec_weak_algo_count because ``_wrapped_phase`` swallowed the exception and
returned no endpoints. These tests pin the compatible interface so the wiring
cannot regress back to the crash.
"""

from quirk.logging_util import Logger


def test_info_accepts_printf_style_args():
    """The exact dnssec/saml crash: logger.info(msg, *args)."""
    lg = Logger(verbose=False)
    # Must not raise; %-substitution applied like stdlib logging.
    lg.info("DNSSEC scan: %d endpoints from %d targets", 2, 2)


def test_warning_method_exists_and_takes_args():
    """The exact kerberos crash: logger.warning(...) on the custom Logger."""
    lg = Logger(verbose=False)
    lg.warning("impacket not installed -- Kerberos scanning disabled")
    lg.warning("KDC UDP probe failed for %r: %s", "host", "boom")


def test_stdlib_level_methods_present():
    lg = Logger(verbose=False)
    for name in ("info", "v", "warning", "warn", "error", "critical",
                 "exception", "debug", "stamp"):
        assert callable(getattr(lg, name)), f"Logger missing {name}()"


def test_debug_is_verbose_gated(capsys):
    Logger(verbose=False).debug("hidden %d", 1)
    assert capsys.readouterr().out == ""
    Logger(verbose=True).debug("shown %d", 1)
    assert "shown 1" in capsys.readouterr().out


def test_malformed_format_does_not_raise(capsys):
    """Mirror stdlib resilience: a bad format string degrades, never raises."""
    lg = Logger(verbose=False)
    lg.info("only one %s slot", "a", "extra")  # too many args
    out = capsys.readouterr().out
    assert "a" in out and "extra" in out

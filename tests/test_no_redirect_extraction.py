"""STAB-02: _NoRedirectHandler must be defined only in quirk/util/no_redirect.py."""
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_redirect_importable():
    from quirk.util.no_redirect import _NoRedirectHandler
    import urllib.request
    assert issubclass(_NoRedirectHandler, urllib.request.HTTPRedirectHandler)


def test_no_duplicate_definitions():
    """webhook.py and servicenow.py must NOT define _NoRedirectHandler after extraction."""
    for rel in [
        "quirk/notify/channels/webhook.py",
        "quirk/ticketing/servicenow.py",
    ]:
        src = (REPO_ROOT / rel).read_text()
        assert "class _NoRedirectHandler" not in src, (
            f"{rel} still defines _NoRedirectHandler — STAB-02 extraction incomplete"
        )

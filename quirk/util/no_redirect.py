"""quirk.util.no_redirect — SSRF redirect guard (STAB-02 extraction).

Extracted from quirk/notify/channels/webhook.py and quirk/ticketing/servicenow.py
where the class was duplicated verbatim. All callers now import from here.
"""
from __future__ import annotations

import urllib.error
import urllib.request


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects to prevent post-validation SSRF bypass.

    urllib.request.urlopen follows 3xx redirects by default via HTTPRedirectHandler.
    An attacker-controlled endpoint returning 302 → http://169.254.169.254/... would
    bypass the validate_external_url() pre-connection check.  This handler refuses
    any redirect by raising HTTPError, keeping the connection to the validated URL.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "Redirect blocked (SSRF guard)", headers, fp
        )

"""Bearer-token minting that is safe to paste after a CLI flag.

`secrets.token_urlsafe` draws from the base64url alphabet (A-Z a-z 0-9 - _),
so about 1 token in 64 starts with "-". The documented way to hand a token to
the sensor is `quirk sensor enroll ... --api-token <token>`, and argparse reads
a "-"-led value as a new option, failing with "argument --api-token: expected
one argument". That is what made Windows Sensor E2E fail about once in 64 runs
(todo 260929, first misread as an empty token on branch dispatches).

Redrawing a dash-led token costs log2(64/63) ~= 0.02 bits of 256, so every
minted token can be passed as a separate argument. Tokens minted before this
module existed can still start with "-"; pass those as `--api-token=<token>`.
"""
from __future__ import annotations

import secrets

TOKEN_BYTES = 32


def mint_token() -> str:
    """Return a fresh URL-safe bearer token that never starts with "-"."""
    while True:
        token = secrets.token_urlsafe(TOKEN_BYTES)
        if not token.startswith("-"):
            return token

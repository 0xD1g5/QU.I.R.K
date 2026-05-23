"""
Deliberately-weak FastAPI service for Phase 96 / LAB-01 fuzz-target chaos profile.

INTENTIONAL WEAKNESSES (this is a controlled lab target — never use in production):
  1. No HSTS security header on any response (HSTS probe target).
  2. /openapi.json server URL declares http:// (HTTP-only cred probe target).
  3. /probe accepts any Bearer token without proper algorithm verification
     (alg-confusion probe target — simulates a server that accepts forged HS256 tokens).
  4. /.well-known/jwks.json exposes the RS256 public key (JWKS fetch for alg-confusion).

THREAT: T-96-11 — Intentional vulnerable lab target; isolated compose profile, off by
default, documented as deliberately weak (RESEARCH A2). Never run in production.
"""

import base64

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="fuzz-target",
    description="Deliberately-weak REST service for QUIRK active REST fuzzer validation",
    version="1.0.0",
    # Disable FastAPI's default /openapi.json auto-generation — we serve our own
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# RSA key pair generated at startup — mirrors jwt/rs256/main.py
# ---------------------------------------------------------------------------
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_pub = _private_key.public_key().public_numbers()


def _b64url(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()


JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "kid": "fuzz-target-key-1",
            "n": _b64url(_pub.n),
            "e": _b64url(_pub.e),
        }
    ]
}

# ---------------------------------------------------------------------------
# Minimal OpenAPI 3.0 spec — http:// server URL (deliberate) + /probe path
# Served manually so the http:// server entry is preserved exactly.
# ---------------------------------------------------------------------------
_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "fuzz-target",
        "version": "1.0.0",
        "description": (
            "Deliberately-weak REST service for QUIRK active REST fuzzer validation. "
            "http:// server URL and /probe endpoint with no alg verification are intentional."
        ),
    },
    # DELIBERATE: http:// (not https://) — HTTP-only credential probe target
    "servers": [{"url": "http://localhost:20100"}],
    "paths": {
        "/probe": {
            "get": {
                "operationId": "probe",
                "summary": "Alg-confusion probe target — accepts any Bearer token",
                "parameters": [
                    {
                        "name": "Authorization",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": "Bearer token (alg verification deliberately omitted)",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Always returns 200 regardless of token validity",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "token_received": {"type": "boolean"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }
    },
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/openapi.json", include_in_schema=False)
def openapi_spec():
    """Minimal OpenAPI 3.0 spec with deliberate http:// server URL."""
    return JSONResponse(content=_OPENAPI_SPEC)


@app.get("/.well-known/jwks.json")
def jwks():
    """Expose RS256 public key — required for alg-confusion probe JWKS fetch."""
    return JWKS


@app.get("/probe")
def probe(request: Request):
    """
    Alg-confusion probe target.

    DELIBERATE WEAKNESS: Accepts ANY Bearer token without verifying the algorithm.
    A real server should reject HS256 tokens signed with a public key (the alg-confusion
    attack). This endpoint simulates a vulnerable server that does not.
    """
    auth = request.headers.get("authorization", "")
    token_received = auth.lower().startswith("bearer ")
    return JSONResponse(
        content={
            "status": "ok",
            "token_received": token_received,
            "note": (
                "deliberately-weak: no algorithm verification performed — "
                "alg-confusion probe target (T-96-11)"
            ),
        }
    )

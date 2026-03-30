from fastapi import FastAPI
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import base64, jwt as pyjwt, datetime

app = FastAPI()

# 1024-bit RSA — deliberately weak
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
_pub = _private_key.public_key().public_numbers()

def _b64url(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()

JWKS = {
    "keys": [{
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": "rsa1024-key-1",
        "n": _b64url(_pub.n),
        "e": _b64url(_pub.e),
    }]
}

@app.get("/.well-known/jwks.json")
def jwks():
    return JWKS

@app.get("/token")
def token():
    private_pem = _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    t = pyjwt.encode(
        {"sub": "lab-user", "iat": datetime.datetime.utcnow(), "kid": "rsa1024-key-1"},
        private_pem,
        algorithm="RS256",
        headers={"kid": "rsa1024-key-1"},
    )
    return {"token": t}

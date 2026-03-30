from fastapi import FastAPI
import base64, jwt as pyjwt, datetime, os

app = FastAPI()

# 16 bytes = 128 bits — deliberately short for weak finding
_secret = os.urandom(16)
_k_b64url = base64.urlsafe_b64encode(_secret).rstrip(b"=").decode()

JWKS = {
    "keys": [{
        "kty": "oct",
        "alg": "HS256",
        "use": "sig",
        "kid": "hs256-weak-key-1",
        "k": _k_b64url,
    }]
}

@app.get("/.well-known/jwks.json")
def jwks():
    return JWKS

@app.get("/token")
def token():
    t = pyjwt.encode(
        {"sub": "lab-user", "iat": datetime.datetime.utcnow(), "kid": "hs256-weak-key-1"},
        _secret,
        algorithm="HS256",
        headers={"kid": "hs256-weak-key-1"},
    )
    return {"token": t}

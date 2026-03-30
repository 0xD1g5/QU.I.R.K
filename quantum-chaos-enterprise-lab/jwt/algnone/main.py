from fastapi import FastAPI
import base64, datetime

app = FastAPI()

JWKS = {
    "keys": [{
        "kty": "oct",
        "alg": "none",
        "kid": "algnone-key-1",
        "k": "",
    }]
}

@app.get("/.well-known/jwks.json")
def jwks():
    return JWKS

@app.get("/token")
def token():
    # Manually construct alg:none JWT (no signature)
    import json
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT", "kid": "algnone-key-1"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "lab-user", "iat": int(datetime.datetime.utcnow().timestamp())}).encode()
    ).rstrip(b"=").decode()
    return {"token": f"{header}.{payload}."}

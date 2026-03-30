---
status: partial
phase: 04-chaos-lab-expansion
source: [04-VERIFICATION.md]
started: 2026-03-30T21:14:19Z
updated: 2026-03-30T21:14:19Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. JWT Profile End-to-End Validation
expected: docker compose --profile jwt up -d starts jwt-rs256/hs256/rsa1024/algnone on ports 20001-20004; curl http://localhost:20001/.well-known/jwks.json returns RSA 2048-bit JWKS; all 4 endpoints respond with valid JWKS JSON
result: [pending]

### 2. JWT Scanner Detection Against All 4 JWT Endpoints
expected: JWT scanner run against ports 20001-20004 returns at least 2 weak-algorithm findings (WEAK_KEY_SIZE for HS256-128bit and RSA-1024, CRITICAL_NO_SIGNATURE for alg:none)
result: [pending]

### 3. Registry Profile Seed Verification
expected: docker compose --profile registry up -d && sleep 30 && curl http://localhost:20005/v2/_catalog returns {"repositories":["image-mixed","image-old-libssl","image-old-pycrypto"]}; container scanner detects cryptography/openssl packages in images
result: [pending]

### 4. SSH Scanner Validation Against ssh-weak Profile
expected: docker compose --profile ssh-weak up -d && ssh-audit localhost:20022 reports CRITICAL findings for diffie-hellman-group1-sha1, ssh-dss, hmac-md5
result: [pending]

### 5. sslyze TLS Validation Against ldaps Profile
expected: docker compose --profile ldaps up -d && sslyze --targets localhost:636 returns TLS certificate findings including self-signed cert detection
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

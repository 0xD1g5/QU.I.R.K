# Technical Findings — Quantum Crypto Readiness - Interactive

- **Generated:** 2026-02-19 20:52 UTC

## Service Inventory

| Host | Port | Protocol | Detail |
|---|---:|---|---|
| 127.0.0.1 | 443 | TLS | TLSv1.3 |
| 127.0.0.1 | 2222 | SSH | SSH-2.0-OpenSSH_10.2 |
| 127.0.0.1 | 5555 | UNKNOWN | OPEN_NOT_TLS |
| 127.0.0.1 | 8000 | HTTP | HTTP/1.1 200 OK |
| 127.0.0.1 | 8443 | TLS | TLSv1.2 |
| 127.0.0.1 | 8444 | HTTP | HTTP/1.1 200 OK |
| 127.0.0.1 | 9443 | TLS | TLSv1.2 |
| 127.0.0.1 | 10443 | TLS | TLSv1.3 |
| 127.0.0.1 | 11443 | TLS | TLSv1.3 |
| 127.0.0.1 | 12443 | TLS | TLSv1.3 |

## TLS Capabilities (v3.6)

| Host | Port | Negotiated TLS | Supported Versions | Weak Ciphers Present | Legacy Suites Present | PFS | Cipher Sample | Notes |
|---|---:|---|---|---|---|---|---|---|
| 127.0.0.1 | 443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |
| 127.0.0.1 | 8443 | TLSv1.2 | TLSv1.2 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | OK |
| 127.0.0.1 | 9443 | TLSv1.2 | TLSv1.2 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | OK |
| 127.0.0.1 | 10443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |
| 127.0.0.1 | 11443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |
| 127.0.0.1 | 12443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |

## Findings

| Severity | Host | Port | Title | Recommendation |
|---|---|---:|---|---|
| INFO | 127.0.0.1 | 2222 | SSH quantum planning advisory | Inventory SSH host keys and KEX algorithms; evaluate lifecycle and PQC readiness. |
| MEDIUM | 127.0.0.1 | 5555 | Unknown open service | Fingerprint with a deeper probe or validate service ownership and purpose. |
| HIGH | 127.0.0.1 | 8000 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 8444 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |

# Technical Findings — Quantum Crypto Readiness - Interactive

- **Generated:** 2026-02-23 04:00 UTC

## Service Inventory

| Host | Port | Protocol | Detail |
|---|---:|---|---|
| 127.0.0.1 | 443 | TLS | TLSv1.3 |
| 127.0.0.1 | 8000 | HTTP | HTTP/1.1 200 OK |
| 127.0.0.1 | 8443 | TLS | TLSv1.2 |
| 127.0.0.1 | 9443 | TLS | TLSv1.3 |
| 127.0.0.1 | 10443 | TLS | TLSv1.3 |

## TLS Capabilities (v3.6)

| Host | Port | Negotiated TLS | Supported Versions | Weak Ciphers Present | Legacy Suites Present | PFS | Cipher Sample | Notes |
|---|---:|---|---|---|---|---|---|---|
| 127.0.0.1 | 443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |
| 127.0.0.1 | 8443 | TLSv1.2 | TLSv1.2 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | OK |
| 127.0.0.1 | 9443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |
| 127.0.0.1 | 10443 | TLSv1.3 | TLSv1.2,TLSv1.3 | NO | YES | YES | ECDHE-RSA-AES128-GCM-SHA256,ECDHE-RSA-AES256-GCM-SHA384,ECDHE-RSA-CHACHA20-POLY1305,AES128-SHA,AES256-SHA | TLS 1.3 supported |

## Findings

| Severity | Host | Port | Title | Recommendation |
|---|---|---:|---|---|
| HIGH | 127.0.0.1 | 8000 | Plaintext HTTP service detected | Migrate management/application endpoints to HTTPS/TLS where feasible. |

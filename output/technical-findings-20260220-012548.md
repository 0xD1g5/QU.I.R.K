# Technical Findings — Quantum Crypto Readiness - Interactive

- **Generated:** 2026-02-20 01:25 UTC

## Service Inventory

| Host | Port | Protocol | Detail |
|---|---:|---|---|
| 127.0.0.1 | 443 | HTTP | HTTP/1.1 400 Bad Request |
| 127.0.0.1 | 2222 | SSH | SSH-2.0-OpenSSH_10.2 |
| 127.0.0.1 | 5555 | UNKNOWN | Banner bytes: CHAOS |
| 127.0.0.1 | 8000 | HTTP | HTTP/1.1 200 OK |
| 127.0.0.1 | 8443 | HTTP | HTTP/1.1 400 Bad Request |
| 127.0.0.1 | 8444 | HTTP | HTTP/1.1 200 OK |
| 127.0.0.1 | 9443 | HTTP | HTTP/1.1 400 Bad Request |
| 127.0.0.1 | 10443 | HTTP | HTTP/1.1 400 Bad Request |
| 127.0.0.1 | 11443 | HTTP | HTTP/1.1 400 Bad Request |
| 127.0.0.1 | 12443 | HTTP | HTTP/1.1 400 Bad Request |

## Findings

| Severity | Host | Port | Title | Recommendation |
|---|---|---:|---|---|
| HIGH | 127.0.0.1 | 443 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| INFO | 127.0.0.1 | 2222 | SSH quantum planning advisory | Inventory SSH host keys and KEX algorithms; evaluate lifecycle and PQC readiness. |
| MEDIUM | 127.0.0.1 | 5555 | Unknown open service | Fingerprint with a deeper probe or validate service ownership and purpose. |
| HIGH | 127.0.0.1 | 8000 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 8443 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 8444 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 9443 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 10443 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 11443 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |
| HIGH | 127.0.0.1 | 12443 | HTTP on TLS-designated port | A plaintext HTTP service responded on a port expected to be TLS/HTTPS. Correct service configuration (enable TLS) or update port policy/registry. |

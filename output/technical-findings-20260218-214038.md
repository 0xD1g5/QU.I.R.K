# Technical Findings — Quantum Crypto Readiness - Interactive

- **Generated:** 2026-02-18 21:40 UTC

## Findings

| Severity | Host | Port | Title | Recommendation |
|---|---|---:|---|---|
| MEDIUM | 192.168.4.1 | 80 | Plaintext HTTP service detected | Migrate management/application endpoints to HTTPS/TLS where feasible. |
| MEDIUM | 192.168.4.21 | 443 | Plaintext HTTP service detected | Migrate management/application endpoints to HTTPS/TLS where feasible. |
| MEDIUM | 192.168.4.21 | 80 | Plaintext HTTP service detected | Migrate management/application endpoints to HTTPS/TLS where feasible. |
| MEDIUM | 192.168.4.21 | 8080 | Plaintext HTTP service detected | Migrate management/application endpoints to HTTPS/TLS where feasible. |
| LOW | 192.168.4.23 | 8443 | Unknown service detected | Fingerprint with a deeper probe or validate service ownership and purpose. |
| LOW | 192.168.4.54 | 80 | Unknown service detected | Fingerprint with a deeper probe or validate service ownership and purpose. |

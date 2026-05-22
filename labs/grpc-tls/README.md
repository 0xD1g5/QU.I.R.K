# labs/grpc-tls — gRPC TLS Chaos Lab Service (Phase 89 / LAB-05)

Minimal Go gRPC server with a self-signed RSA-2048 certificate. The `grpc-go` runtime
automatically advertises ALPN `h2`, making this the canonical lab target for verifying
sslyze's behavior against an h2-only TLS endpoint.

## Weakness Inventory

| Property | Value | Scanner Finding |
|----------|-------|-----------------|
| Key type | RSA-2048 | Quantum-vulnerable certificate (MEDIUM, TLS-02) |
| TLS versions | 1.2 + 1.3 (Go defaults) | Informational |
| ALPN | h2 only (grpc-go auto-sets) | See D-03 note below |
| Cert validity | 10 years self-signed | Untrusted CA (scanner advisory) |

## D-03: ALPN h2 + sslyze behavior

`grpc-go` sets `NextProtos: ["h2"]` in the `tls.Config` automatically when
`credentials.NewServerTLSFromFile` is used. sslyze does not have a dedicated ALPN
ScanCommand, but the TLS handshake itself succeeds and sslyze emits `CERTIFICATE_INFO`
and cipher-suite findings. If sslyze returns a connection error, the fallback evidence
source is `openssl s_client -alpn h2 -connect localhost:39443`.

The executor's first task for this profile runs the empirical check per decision D-03
before finalizing the expected_results oracle. The actual outcome is documented in the
Phase 89 Plan 03 SUMMARY.

## Expected Findings (if sslyze succeeds)

- RSA-2048 cert (quantum-vulnerable) — MEDIUM
- Cipher suite info — informational
- ALPN h2 negotiated — informational

## Usage

```bash
# From quantum-chaos-enterprise-lab/
PROFILE_ARGS="--profile grpc-tls" ./lab.sh up

# Generate certs first
cd labs/grpc-tls && make certs
```

## Files

| File | Purpose |
|------|---------|
| `main.go` | Minimal `grpc.NewServer` with `credentials.NewServerTLSFromFile` |
| `go.mod` / `go.sum` | Pinned `google.golang.org/grpc` dependency |
| `Dockerfile` | Multi-stage build (`golang:1.23-alpine` → `alpine:3.20`) |
| `Makefile` | `make certs` generates RSA-2048 self-signed cert |
| `certs/` | Generated at lab-spin-up time; `*.key` / `*.crt` gitignored |

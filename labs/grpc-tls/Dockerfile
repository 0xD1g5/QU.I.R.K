# Phase 89 / LAB-05: Minimal gRPC TLS chaos-lab server.
# CHAOS-05: FROM golang:1.23-alpine pinned (build-only stage satisfies the pin gate).
# Multi-stage build: builder compiles the binary; runtime stage uses minimal alpine.

# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for layer-cache efficiency.
COPY go.mod go.sum ./
# Bounded retry (D-16): transient proxy.golang.org stream errors; still fails after attempt 3.
RUN for i in 1 2 3; do \
      go mod download && exit 0; \
      echo "go mod download failed (attempt $i/3)" >&2; \
      if [ "$i" -lt 3 ]; then sleep $((i * 10)); fi; \
    done; \
    exit 1

COPY main.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o grpc-server .

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM alpine:3.20

WORKDIR /

# Copy the compiled binary from the builder stage.
COPY --from=builder /app/grpc-server /grpc-server

# Certs are bind-mounted from labs/grpc-tls/certs/ at run time (see docker-compose.yml).
# The expected mount points match credentials.NewServerTLSFromFile in main.go.
EXPOSE 443

CMD ["/grpc-server"]

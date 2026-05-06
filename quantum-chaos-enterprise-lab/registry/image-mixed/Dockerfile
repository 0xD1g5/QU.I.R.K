# Stage 1: build a tiny Go binary that imports crypto/tls
FROM golang:1.20-alpine AS gobuilder
RUN mkdir /gobuild && cat > /gobuild/main.go <<'EOF'
package main

import (
    "crypto/tls"
    "fmt"
)

func main() {
    cfg := &tls.Config{MinVersion: tls.VersionTLS10}
    fmt.Println("tls min version:", cfg.MinVersion)
}
EOF
RUN cd /gobuild && go build -o /app-binary main.go

# Stage 2: runtime with old Python crypto + old libssl + Go binary
FROM ubuntu:18.04
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip \
        openssl libssl1.0.0 \
        gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir setuptools wheel && \
    python3 -m pip install --no-cache-dir --no-build-isolation \
    "cryptography==2.9.2" \
    "pyOpenSSL==19.1.0"
COPY --from=gobuilder /app-binary /usr/local/bin/app-binary
LABEL quirk.lab="image-mixed" \
      quirk.openssl-version="1.0.2n" \
      quirk.cryptography-version="2.9.2"
CMD ["/usr/local/bin/app-binary"]

# QU.I.R.K. — Sensor / Console container image for the distributed chaos lab
#
# Used by docker-compose.distributed.yml for both sensor and console services.
# The compose file overrides `command:` per-service; the default CMD is
# informative only.
#
# Base image: python:3.11.12-slim (patch-pinned per CHAOS-05 policy).
# Entrypoint: quirk (the CLI installed via `pip install ".[all]"`)
#
# Why ".[all]":
#   - sensor services need [tls], [ssh], [jwt] etc. for local scanning
#   - console needs [dashboard] (fastapi + uvicorn) for `quirk serve`
#   - [identity] (impacket) is intentionally excluded from [all] — correct here
#
# Build context is the repo root (../../ relative to this Dockerfile):
#   docker compose -f docker-compose.distributed.yml build

FROM python:3.11.12-slim

# System dependencies:
#   * nmap            — required by TLS/SSH scanners
#   * curl            — used by network probes + diagnostics
#   * ca-certificates — TLS trust store for HTTPS scans
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        nmap \
        curl \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install from the local repo checkout (build context = repo root).
# The wheel build is skipped; pip sees a local directory with pyproject.toml.
WORKDIR /quirk
COPY . /quirk/
RUN pip install --no-cache-dir ".[all]"

# Default CMD is informative — compose overrides `command:` per service:
#   console:  ["serve", "--host", "0.0.0.0", "--port", "8512"]
#   sensor-*: ["sensor", "push"]
ENTRYPOINT ["quirk"]
CMD ["--help"]

# QU.I.R.K. — Quantum Infrastructure Readiness Kit
#
# Multi-arch container image (linux/amd64 + linux/arm64) published to
# ghcr.io/0xd1g5/quirk by .github/workflows/release-container.yml on every
# v*.*.* tag push, AFTER the PyPI publish workflow (release.yml) lands the
# matching `qu-i-r-k` wheel.
#
# Base image rationale (Phase 85 D-LAUNCH Docker):
#   * python:3.11-slim — Debian slim, glibc — full `cryptography` wheel
#     compatibility plus `nmap`/`apt` availability for first-run debugging.
#   * NOT alpine (musl/cryptography friction) and NOT distroless (no shell =
#     no `--help` debugging affordance for first-time evaluators).
#
# What this image does NOT include (out of scope for v4.10 GHCR ship):
#   * `playwright` browsers — optional extra, omitted to keep the image lean.
#     Pull and install them at runtime if needed for a specific scan path.

FROM python:3.11-slim

# QUIRK_VERSION is injected by the release-container.yml workflow from the
# triggering git tag (e.g. `v4.10.0` -> `4.10.0`). No default — the build MUST
# pin a specific PyPI version so the image is a faithful reflection of the
# published wheel.
ARG QUIRK_VERSION

LABEL org.opencontainers.image.source="https://github.com/0xD1g5/QU.I.R.K."
LABEL org.opencontainers.image.title="QU.I.R.K."
LABEL org.opencontainers.image.description="Quantum Infrastructure Readiness Kit — cryptographic inventory scanner + CBOM generator"
LABEL org.opencontainers.image.licenses="MIT"

# System dependencies:
#   * nmap            — required by TLS/SSH scanners
#   * curl            — used by network probes + diagnostics
#   * ca-certificates — TLS trust store for HTTPS scans
# Combined into a single RUN so the apt cache cleanup actually shrinks the
# resulting layer.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        nmap \
        curl \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Non-root user for the runtime. Use a fixed UID/GID so bind-mounted output
# directories from a host user can be chown'd predictably.
RUN groupadd --system --gid 1000 quirk \
 && useradd  --system --uid 1000 --gid quirk --create-home --shell /bin/bash quirk

# Install QU.I.R.K. from the published PyPI wheel — NOT from the local source
# tree. This keeps the container in lock-step with the wheel users would get
# via `pip install qu-i-r-k[all]==X.Y.Z`.
RUN pip install --no-cache-dir "qu-i-r-k[all]==${QUIRK_VERSION}"

USER quirk
WORKDIR /home/quirk

# Default CMD prints --help so `docker run ghcr.io/0xd1g5/quirk:latest` is
# informative on first run (D-LAUNCH Docker — debuggability over minimalism).
CMD ["quirk", "--help"]

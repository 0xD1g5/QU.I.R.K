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

# Chromium + its OS libraries, for report-{stamp}.pdf.
#
# `.[all]` pulls in `[dashboard]`, which includes the playwright PYTHON package
# -- but that package alone renders nothing. The browser binary is a separate
# download (`playwright install`) and its ~19 system shared libraries are a
# third thing again (`playwright install-deps`, which needs apt and therefore
# root). Without the deps the binary exists and fails at exec with
# "libglib-2.0.so.0: cannot open shared object file".
#
# That failure was INVISIBLE: render_pdf_report() catches PlaywrightError and
# returns False, writer.py then sets pdf_path = None, and the scan exits 0 with
# every other artifact written and no warning. Graceful degradation intended for
# "playwright not installed" silently absorbed "playwright installed but
# unlaunchable", so every containerised scan quietly produced no PDF.
#
# Split across the USER boundary on purpose: install-deps needs root for apt;
# the browser download must land in the quirk user's ~/.cache/ms-playwright,
# which is where playwright looks at run time.
RUN playwright install-deps chromium

# Run as a non-root user.
# nmap TCP/SYN scanning requires raw socket access — this is granted via
# cap_add: [NET_RAW] in docker-compose.distributed.yml instead of running
# as root.  This keeps the blast radius minimal if the container is
# compromised or if the image is inadvertently reused in a non-lab context.
RUN useradd --create-home --shell /bin/bash quirk

USER quirk
WORKDIR /home/quirk

# Browser binary into ~/.cache/ms-playwright (see the install-deps note above).
RUN playwright install chromium

# Default CMD is informative — compose overrides `command:` per service:
#   console:  ["serve", "--host", "0.0.0.0", "--port", "8512"]
#   sensor-*: idle (tail -f /dev/null); e2e script drives via docker compose exec
ENTRYPOINT ["quirk"]
CMD ["--help"]

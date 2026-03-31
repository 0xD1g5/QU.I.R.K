# Docker Container Connector Setup

QU.I.R.K.'s container connector uses Syft to enumerate crypto libraries embedded in Docker
container images. It identifies outdated or vulnerable cryptographic libraries (e.g.,
`openssl` < 1.1.1, `pycryptodome`) that carry known vulnerabilities or deprecated algorithm
support.

## Prerequisites

- Docker installed and running
- Syft installed — the connector looks for `syft` on your `PATH`:

  ```bash
  # macOS
  brew install syft

  # Linux (official install script)
  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

  # Via pip (wraps the binary)
  pip install syft
  ```

- Docker socket accessible (default: `/var/run/docker.sock`)

> **Note:** On macOS with Docker Desktop, the socket is at `/var/run/docker.sock` by default.
> On Linux, add your user to the `docker` group if needed:
>
> ```bash
> sudo usermod -aG docker $USER && newgrp docker
> ```

## config.yaml Snippet

```yaml
connectors:
  enable_container: true
  container_targets:
    - "nginx:1.18"                       # public registry image by tag
    - "myregistry.example.com/app:v2"    # private registry image
    - "sha256:abc123def456..."            # image by digest
```

Each entry in `container_targets` is passed directly to `syft` as the image reference.
Syft resolves tags, digests, and registry URLs using Docker's credential helpers.

## What Gets Scanned

Syft enumerates the software bill of materials (SBOM) from the image layers. QU.I.R.K.
filters results to the following crypto-relevant packages:

| Package Name | Category |
|--------------|----------|
| `openssl`, `libssl`, `libssl3`, `libssl1.1` | TLS/SSL library |
| `libcrypto`, `libcrypto3` | Cryptographic primitives |
| `botan`, `libgcrypt`, `libgcrypt20` | Crypto toolkit |
| `nss`, `libnss3` | Network Security Services |
| `mbedtls`, `libmbedtls`, `wolfssl`, `gnutls`, `libgnutls` | Embedded/alternative TLS |
| `cryptography` | Python cryptography library |
| `pyopenssl`, `pycryptodome`, `pycryptodomex` | Python crypto wrappers |
| `bcrypt`, `nacl`, `pynacl` | Password hashing / NaCl |

Any other packages found in the SBOM are ignored. Each matched package produces one finding
in the QU.I.R.K. report.

## How the Scan Works

QU.I.R.K. calls:

```
syft <image_ref> -o json
```

The JSON output is parsed for the `artifacts` list. Each artifact whose `name` matches the
allowlist above is converted to a finding with the library name and version.

The default scan timeout is **120 seconds** per image. Large images or slow registries may
require more time — this is currently set per image, not configurable in `config.yaml`.

## Private Registry Access

For private registries, authenticate before running the scan:

```bash
docker login myregistry.example.com
```

QU.I.R.K. inherits Docker credential helpers from the host environment — no additional
configuration is needed in `config.yaml`.

## Graceful Degradation

If Syft is not found on `PATH`, the container connector returns an empty result set and logs:

```
syft not found — install with: brew install syft
```

All other scanners (TLS, SSH, cloud) continue to run normally. Install Syft and re-run to
include container results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Empty results for all images | Syft not on PATH | Run `which syft`; if not found, install via `brew install syft` or the install script above |
| `permission denied` on `/var/run/docker.sock` | User not in docker group | Run `sudo usermod -aG docker $USER && newgrp docker` |
| Timeout for large image | Default 120s exceeded | Pull the image first with `docker pull <image>` so Syft reads from local cache |
| Private registry: `authentication required` | Docker credentials not set | Run `docker login <registry>` before running the scan |

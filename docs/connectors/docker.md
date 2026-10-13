# Docker Container Connector Setup

QU.I.R.K.'s container connector uses Syft to enumerate crypto libraries embedded in Docker
container images and inventories the cryptographic libraries it finds. The findings evaluator
flags end-of-life OpenSSL release lines (0.x, 1.0.x, 1.1.x, 3.0.x, 3.1.x), Python `cryptography`
below 41, `pyopenssl` below 20 and `libgcrypt` 1.8.x; every other matched library is reported as
a LOW inventory finding.

## Prerequisites

- Syft installed — the connector looks for `syft` on your `PATH`:

  ```bash
  # macOS (Homebrew)
  brew install syft

  # Linux and macOS (Anchore's installer script)
  curl -sSfL https://get.anchore.io/syft | sudo sh -s -- -b /usr/local/bin
  ```

  Do not install Syft from PyPI: the `syft` package there is OpenMined's PySyft, an
  unrelated project, and it does not provide the Anchore `syft` binary.

- A container runtime is optional. For a plain image reference Syft checks the local Docker
  daemon first, then Podman, then containerd, and finally pulls directly from the registry.

> **Note:** If you want Syft to read images from your local Docker daemon on Linux, add your
> user to the `docker` group if needed:
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
    - "nginx@sha256:<64-hex-digest>"       # image pinned by digest
```

Each entry in `container_targets` is passed to `syft` as the image reference, after QU.I.R.K.
validates it as an OCI image reference. Entries that start with `-`, use a local-access prefix
such as `dir:` or `docker-daemon:`, or contain shell metacharacters are rejected and reported as
an `invalid_input` error instead of being scanned.

## What Gets Scanned

Syft enumerates the software bill of materials (SBOM) from the image layers. QU.I.R.K.
filters results to the following crypto-relevant packages:

| Package Name | Category |
|--------------|----------|
| `openssl`, `libssl`, `libssl1.0`, `libssl1.0.0`, `libssl1.1`, `libssl3` | TLS/SSL library |
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
syft -o json -- <image_ref>
```

The JSON output is parsed for the `artifacts` list. Each artifact whose `name` matches the
allowlist above is converted to a finding with the library name and version.

The default scan timeout is **120 seconds** per image. Large images or slow registries may
require more time; raise `scan.timeouts.container_seconds` in `config.yaml` (default `120`).

## Private Registry Access

For private registries, authenticate before running the scan:

```bash
docker login myregistry.example.com
```

Syft reads the registry credentials from the container runtime you logged in with (for the
direct-registry path, from `~/.docker/config.json`), so no additional configuration is needed in
`config.yaml`.

## Graceful Degradation

If Syft is not found on `PATH`, the container connector returns an empty result set and, in
verbose runs, logs a message that begins `syft is not installed`. The rest of that message
carries an install hint that is known to be wrong; follow the Prerequisites section above
instead.

All other scanners (TLS, SSH, cloud) continue to run normally. Install Syft and re-run to
include container results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Empty results for all images | Syft not on PATH | Run `which syft`; if not found, install via `brew install syft` or the install script above |
| `permission denied` on `/var/run/docker.sock` (Docker daemon path) | User not in docker group | Run `sudo usermod -aG docker $USER && newgrp docker` |
| Timeout for large image | Default 120s exceeded | Raise `scan.timeouts.container_seconds`, or pull the image first with `docker pull <image>` so Syft reads from the local daemon |
| Private registry: `authentication required` | Docker credentials not set | Run `docker login <registry>` before running the scan |

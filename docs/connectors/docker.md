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

- A container runtime is not needed. QU.I.R.K. asks Syft to pull each image from its registry; it
  does not read images from a local Docker, Podman or containerd runtime. To scan a locally built
  image, push it to a registry the scan host can reach.

## config.yaml Snippet

```yaml
connectors:
  enable_container: true
  container_targets:
    - "nginx:1.18"                       # public registry image by tag
    - "myregistry.example.com/app:v2"    # private registry image
    - "nginx@sha256:<64-hex-digest>"       # image pinned by digest
```

Each entry must be a plain registry reference: `host/repository:tag`, `host:port/repository:tag`,
a reference pinned by digest, or a Docker Hub name such as `nginx:1.18`. QU.I.R.K. validates every
entry before Syft runs. An entry that starts with `-`, uses a local-access prefix such as `dir:` or
`docker-daemon:`, carries a prefix or port that is not part of a registry address, or contains
shell metacharacters is refused and reported as an `invalid_input` error naming the expected form
`host/repository:tag`, instead of being scanned.

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

QU.I.R.K. runs `syft` with JSON output, selects the registry as the only image source, and
passes the validated image reference after an option terminator. The JSON output is parsed for the `artifacts` list. Each artifact whose `name` matches the
allowlist above is converted to a finding with the library name and version.

The default scan timeout is **120 seconds** per image. Large images or slow registries may
require more time; raise `scan.timeouts.container_seconds` in `config.yaml` (default `120`).

## Private Registry Access

For private registries, authenticate before running the scan:

```bash
docker login myregistry.example.com
```

Syft reads the credentials `docker login` writes to `~/.docker/config.json`, so no additional
configuration is needed in `config.yaml`.

## Graceful Degradation

If Syft is not found on `PATH`, the container phase is skipped with reason `missing-binary` (5.28.1): Scan Coverage reads Not assessed, one `missing_binary` advisory row is recorded and counted as a scan error, `quirk doctor` warns that syft is configured but missing, and, in
verbose runs, a log a message that begins `syft is not installed`. The rest of that message
carries an install hint that is known to be wrong; follow the Prerequisites section above
instead.

All other scanners (TLS, SSH, cloud) continue to run normally. Install Syft and re-run to
include container results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Empty results for all images | Syft not on PATH | Run `which syft`; if not found, install via `brew install syft` or the install script above |
| Timeout for large image | Default 120s exceeded | Raise `scan.timeouts.container_seconds` |
| `invalid_input` with `image_ref_not_plain` | The entry is not a plain registry reference | Rewrite it as `host/repository:tag` |
| Private registry: `authentication required` | Docker credentials not set | Run `docker login <registry>` before running the scan |

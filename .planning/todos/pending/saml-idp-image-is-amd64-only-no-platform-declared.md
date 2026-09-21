# `mh-saml-idp` is an amd64-only image with no `platform:` declaration — it cannot start on aarch64 Linux

**Filed:** 2026-09-17 (demo-prep, operator VM)
**Priority:** P1 before any demo run on non-macOS hardware, P2 otherwise
**Status:** open (worked around on the operator VM by installing binfmt; the compose file is unchanged)

## What happened

On a clean aarch64 Ubuntu VM, `chaoslab-mh-saml-idp-1` exited 255 immediately and the scan
reported `SAML fetch failed ... [Errno 113] No route to host`, then `SAML scan: 0 endpoints`.
Container logs showed the real cause:

```
exec /usr/local/bin/docker-php-entrypoint: exec format error
```

`kenchan0130/simplesamlphp:1.19.7` is published for **amd64 only** (`docker inspect` reports
`Architecture: amd64`). A plain Linux aarch64 host has no binfmt handler registered, so the ELF
cannot execute at all.

## Why nobody noticed

**Docker Desktop on Apple Silicon emulates amd64 silently.** On the maintainer's Mac this
container has run for 33+ hours; `uname -m` inside it reports `x86_64` and nothing warns. The
profile's other 41 containers are all native arm64 — an enumeration over
`docker inspect <image> --format '{{.Architecture}}'` across every `mh-*` container found exactly
one non-arm64 image, and it is this one.

This is the same class as the undeclared `sslyze` dependency found the same day: something that
works on every maintainer machine and fails on a clean host, surviving because the environment
that would expose it was not in anyone's loop.

## Fix

1. Declare `platform: linux/amd64` on the `mh-saml-idp` service so Compose stops emitting
   "the requested image's platform does not match the detected host platform" as a *warning* and
   the intent is explicit in the file.
2. Document the prerequisite in `docs/chaos-lab.md` §3.32: aarch64 Linux hosts must register
   emulation before `PROFILE_ARGS="--profile multihost" ./lab.sh up`:
   ```bash
   docker run --privileged --rm tonistiigi/binfmt --install amd64
   # persistent: sudo apt install -y qemu-user-binfmt   (NOT qemu-user-static — virtual package)
   ```
3. Consider whether an arm64-native SAML IdP image exists and is worth swapping to. Not
   investigated.

## Verification note

The binfmt install was confirmed to work: after it, the container reached `Up`, `nc -zv
10.80.0.41 8080` connected, and a rerun produced `SAML scan: 3 endpoints from 1 targets`.

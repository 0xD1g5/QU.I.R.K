"""Phase 220 D-04: pure registry-refusal classifier + anonymous control probe.

This module holds the CHECKABLE condition behind the one allowed skip in
``tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent``: a
skip fires only when a `docker compose up` failure is BOTH (a) a registry
pull refusal that names a specific image, AND (b) accompanied by a
successful anonymous probe against a known-public repo on the SAME
registry — proving the registry itself is reachable and the refusal is
image-specific, not a network/registry-wide outage that would make the
"control" probe meaningless.

Deliberately stdlib-only (re, json, urllib.request, dataclasses) and
contains NO test-framework import and NO skip-marker call of any kind. This
is load bearing: ``tests/test_skip_registry.py``'s AST walker keys skips by
``(file, enclosing qualname)`` inside ``tests/*.py`` files that contain a
recognized skip construct. A helper module with none of those constructs
introduces no new registry key — the actual skip call lives inside
``test_profile_re_up_is_idempotent`` itself (Task 2), which is the only
qualname that needs one.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

# Anonymous-pull control images, one known-public repo per registry this
# project's chaos lab currently pulls from. Verified live against the
# registry v2 API during Phase 220 research (2026-09-30):
#   ghcr.io/github/super-linter:v4.0.0  -> 200
#   quay.io/prometheus/node-exporter:latest -> 200
# docker.io's library/alpine:3.20 is the de-facto standard "is Docker Hub
# up" control and is included for completeness even though this project's
# chaos lab no longer pulls MinIO from Docker Hub.
CONTROL_IMAGES: dict[str, str] = {
    "ghcr.io": "github/super-linter:v4.0.0",
    "quay.io": "prometheus/node-exporter:latest",
    "docker.io": "library/alpine:3.20",
}

_REFUSAL_KEYWORDS = re.compile(
    r"unauthorized|denied|not found|manifest unknown", re.IGNORECASE
)

# Matches an image reference appearing on the SAME line as a refusal, or on
# a preceding "Pulling <service> (<image>)..." / "pull access denied for
# <image>" style compose/docker line. Image refs look like
# [registry/]repo/path:tag or [registry/]name:tag (bare docker.io images
# have no registry segment, e.g. "minio/minio:RELEASE...").
_IMAGE_REF = re.compile(
    r"(?P<ref>(?:[a-zA-Z0-9.-]+\.[a-zA-Z0-9.-]+(?::\d+)?/)?"
    r"[a-zA-Z0-9][a-zA-Z0-9._/-]*:[a-zA-Z0-9._-]+)"
)

_PULLING_LINE = re.compile(r"Pulling\s+\S+\s+\((?P<ref>[^)]+)\)")
_DENIED_FOR = re.compile(r"(?:pull access )?denied for (?P<ref>\S+?),")


@dataclass(frozen=True)
class RegistryRefusal:
    image: str
    registry: str
    kind: str  # "unauthorized" | "denied" | "not_found"


def _registry_of(image_ref: str) -> str:
    first_segment = image_ref.split("/", 1)[0]
    if "." in first_segment or ":" in first_segment:
        return first_segment
    return "docker.io"


def _kind_of(line: str) -> str | None:
    lowered = line.lower()
    if "unauthorized" in lowered:
        return "unauthorized"
    if "denied" in lowered:
        return "denied"
    if "not found" in lowered or "manifest unknown" in lowered:
        return "not_found"
    return None


def classify_registry_refusal(output: str) -> RegistryRefusal | None:
    """Classify combined stdout+stderr as a named-image registry refusal, or None.

    Returns None for any failure that does not both (a) match a refusal
    keyword and (b) yield a recoverable image reference — including a
    refusal keyword with no identifiable image (cannot name the image, so
    there is nothing checkable to skip on).
    """
    lines = output.splitlines()
    last_pulling_ref: str | None = None

    for line in lines:
        pulling_match = _PULLING_LINE.search(line)
        if pulling_match:
            last_pulling_ref = pulling_match.group("ref")

        if not _REFUSAL_KEYWORDS.search(line):
            continue

        kind = _kind_of(line)
        if kind is None:
            continue

        # Prefer an image ref on the refusal line itself (e.g. "pull access
        # denied for minio/minio, ...").
        denied_match = _DENIED_FOR.search(line)
        ref: str | None = None
        if denied_match:
            ref = denied_match.group("ref")
        else:
            image_match = _IMAGE_REF.search(line)
            if image_match:
                ref = image_match.group("ref")
            elif last_pulling_ref:
                ref = last_pulling_ref

        if not ref:
            continue

        return RegistryRefusal(image=ref, registry=_registry_of(ref), kind=kind)

    return None


def control_probe(
    registry: str,
    *,
    opener=urllib.request.urlopen,
    timeout: int = 10,
) -> tuple[str | None, int | None]:
    """Anonymously probe a known-public repo on `registry`.

    Returns (control_ref, http_status). control_ref is None (and status
    None) when `registry` has no entry in CONTROL_IMAGES — such a registry
    can never yield a skip. Any network exception also yields status None,
    which also means no skip (should_skip requires status == 200).
    """
    control_ref = CONTROL_IMAGES.get(registry)
    if control_ref is None:
        return None, None

    try:
        token_url = (
            f"https://{registry}/token?service={registry}"
            f"&scope=repository:{control_ref.rsplit(':', 1)[0]}:pull"
        )
        token_req = urllib.request.Request(token_url)
        with opener(token_req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
        token = payload.get("token") or payload.get("access_token")

        repo, tag = control_ref.rsplit(":", 1)
        manifest_url = f"https://{registry}/v2/{repo}/manifests/{tag}"
        headers = {
            "Accept": ",".join(
                [
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                ]
            ),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        manifest_req = urllib.request.Request(manifest_url, headers=headers)
        with opener(manifest_req, timeout=timeout) as resp:
            status = getattr(resp, "status", None)
        return control_ref, status
    except Exception:
        return control_ref, None


def should_skip(
    refusal: RegistryRefusal | None, probe: tuple[str | None, int | None]
) -> bool:
    """True only when a named-image refusal is paired with a 200 control probe."""
    if refusal is None:
        return False
    _, status = probe
    return status == 200


def skip_reason(
    refusal: RegistryRefusal, probe: tuple[str | None, int | None]
) -> str:
    control_ref, status = probe
    return (
        f"registry refusal: {refusal.image} refused by {refusal.registry} "
        f"({refusal.kind}); control probe {refusal.registry}/{control_ref} -> "
        f"HTTP {status} (registry reachable, refusal is image-specific) — "
        "see todo 260930 / Phase 220 D-04"
    )

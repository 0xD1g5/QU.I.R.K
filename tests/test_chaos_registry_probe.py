"""Phase 220 D-04: unit tests for the checkable registry-refusal skip condition.

No Docker, no network, no pytest.skip in this module — see
tests/chaos_registry_probe.py's module docstring for why that matters to
tests/test_skip_registry.py's AST walker.
"""
from __future__ import annotations

import json

from tests.chaos_registry_probe import (
    CONTROL_IMAGES,
    RegistryRefusal,
    classify_registry_refusal,
    control_probe,
    should_skip,
    skip_reason,
)

# Verbatim-ish refusal text from the todo
# (.planning/todos/pending/260930-minio-images-withdrawn-from-quay-chaos-lab-cannot-pull-in-ci.md),
# reproduced as the first real-world fixture.
TODO_GHCR_STDERR = (
    "Pulling minio (ghcr.io/0xd1g5/minio:RELEASE.2025-09-07T16-13-09Z)...\n"
    "Error response from daemon: unauthorized: access to the requested "
    "resource is not authorized\n"
)


def test_classify_unauthorized_recovers_image_and_registry() -> None:
    refusal = classify_registry_refusal(TODO_GHCR_STDERR)
    assert refusal is not None
    assert refusal.image == "ghcr.io/0xd1g5/minio:RELEASE.2025-09-07T16-13-09Z"
    assert refusal.registry == "ghcr.io"
    assert refusal.kind == "unauthorized"


def test_classify_docker_hub_denied() -> None:
    output = (
        "Pulling minio (minio/minio:RELEASE.2025-09-07T16-13-09Z)...\n"
        "pull access denied for minio/minio, repository does not exist or "
        "may require 'docker login'\n"
    )
    refusal = classify_registry_refusal(output)
    assert refusal is not None
    assert refusal.registry == "docker.io"
    assert refusal.kind == "denied"
    assert refusal.image.startswith("minio/minio")


def test_classify_manifest_unknown() -> None:
    output = (
        "Pulling mc (ghcr.io/0xd1g5/mc:RELEASE.2024-11-21T17-21-54Z)...\n"
        "manifest unknown: not found: manifest unknown\n"
    )
    refusal = classify_registry_refusal(output)
    assert refusal is not None
    assert refusal.kind == "not_found"
    assert refusal.registry == "ghcr.io"


def test_classify_generic_failure_returns_none() -> None:
    assert classify_registry_refusal("Error: port is already allocated\n") is None
    assert classify_registry_refusal("exit code 1\n") is None
    assert (
        classify_registry_refusal(
            "healthcheck for container XYZ timed out after 60s\n"
        )
        is None
    )


def test_classify_refusal_keyword_without_image_returns_none() -> None:
    # "unauthorized" appears, but no image ref is recoverable from this text.
    assert classify_registry_refusal("unauthorized\n") is None


def _fake_opener(token_payload: dict, status: int):
    class _Resp:
        def __init__(self, body: bytes, status: int):
            self._body = body
            self.status = status

        def read(self) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    calls = {"n": 0}

    def opener(req, timeout=10):
        calls["n"] += 1
        if calls["n"] == 1:
            # token exchange
            return _Resp(json.dumps(token_payload).encode(), 200)
        # manifest fetch
        return _Resp(b"{}", status)

    return opener, calls


def test_control_probe_returns_200_on_success() -> None:
    opener, calls = _fake_opener({"token": "abc"}, 200)
    ref, status = control_probe("ghcr.io", opener=opener)
    assert ref == CONTROL_IMAGES["ghcr.io"]
    assert status == 200
    assert calls["n"] == 2


def test_control_probe_returns_non_200_status() -> None:
    opener, _ = _fake_opener({"token": "abc"}, 404)
    ref, status = control_probe("ghcr.io", opener=opener)
    assert status == 404


def test_control_probe_network_exception_returns_none_status() -> None:
    def opener(req, timeout=10):
        raise OSError("network unreachable")

    ref, status = control_probe("ghcr.io", opener=opener)
    assert ref == CONTROL_IMAGES["ghcr.io"]
    assert status is None


def test_control_probe_unknown_registry_returns_none_none() -> None:
    def opener(req, timeout=10):  # pragma: no cover - must never be called
        raise AssertionError("opener should not be invoked for unknown registry")

    ref, status = control_probe("example.invalid", opener=opener)
    assert ref is None
    assert status is None


def test_should_skip_true_only_when_refusal_and_control_200() -> None:
    refusal = RegistryRefusal(image="ghcr.io/0xd1g5/minio:tag", registry="ghcr.io", kind="unauthorized")
    assert should_skip(refusal, (CONTROL_IMAGES["ghcr.io"], 200)) is True


def test_should_skip_false_when_control_not_200() -> None:
    refusal = RegistryRefusal(image="ghcr.io/0xd1g5/minio:tag", registry="ghcr.io", kind="unauthorized")
    assert should_skip(refusal, (CONTROL_IMAGES["ghcr.io"], 503)) is False
    assert should_skip(refusal, (CONTROL_IMAGES["ghcr.io"], None)) is False


def test_should_skip_false_when_refusal_is_none() -> None:
    assert should_skip(None, (CONTROL_IMAGES["ghcr.io"], 200)) is False


def test_skip_reason_names_image_registry_control_and_status() -> None:
    refusal = RegistryRefusal(image="ghcr.io/0xd1g5/minio:tag", registry="ghcr.io", kind="unauthorized")
    reason = skip_reason(refusal, (CONTROL_IMAGES["ghcr.io"], 200))
    assert "ghcr.io/0xd1g5/minio:tag" in reason
    assert "ghcr.io" in reason
    assert CONTROL_IMAGES["ghcr.io"] in reason
    assert "200" in reason
    assert "unauthorized" in reason

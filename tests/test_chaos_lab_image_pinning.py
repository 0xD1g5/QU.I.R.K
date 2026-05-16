"""CHAOS-05: Compose-file image-pin policy gate.

Asserts every `image:` field in `quantum-chaos-enterprise-lab/docker-compose.yml`
is pinned to a specific tag (not `:latest`, not a bare image reference).

Pure file parse — no Docker daemon required; runs in the default pytest suite.
"""
from pathlib import Path

import yaml

COMPOSE_FILE = (
    Path(__file__).resolve().parent.parent
    / "quantum-chaos-enterprise-lab"
    / "docker-compose.yml"
)


def _is_pinned(image: str) -> bool:
    if image.endswith(":latest"):
        return False
    if ":" not in image:
        return False
    return True


def test_every_image_is_pinned():
    data = yaml.safe_load(COMPOSE_FILE.read_text())
    violations = []
    for name, svc in (data.get("services") or {}).items():
        if not isinstance(svc, dict):
            continue
        img = svc.get("image")
        if img is None:
            # build-only service (uses `build:` context); pinning enforced
            # via the Dockerfile's `FROM` directive in the service subdir.
            continue
        if not _is_pinned(img):
            violations.append(f"{name}: {img}")
    assert not violations, (
        "Unpinned chaos-lab images (CHAOS-05 policy violation):\n  "
        + "\n  ".join(violations)
    )

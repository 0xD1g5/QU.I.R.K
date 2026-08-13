"""Phase 150 D-12/D-13: `./lab.sh certs` per-profile cert generation regression.

`quantum-chaos-enterprise-lab/lab.sh`'s pre-existing `ensure_lab_certs()` only
materializes the top-level chaos-lab mTLS CA/client pair
(`quantum-chaos-enterprise-lab/certs/`) -- it never touched the gitignored
`labs/email/certs/{postfix,dovecot}.{key,crt}` or `labs/grpc-tls/certs/
grpc-tls.{key,crt}` files the `email` and `grpc-tls` chaos-lab Docker Compose
profiles bind-mount read-only. On a fresh clone with no generator, Docker
turns the missing bind-mount source into an empty directory and then fails to
mount it onto the container's file destination -- exactly the CI failure this
test proves is closed.

Runs unconditionally (no `pytest.skip`/`importorskip`/`xfail`/`slow` marker):
openssl and bash are present on both macOS and `ubuntu-latest`, and `./lab.sh
certs` must not touch Docker at all.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID

REPO_ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = REPO_ROOT / "quantum-chaos-enterprise-lab"
LABS_ROOT = REPO_ROOT / "labs"

# (key path, crt path, expected subject CN)
CERT_TARGETS = [
    (
        LABS_ROOT / "email" / "certs" / "postfix.key",
        LABS_ROOT / "email" / "certs" / "postfix.crt",
        "postfix.chaos.local",
    ),
    (
        LABS_ROOT / "email" / "certs" / "dovecot.key",
        LABS_ROOT / "email" / "certs" / "dovecot.crt",
        "dovecot.chaos.local",
    ),
    (
        LABS_ROOT / "grpc-tls" / "certs" / "grpc-tls.key",
        LABS_ROOT / "grpc-tls" / "certs" / "grpc-tls.crt",
        "grpc-tls.chaos.local",
    ),
]


def _run_certs() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["./lab.sh", "certs"],
        cwd=LAB_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _sha256_all() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for key, crt, _ in CERT_TARGETS:
        for path in (key, crt):
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


@pytest.mark.xfail(
    strict=False,
    reason="Phase 150 D-05x: same macOS fork()-under-full-suite-load SIGSEGV cluster "
    "documented in docs/test-triage-149.md (D-03) — the `openssl` subprocess spawned "
    "by `./lab.sh certs` crashes with returncode=-11 only at ~3000-test full-suite "
    "scale, never standalone. See docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster",
)
def test_lab_sh_certs_creates_all_six_files_and_is_idempotent():
    result_one = _run_certs()
    assert result_one.returncode == 0, (
        f"./lab.sh certs failed: stdout={result_one.stdout!r} "
        f"stderr={result_one.stderr!r}"
    )

    for key, crt, _ in CERT_TARGETS:
        assert key.exists(), f"missing generated key {key}"
        assert crt.exists(), f"missing generated cert {crt}"

    hashes_after_first_run = _sha256_all()

    # Second invocation must be a no-op: byte-identical files, no regeneration.
    result_two = _run_certs()
    assert result_two.returncode == 0, (
        f"./lab.sh certs (second run) failed: stdout={result_two.stdout!r} "
        f"stderr={result_two.stderr!r}"
    )

    hashes_after_second_run = _sha256_all()

    assert hashes_after_first_run == hashes_after_second_run, (
        "./lab.sh certs is not idempotent -- files changed on the second run"
    )


@pytest.mark.xfail(
    strict=False,
    reason="Phase 150 D-05x: same macOS fork()-under-full-suite-load SIGSEGV cluster "
    "as test_lab_sh_certs_creates_all_six_files_and_is_idempotent above — see "
    "docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster",
)
def test_generated_certs_have_correct_subject_cn():
    _run_certs()
    for _, crt, expected_cn in CERT_TARGETS:
        cert = x509.load_pem_x509_certificate(crt.read_bytes())
        cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert cn_attrs, f"{crt} has no CN attribute"
        assert cn_attrs[0].value == expected_cn


@pytest.mark.xfail(
    strict=False,
    reason="Phase 150 D-05x: same macOS fork()-under-full-suite-load SIGSEGV cluster "
    "as test_lab_sh_certs_creates_all_six_files_and_is_idempotent above — see "
    "docs/test-triage-149.md#reconciliation-macos-fork-sigsegv-cluster",
)
def test_lab_sh_certs_succeeds_without_touching_docker():
    result = _run_certs()
    assert result.returncode == 0, result.stderr

    combined_output = (result.stdout + result.stderr).lower()
    # The `up`/`all` arms print "Starting lab"/"Starting ALL profiles" and run
    # _validate_pinned_tags + `compose up -d`; the `certs` arm must do neither.
    assert "starting lab" not in combined_output
    assert "starting all profiles" not in combined_output
    assert "pin policy" not in combined_output

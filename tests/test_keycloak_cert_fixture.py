"""Regression test for TRIAGE-176-01 (Phase 186, plan 186-01).

`quantum-chaos-enterprise-lab/certs/keycloak.crt` was a byte-identical hand-copy of
`certs/modern.crt`, serving `CN=modern.chaos.local` instead of the Keycloak-specific
subject that `nginx/identity/keycloak/nginx.conf` declares as its `server_name`. The
defect had no generator provenance in `scripts/gen-certs.sh` at all.

Per D-04, this test asserts behaviour on the committed artifact directly -- it does not
grep for a generator line (a line can exist and still emit the wrong subject) and does
not probe a live container (that would require a `live_infra` skip-registry entry and
Docker health is known to move this suite's collected node count). It needs no Docker
and runs unconditionally in the `Linux Full Suite` CI job.

Per D-05, this test asserts the subject CN only -- no byte-identity/digest-uniqueness
assertion against sibling fixtures. The one-shot duplicate sweep (D-03) is separate,
recorded evidence, not a standing test.
"""
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID

CERT_PATH = (
    Path(__file__).resolve().parent.parent
    / "quantum-chaos-enterprise-lab"
    / "certs"
    / "keycloak.crt"
)


def test_keycloak_cert_subject_cn_is_keycloak_chaos_local():
    cert = x509.load_pem_x509_certificate(CERT_PATH.read_bytes())
    cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    assert cn_attrs, f"{CERT_PATH} has no CN attribute"
    assert cn_attrs[0].value == "keycloak.chaos.local"

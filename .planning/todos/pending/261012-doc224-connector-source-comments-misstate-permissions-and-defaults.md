---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONN-GCP-*, DCL-CONN-VAULT-*, DCL-CONN-DB-*
priority: low
area: quirk/scanner/gcp_connector.py, quirk/scanner/vault_connector.py, quirk/scanner/db_connector.py
status: pending
resolves_phase: null
---

# Three connector docstrings/comments state permissions or defaults the code or the provider contradict

Found while writing the GCP, Vault and database connector pages from the code rather than from the comments. The
docs now state the verified behaviour; the comments below should be corrected so the next reader is not misled.

- `quirk/scanner/gcp_connector.py` module docstring lists `roles/storage.objectViewer (or storage.buckets.list)` as
  the minimum role for the Cloud Storage scan. Google's IAM role reference (`roles/storage.objectViewer`, 8
  permissions) does not include `storage.buckets.list`, which the scan's `buckets().list` call needs; a role that does
  is `roles/storage.viewer`.
- `quirk/scanner/vault_connector.py` module docstring lists `read on <pki_mount>/cert/ca` and `.../cert/ca_chain`; the
  calls the code makes are hvac `read_ca_certificate` (GET `/v1/<mount>/ca/pem`) and `read_ca_certificate_chain`
  (GET `/v1/<mount>/ca_chain`), which Vault documents as unauthenticated endpoints.
- `quirk/scanner/db_connector.py` (MySQL branch) says an unset password lets "pymysql read from defaults file / env".
  The call never passes `read_default_file` (PyMySQL default `None`) and the `password` default is `''`, so an unset
  password is simply sent empty. Reproduce:
  `python -c "import inspect; from pymysql.connections import Connection as C; s=inspect.signature(C.__init__).parameters; print(repr(s['password'].default), s['read_default_file'].default)"` -> `'' None`.

- [ ] Correct the three comments (no behaviour change), or pass `read_default_file` deliberately if the defaults-file
      fallback is wanted.

## Feasibility & Effort

**CONFIRMED** (each claim checked against the provider's published role/endpoint reference or the installed library on
2026-10-12). Effort **S**: comment edits only; the MySQL item is a one-line decision. **No spike needed.**

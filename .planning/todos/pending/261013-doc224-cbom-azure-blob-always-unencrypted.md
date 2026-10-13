---
type: todo
created: 2026-10-13
source: Phase 224 GC3 (REST3) wording sweep; ledger row DCL-CBOM-0437 (docs/cbom-guide.md "Data at rest" bullet)
priority: medium
area: quirk/cbom/builder.py (S3 / AZURE_BLOB branch), quirk/scanner/azure_connector.py (_scan_blob_encryption)
status: pending
resolves_phase: null
---

# The CBOM marks every Azure Blob container "unencrypted" and never records AES-256 for it

`_scan_blob_encryption` writes `protocol="AZURE_BLOB"` with `service_detail` `BLOB/cmk`, `BLOB/platform-managed` or
`BLOB/unknown` (`quirk/scanner/azure_connector.py:212`, `:217`, `:226`, `:261`). The CBOM builder's Blob branch
(`quirk/cbom/builder.py:771-790`) registers AES-256 only when the detail contains `sse-cmek` or
`sse-microsoft-storage` (`:778`), values no scanner writes, and otherwise appends the note "unencrypted S3/Blob
endpoint — no server-side encryption observed". Azure Storage encrypts at rest in every one of those states.

Probe (`work/probes/gc3-rest3-cbom-dar-probe.py` in the phase directory, build_cbom on one row each): all three
`AZURE_BLOB` details give no algorithm and the "unencrypted" note; `S3/sse-s3` and `S3/sse-kms-cmk` give AES-256.

- [ ] Match the builder's postures to the connector's values (`BLOB/cmk`, `BLOB/platform-managed` -> AES-256;
      `BLOB/unknown` -> a "posture unknown" note, not "unencrypted").
- [ ] Add a builder test that feeds the connector's real `service_detail` strings.
- [ ] Then drop the "known defect" sentence from docs/cbom-guide.md (Step 1, Data at rest).

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `quirk/cbom/builder.py:776-790` and
  `quirk/scanner/azure_connector.py:205-262`.
- Effort **S**: a mapping change plus a test. Unknown: whether the Blob scoring path (`quirk/intelligence/evidence.py`
  data-at-rest counting) reads the same strings correctly; check it in the same change.

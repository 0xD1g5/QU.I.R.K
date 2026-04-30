# CBOM Golden Fixture Changelog

Per D-09 (Phase 42) — one entry per intentional snapshot change.

## 2026-04-30 — Phase 42: shape-coverage expansion

**Reason:** Added three goldens to cover the curated CBOM output shapes
per D-07 (Phase 42 — CBOM Correctness Audit):

- `expected_pki_cbom.json` — TLS-with-cert shape (mTLS step-CA, port 17443)
- `expected_vault_cbom.json` — Data-at-rest shape (VAULT protocol; Pass 2/3 skipped, Pass 1 emits algorithm components only)
- `expected_saml_cbom.json` — Identity shape (SAML IdP signing cert; no TLS protocol component)

**Files touched:** new files only — no diff in `expected_email_cbom.json` or `expected_broker_cbom.json`.

**Regen:** `REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py::test_generate_fixtures -s -m ""`

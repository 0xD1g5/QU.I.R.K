# Golden CBOM Fixtures

Lab-driven structural snapshots of the CycloneDX CBOM produced by
`quirk.cbom.builder.build_cbom()` for the email and broker chaos-lab
profiles. Anchors Phase 35 / D-04 verification for requirements
**CBOM-01**, **CBOM-02**, **CBOM-03**, and **CBOM-04**.

## Source of truth

- `labs/email/expected_results.md` — port map for the 7 email TLS endpoints
  (6 distinct labels: SMTP-STARTTLS, SMTPS, IMAP-STARTTLS, IMAPS,
  POP3-STARTTLS, POP3S — ports 30025/30587 share `SMTP-STARTTLS`).
- `labs/broker/expected_results.md` — port map for the 6 broker endpoints
  (3 TLS: KAFKA-TLS, AMQPS, REDIS-TLS — 3 plaintext: KAFKA-PLAIN,
  AMQP-PLAIN, REDIS-PLAIN).

The endpoint generators in `tests/test_cbom_motion_golden.py` mirror these
port maps verbatim — same labels, same ports, same cipher suites. No Docker
required at test time.

## Snapshot scope (structural — not byte-for-byte)

Each fixture is a sorted list of components keyed by `bom_ref`. For each
component we capture only the **stable** fields:

- `bom_ref`, `name`, `type`
- `crypto_properties.asset_type` (e.g. `algorithm`, `certificate`, `protocol`)
- `crypto_properties.protocol_properties.{type, version}`
- Sorted list of cipher-suite **names** under each protocol component

We deliberately strip volatile fields: `metadata.timestamp`, BOM
`serial_number`, BOM `version`, certificate `not_valid_before` /
`not_valid_after`, and any UUIDs. This keeps the diff stable across runs
and library bumps that only affect serialization metadata.

## Regeneration

When the scanner emits a new label, the builder Pass-N layout changes
intentionally, or `cyclonedx-python-lib` bumps a major version that affects
component shapes, regenerate the fixtures with:

```bash
REGEN_CBOM_FIXTURES=1 python -m pytest \
    tests/test_cbom_motion_golden.py::test_generate_fixtures -s
```

Then `git diff tests/fixtures/cbom/` to review the change. Commit the
updated JSON files only after confirming the diff matches the intended
production behavior change.

## When **not** to regenerate

If `test_email_cbom_matches_snapshot` or `test_broker_cbom_matches_snapshot`
fails unexpectedly during normal development, the change is most likely a
**regression** — investigate the builder diff before regenerating. Fixture
churn must always be paired with an explicit, plan-level decision.

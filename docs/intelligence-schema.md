# Intelligence JSON Output

Each scan writes `intelligence-<timestamp>.json` in the configured output directory.

## Versioning

- `intelligence_version`: schema/version marker for this file.
- Current version: `1.0.0`.

## Top-level fields

- `intelligence_version`: string
- `generated_utc`: UTC timestamp when the file was generated
- `assessment`: metadata only
  - `name`
  - `report_owner`
  - `data_classification`
  - `timezone`
- `evidence_summary`: normalized evidence from endpoints + findings
  - protocol counts, plaintext HTTP counts, mTLS signals
  - certificate observation counts (expired/expiring/self-signed, key type counts)
  - scan error and TLS enum coverage metrics
- `score_breakdown`: readiness score output
  - `score`, `rating`, `subscores`, `drivers`
- `confidence_factors`: confidence output
  - `confidence_score`, `confidence_rating`, `factor_breakdown`
- `roadmap`: phased roadmap output
  - `roadmap_version`, `item_count`, `phase_counts`, `items`

## Data safety

- The intelligence JSON excludes raw certificate PEMs and secrets.
- Output is summary-level and deterministic for identical inputs.

# Intelligence Output Schema

This project uses a deterministic JSON shape for intelligence outputs.

## Versioning

- `schema_version` is required in every intelligence payload.
- Current version: `1.0.0`.
- Backward incompatible changes must bump the major version.
- Additive, backward compatible changes must bump the minor version.

## Top-level Structure

```json
{
  "schema_version": "1.0.0",
  "generated_utc": "2026-02-19T20:00:00Z",
  "score_inputs": {},
  "score_result": {},
  "confidence_result": {},
  "roadmap": []
}
```

## Fields

- `score_inputs` (`ScoreInputs`)
  - `total_endpoints` (int)
  - `tls_success` (int)
  - `ssh_success` (int)
  - `http_plain` (int)
  - `unknown_open` (int)
  - `high_impact` (int)
- `score_result` (`ScoreResult`)
  - `score` (int)
  - `rating` (str)
  - `drivers` (array of `{label: str, points: int}`)
- `confidence_result` (`ConfidenceResult`)
  - `confidence_score` (int)
  - `confidence_rating` (str)
  - `coverage_pct` (float)
  - `tls_enum_coverage_pct` (float)
  - `blockers_top` (array of `{category: str, count: int}`)
- `roadmap` (array of `RoadmapItem`)
  - `wave` (str)
  - `title` (str)
  - `rationale` (str)
  - `deliverable` (str)
  - `owner_hint` (str)
  - `effort` (str)

## Determinism

- `IntelligenceReport.to_json()` emits compact JSON with sorted keys.
- List ordering is caller-controlled and preserved.

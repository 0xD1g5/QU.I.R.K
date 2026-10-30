---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc-D; ledger rows DCL-INTELSCHEMA-0065 and the trend-example rows in docs/intelligence-schema.md
priority: low
area: quirk/intelligence/trends.py (_SEVERITY_BUCKET comment, compute_trend_report docstring, _sample_findings)
status: pending
resolves_phase: null
owner: "999.134"
---

# Trend report puts INFO-severity rows in the samples and totals while its comments say INFO is excluded

`quirk/intelligence/trends.py` documents decision D-05 as "INFO intentionally absent - excluded from counts and samples"
(the `_SEVERITY_BUCKET` comment, line 37) and the `compute_trend_report` docstring repeats "INFO/None -> excluded from
counts and samples". The code only excludes INFO from the three severity buckets. `_sample_findings` includes every row
whose `(host, port, protocol)` key is new or resolved, whatever its severity, and `new_total` / `resolved_total` are
`len(new_keys)` / `len(resolved_keys)`:

```
GET /api/trends  (current session has CRITICAL, HIGH, MEDIUM, LOW and INFO rows on five hosts; previous has LOW and INFO)
  new_high 2  new_medium 1  new_low 1  new_total 5   <- INFO is in new_total, in no bucket
  new_findings_sample: ... {"host": "10.0.3.4", "severity": "INFO"}   <- INFO is in the sample
  resolved_findings_sample: 10.0.3.9 LOW, 10.0.3.8 INFO
```

`docs/intelligence-schema.md` now describes the actual behaviour (INFO is excluded from the buckets only; NULL severity
and INFO sort after LOW in the samples). Either the behaviour or the comments are wrong; the doc follows the behaviour.

- [ ] Decide D-05's intent: if INFO must stay out of the dashboard's sample lists, filter it in `_sample_findings` and
      decide whether `new_total` should also drop it; otherwise correct the two comments.
- [ ] Update the "Severity buckets" and "Sample arrays" text in `docs/intelligence-schema.md` to match the decision.
- [ ] Add a test pinning whichever behaviour is chosen (there is none for INFO today).

## Feasibility & Effort

**CONFIRMED** by a live `GET /api/trends` against an in-memory two-session database (script: seed rows with severities
CRITICAL/HIGH/MEDIUM/LOW/INFO, then call the endpoint through `TestClient` with `get_db` overridden); the comment text and
the sample/total code paths were read at `quirk/intelligence/trends.py:37`, `:195-205` and the `new_total=len(new_keys)`
return. Effort **S**: either a one-line filter in `_sample_findings` plus a test, or two comment edits. No spike needed.

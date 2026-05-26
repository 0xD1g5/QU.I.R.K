# Phase 106: Architecture Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 106-Architecture Documentation
**Areas discussed:** Windows scope, Merge trigger, Dedup & replay, Version-skew, Doc location & structure, Enrollment manifest fields, Coverage-warning & staleness, Air-gap export/import

---

## Windows scope (floor vs ceiling)

| Option | Description | Selected |
|--------|-------------|----------|
| Floor in v5.4, ceiling → v5.5 | OS-agnostic contract + pip install + POSIX-ism audit + windows-latest CI smoke; PyInstaller/Scheduled-Task → v5.5 | ✓ |
| Floor + ceiling both in v5.4 | Also ship full PyInstaller frozen EXE + Scheduled Task; risks milestone slip | |

**User's choice:** Floor in v5.4, ceiling → v5.5
**Notes:** Matches the memory-note lean (floor-in / ceiling-likely-v5.5). pywin32 Service out entirely either way.

---

## Merge trigger mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Manual `quirk sensor merge` | Operator-invoked; simplest, no poll infra | |
| Automatic poll on full check-in | Auto-merge when all sensors push; more state | |
| Both: manual now, auto-hook stubbed | Ship manual; design `merge_scan()` so v5.5 auto-trigger needs no refactor | ✓ |

**User's choice:** Both — manual now, auto-hook stubbed
**Notes:** No poller built in v5.4; doc records the standalone-callable seam only.

---

## Dedup & replay policy

| Option | Description | Selected |
|--------|-------------|----------|
| Research defaults | ±15 min replay window; 10 MB/413; dup payload_id → 409; no TTL | ✓ |
| Research defaults + TTL cleanup | Same + 90-day purge of accepted payload_ids | |

**User's choice:** Research defaults (no TTL in v5.4)
**Notes:** Unbounded growth acceptable for single-tenant volume; TTL deferred to v5.5.

---

## Version-skew handling

| Option | Description | Selected |
|--------|-------------|----------|
| Warn-only, accept | `extra='ignore'`; accept regardless; non-blocking registry warning | ✓ |
| Reject on major-version mismatch | 422 on major mismatch; hostile to air-gapped fleets | |

**User's choice:** Warn-only, accept

---

## Doc location & structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single doc + diagrams | `docs/architecture-distributed.md` + Mermaid topology & push-sequence | ✓ |
| Single doc, prose-only | Same file, no diagrams | |
| Split docs | Separate cross-linked files; more drift surface | |

**User's choice:** Single doc + diagrams
**Notes:** 10-section outline agreed (overview → forbidden additions → Windows scope).

---

## Enrollment manifest fields

| Option | Description | Selected |
|--------|-------------|----------|
| Full set incl. engagement label | sensor_id, segment, engagement (nullable), enrolled_at, last_push_at, expected_cadence_minutes, sensor_version | ✓ |
| Minimal set, engagement → v5.5 | Drop engagement label for now | |

**User's choice:** Full set incl. engagement label
**Notes:** Engagement label cheap now; matches consulting use case.

---

## Coverage-warning & staleness thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Research defaults | 24h cadence; overdue at 2× cadence; coverage_warning list; 30-day staleness; overridable | ✓ |
| Stricter (1× cadence overdue) | Overdue at first missed window; noisier | |

**User's choice:** Research defaults
**Notes:** Partial coverage scored-but-flagged, never silently merged.

---

## Air-gap export/import contract

| Option | Description | Selected |
|--------|-------------|----------|
| Identical payload schema | export-results = same wire payload; import = same ingest+dedup path | ✓ |
| Separate import format | Distinct file format + import path; doubles maintenance | |

**User's choice:** Identical payload schema
**Notes:** Carve-out added by Claude — ±15-min replay window is HTTPS-push only; air-gap import skips the time-window check but keeps payload_id dedup (transport-conditional, not payload-conditional).

---

## Claude's Discretion

- Mermaid diagram styling and per-section prose depth.
- Whether wire contract is presented as JSON example, field table, or both.

## Deferred Ideas

- Windows ceiling (PyInstaller/Scheduled Task/signed) → v5.5
- Automatic merge trigger → v5.5
- `sensor_pushes` dedup TTL/cleanup → v5.5
- Weighted scoring Option B → v5.5
- pywin32 Service / Windows Event Log / MSI installer → v5.5+

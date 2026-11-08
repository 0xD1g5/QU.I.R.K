---
type: todo
created: 2026-11-08
title: Malformed S3 endpoint fails as 'Invalid region'
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: low
area: S3 connector and its form
status: pending
resolves_phase: null
owner: null
---

# Malformed S3 endpoint fails as 'Invalid region'

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261107-s3-endpoint-invalid-region`) when PR #70 lands.

## Observed

A malformed S3 endpoint ("http://localhost:29000,") fails as "EndpointResolutionError: Invalid region": the wrong field is blamed and the form does not validate the URL.

## Evidence

passA.md attempt 1 (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Small (1-2h): validate the endpoint in the form/connector and name the field.

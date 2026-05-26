# Backlog 999.87 — CMVP cache file missing in installed package

**Type:** bug (minor)
**Source:** v5.4 live human-UAT (UAT-112-03 merge step), 2026-05-26
**Candidate for:** v5.5

## Problem

During `quirk sensor merge` the console prints repeated warnings:

```
CMVP cache unavailable: [Errno 2] No such file or directory:
  /usr/local/lib/python3.11/site-packages/quirk/compliance/cmvp_cache.json
```

`cmvp_cache.json` is not shipped in the wheel / installed site-packages, so any
pip-installed deployment (including the distributed lab images) logs this on every
merge/score. Output is otherwise correct (Score 95), but the noise is unprofessional
for a consulting-grade tool and may mask a real compliance-data gap.

## Fix

Either package `cmvp_cache.json` in the wheel (add to `pyproject.toml` package-data /
MANIFEST) or generate it on first use with a graceful fallback. Add a packaging test
that asserts the file is importable from the installed package.

## References

- `.planning/v5.4-deferred-uat.md` (notes)
- `quirk/compliance/` (CMVP cache loader)

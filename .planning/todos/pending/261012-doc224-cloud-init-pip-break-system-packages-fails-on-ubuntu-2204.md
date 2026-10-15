---
type: todo
created: 2026-10-13
source: Phase 224 gap closure C (docs/deployment-cloud-console.md audit)
priority: low
area: deploy/cloud-init.yaml
status: pending
resolves_phase: null
owner: "999.129"
---

# `deploy/cloud-init.yaml` (and the manual path) run `pip3 install --break-system-packages`, which Ubuntu 22.04's pip rejects

**Filed:** 2026-10-13 (Phase 224 gap closure C, docs/deployment-cloud-console.md audit)
**Priority:** P3 — the documented cloud-init path fails at the install step on a still-supported Ubuntu LTS
**Status:** open
Frontmatter added by Phase 227 (D-02): priority derived from the body Priority line (P3 → low).

## What happens

`deploy/cloud-init.yaml:106` runs `pip3 install --break-system-packages "quirk-scanner[all]"`, and
`docs/deployment-cloud-console.md` repeats it in section 4.1 and section 7. `--break-system-packages` was added in
pip 23.0.1 (https://pip.pypa.io/en/stable/news/ -> "23.0.1 (2023-02-17) ... Implement --break-system-packages").
Ubuntu 22.04 ships `python3-pip 22.0.2+dfsg-1ubuntu0.7`
(https://packages.ubuntu.com/jammy/python3-pip), so pip aborts with an unknown-option error and the unit the
cloud-init file then enables (`/usr/local/bin/quirk`) does not exist. Ubuntu 22.04 has Python 3.10, so the package
itself would install; only the flag breaks it. Debian 12 (pip 23.0.1) and Ubuntu 24.04 (pip 24.0) are fine, and
Debian 11 ships Python 3.9, below `requires-python >= 3.10`.

`docs/deployment-cloud-console.md` now says the guide needs Debian 12 or Ubuntu 24.04 or newer, which is the
documentation-side fix. The cloud-init file itself still advertises "a fresh Debian/Ubuntu VM".

## Fix

Install into a venv (`python3 -m venv /opt/quirk && /opt/quirk/bin/pip install ...`) and point `ExecStart` at the
venv's `quirk`, which works on every supported release and needs no PEP 668 override, or probe the pip version and
add the flag only when it is accepted. Update the unit file, the cloud-init copy, and sections 4.1 and 7.

## Feasibility & Effort

- Feasibility: CONFIRMED from the pip release notes and the Debian/Ubuntu package pages (not by booting a 22.04 VM).
- Effort: S — one install line in two files plus the matching doc lines.
- Unknowns: whether anyone relies on `/usr/local/bin/quirk` from the unit file.
- Spike needed: no.

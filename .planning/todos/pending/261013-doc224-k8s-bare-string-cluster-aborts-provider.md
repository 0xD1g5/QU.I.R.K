---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Connectors Block gke/aks_clusters)
priority: low
area: quirk/scanner/k8s_connector.py
status: pending
resolves_phase: null
owner: "999.126"
---

# One malformed GKE/AKS cluster entry skips every later cluster

For GKE the cluster path is built outside the per-cluster `try` (`quirk/scanner/k8s_connector.py:124-128`
`cfg['location']`), and the per-element `except` handlers call `cfg.get(...)` (`:175`, `:261`), which raises
again on a bare string. The outer handler then ends the whole provider loop. So a bare-string entry stops
GKE and AKS alike. docs/configuration.md now says this.

- [ ] Guard with `isinstance(cfg, dict)` per element, or validate the shape at load in quirk/config.py.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (the fork probe reproduced the skip for both providers).
- **Effort: S.**
- **Unknowns:** none.
- **Spike:** no.

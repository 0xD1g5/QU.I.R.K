---
type: todo
created: 2026-09-13
source: operator decision after phase 203 — "instead of fixing it, start building the structure for doc id being separate"
priority: high
requirement: none yet — candidate for a v5.24 tail phase or v5.25
resolves_phase: null
---

# Decouple document *identity* from document *URL* in `HARDWARE_MATRIX`

**Operator decision, 2026-09-13:** do **not** spend a phase re-sourcing the 7 rotted URLs. The
operator is taking the URL re-sourcing themselves. QUIRK's side of the work is the **structural
change that stops this recurring** — which is the higher-value half.

**Scheduling: deferred.** Not now — v5.24 continues through Phases 204-208 first. This is a
candidate for a v5.24 tail phase or v5.25.

## The problem this solves

7 of 8 `HARDWARE_MATRIX` `source_url`s died in roughly three months (Phase 203). That is not bad
luck — it is what the current sourcing strategy selects for. Every rotted entry pinned a **deep link
into a version-numbered documentation tree**:

```
docs.fortinet.com/document/fortigate/7.6.0/administration-guide/761917/...
docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/decryption/...
thalesdocs.com/gphsm/luna/7/docs/network/Content/admin_partition/pqc.htm
```

Vendors rotate those on every release. **Replacing seven deep links with seven newer deep links
buys exactly one release cycle.**

## The key observation

Both documents whose URLs changed but which were still findable were findable **by their document
identifier, not their path**:

| Vendor | URL changed | Identifier survived |
|---|---|---|
| F5 | `support.f5.com/csp/article/K000141701` → `my.f5.com/manage/s/article/K000141701` | **`K000141701`** |
| Fortinet | `.../7.6.0/.../761917/post-quantum-preshared-keys` → `.../8.0.0/.../527690/post-quantum-preshared-key-support` | **`527690`** (the new doc number, found by title search) |

The article ID is the durable key. The URL is a rendering of where that ID currently lives.
**Re-sourcing should be a lookup, not a search.**

## Proposed shape (design, not locked — needs a discuss pass)

Per entry, alongside the existing `source_url`:

- **`doc_id`** — the vendor's own stable identifier (`K000141701`, `527690`, `a00128516en_us`,
  a spec name/revision). Nullable where a vendor genuinely has none.
- **`doc_id_scheme`** — which vendor namespace the id belongs to, so it is resolvable
  (`f5-kb`, `fortinet-docid`, `hpe-docid`, …). Without this, a bare number is not actionable.
- **`evidence`** + **`evidence_checked`** — a short verbatim line from the source that supports this
  entry's `pqc_status`/`notes` claim. This is the idea offered and deliberately deferred at Phase
  203's discuss (`203-CONTEXT.md` §Deferred Ideas); the rot pattern is the argument for it. Turns
  the next re-verification into a **diff** rather than a re-read, and makes a silent vendor rewrite
  **detectable**.

Open questions for the discuss pass:
- Is `doc_id` a required key (gated like `last_verified` now is) or optional-with-a-reason?
- Do we prefer stable anchors (PSIRT indexes, trust centers, product landing pages) over precise
  deep links as a *policy*, accepting less precision for more durability?
- Does `evidence` live per entry, or per claim within an entry (several entries assert two or three
  separable things)?

## The other half — a link check that reads content, not status codes

Phase 203's decisive finding: **HTTP 200 is not evidence of content.**

| Vendor | Serves | Why a status check passes it |
|---|---|---|
| Cisco | 200 + "No Data Found For This Page." | 200 |
| Intel | 200 + a generic product-selector page | 200, and it is real content |
| Fortinet (pre-fix) | silent 301 → "Getting started" | 200, real content, no error anywhere |

A catalog can be simultaneously *"every URL returns 200"* and *"no URL supports its entry's claim"*.
Any checker keyed on status codes reports the first and misses the second.

With `evidence` present, a useful check becomes possible: **assert the page still contains the
entry's evidence string.** That is a real freshness signal rather than a liveness ping. Note it
cannot run in CI as-is — six of these hosts block non-browser clients — so it is an operator-run or
browser-driven check, not a GitHub Action. Worth designing that constraint in from the start rather
than discovering it later.

## Ownership split (operator decision 2026-09-13)

| Half | Owner |
|---|---|
| Re-sourcing the 7 rotted URLs + verifying claims | **Operator** — see the work matrix in `hardware-matrix-source-urls-broadly-rotted.md` |
| `doc_id` / `evidence` structure + content-aware check | **QUIRK / this todo** |

These interlock: the structure should land in a shape the operator's re-sourcing can populate as it
goes, so the two halves converge rather than one redoing the other. If the structural work lands
first, the operator fills `doc_id`/`evidence` while re-sourcing. If re-sourcing lands first, the
structure backfills from what was found. **Neither should block the other** — but sequencing the
structure first is cheaper, because it avoids a second pass over the same eight entries.

## Does NOT include

- Re-sourcing the URLs (operator's half).
- Rewriting the IPMI/Intel claim, which is unfalsifiable as written — it bundles a historical fact
  with a negative-existence claim no single source can support. That is a separate design decision,
  tracked in `hardware-matrix-source-urls-broadly-rotted.md`.
- Bumping any `last_verified`. The staleness gate stays red under its recorded deferral until real
  verification happens.

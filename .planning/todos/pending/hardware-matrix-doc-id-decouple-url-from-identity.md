---
type: todo
created: 2026-09-13
source: operator decision after phase 203 — "instead of fixing it, start building the structure for doc id being separate"
updated: 2026-09-13 — re-sourcing executed; three hypotheses in this file now have evidence
priority: high
requirement: none yet — candidate for a v5.24 tail phase or v5.25
resolves_phase: null
---

# Decouple document *identity* from document *URL* in `HARDWARE_MATRIX`

**Operator decision, 2026-09-13:** do **not** spend a phase re-sourcing the 7 rotted URLs. The
operator is taking the URL re-sourcing themselves. QUIRK's side of the work is the **structural
change that stops this recurring** — which is the higher-value half.

> **UPDATE 2026-09-13 — the re-sourcing HAPPENED, and it produced evidence that changes this design.**
> The operator supplied candidate URLs; all were read in a browser and checked against their claims,
> and 7 of 8 entries were corrected and committed (`5670d550`). See
> `hardware-matrix-source-urls-broadly-rotted.md` for the per-vendor outcome. **Three proposals below
> moved from hypothesis to observation, and two new findings were added** — see
> §"What the 2026-09-13 pass actually proved" at the end. Still open, still deferred; now better
> specified.

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


---

# What the 2026-09-13 pass actually proved

Four findings, in descending order of how much they should change the design.

## 1. The durable anchor usually EXISTS — it is just less precise than the deep link

This file previously *proposed* preferring stable anchors, reasoning from the rot pattern. It is now
an observation. **Two of the three replacement sources found have no release number in their path:**

```
thalesdocs.com/gphsm/luna/7/docs/network/Content/sdk/extensions/pqc/post_quantum_algorithms.htm
docs.paloaltonetworks.com/network-security/decryption/administration/
    post-quantum-cryptography-decryption/detection-control-post-quantum-cryptography
```

Both are **topic pages the vendor maintains in place** rather than forking per release, and both state
their claim directly. In both cases the original entry had reached past the topic page for a
version-pinned deep link that was more precise the day it was written and 404s today.

Palo Alto is the cleanest demonstration: the old URL was
`pan-os/11-1/pan-os-admin/decryption/post-quantum-cryptography` (404); the live page is the same
subject under a **version-free** path. The information never moved. The versioned rendering of where
it lived did.

**Design consequence — make this a recorded rule, not a preference:** when a topic page states the
claim, record the topic page. Reach for a version-pinned path only when the claim is genuinely
version-specific *and* no topic page carries it — and mark that entry as expected to rot.

## 2. `doc_id` gives you a LOOKUP KEY, not immortality — F5 disproved the stronger version

This file's key observation was that F5's `K000141701` and Fortinet's `527690` survived their URL
changes, concluding "the article ID is the durable key."

**Half right.** `K000141701` did *not* survive: the article was **retired**, not moved, and its
content now lives across **two different** K-numbers — `K000149577` (the how-to) and `K000136126` (the
support matrix). Searching MyF5 by K-number is still far better than guessing paths, but `doc_id` must
not be modelled as a permanent pointer to the same document.

**Design consequence:** `doc_id` is a *search key within a vendor namespace* — which makes
`doc_id_scheme` load-bearing rather than a nicety. It should also be **nullable and non-unique**: one
claim may need several ids. The F5 entry now cites two articles, with the second referenced only in
prose because the schema holds a single `source_url`.

## 3. NEW — evidence belongs per CLAIM, not per ENTRY, and a recurring data error proves it

**Four of the five corrections share one shape:** the catalog recorded **transport-layer PQC** while
the vendor had shipped **artifact-signing PQC**.

| Vendor | Catalog claimed | Vendor actually shipped |
|---|---|---|
| HPE | iLO 6 hybrid **TLS** | iLO 7 **LMS firmware-update signing** |
| Juniper | nothing (`unsupported`) | **ML-DSA-87 image signing** + hybrid SSH KEX |
| Thales | ML-KEM/ML-DSA generation at 7.7.1 | generation at **7.9.0**, **LMS-HSS** at 7.8.9, wrapping at 7.9.1 |
| Cisco | nothing (`unsupported`) | **IKEv2 RFC 9370** multiple key exchange |

These solve different problems — signing protects supply-chain integrity, KEMs protect against
harvest-now-decrypt-later. **One `pqc_status` per vendor cannot express "signs firmware post-quantum,
negotiates sessions classically,"** so it collapses toward whichever the author found first. That
collapse produced four of today's six corrections.

This answers the open question this file raised as *"Does `evidence` live per entry, or per claim
within an entry?"* — **per claim.** Each needs its own plane, version floor, and evidence line.
Several entries now assert three or four separable things inside one `notes` blob.

## 4. NEW — `pqc_status` cannot express "actively strips PQC", and that is a real device class

Palo Alto forced a decision the schema does not support. In a decryption path a PAN-OS NGFW does not
merely lack PQC — it **removes hybrid groups from the ClientHello** to force classical negotiation and
**drops** PQC-only sessions, preventing everything behind it from being quantum-safe regardless of
endpoint capability.

The entry was set to `unsupported` because it is the most conservative available value and maps to
Tier 1. That is a **workaround, not a representation**: `unsupported` says "this device can't", where
the truth is "this device stops others from". Structurally it is closer to the gateway/legacy pairing
logic already in `cbom/bridge.py` than to a vendor capability row.

**Open question for the discuss pass:** does the catalog need a downgrade/interference concept
distinct from capability? Any middlebox that terminates TLS to inspect it is a candidate, so this is
not Palo-Alto-specific.

---

# The process finding this file should carry

A structural fix makes re-sourcing a lookup. **It does not make anyone read the page.**

F5 published the article refuting its own entry in **February 2025** — sixteen months before that
entry's `2026-06-13` attestation — at the very K-number the catalog already cited. `doc_id` would have
surfaced it instantly; it would not have caused anyone to compare it against the claim.

That is a stronger argument for `evidence` + `evidence_checked` than the rot pattern that originally
motivated it: **an evidence quote turns re-verification into a diff that cannot be passed by glancing
at a live page.** The content-aware check then has something real to assert against.

# Revised scope sketch

- **`doc_id` + `doc_id_scheme`** — nullable, **non-unique**, a vendor-namespace search key rather than
  a permanent pointer (finding 2).
- **`evidence` + `evidence_checked`** — **per claim, not per entry** (finding 3).
- **Sourcing policy: topic page over version-pinned deep link** where the topic page states the claim
  (finding 1), with version-pinned entries flagged as expected to rot.
- **Content-aware link check** — unchanged; still operator-run or browser-driven, not a GitHub Action.
  Six of these hosts block non-browser clients, and this pass re-confirmed HTTP 200 is not evidence of
  content.
- **NEW: a claim-plane field** (transport / signing / key-storage) — the minimum change that would
  have prevented four of today's six corrections.
- **NEW, possibly a separate todo: a downgrade/interference concept** distinct from capability
  (finding 4).

# Does NOT include

- Re-sourcing — done 2026-09-13, except IPMI.
- The IPMI claim rewrite. The unfalsifiable clause is removed and the status moved to `unsupported`
  ahead of verification (fails safe — see the other todo), but the structural cipher-suite claim is
  **still unverified** and `last_verified` is deliberately not bumped.
- Bumping any `last_verified`. The gate stays red on IPMI alone.

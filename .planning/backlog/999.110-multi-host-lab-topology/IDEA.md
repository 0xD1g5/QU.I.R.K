# 999.110 — Multi-host chaos-lab topology: independent hosts, not just services-by-port

**Filed:** 2026-09-12 (operator request, during Phase 202 planning)
**Priority:** P2 — see "Why this is not just a demo nicety" below
**Status:** open, not scheduled

## The ask

The chaos lab should present **independent hosts across the lab**, not a single host differentiated
only by port. Three stated motivations, in the operator's framing:

1. **Better scanning coverage** — a scan that walks many hosts exercises different code paths than
   one that walks many ports on one host.
2. **Better finding information** — per-host grouping, attribution, and inventory become real.
3. **Visual demonstration of platform capability** — e.g. a host can carry **Crown Jewels**, which
   makes the Quantum Exposure Map visual genuinely worth showing when explaining the platform.

## Current state (verified 2026-09-12, not assumed)

`quantum-chaos-enterprise-lab/docker-compose.yml` defines **90 services across 30 profiles**, and
almost all of them publish ports onto the Docker host. From the scanner's vantage point that is
**one IP address with many open ports** — precisely the shape the operator is describing as a
limitation.

**There is already a working precedent for the fix in this very file.** The `segmented-network`
profile (Phase 152, DISC-09/DISC-10, `docker-compose.yml:1400-1467+`) builds two custom bridge
networks (`segnet-live`, `segnet-dead`) with **static per-container addresses**
(`segnet-gateway` at `ipv4_address: "10.70.0.2"`, `sysctls: net.ipv4.ip_forward=1`,
`cap_add: NET_ADMIN` scoped to that one container) and a gateway whose FORWARD-chain iptables
REJECT rules produce genuine RST / ICMP-host-unreachable results.

`grep -c ipv4_address docker-compose.yml` → **5**, all inside that one profile. So the mechanism is
proven in-repo and simply has not been generalised.

## Why this is not just a demo nicety — it unblocks deferred work

**This is the missing ingredient for backlog 999.107.** That item (operator-declared reachability +
crown-jewel declaration for the Quantum Exposure Map — Phase 195's Tier B) was deferred 2026-09-09
by the MAP-01 spike gate, and its recorded reason was explicitly a *data* problem, not an effort
problem:

> "no live `upstream_mitigated`/reachability data exists to exercise it today … Build when a client
> engagement actually needs operator-declared attack paths."

Phase 195 also had to close with **honest UAT GAPs** for exactly this reason — `195-06-SUMMARY.md`
records that the hardware-bridge edge styling and the crown-jewel badge could not be verified
because "no live data in this DB exercises either path," and `195-01-SUMMARY.md` found that
`test_cbom_bridge_detection.py` is 100% synthetic fixtures, the one live Phase 140 lab run validated
only ARP-walk collection, and 7 local dev-scan SQLite DBs had **zero** populated
`bridge_evidence_json` rows.

A multi-host lab is what turns those synthetic-only paths into live-data paths. That makes this item
an **enabler**, which is why it is filed at P2 rather than P3 despite the demo framing:

- Unblocks 999.107 (P2) by creating the reachability/crown-jewel data its gate was waiting for.
- Converts at least 2 standing Phase 195 UAT GAPs into exercisable cases (crown-jewel badge,
  hardware-bridge edge styling) — relevant to the **v5.24 UAT Coverage Drain** milestone already
  committed at the v5.23 boundary.
- Improves the demo surface the operator actually uses to explain the platform.

## Feasibility & Effort

**Verdict: feasibility CONFIRMED · effort M · no spike needed** — the mechanism is already running
in this repo, so this is generalisation rather than invention.

| Claim | Evidence |
|-------|----------|
| Lab is currently single-host-by-port | 90 services / 30 profiles, ports published to the Docker host |
| Static per-host addressing already works here | `docker-compose.yml:1443-1457` — `segnet-gateway` on `ipv4_address: "10.70.0.2"` |
| Custom bridge networks already declared | top-level `networks:` block present; `segnet-live` / `segnet-dead` |
| Only one profile uses it so far | `grep -c ipv4_address` → 5, all in `segmented-network` |
| Crown-jewel surface exists but is unfed | `OperatorContext.crown_jewels` confirmed per-scan-run ephemeral with zero downstream consumers (`195-01-SUMMARY.md`) |

**Known unknowns (resolve during planning, not now):**

- **Host-grouping scheme.** Which of the 90 services belong to which logical host? This is a content
  decision about what story the lab tells (e.g. a "finance DB host", a "legacy edge host", a
  "crown-jewel app host"), not a mechanical one.
- **macvlan vs bridge-with-static-IPs.** Bridge + `ipv4_address` is the proven in-repo path; macvlan
  gives host-like L2 presence but is notoriously platform-dependent (macOS Docker Desktop in
  particular). Default to bridge unless a capability genuinely requires macvlan.
- **Scanner target config.** Scanning a subnet rather than `127.0.0.1:<ports>` changes the target
  spec, and the port-scope ↔ connector-suppression interaction (Phase 121) may need a look.
- **Crown-jewel declaration persistence** is 999.107's scope, not this item's. This item creates the
  *hosts*; 999.107 lets an operator *declare* which are crown jewels. They can ship in either order,
  but the demo value the operator described needs both.
- **CI cost.** More networks and containers per `./lab.sh all`; check whether the existing
  `test_chaos_lab_idempotency` parametrization (which reads `docker compose config --profiles` at
  collection time) copes, and whether the Docker network-race flakiness already recorded as an
  environmental class gets worse with more networks.

**Mandatory companion work (CLAUDE.md §Chaos Lab Maintenance, non-negotiable):** any profile/port/
service/topology change must update `lab.sh`'s `ALL_PROFILES`, the chaos-lab `README.md`, and the
matching `expected_results_*.md` oracle **in the same change**. A topology change of this size means
the oracles gain per-host expectations, which is a real share of the effort — not an afterthought.

## Sketch of a plan shape (not a commitment)

1. Decide the host-grouping story and write it down as the oracle's spine.
2. Add a top-level lab network with a documented subnet; give each logical host a static address.
3. Re-home existing services onto their host, preserving every current port expectation.
4. Update `lab.sh`, `README.md`, and every affected `expected_results_*.md`.
5. Verify a live scan discovers N hosts (not 1) and that per-host attribution is correct end to end.
6. Optionally pair with 999.107 so a declared crown-jewel host lights up the Exposure Map.

## Related

- **999.107** — operator-declared reachability + crown-jewel declaration (this item is its enabler).
- **999.99** — Quantum Exposure Map, CLOSED at Phase 195 Tier A; this feeds its unexercised paths.
- **Phase 152 / DISC-09 / DISC-10** — the `segmented-network` precedent to generalise.
- **Phase 195** (`195-01-SUMMARY.md`, `195-06-SUMMARY.md`) — the recorded data-absence findings.
- **v5.24 UAT Coverage Drain** — the committed next milestone, where the GAPs this unblocks live.

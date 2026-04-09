# Phase 21: Identity Surface - Context

**Gathered:** 2026-04-09 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Identity protocol findings from all three scanners (Kerberos, SAML/OIDC, DNSSEC) are surfaced
in the quantum-readiness score, the dashboard Identity tab, and the findings table — giving
consultants a complete view of the identity crypto attack surface.

Four requirements: IDENT-01 (evidence counters + scoring), IDENT-02 (IdentityFinding model +
API field), IDENT-03 (Identity tab with summary cards + findings list), IDENT-04 (findings table
protocol filter). Two-plan TDD structure: Plan 01 creates RED scaffold, Plan 02 implements GREEN.

All three identity scanners are already complete (Phases 18–20). This phase wires their output
into the intelligence layer and dashboard — no new scanner code.

</domain>

<decisions>
## Implementation Decisions

### Scoring Integration (IDENT-01)
- **D-01:** Add three named counter keys to `build_evidence_summary()` in `evidence.py`:
  - `identity_weak_etype_count`: count of KERBEROS `CryptoEndpoint` rows where `service_detail`
    indicates CRITICAL or HIGH severity (RC4/DES etypes). Derived by parsing `service_detail`
    format `etype:{id}:{name}:{severity}` for endpoints where `ep.protocol == "KERBEROS"`.
  - `saml_weak_signing_count`: count of SAML `CryptoEndpoint` rows that are CRITICAL or HIGH
    (RSA < 2048 signing certs, SHA-1 URI findings). Detected via `ep.protocol == "SAML"` and
    `ep.cert_pubkey_size < 2048` or `ep.cert_pubkey_alg == "SHA1"`.
  - `dnssec_weak_algo_count`: count of DNSSEC `CryptoEndpoint` rows that are CRITICAL or HIGH.
    Detected via `ep.protocol == "DNSSEC"` and `service_detail` severity field (same format as
    the DNSSEC scanner writes: contains the severity classification).

- **D-02:** Add three new weight keys to `SCORE_WEIGHTS` in `scoring.py`:
  ```python
  "identity_kerberos_weak_etype_ratio": 10.0,
  "identity_saml_weak_signing_ratio":   8.0,
  "identity_dnssec_weak_algo_ratio":    8.0,
  ```
  Exact weight values are Claude's discretion — should be calibrated so RC4 Kerberos is a
  noticeable but not catastrophic penalty on its own (similar to `identity_expired_ratio` = 14).

- **D-03:** Add these to `identity_trust_impacts` in `compute_readiness_score()`:
  ```python
  ("RC4/DES Kerberos etypes detected",
   -_ratio(kerberos_weak_count, denom) * w["identity_kerberos_weak_etype_ratio"]),
  ("Weak SAML signing key",
   -_ratio(saml_weak_count, denom) * w["identity_saml_weak_signing_ratio"]),
  ("Weak DNSSEC signing algorithm",
   -_ratio(dnssec_weak_count, denom) * w["identity_dnssec_weak_algo_ratio"]),
  ```
  These automatically inherit strict/balanced/lenient profile multipliers via the `identity_`
  prefix already present in `PROFILE_MULTIPLIERS`. No additional multiplier wiring needed.

### IdentityFinding Model (IDENT-02)
- **D-04:** Add `IdentityFinding` Pydantic model to `quirk/dashboard/api/schemas.py`:
  - All fields from `FindingItem` (host, port, severity, title, protocol, description,
    remediation, quantum_risk, source) PLUS `algorithm: str` (the weak algorithm or etype
    name, e.g. `"rc4-hmac"`, `"RSA-1024"`, `"RSASHA1"`).
  - No protocol-specific bonus fields (no `etype_id`, `key_bits`, `alg_id`) — `algorithm`
    string carries the needed info for consultant display.

- **D-05:** Add `identity_findings: List[IdentityFinding] = []` to `ScanLatestResponse`.
  TypeScript `api.ts` gains `IdentityFinding` interface + `identity_findings` field on
  `ScanLatestResponse` (mirrors Pydantic model exactly).

### Findings Derivation (IDENT-02 + IDENT-04)
- **D-06:** Add `_derive_identity_findings(endpoints)` helper to `scan.py`. This single function
  returns `list[IdentityFinding]`. Pattern: iterate endpoints, match on `ep.protocol` in
  `{"KERBEROS", "SAML", "DNSSEC"}`, construct `IdentityFinding` with protocol-appropriate
  title/description/algorithm.
  - KERBEROS: parse `service_detail` (`etype:{id}:{name}:{severity}`), title = f"Kerberos
    weak etype: {name}", algorithm = name, severity from etype severity map.
  - SAML: title = "Weak SAML signing certificate" or "SHA-1 algorithm URI detected",
    algorithm = `ep.cert_pubkey_alg`, severity from cert_pubkey_size threshold.
  - DNSSEC: title from service_detail finding type, algorithm = `ep.cert_pubkey_alg`.

- **D-07:** Derive once, expose twice:
  1. `identity_findings_rich = _derive_identity_findings(endpoints)` — rich IdentityFinding list
  2. Convert to `FindingItem` and APPEND to the main `findings` list (satisfies IDENT-04 —
     identity rows appear in the existing findings table with protocol column filter)
  3. Expose `identity_findings_rich` directly as `identity_findings` in `ScanLatestResponse`
  No duplicate derivation logic.

### Findings Table Protocol Filter (IDENT-04)
- **D-08:** Add a protocol `Select` dropdown to `FindingsPage` alongside the existing severity
  filter. Options: ALL / TLS / SSH / KERBEROS / SAML / DNSSEC. Filter applied to
  `data.findings` by `f.protocol` field match (already present on `FindingItem`). The default
  is ALL (no behavior change for existing users).

### Identity Tab (IDENT-03)
- **D-09:** New route `/identity` added to `App.tsx`. New `IdentityPage` component in
  `src/dashboard/src/pages/identity.tsx`. Nav item added to `NAV_ITEMS` in `sidebar.tsx`
  with `Fingerprint` icon from lucide-react.

- **D-10:** Three per-protocol summary cards (Kerberos, SAML/OIDC, DNSSEC). Each card shows:
  - Protocol icon + name (Kerberos / SAML/OIDC / DNSSEC)
  - Total finding count
  - Worst severity badge (CRITICAL / HIGH / MEDIUM / NONE)
  - Status label: "Critical" (any CRITICAL) / "At Risk" (any HIGH, no CRITICAL) /
    "Clean" (no HIGH/CRITICAL findings) / "Not Scanned" (zero identity findings of that protocol)
  - Uses shadcn/ui `Card`, `Badge` — same components as executive summary cards.

- **D-11:** Below the 3 cards: a TanStack table of all identity findings (KERBEROS + SAML +
  DNSSEC). Columns: severity badge, protocol, host, port, title, algorithm. Sourced from
  `data.identity_findings`. Same sorting/filtering pattern as `FindingsPage` but pre-filtered
  to identity protocols (no protocol dropdown needed on this tab — they're all identity).
  Click-to-detail Sheet drawer (same pattern as findings.tsx) is Claude's discretion.

### Claude's Discretion
- Exact weight values for the three new SCORE_WEIGHTS entries (stay within the existing
  range of 6–18 to maintain score balance)
- Lucide icon choice for Identity tab (Fingerprint, Users2, or ShieldCheck — all reasonable)
- Whether identity tab findings list includes a click-to-detail Sheet drawer
- `useScanData` hook update: whether `identity_findings` is accessed via the existing hook
  return value or requires a type cast (TypeScript types will propagate automatically)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §IDENT-01 through IDENT-04 — all 4 identity surface requirements

### Intelligence layer (read before touching evidence/scoring)
- `quirk/intelligence/evidence.py` — `build_evidence_summary()` full implementation;
  understand the dict structure and how new counter keys are appended
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS`, `PROFILE_MULTIPLIERS`,
  `identity_trust_impacts` list construction, `_apply_weighted_impacts()` usage

### API layer (read before touching schemas/routes)
- `quirk/dashboard/api/schemas.py` — all Pydantic models; understand how `ScanLatestResponse`
  is composed and how to add `IdentityFinding` and the new field
- `quirk/dashboard/api/routes/scan.py` — full `get_latest_scan()` route, `_derive_findings()`
  helper (the template for `_derive_identity_findings()`), `ScanLatestResponse` construction

### Frontend (read before touching React)
- `src/dashboard/src/pages/findings.tsx` — TanStack table pattern: column defs, severity
  badges, Sheet drawer, severity/text filters — template for Identity tab findings list
- `src/dashboard/src/pages/executive.tsx` — shadcn Card pattern for summary cards
- `src/dashboard/src/components/sidebar.tsx` — `NAV_ITEMS` array pattern for adding Identity tab
- `src/dashboard/src/App.tsx` — route registration pattern
- `src/dashboard/src/types/api.ts` — TypeScript interface mirroring convention

### Scanner output format (read to understand identity endpoint structure)
- `quirk/scanner/kerberos_scanner.py` — `service_detail` format: `etype:{id}:{name}:{severity}`;
  `cert_pubkey_alg` = etype name; `protocol = "KERBEROS"`
- `quirk/scanner/saml_scanner.py` — `cert_pubkey_alg` = key type (RSA/SHA1);
  `cert_pubkey_size` = key bits; `service_detail` = entity_id context; `protocol = "SAML"`
- `quirk/scanner/dnssec_scanner.py` — `cert_pubkey_alg` = algorithm name; `service_detail`
  encodes finding type and severity; `protocol = "DNSSEC"`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_derive_findings(endpoints)` in `scan.py` — direct template for `_derive_identity_findings()`;
  iterate endpoints, match on `ep.protocol`, construct result objects
- `SEVERITY_STYLES` dict in `findings.tsx` — reuse as-is for identity tab severity badges
- shadcn `Card`, `CardContent`, `CardHeader`, `CardTitle` — already used in executive.tsx for
  summary cards; same component for Identity tab protocol cards
- `Badge` from `@/components/ui/badge` — severity and status badges already styled
- `useScanData` hook — returns full `ScanLatestResponse`; adding `identity_findings` field to
  TypeScript types will automatically propagate to hook consumers

### Established Patterns
- Evidence dict: plain `Dict[str, Any]`, new keys simply appended at the end of the return
  statement — no class instantiation, no schema migration
- Scoring: `identity_trust_impacts` list grows by appending tuples `(label, -ratio * weight)`;
  `_apply_weighted_impacts()` handles everything else
- Pydantic models: `BaseModel` subclass, all fields typed, `Optional` with `= None` default
  for nullable fields, `List[T] = []` for empty list defaults
- API route: all derivation helpers called in sequence, results passed to next step;
  no DB re-queries after the initial `endpoints` fetch
- React component: `useScanData()` → `data.identity_findings` → filter/display; same hook,
  no new fetch needed

### Integration Points
- `quirk/intelligence/evidence.py:build_evidence_summary()` — add 3 new counter keys at the
  bottom of the return dict (after `finding_severity_counts`)
- `quirk/intelligence/scoring.py:SCORE_WEIGHTS` — add 3 new keys; `identity_trust_impacts`
  — add 3 new tuples after existing `identity_mtls_ratio_bonus` entry
- `quirk/dashboard/api/schemas.py` — add `IdentityFinding` class before `ScanLatestResponse`;
  add `identity_findings: List[IdentityFinding] = []` field to `ScanLatestResponse`
- `quirk/dashboard/api/routes/scan.py` — add `_derive_identity_findings()` helper; call after
  `findings = _derive_findings(endpoints)`; extend findings list; pass to `ScanLatestResponse`
- `src/dashboard/src/App.tsx` — add `import { IdentityPage }` and `<Route path="/identity" ...>`
- `src/dashboard/src/components/sidebar.tsx` — add Identity item to `NAV_ITEMS`
- `src/dashboard/src/types/api.ts` — add `IdentityFinding` interface + `identity_findings` to
  `ScanLatestResponse`
- `src/dashboard/src/pages/identity.tsx` — NEW FILE (summary cards + filtered findings table)
- `src/dashboard/src/pages/findings.tsx` — add protocol `Select` filter alongside severity filter

</code_context>

<specifics>
## Specific Ideas

- Identity tab status labels: "Critical" / "At Risk" / "Clean" / "Not Scanned" — gives
  consultants an immediate at-a-glance posture per protocol without reading individual findings
- Protocol filter default = "ALL" on the findings table — zero behavior change for existing
  users who haven't run identity scanners
- `algorithm: str` on `IdentityFinding` carries the human-readable algorithm name exactly as
  the scanner wrote it (e.g., `"rc4-hmac"`, `"RSA-1024"`, `"RSASHA1"`) — consistent with
  how the CBOM classifier uses algorithm names as lookup keys

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 21-identity-surface*
*Context gathered: 2026-04-09*

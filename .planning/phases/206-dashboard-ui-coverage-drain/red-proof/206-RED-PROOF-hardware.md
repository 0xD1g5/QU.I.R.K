| UAT-7-40 | `src/dashboard/src/pages/__tests__/hardware-advisory-banner.test.tsx::"renders the hardware advisory banner text from the fixture drift data"` | `hardware.tsx`'s unconditional advisory `<div role="note">…Hardware findings are advisory-only and do not affect the readiness score.</div>` block was deleted outright, so the page renders with no advisory banner while every other element is untouched. | `TestingLibraryElementError: Unable to find an accessible element with the role "note"` (at `screen.getAllByRole("note")`) | 49a5aa2b | f4e1b775 |
| UAT-7-41 | `src/dashboard/src/pages/__tests__/hardware-device-table.test.tsx::"renders the hardware device table with its documented columns and tier badges in fixture order"` | Ordering mutation: `hardware.tsx`'s `sorted` comparator was reversed on both keys (`TIER_ORDER[b] - TIER_ORDER[a] \|\| b.vendor.localeCompare(a.vendor)`), so every row still renders with its own correct data and only the row ORDER — the property UAT-7-41 names — changes. | `AssertionError: expected [ 'Zebra', 'Aruba', 'Fortinet', …(2) ] to deeply equal [ 'Cisco', 'HPE', 'Fortinet', …(2) ]` (at `expect(renderedVendorOrder).toEqual(EXPECTED_DISPLAY_ORDER)`) | 49a5aa2b | f4e1b775 |

## Citations

UAT-7-40 -> `src/dashboard/src/pages/__tests__/hardware-advisory-banner.test.tsx::"renders the hardware advisory banner text from the fixture drift data"`
- **Partial coverage. Two of the case's four Pass Criteria bullets are uncovered**, recorded here
  verbatim rather than silently dropped:
  - "Sidebar shows \"Hardware\" entry after \"Data in Motion\", before CBOM" — **not asserted.**
    Not reachable from a bare `HardwarePage` render: the nav list lives in
    `src/dashboard/src/components/sidebar.tsx:40` (`{ path: "/hardware", label: "Hardware", Icon:
    Server }`), a sibling of the page inside `AppShell`, not a child of it. Plan 206-09 Task 1
    forbids stretching the test to reach it. Plan 206-10's scope (`shell-spa-routing.test.tsx`,
    `theme-toggle-persistence.test.tsx`, `dashboard-branding.test.tsx` for UAT-7-20/7-22/7-31)
    does **not** name sidebar nav-entry ordering either, so this bullet is recorded as uncovered
    rather than delegated — 206-12/206-13 should qualify UAT-7-40's disposition accordingly rather
    than flipping it to an unqualified PASS.
  - "Score gauge on Executive page is unchanged (HWCOMPAT-SCORE-LOCK)" — **not asserted.** A claim
    about a different page (`executive.tsx`) and about the scoring pipeline's exclusion of hardware
    findings, not about `/hardware`'s render. Out of this test's subject.
  - The two covered bullets: page title "Hardware Compatibility" and sub-header "PQC readiness of
    identified network devices" both render; the advisory banner renders as a `role="note"` element
    whose trimmed text is the case's verbatim copy, asserted on that element specifically (not a
    loose document-wide text match) plus a negative half (`toHaveLength(1)`) so a duplicated banner
    or a leaked bridge-caveat note would also fail.
- **Title-vs-subject note for the verifier:** the `it()` title is the exact string plan 206-09 Task
  1 mandates, and is kept verbatim so the citation resolves. It says "from the fixture drift data",
  but the banner is **not** fixture-derived — reading `hardware.tsx` in full shows it is static
  product copy rendered unconditionally, and UAT-7-40 itself quotes that copy verbatim as its Pass
  Criterion. The plan's expectation that the banner text would come from the drift hook's fixture
  was a hypothesis about the product that the product does not bear out. The assertion is therefore
  against the verbatim UAT string, declared once in the test's `ADVISORY_BANNER` const. Asserting
  it against a fixture field that does not exist would have required inventing one.

UAT-7-41 -> `src/dashboard/src/pages/__tests__/hardware-device-table.test.tsx::"renders the hardware device table with its documented columns and tier badges in fixture order"`
- **Partial coverage. One of the case's five Pass Criteria bullets is uncovered:**
  - "Tier 1 badge is red; Tier 2 badge is orange/yellow; Tier 3 badge is blue; Tier N/A badge is
    gray" — the **hue** half is not asserted. Per plan 206-09 Task 2's explicit instruction, tier
    assertions are on the rendered tier VALUE, not on a CSS class name: jsdom computes no real
    color, so the only available proxy is `TIER_STYLES`' Tailwind arbitrary-value class strings,
    and pinning those would couple the test to a token rename that changes nothing a user sees.
    The *distinctness* of those four hues is separately locked from the other side by
    `components/__tests__/vendor-trend-advisory-guard.test.ts`, whose `FORBIDDEN_PALETTE` enumerates
    all four `TIER_STYLES` literals.
  - The four covered bullets: all eight documented columns (Tier, Vendor, Model, Host:Port, PQC
    Status, Confidence, EOL Date, Method) present as column headers; each row's Tier cell shows
    that device's own tier, matched back to the fixture by vendor rather than by position; rendered
    row ORDER equals tier-ascending-then-vendor-alphabetical (both halves of the sort key are
    load-bearing — Cisco-before-HPE can only come from the vendor tiebreak, Aruba-after-HPE only
    from the tier key); the Host:Port cell carries `font-mono`; and the HPE-iLO5 device renders
    vendor=HPE, model=iLO5, `10.10.0.22:20222`, confidence=high.
- The HPE-iLO5 bullet is a **render** assertion over a fixture shaped like the `hwcompat` lab's
  port-20222 device. It does not — and cannot, in jsdom — attest that a real scan of that lab
  profile produces those values; that half remains the lab oracle's job
  (`quantum-chaos-enterprise-lab/expected_results_*.md`).

## Product finding filed during this plan

`.planning/todos/pending/lifecycle-event-row-unknown-event-type-crash.md` —
`LifecycleEventRow.tsx:64` indexes `EVENT_TYPE_META[event.event_type]` and dereferences `.icon`
with no fallback, so an unrecognised `event_type` (or `direction`) on the wire crashes the whole
`/hardware` page render with `TypeError: Cannot read properties of undefined (reading 'icon')`.
Its sibling `VendorTrendRow.tsx:24` defends the identical lookup with `?? { icon: ShieldCheck,
label: event.event_type }`. Discovered live while building this plan's drift fixture (the first
fixture used an event_type that is not in the union, and the page render threw). **Not fixed** —
Phase 206 is test-only per 206-CONTEXT.md.

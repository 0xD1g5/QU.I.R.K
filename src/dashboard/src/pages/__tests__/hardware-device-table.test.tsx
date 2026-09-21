import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within } from "@testing-library/react"

// UAT-7-41 — Hardware Tab — Device Table with Tier Badges (HWCOMPAT-07).
//
// Model: pages/__tests__/certificates-inventory-table.test.tsx. All three of hardware.tsx's hooks
// are mocked (RESEARCH § Q2) — useScanData supplies the device rows; useHardwareDrift and
// useVendorPqcTrends are mocked to empty-but-loaded so the page's sibling lifecycle/vendor-trend
// sections render their real empty path and never attempt a fetch.
//
// Fixture design (load-bearing): five devices spanning all four tier values (1, 2, 3, N/A), supplied
// in an order that differs from the order hardware.tsx is expected to display. Supplied order is
//   Fortinet (Tier 2) -> Aruba (Tier 3) -> HPE (Tier 1) -> Zebra (Tier N/A) -> Cisco (Tier 1)
// and the documented display order is
//   Cisco (Tier 1) -> HPE (Tier 1) -> Fortinet (Tier 2) -> Aruba (Tier 3) -> Zebra (Tier N/A)
// i.e. tier ascending, then vendor alphabetically within a tier. Both halves of the sort key are
// exercised: Cisco-before-HPE can only come from the vendor tiebreak, and Aruba-after-HPE can only
// come from the tier key (alphabetically Aruba would otherwise lead). A test that merely asserted
// row membership, or that used a fixture already in display order, would survive a reversed or
// removed sort — see the red-proof row in 206-RED-PROOF-hardware.md.
//
// Badge assertions are on the rendered tier VALUE, not on a CSS class. UAT-7-41's "Tier 1 badge is
// red / Tier 2 orange / Tier 3 blue / Tier N/A gray" hue bullet is therefore NOT covered by this
// test and is named explicitly in the red-proof fragment's Citations section: a class-name
// assertion would couple this test to a styling token rename that changes nothing a user sees, and
// jsdom computes no real color to assert instead.

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))
vi.mock("@/hooks/useHardwareDrift", () => ({
  useHardwareDrift: () => driftReturn,
}))
vi.mock("@/hooks/useVendorPqcTrends", () => ({
  useVendorPqcTrends: () => vendorTrendsReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }
let driftReturn: { data: unknown; loading: boolean; error: string | null }
let vendorTrendsReturn: { data: unknown; loading: boolean; error: string | null }

// UAT-7-41 Pass Criteria bullet 1, verbatim: "Columns present: Tier, Vendor, Model, Host:Port,
// PQC Status, Confidence, EOL Date, Method". hardware.tsx renders five further columns (SNMP,
// Modbus, BACnet, Bridge Status, CVEs) after Method; those are out of this case's scope and are
// not asserted, but their presence does not affect the eight the case names.
const DOCUMENTED_COLUMNS = [
  "Tier",
  "Vendor",
  "Model",
  "Host:Port",
  "PQC Status",
  "Confidence",
  "EOL Date",
  "Method",
]

// Supplied in a deliberately non-display order — see the header comment.
const FIXTURE_DEVICES = [
  {
    host: "10.10.0.51",
    port: 443,
    severity: "MEDIUM",
    title: "Fortinet FortiGate management interface",
    vendor: "Fortinet",
    model: "FortiGate 100F",
    pqc_status: "partial",
    remediation_tier: "Tier 2",
    confidence: "medium",
    fingerprint_method: "http_mgmt",
    eol_date: null,
  },
  {
    host: "10.10.0.31",
    port: 22,
    severity: "LOW",
    title: "Aruba switch SSH banner",
    vendor: "Aruba",
    model: "CX 6300",
    pqc_status: "partial",
    remediation_tier: "Tier 3",
    confidence: "medium",
    fingerprint_method: "ssh_banner",
    eol_date: null,
  },
  {
    // UAT-7-41 Pass Criteria bullet 5: the hwcompat lab's HPE-iLO5 device on port 20222,
    // vendor=HPE, model=iLO5, confidence=high.
    host: "10.10.0.22",
    port: 20222,
    severity: "HIGH",
    title: "HPE iLO5 management interface",
    vendor: "HPE",
    model: "iLO5",
    pqc_status: "unsupported",
    remediation_tier: "Tier 1",
    confidence: "high",
    fingerprint_method: "http_mgmt",
    eol_date: null,
  },
  {
    host: "10.10.0.44",
    port: 22,
    severity: "INFO",
    title: "Zebra printer SSH banner",
    vendor: "Zebra",
    model: null,
    pqc_status: "VENDOR-SILENT",
    remediation_tier: "Tier N/A",
    confidence: "unknown",
    fingerprint_method: "ssh_banner",
    eol_date: null,
  },
  {
    host: "10.10.0.11",
    port: 22,
    severity: "HIGH",
    title: "Cisco router SSH banner",
    vendor: "Cisco",
    model: "ISR 4331",
    pqc_status: "unsupported",
    remediation_tier: "Tier 1",
    confidence: "high",
    fingerprint_method: "ssh_banner",
    eol_date: null,
  },
]

// UAT-7-41 Pass Criteria bullet 3: "Rows sorted Tier 1 -> Tier 2 -> Tier 3 -> Tier N/A; within
// same tier sorted by vendor alphabetically".
const EXPECTED_DISPLAY_ORDER = ["Cisco", "HPE", "Fortinet", "Aruba", "Zebra"]

const SCAN_FIXTURE = { hardware_findings: FIXTURE_DEVICES }

afterEach(() => {
  cleanup()
})

describe("HardwarePage — device table (UAT-7-41)", () => {
  it("renders the hardware device table with its documented columns and tier badges in fixture order", async () => {
    scanDataReturn = { data: SCAN_FIXTURE, loading: false, error: null }
    driftReturn = { data: { has_prior_scan: false, latest_scan_at: null, latest_events: [], historical_events: [], historical_truncated: false }, loading: false, error: null }
    vendorTrendsReturn = { data: { events: [], truncated: false }, loading: false, error: null }

    const { HardwarePage } = await import("@/pages/hardware")
    render(<HardwarePage />)

    const table = screen.getByRole("table")

    // Bullet 1 — every column the case names is present as a column header.
    for (const name of DOCUMENTED_COLUMNS) {
      expect(within(table).getByRole("columnheader", { name })).toBeInTheDocument()
    }

    // One row per fixture device (header row excluded).
    const rows = within(table).getAllByRole("row")
    const bodyRows = rows.slice(1)
    expect(bodyRows).toHaveLength(FIXTURE_DEVICES.length)

    // Bullet 3 — rendered row ORDER, read off the Vendor cell of each body row in document order.
    const renderedVendorOrder = bodyRows.map((r) => within(r).getAllByRole("cell")[1].textContent?.trim())
    expect(renderedVendorOrder).toEqual(EXPECTED_DISPLAY_ORDER)

    // Bullet 2 (value half) — each row's Tier cell shows THAT device's own tier, matched back to
    // the fixture by vendor rather than by position, so a mis-paired badge fails even if the row
    // order happens to be right.
    for (const row of bodyRows) {
      const cells = within(row).getAllByRole("cell")
      const vendor = cells[1].textContent?.trim()
      const device = FIXTURE_DEVICES.find((d) => d.vendor === vendor)
      expect(device, `no fixture device for rendered vendor ${vendor}`).toBeDefined()
      expect(cells[0]).toHaveTextContent(device!.remediation_tier)
    }

    // All four distinct tier values are actually exercised — guards against a fixture that
    // silently collapsed to one tier and made the ordering assertion vacuous.
    expect(new Set(FIXTURE_DEVICES.map((d) => d.remediation_tier)).size).toBe(4)

    // Bullet 4 — the Host:Port column renders in a monospace face.
    const hpeRow = bodyRows[EXPECTED_DISPLAY_ORDER.indexOf("HPE")]
    const hpeCells = within(hpeRow).getAllByRole("cell")
    expect(hpeCells[3].className).toContain("font-mono")

    // Bullet 5 — the HPE-iLO5 device renders vendor=HPE, model=iLO5, host:port 10.10.0.22:20222,
    // confidence=high.
    expect(hpeCells[1]).toHaveTextContent("HPE")
    expect(hpeCells[2]).toHaveTextContent("iLO5")
    expect(hpeCells[3]).toHaveTextContent("10.10.0.22:20222")
    expect(hpeCells[5]).toHaveTextContent("high")

    // The Tier N/A device has no model; the page renders its documented "Unknown" placeholder
    // rather than an empty cell.
    const zebraRow = bodyRows[EXPECTED_DISPLAY_ORDER.indexOf("Zebra")]
    expect(within(zebraRow).getAllByRole("cell")[2]).toHaveTextContent("Unknown")
  })
})

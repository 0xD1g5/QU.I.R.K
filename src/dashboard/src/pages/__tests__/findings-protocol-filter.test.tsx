// Phase 206 Plan 04 (COV-04) — UAT-7-37: Findings Page protocol filter,
// combined with the severity filter.
//
// `useScanData` is mocked (not `fetchApi`); the real `FindingsPage` is
// rendered and both real Radix Select controls are driven with `user-event`.
// The fixture is built so protocol-only, severity-only, and both-applied each
// yield a DIFFERENT row set — otherwise "combines with the severity filter"
// could not be distinguished from either filter acting alone.
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { FindingItem } from "@/types/api"

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: false,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeFinding(overrides: Partial<FindingItem> = {}): FindingItem {
  return {
    id: 1,
    host: "web01.example.com",
    port: 443,
    severity: "HIGH",
    title: "finding",
    protocol: "TLS",
    ...overrides,
  }
}

// Row sets by filter combination:
//   no filter            -> tls-crit, tls-low, krb-crit, ssh-medium
//   protocol=TLS         -> tls-crit, tls-low
//   protocol=KERBEROS    -> krb-crit
//   severity=CRITICAL    -> tls-crit, krb-crit
//   TLS + CRITICAL       -> tls-crit          (the intersection)
const TLS_CRIT = "tls-crit.example.com"
const TLS_LOW = "tls-low.example.com"
const KRB_CRIT = "krb-crit.example.com"
const SSH_MEDIUM = "ssh-medium.example.com"
const ALL_HOSTS = [TLS_CRIT, TLS_LOW, KRB_CRIT, SSH_MEDIUM].sort()

const FIXTURE = {
  findings: [
    makeFinding({ id: 1, host: TLS_CRIT, protocol: "TLS", severity: "CRITICAL", title: "tls critical finding" }),
    makeFinding({ id: 2, host: TLS_LOW, protocol: "TLS", severity: "LOW", title: "tls low finding" }),
    makeFinding({ id: 3, host: KRB_CRIT, protocol: "KERBEROS", severity: "CRITICAL", title: "kerberos critical finding" }),
    makeFinding({ id: 4, host: SSH_MEDIUM, protocol: "SSH", severity: "MEDIUM", title: "ssh medium finding" }),
  ],
}

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

function currentHostSet(): string[] {
  const rows = screen.getAllByRole("row").slice(1)
  return rows.map((row) => row.querySelectorAll("td")[1]?.textContent ?? "").sort()
}

async function openSelect(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole("combobox", { name }))
  return screen.findAllByRole("option")
}

async function choose(user: ReturnType<typeof userEvent.setup>, name: string, label: string) {
  const options = await openSelect(user, name)
  const target = options.find((o) => (o.textContent ?? "") === label)
  expect(target, `option ${label} should exist in ${name}`).toBeDefined()
  await user.click(target!)
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("FindingsPage — protocol filter combined with severity (UAT-7-37)", () => {
  it("combines the protocol filter with the severity filter to narrow the findings table", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    // The protocol dropdown is present alongside the severity one, and the
    // unfiltered default shows every fixture row.
    const protocolTrigger = screen.getByRole("combobox", { name: "Filter by protocol" })
    expect(screen.getByRole("combobox", { name: "Filter by severity" })).toBeInTheDocument()
    expect(protocolTrigger).toHaveTextContent("All Protocols")
    expect(currentHostSet()).toEqual(ALL_HOSTS)

    // The documented option set.
    const options = await openSelect(user, "Filter by protocol")
    expect(options.map((o) => o.textContent ?? "")).toEqual([
      "All Protocols", "TLS", "SSH", "HTTP", "KERBEROS", "SAML", "DNSSEC",
    ])
    await user.keyboard("{Escape}")

    // Protocol alone: KERBEROS.
    await choose(user, "Filter by protocol", "KERBEROS")
    expect(currentHostSet()).toEqual([KRB_CRIT])

    // Protocol alone: TLS — two rows, neither of them the KERBEROS or SSH row.
    await choose(user, "Filter by protocol", "TLS")
    expect(currentHostSet()).toEqual([TLS_CRIT, TLS_LOW].sort())
    expect(screen.queryByText(KRB_CRIT)).toBeNull()
    expect(screen.queryByText(SSH_MEDIUM)).toBeNull()

    // Severity applied ON TOP of the protocol filter: the intersection, which
    // is strictly smaller than either filter's own result set.
    await choose(user, "Filter by severity", "CRITICAL")
    expect(currentHostSet()).toEqual([TLS_CRIT])
    expect(screen.queryByText(TLS_LOW)).toBeNull()

    // Releasing only the protocol filter leaves the severity filter applied —
    // proof both were genuinely in force simultaneously, rather than the last
    // selection alone deciding the row set.
    await choose(user, "Filter by protocol", "All Protocols")
    expect(currentHostSet()).toEqual([TLS_CRIT, KRB_CRIT].sort())

    // Releasing both restores the full findings list.
    await choose(user, "Filter by severity", "All Severities")
    expect(currentHostSet()).toEqual(ALL_HOSTS)
  })
})

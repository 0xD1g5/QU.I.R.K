// Phase 193 Plan 07 (PARITY-02/PARITY-03) — Connectors panel component tests.
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ConnectorsPanel } from "../ConnectorsPanel"

const mockFetchApi = vi.fn()

vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({ id: "healthcare", label: "Healthcare" }),
}))

function jsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  }
}

const FIXTURE = {
  connectors: [
    { flag: "enable_kerberos", label: "Kerberos", category: "Identity", available: true, reason: "", install_hint: "" },
    { flag: "enable_aws", label: "AWS KMS", category: "Cloud", available: true, reason: "", install_hint: "" },
    {
      flag: "enable_db",
      label: "Database TLS (PostgreSQL/MySQL)",
      category: "Database",
      available: false,
      reason: "optional extra 'db' is not installed",
      install_hint: "pip install quirk[db]",
    },
    { flag: "enable_email", label: "Email / SMTP", category: "Email & Broker", available: true, reason: "", install_hint: "" },
    { flag: "enable_snmp", label: "SNMP Hardware Fingerprinting", category: "OT/ICS", available: true, reason: "", install_hint: "" },
    { flag: "enable_jwt", label: "JWT / API Endpoints", category: "Source & API", available: true, reason: "", install_hint: "" },
  ],
  unavailable_count: 1,
}

function defaultProps(overrides: Partial<Parameters<typeof ConnectorsPanel>[0]> = {}) {
  return {
    connectors: {},
    onConnectorsChange: vi.fn(),
    credentials: {},
    onCredentialsChange: vi.fn(),
    presetState: null,
    ...overrides,
  }
}

afterEach(() => {
  mockFetchApi.mockReset()
})

describe("ConnectorsPanel", () => {
  it("is collapsed by default and issues no availability fetch on mount", () => {
    render(<ConnectorsPanel {...defaultProps()} />)

    expect(screen.getByText("Connectors")).toBeInTheDocument()
    expect(mockFetchApi).not.toHaveBeenCalled()
  })

  it("fetches /api/connectors/availability exactly once on first expand", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    render(<ConnectorsPanel {...defaultProps()} />)

    fireEvent.click(screen.getByText("Connectors"))
    await waitFor(() => expect(mockFetchApi).toHaveBeenCalledTimes(1))
    expect(mockFetchApi.mock.calls[0][0]).toBe("/api/connectors/availability")
  })

  it("renders connectors under their category headings in the six-heading fixed order", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    render(<ConnectorsPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Connectors"))

    await screen.findByText("Kerberos")
    const headings = ["Identity", "Cloud", "Database", "Email & Broker", "OT/ICS", "Source & API"]
    const positions = headings.map((h) => screen.getByText(h).compareDocumentPosition)
    expect(positions.length).toBe(6)
    for (const h of headings) {
      expect(screen.getByText(h)).toBeInTheDocument()
    }
    // Order check: each heading's DOM position precedes the next one's.
    const nodes = headings.map((h) => screen.getByText(h))
    for (let i = 0; i < nodes.length - 1; i++) {
      // eslint-disable-next-line no-bitwise
      expect(nodes[i].compareDocumentPosition(nodes[i + 1]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    }
  })

  it("disables an unavailable connector's switch and shows its reason + install hint as visible text", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    render(<ConnectorsPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Connectors"))

    await screen.findByText("Database TLS (PostgreSQL/MySQL)")
    const dbSwitch = screen.getByRole("switch", { name: "Database TLS (PostgreSQL/MySQL)" })
    expect(dbSwitch).toBeDisabled()
    expect(screen.getByText(/optional extra 'db' is not installed/)).toBeInTheDocument()
    expect(screen.getByText(/pip install quirk\[db\]/)).toBeInTheDocument()
  })

  it("shows a masked, not-saved credential input when a credentialed connector is turned ON, and removes it when turned OFF", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const onConnectorsChange = vi.fn()
    const { rerender } = render(
      <ConnectorsPanel {...defaultProps({ onConnectorsChange })} />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    await screen.findByText("SNMP Hardware Fingerprinting")

    expect(screen.queryByLabelText("SNMP Community String")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("switch", { name: "SNMP Hardware Fingerprinting" }))
    expect(onConnectorsChange).toHaveBeenCalledWith({ enable_snmp: true })

    rerender(
      <ConnectorsPanel {...defaultProps({ onConnectorsChange, connectors: { enable_snmp: true } })} />,
    )
    const input = await screen.findByLabelText("SNMP Community String")
    expect(input).toHaveAttribute("type", "password")
    expect(
      screen.getAllByText("Not saved — cleared after this scan. Re-enter on every submission.").length,
    ).toBeGreaterThanOrEqual(1)

    rerender(
      <ConnectorsPanel {...defaultProps({ onConnectorsChange, connectors: { enable_snmp: false } })} />,
    )
    expect(screen.queryByLabelText("SNMP Community String")).not.toBeInTheDocument()
  })

  it("renders the ambient-auth note and no input element for an ambient-auth cloud connector when ON", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    render(<ConnectorsPanel {...defaultProps({ connectors: { enable_aws: true } })} />)
    fireEvent.click(screen.getByText("Connectors"))

    await screen.findByText("AWS KMS")
    expect(
      screen.getByText("AWS KMS uses environment or instance credentials — no field needed here."),
    ).toBeInTheDocument()
    expect(document.querySelector("input[type='password']")).toBeNull()
  })

  it("D-15: a connector ON with an empty credential shows the warn copy without any submit-blocking element", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    render(<ConnectorsPanel {...defaultProps({ connectors: { enable_snmp: true } })} />)
    fireEvent.click(screen.getByText("Connectors"))

    await screen.findByText(
      "SNMP Hardware Fingerprinting is enabled with no credentials supplied. The scan will run and record a missing-credentials skip for this connector if it can't authenticate. Submit anyway, or add credentials above.",
    )
    expect(document.querySelector("[disabled][type='submit']")).toBeNull()
  })

  it("D-13: clicking one toggle calls onConnectorsChange with exactly that one key", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const onConnectorsChange = vi.fn()
    render(<ConnectorsPanel {...defaultProps({ onConnectorsChange })} />)
    fireEvent.click(screen.getByText("Connectors"))

    await screen.findByText("Kerberos")
    fireEvent.click(screen.getByRole("switch", { name: "Kerberos" }))

    expect(onConnectorsChange).toHaveBeenCalledTimes(1)
    const arg = onConnectorsChange.mock.calls[0][0]
    expect(Object.keys(arg).length).toBe(1)
    expect(arg).toEqual({ enable_kerberos: true })
  })

  it("renders the failure copy and does not throw when the availability fetch fails", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse({}, false, 500))
    const user = userEvent.setup()
    render(<ConnectorsPanel {...defaultProps()} />)

    await user.click(screen.getByText("Connectors"))

    expect(await screen.findByText("Connector availability failed to load (500)")).toBeInTheDocument()
  })
})

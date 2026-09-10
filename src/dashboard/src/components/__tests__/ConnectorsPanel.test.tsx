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
    { flag: "enable_gcp", label: "GCP KMS", category: "Cloud", available: true, reason: "", install_hint: "" },
    { flag: "enable_vault", label: "HashiCorp Vault", category: "Cloud", available: true, reason: "", install_hint: "" },
    { flag: "enable_k8s", label: "Kubernetes", category: "Cloud", available: true, reason: "", install_hint: "" },
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

  // Phase 197 Plan 02 (PARITY-05/PARITY-06) — per-connector detail rows.

  it("Test A (D-06 visibility gate): detail field renders only when available AND on; unavailable never renders it even with the flag true in state", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const { rerender } = render(<ConnectorsPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Connectors"))
    await screen.findByText("JWT / API Endpoints")

    expect(screen.queryByLabelText("JWT Targets")).not.toBeInTheDocument()

    rerender(<ConnectorsPanel {...defaultProps({ connectors: { enable_jwt: true } })} />)
    expect(await screen.findByLabelText("JWT Targets")).toBeInTheDocument()

    // Database connector is unavailable in the fixture — even with its flag
    // forced true in state, no detail field for it ever renders.
    rerender(<ConnectorsPanel {...defaultProps({ connectors: { enable_jwt: true, enable_db: true } })} />)
    expect(screen.queryByLabelText("PostgreSQL Targets")).not.toBeInTheDocument()
  })

  it("Test B (D-07 list parse): typing a comma/newline-separated list calls onConnectorsChange with a parsed array", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const onConnectorsChange = vi.fn()
    render(
      <ConnectorsPanel {...defaultProps({ onConnectorsChange, connectors: { enable_jwt: true } })} />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    const field = await screen.findByLabelText("JWT Targets")

    fireEvent.change(field, { target: { value: "a.example.com, b.example.com\nc.example.com" } })

    expect(onConnectorsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        jwt_targets: ["a.example.com", "b.example.com", "c.example.com"],
      }),
    )
  })

  it("Test C (D-08 delete-on-blank): clearing a list field deletes its key from the delta rather than sending []", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const onConnectorsChange = vi.fn()
    render(
      <ConnectorsPanel
        {...defaultProps({
          onConnectorsChange,
          connectors: { enable_jwt: true, jwt_targets: ["a.example.com"] },
        })}
      />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    // The field already carries a value, so its Label also renders the
    // "Set" badge inline — match on the label prefix rather than the exact
    // (now badge-suffixed) accessible name.
    const field = await screen.findByLabelText(/^JWT Targets/)

    fireEvent.change(field, { target: { value: "" } })

    const next = onConnectorsChange.mock.calls[onConnectorsChange.mock.calls.length - 1][0]
    expect("jwt_targets" in next).toBe(false)
  })

  it("Test D (Pitfall 6): vault_tls_verify Switch renders CHECKED when absent from state; turning it off writes an explicit false", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const onConnectorsChange = vi.fn()
    render(
      <ConnectorsPanel {...defaultProps({ onConnectorsChange, connectors: { enable_vault: true } })} />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    const sw = await screen.findByRole("switch", { name: "Verify Vault TLS certificate" })
    expect(sw).toBeChecked()

    fireEvent.click(sw)
    expect(onConnectorsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ vault_tls_verify: false }),
    )
  })

  it("Test D (deliberate-break check, performed and reverted — pasted into SUMMARY): a truthiness blank-predicate would delete an explicit false", () => {
    // This test documents the invariant asserted above via a standalone
    // predicate check; the actual break-and-restore is performed manually
    // against ConnectorsPanel.tsx's isBlankDetailValue and recorded in the
    // plan SUMMARY, not left as permanently-broken source.
    function truthinessBlank(v: unknown) {
      return !v
    }
    function correctBlank(v: unknown) {
      if (v === undefined) return true
      if (typeof v === "string") return v.trim().length === 0
      if (Array.isArray(v)) return v.length === 0
      return false
    }
    expect(truthinessBlank(false)).toBe(true) // would wrongly delete the key
    expect(correctBlank(false)).toBe(false) // correctly kept as a real value
  })

  it("Test E (empty-targets hint): enabled with no targets shows the amber hint; supplying targets removes it; a zero-list connector never shows it", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const { rerender } = render(
      <ConnectorsPanel {...defaultProps({ connectors: { enable_jwt: true } })} />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    await screen.findByLabelText("JWT Targets")

    expect(
      screen.getByText(
        "JWT / API Endpoints is enabled but has no targets configured. The scan will run but this connector's list is empty, so it has nothing to check. Add targets above, or submit anyway.",
      ),
    ).toBeInTheDocument()

    rerender(
      <ConnectorsPanel
        {...defaultProps({ connectors: { enable_jwt: true, jwt_targets: ["a.example.com"] } })}
      />,
    )
    expect(
      screen.queryByText(/is enabled but has no targets configured/),
    ).not.toBeInTheDocument()

    // GCP has zero list-typed detail fields (only gcp_project_id, a text
    // field) — the hint never shows for it regardless of state.
    rerender(<ConnectorsPanel {...defaultProps({ connectors: { enable_gcp: true } })} />)
    await screen.findByLabelText("GCP Project ID")
    expect(
      screen.queryByText(/is enabled but has no targets configured/),
    ).not.toBeInTheDocument()
  })

  it("Test F (pairlist): typing name@location parses to a {name, location} object", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const onConnectorsChange = vi.fn()
    render(
      <ConnectorsPanel {...defaultProps({ onConnectorsChange, connectors: { enable_k8s: true } })} />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    const field = await screen.findByLabelText("GKE Clusters")

    fireEvent.change(field, { target: { value: "prod-1@us-central1" } })

    expect(onConnectorsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        gke_clusters: [{ name: "prod-1", location: "us-central1" }],
      }),
    )
  })

  it("Test G (field-level Set badge): a non-blank detail field shows a Set badge; an untouched one does not", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    const { rerender } = render(
      <ConnectorsPanel {...defaultProps({ connectors: { enable_jwt: true } })} />,
    )
    fireEvent.click(screen.getByText("Connectors"))
    const field = await screen.findByLabelText("JWT Targets")
    const label = field.closest("div")?.querySelector("label")
    expect(label?.textContent).not.toMatch(/Set/)

    rerender(
      <ConnectorsPanel
        {...defaultProps({ connectors: { enable_jwt: true, jwt_targets: ["a.example.com"] } })}
      />,
    )
    const labelAfter = (await screen.findByLabelText(/^JWT Targets/)).closest("div")?.querySelector("label")
    expect(labelAfter?.textContent).toMatch(/Set/)
  })

  it("ambient-auth and detail fields coexist: AWS shows both the ambient-auth note and its detail fields when ON", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(FIXTURE))
    render(<ConnectorsPanel {...defaultProps({ connectors: { enable_aws: true } })} />)
    fireEvent.click(screen.getByText("Connectors"))

    await screen.findByText("AWS KMS uses environment or instance credentials — no field needed here.")
    expect(screen.getByLabelText("AWS Region")).toBeInTheDocument()
    expect(screen.getByLabelText("AWS Profile")).toBeInTheDocument()
  })
})

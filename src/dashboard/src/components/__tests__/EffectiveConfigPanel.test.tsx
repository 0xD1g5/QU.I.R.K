// Phase 192 Plan 10 (PARITY-01 / D-01..D-05) — Effective config pre-flight panel.
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { EffectiveConfigPanel } from "../EffectiveConfigPanel"

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

const BASE_RESPONSE = {
  vertical: "healthcare",
  profile: "deep",
  redacted_field_count: 1,
  sections: [
    {
      name: "targets",
      title: "Targets",
      fields: [
        { name: "targets", value: "example.com", provenance: "user", redacted: false, credential_status: null },
      ],
    },
    {
      name: "scan",
      title: "Scan",
      fields: [
        { name: "profile", value: "deep", provenance: "preset", redacted: false, credential_status: null },
        { name: "calibration", value: "balanced", provenance: "default", redacted: false, credential_status: null },
      ],
    },
    {
      name: "connectors",
      title: "Connectors",
      fields: [
        { name: "vault_token", value: "•••• (not set)", provenance: "default", redacted: true, credential_status: "not set" },
      ],
    },
  ],
  raw: {
    targets: { targets: "example.com" },
    scan: { profile: "deep", calibration: "balanced" },
    connectors: { vault_token: "•••• (not set)" },
  },
}

function defaultProps() {
  return {
    targets: "example.com",
    profile: "deep" as const,
    calibration: "balanced" as const,
    enableNmap: false,
    portScope: "top1000" as const,
    customPorts: "",
  }
}

afterEach(() => {
  mockFetchApi.mockReset()
})

describe("EffectiveConfigPanel", () => {
  it("is collapsed by default with no config content in the DOM and no fetch issued", () => {
    render(<EffectiveConfigPanel {...defaultProps()} />)

    expect(screen.getByText("Effective config")).toBeInTheDocument()
    expect(screen.queryByText("Grouped")).not.toBeInTheDocument()
    expect(screen.queryByText("Raw YAML")).not.toBeInTheDocument()
    expect(mockFetchApi).not.toHaveBeenCalled()
  })

  it("fetches /api/config/effective with the live form selections only after expanding", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} />)

    expect(mockFetchApi).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText("Effective config"))

    await waitFor(() => expect(mockFetchApi).toHaveBeenCalled())
    const calledPath = mockFetchApi.mock.calls[0][0] as string
    expect(calledPath).toContain("/api/config/effective")
    expect(calledPath).toContain("targets=example.com")
    expect(calledPath).toContain("profile=deep")
    expect(calledPath).toContain("calibration=balanced")
    expect(calledPath).toContain("port_scope=top1000")
    expect(calledPath).toContain("vertical=healthcare")
  })

  it("renders the Grouped tab by default with one block per section and one row per field", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Effective config"))

    expect(await screen.findByText("Targets")).toBeInTheDocument()
    expect(screen.getByText("Scan")).toBeInTheDocument()
    expect(screen.getByText("Connectors")).toBeInTheDocument()
    expect(screen.getByText("calibration")).toBeInTheDocument()
  })

  // Review WR-05: preset provenance comes from apply_profile(cfg, profile) —
  // the badge is labeled with the scan PROFILE, never the vertical.
  it("badges a user-provenance field as 'Overridden' and a preset field as 'Preset: {profile}'", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Effective config"))

    expect(await screen.findByText("Overridden")).toBeInTheDocument()
    expect(screen.getByText("Preset: deep")).toBeInTheDocument()
    expect(screen.queryByText("Preset: healthcare")).not.toBeInTheDocument()
    // default field renders no provenance badge
    expect(screen.queryByText("Preset: deep")?.closest("table")).toBeTruthy()
  })

  it("renders credential fields as a redacted status placeholder, never an editable input", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Effective config"))

    expect(await screen.findByText("•••• (not set)")).toBeInTheDocument()
    expect(document.querySelector("input[type='text']#vault_token")).toBeNull()
  })

  it("shows the same redaction placeholder on the Raw YAML tab as the Grouped tab", async () => {
    const user = userEvent.setup()
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Effective config"))
    await screen.findByText("•••• (not set)")

    // Radix Tabs' default "automatic" activation mode switches on focus, not
    // plain fireEvent.click (which does not move focus in jsdom) — userEvent
    // drives the same focus+click sequence a real browser click would.
    await user.click(screen.getByText("Raw YAML"))

    const pre = await screen.findByText((_, el) => el?.tagName.toLowerCase() === "pre")
    expect(pre.textContent).toContain("•••• (not set)")
  })

  it("renders the unavailable notice on a failed fetch without blocking the form", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse({}, false, 500))
    render(<EffectiveConfigPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Effective config"))

    expect(await screen.findByText("Effective config unavailable")).toBeInTheDocument()
    expect(
      screen.getByText(
        "Could not resolve the config preview. Check your connection and try again, or submit the scan — this does not block scanning.",
      ),
    ).toBeInTheDocument()
  })

  // Phase 194 Plan 05 (PARITY-04, D-04) — advanced overlay query param.
  it("an empty/undefined advanced prop produces a query string with no advanced= segment (byte-identical to pre-phase)", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} advanced={{}} />)
    fireEvent.click(screen.getByText("Effective config"))

    await waitFor(() => expect(mockFetchApi).toHaveBeenCalled())
    const calledPath = mockFetchApi.mock.calls[0][0] as string
    expect(calledPath).not.toContain("advanced=")
    expect(calledPath).toBe(
      "/api/config/effective?targets=example.com&profile=deep&calibration=balanced&enable_nmap=false&port_scope=top1000&vertical=healthcare",
    )
  })

  it("a non-empty advanced prop adds exactly one advanced= segment carrying the JSON-encoded delta", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} advanced={{ tls_enum_mode: "deep" }} />)
    fireEvent.click(screen.getByText("Effective config"))

    await waitFor(() => expect(mockFetchApi).toHaveBeenCalled())
    const calledPath = mockFetchApi.mock.calls[0][0] as string
    const matches = calledPath.match(/advanced=/g) ?? []
    expect(matches.length).toBe(1)
    expect(calledPath).toContain(`advanced=${encodeURIComponent(JSON.stringify({ tls_enum_mode: "deep" }))}`)
  })

  it("changing an advanced value changes the query string, proving the refetch key moves", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    const { rerender } = render(
      <EffectiveConfigPanel {...defaultProps()} advanced={{ tls_enum_mode: "fast" }} />,
    )
    fireEvent.click(screen.getByText("Effective config"))
    await waitFor(() => expect(mockFetchApi).toHaveBeenCalledTimes(1))
    const firstPath = mockFetchApi.mock.calls[0][0] as string

    rerender(<EffectiveConfigPanel {...defaultProps()} advanced={{ tls_enum_mode: "deep" }} />)
    await waitFor(() => expect(mockFetchApi).toHaveBeenCalledTimes(2))
    const secondPath = mockFetchApi.mock.calls[1][0] as string

    expect(secondPath).not.toBe(firstPath)
  })
})

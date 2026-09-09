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

  it("badges a user-provenance field as 'Overridden' and a preset field as 'Preset: {vertical}'", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(BASE_RESPONSE))
    render(<EffectiveConfigPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Effective config"))

    expect(await screen.findByText("Overridden")).toBeInTheDocument()
    expect(screen.getByText("Preset: healthcare")).toBeInTheDocument()
    // default field renders no provenance badge
    expect(screen.queryByText("Preset: healthcare")?.closest("table")).toBeTruthy()
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
})

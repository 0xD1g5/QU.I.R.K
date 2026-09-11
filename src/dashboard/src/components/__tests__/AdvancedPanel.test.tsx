// Phase 194 Plan 05 (PARITY-04) — Advanced panel component tests.
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { AdvancedPanel } from "../AdvancedPanel"
import type { AdvancedScanFields } from "@/types/api"

function defaultProps(overrides: Partial<Parameters<typeof AdvancedPanel>[0]> = {}) {
  return {
    advanced: {} as AdvancedScanFields,
    onAdvancedChange: vi.fn(),
    presetState: null,
    disabled: false,
    ...overrides,
  }
}

describe("AdvancedPanel", () => {
  it("is collapsed by default with trigger text 'Advanced' present", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    expect(screen.getByText("Advanced")).toBeInTheDocument()
    expect(screen.queryByLabelText("TLS Enumeration Mode")).not.toBeInTheDocument()
  })

  it("editing only tls_enum_mode calls onAdvancedChange with a map whose keys are exactly ['tls_enum_mode']", () => {
    const onAdvancedChange = vi.fn()
    render(<AdvancedPanel {...defaultProps({ onAdvancedChange })} />)
    fireEvent.click(screen.getByText("Advanced"))

    fireEvent.click(screen.getByLabelText("TLS Enumeration Mode"))
    fireEvent.click(screen.getByText("Deep"))

    expect(onAdvancedChange).toHaveBeenCalledTimes(1)
    const arg = onAdvancedChange.mock.calls[0][0]
    expect(Object.keys(arg)).toEqual(["tls_enum_mode"])
    expect(arg.tls_enum_mode).toBe("deep")
  })

  it("clearing a previously set numeric field removes the key from the map entirely", () => {
    const onAdvancedChange = vi.fn()
    render(
      <AdvancedPanel
        {...defaultProps({ advanced: { retry_count: 3 }, onAdvancedChange })}
      />,
    )
    fireEvent.click(screen.getByText("Advanced"))

    const retryInput = screen.getByLabelText(/Retry count/)
    fireEvent.change(retryInput, { target: { value: "" } })

    expect(onAdvancedChange).toHaveBeenCalledTimes(1)
    const arg = onAdvancedChange.mock.calls[0][0]
    expect(Object.keys(arg)).not.toContain("retry_count")
  })

  it("the TLS-mode select renders exactly Fast and Deep and no option whose text is Off", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))
    fireEvent.click(screen.getByLabelText("TLS Enumeration Mode"))

    expect(screen.getByText("Fast")).toBeInTheDocument()
    expect(screen.getByText("Deep")).toBeInTheDocument()
    expect(screen.queryByText("Off")).not.toBeInTheDocument()
  })

  it("the data-classification select renders exactly Public/Internal/Confidential/Regulated and no Restricted", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))
    fireEvent.click(screen.getByLabelText("Data Classification"))

    expect(screen.getByText("Public")).toBeInTheDocument()
    expect(screen.getByText("Internal")).toBeInTheDocument()
    expect(screen.getByText("Confidential")).toBeInTheDocument()
    expect(screen.getByText("Regulated")).toBeInTheDocument()
    expect(screen.queryByText("Restricted")).not.toBeInTheDocument()
  })

  it("renders no element with the text 'SSH Ports' anywhere", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))
    expect(screen.queryByText(/SSH Ports/)).not.toBeInTheDocument()
  })

  // Phase 198 Plan 02 (PARITY-08/PARITY-09, D-05..D-08)

  it("renders the two new group labels 'Per-Scanner Timeouts' and 'Concurrency'", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))
    expect(screen.getByText("Per-Scanner Timeouts")).toBeInTheDocument()
    expect(screen.getByText("Concurrency")).toBeInTheDocument()
  })

  it("renders all 11 short per-scanner timeout labels with full-phrase aria-labels", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))

    const shortLabels = [
      "Fingerprint", "JWT", "Container", "Source", "DNSSEC", "SAML",
      "Kerberos", "Vault", "DB Connect", "Broker", "Email",
    ]
    for (const label of shortLabels) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(screen.getByLabelText("Fingerprint scanner timeout, seconds")).toBeInTheDocument()
    expect(screen.getByLabelText("Broker scanner timeout, seconds")).toBeInTheDocument()
  })

  it("typing 45 into the Broker timeout calls onAdvancedChange with exactly timeout_broker_seconds: 45", () => {
    const onAdvancedChange = vi.fn()
    render(<AdvancedPanel {...defaultProps({ onAdvancedChange })} />)
    fireEvent.click(screen.getByText("Advanced"))

    const brokerInput = screen.getByLabelText("Broker scanner timeout, seconds")
    fireEvent.change(brokerInput, { target: { value: "45" } })

    expect(onAdvancedChange).toHaveBeenCalledTimes(1)
    const arg = onAdvancedChange.mock.calls[0][0]
    expect(Object.keys(arg)).toEqual(["timeout_broker_seconds"])
    expect(arg.timeout_broker_seconds).toBe(45)
  })

  it("clearing the Broker timeout back to blank deletes the key from the delta", () => {
    const onAdvancedChange = vi.fn()
    render(
      <AdvancedPanel
        {...defaultProps({ advanced: { timeout_broker_seconds: 45 }, onAdvancedChange })}
      />,
    )
    fireEvent.click(screen.getByText("Advanced"))

    const brokerInput = screen.getByLabelText("Broker scanner timeout, seconds")
    fireEvent.change(brokerInput, { target: { value: "" } })

    expect(onAdvancedChange).toHaveBeenCalledTimes(1)
    const arg = onAdvancedChange.mock.calls[0][0]
    expect(Object.keys(arg)).not.toContain("timeout_broker_seconds")
  })

  it("renders the 5 concurrency fields with the motion helper naming the shared email + broker pool", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))

    expect(screen.getByText("Scan concurrency")).toBeInTheDocument()
    expect(screen.getByText("Fingerprint concurrency")).toBeInTheDocument()
    expect(screen.getByText("TLS concurrency")).toBeInTheDocument()
    expect(screen.getByText("SSH concurrency")).toBeInTheDocument()
    expect(screen.getByText("Motion concurrency")).toBeInTheDocument()
    expect(screen.getByText(/Shared worker pool for email and broker connector scanning\./)).toBeInTheDocument()
  })

  it("renders the backoff pair inside the existing Timeouts & Retry group with step 0.1", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))

    const baseInput = screen.getByLabelText(/Backoff base \(seconds\)/)
    const maxInput = screen.getByLabelText(/Backoff max \(seconds\)/)
    expect(baseInput).toHaveAttribute("step", "0.1")
    expect(maxInput).toHaveAttribute("step", "0.1")
  })

  it("renders 'TLS-Designated Ports' next to TLS Ports and shows the same invalid-format warning", () => {
    render(
      <AdvancedPanel {...defaultProps({ advanced: { tls_designated_ports: "abc" } })} />,
    )
    fireEvent.click(screen.getByText("Advanced"))

    expect(screen.getByText("TLS-Designated Ports")).toBeInTheDocument()
    expect(screen.getByLabelText("TLS-Designated Ports")).toBeInTheDocument()
    expect(screen.getAllByText("Ports must be numbers, ranges, or commas.").length).toBeGreaterThan(0)
  })

  it("a set field shows the 'Set' badge and no group label carries a badge", () => {
    render(
      <AdvancedPanel {...defaultProps({ advanced: { timeout_broker_seconds: 45 } })} />,
    )
    fireEvent.click(screen.getByText("Advanced"))
    expect(screen.getAllByText("Set").length).toBeGreaterThan(0)
  })

  it("renders no element referencing openapi, retention, or hardware_history", () => {
    render(<AdvancedPanel {...defaultProps()} />)
    fireEvent.click(screen.getByText("Advanced"))
    expect(screen.queryByText(/openapi/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/retention/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/hardware_history/i)).not.toBeInTheDocument()
  })
})

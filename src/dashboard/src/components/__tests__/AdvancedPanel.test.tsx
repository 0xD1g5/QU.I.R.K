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
})

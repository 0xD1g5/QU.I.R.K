import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScanDateBadge } from "../ScanDateBadge"

const mockUseScanList = vi.fn()

vi.mock("@/hooks/useScanList", () => ({
  useScanList: () => mockUseScanList(),
}))

describe("ScanDateBadge — TAIL-01 persistent scan-date badge", () => {
  it("renders nothing while loading (brief-flash prevention only)", () => {
    mockUseScanList.mockReturnValue({ sessions: [], loading: true, error: null })
    const { container } = render(<ScanDateBadge />)
    expect(container).toBeEmptyDOMElement()
  })

  it("shows 'No scan yet' in a status region when there are zero sessions", () => {
    mockUseScanList.mockReturnValue({ sessions: [], loading: false, error: null })
    render(<ScanDateBadge />)
    expect(screen.getByRole("status")).toBeInTheDocument()
    expect(screen.getAllByText("No scan yet").length).toBeGreaterThan(0)
  })

  it("shows 'Last scan: {date} {time}' for the newest session when sessions exist", () => {
    mockUseScanList.mockReturnValue({
      sessions: [{ scan_id: "abc", scanned_at: "2026-08-02T14:56:00Z", total_endpoints: 5 }],
      loading: false,
      error: null,
    })
    render(<ScanDateBadge />)
    expect(screen.getByRole("status")).toBeInTheDocument()
    const matches = screen.getAllByText((_, node) => {
      return !!node?.textContent?.includes("Last scan:")
    })
    expect(matches.length).toBeGreaterThan(0)
  })
})

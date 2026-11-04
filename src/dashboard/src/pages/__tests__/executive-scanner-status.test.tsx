// Phase 235.1 Plan 04 (SRCSCAN-01 / D-06) — ScannerStatusCard labels a
// missing_binary partial failure "Skipped", never "Partial". The card is
// rendered directly (no ExecutivePage), so no fetchApi call can go un-mocked.
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScannerStatusCard } from "../executive"
import type { PartialFailureEntry } from "@/types/api"

function entry(error_category: string): PartialFailureEntry {
  return {
    stage: "source_scanning",
    scanner: "semgrep",
    error_category,
    error_message: "tool unavailable",
    endpoint_count: 0,
  }
}

describe("ScannerStatusCard skip classification", () => {
  it("labels a missing_binary failure Skipped and never Partial", () => {
    render(<ScannerStatusCard failures={[entry("missing_binary")]} />)
    expect(screen.getByLabelText("status: Skipped")).toBeInTheDocument()
    expect(screen.queryByLabelText("status: Partial")).not.toBeInTheDocument()
  })

  it("still labels a missing_extra failure Skipped (regression guard)", () => {
    render(<ScannerStatusCard failures={[entry("missing_extra")]} />)
    expect(screen.getByLabelText("status: Skipped")).toBeInTheDocument()
  })
})

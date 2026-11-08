import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }

const phase = (phase_name: string, status: string, reason: string | null, detail: string | null = null) => ({
  phase_name, label: phase_name.replace("_scanning", ""), status, reason, detail, duration_sec: null,
})
const cov = (...phases: unknown[]) => ({ recorded: true, ran: 0, skipped: phases.length, phases })

afterEach(() => {
  cleanup()
})

describe("MotionPage empty states (COVTRUTH-04)", () => {
  it("motion email card shows the recorded skip reason", async () => {
    scanDataReturn = { data: { motion_findings: [], coverage: cov(phase("email_scanning", "skipped", "missing-credentials")) }, loading: false, error: null }
    const { MotionPage } = await import("@/pages/motion")
    render(<MotionPage />)
    expect(screen.getByText(/Skipped: missing credentials \(email\)/)).toBeInTheDocument()
    expect(screen.queryByText(/enable the email scanner/)).not.toBeInTheDocument()
  })

  it("motion broker card falls back to static text without coverage", async () => {
    scanDataReturn = { data: { motion_findings: [] }, loading: false, error: null }
    const { MotionPage } = await import("@/pages/motion")
    render(<MotionPage />)
    expect(screen.getByText(/enable the broker scanner in your config/)).toBeInTheDocument()
    expect(screen.getByText(/enable the email scanner in your config/)).toBeInTheDocument()
  })
})

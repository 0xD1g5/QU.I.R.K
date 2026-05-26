import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Phase 111: sensors-loading.test.tsx
// Asserts: loading skeleton renders (role="status"), empty state renders enroll-command copy,
// populated list renders one row per sensor with its status text label present.
// Presence-only assertions — visual fidelity is gated on human UAT (111-03).

vi.mock("@/hooks/useSensorRegistry", () => ({
  useSensorRegistry: vi.fn(),
}))

import { useSensorRegistry } from "@/hooks/useSensorRegistry"
import { SensorsPage } from "@/pages/sensors"

const mockUseSensorRegistry = useSensorRegistry as ReturnType<typeof vi.fn>

describe("SensorsPage — loading / empty / populated states", () => {
  it("renders loading skeleton with role=status while loading", () => {
    mockUseSensorRegistry.mockReturnValue({
      sensors: [],
      loading: true,
      error: null,
    })

    render(<SensorsPage />)

    const statusEl = screen.getByRole("status")
    expect(statusEl).toBeDefined()
    expect(statusEl.getAttribute("aria-label")).toBe("Loading sensors")
    // sr-only text
    expect(screen.getByText("Loading...")).toBeDefined()
  })

  it("renders empty state with enroll-command copy when no sensors enrolled", () => {
    mockUseSensorRegistry.mockReturnValue({
      sensors: [],
      loading: false,
      error: null,
    })

    render(<SensorsPage />)

    // The enroll-command copy from UI-SPEC copywriting contract
    expect(
      screen.getByText(/No sensors enrolled\. Run: quirk sensor enroll --console/i),
    ).toBeDefined()
  })

  it("renders one table row per sensor with status text label present", () => {
    mockUseSensorRegistry.mockReturnValue({
      sensors: [
        {
          sensor_id: "sensor-abc-123",
          segment: "dmz",
          sensor_version: "1.2.3",
          last_push_at: new Date(Date.now() - 60_000).toISOString(), // 1 min ago
          status: "current" as const,
        },
        {
          sensor_id: "sensor-def-456",
          segment: "corp",
          sensor_version: null,
          last_push_at: null,
          status: "unknown" as const,
        },
        {
          sensor_id: "sensor-ghi-789",
          segment: "infra",
          sensor_version: "0.9.0",
          last_push_at: new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString(), // 7 days ago
          status: "stale" as const,
        },
      ],
      loading: false,
      error: null,
    })

    render(<SensorsPage />)

    // h1 heading present
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined()

    // Sensor IDs visible (font-mono span)
    expect(screen.getByText("sensor-abc-123")).toBeDefined()
    expect(screen.getByText("sensor-def-456")).toBeDefined()
    expect(screen.getByText("sensor-ghi-789")).toBeDefined()

    // Status text labels present (not color-only — accessibility requirement)
    expect(screen.getByText("Current")).toBeDefined()
    expect(screen.getByText("Unknown")).toBeDefined()
    expect(screen.getByText("Stale")).toBeDefined()
  })
})

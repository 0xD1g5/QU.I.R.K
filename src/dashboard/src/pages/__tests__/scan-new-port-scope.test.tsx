/**
 * Phase 121-01 — scan-new port scope UI stubs (PORT-07, PORT-08).
 *
 * Tests are intentionally RED: the port scope RadioGroup does not exist in
 * scan-new.tsx yet. These stubs define the sampling points for Plans 02–03
 * which will make them green.
 *
 * Covers:
 * - Renders 4 RadioGroupItems: common, top1000, all, custom (PORT-07)
 * - Custom ports input absent until 'custom' selected (PORT-08)
 * - Custom ports input present after clicking 'custom' radio (PORT-08)
 * - nmap checkbox disabled when top1000 or all selected (PORT-08)
 * - nmap checkbox enabled when common or custom selected (PORT-08)
 */
import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { setupServer } from "msw/node"
import { MemoryRouter } from "react-router-dom"

// Mock fetchApi so MSW intercepts correctly in jsdom
vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

// Mock useVertical (used in ScanNewPage)
vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({ name: "General", slug: "general" }),
}))

// Mock useSelectedScan (navigation side-effects)
vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId: null, setSelectedScanId: vi.fn() }),
}))

const server = setupServer()
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// Import the page under test (currently lacks port_scope UI — tests will fail RED)
import { ScanNewPage } from "@/pages/scan-new"

function renderPage() {
  return render(
    <MemoryRouter>
      <ScanNewPage />
    </MemoryRouter>,
  )
}

describe("ScanNewPage — port scope controls (PORT-07, PORT-08)", () => {
  it("renders 4 RadioGroupItems with values common, top1000, all, custom", () => {
    renderPage()
    // Each option must be present in the DOM (PORT-07)
    expect(screen.getByRole("radio", { name: /top 1000/i })).toBeDefined()
    expect(screen.getByRole("radio", { name: /common tls/i })).toBeDefined()
    expect(screen.getByRole("radio", { name: /all ports/i })).toBeDefined()
    expect(screen.getByRole("radio", { name: /custom/i })).toBeDefined()
  })

  it("custom ports input is absent when portScope is not 'custom'", () => {
    renderPage()
    // Default is top1000 — custom_ports input must NOT be in DOM (PORT-08)
    const customInput = document.getElementById("custom_ports")
    expect(customInput).toBeNull()
  })

  it("custom ports input is present after clicking the custom radio", () => {
    renderPage()
    // Click the custom radio (PORT-08)
    const customRadio = document.getElementById("scope-custom")
    if (!customRadio) throw new Error("scope-custom radio not found")
    fireEvent.click(customRadio)
    // After clicking, the custom_ports input must appear
    const customInput = document.getElementById("custom_ports")
    expect(customInput).not.toBeNull()
  })

  it("nmap checkbox is disabled when top1000 is selected", () => {
    renderPage()
    // Default is top1000 — checkbox should be disabled (PORT-08)
    const checkbox = document.getElementById("enable_nmap")
    if (!checkbox) throw new Error("enable_nmap checkbox not found")
    expect((checkbox as HTMLInputElement).disabled).toBe(true)
  })

  it("nmap checkbox is disabled when all is selected", () => {
    renderPage()
    const allRadio = document.getElementById("scope-all")
    if (!allRadio) throw new Error("scope-all radio not found")
    fireEvent.click(allRadio)
    const checkbox = document.getElementById("enable_nmap")
    if (!checkbox) throw new Error("enable_nmap checkbox not found")
    expect((checkbox as HTMLInputElement).disabled).toBe(true)
  })

  it("nmap checkbox is enabled when common is selected", () => {
    renderPage()
    const commonRadio = document.getElementById("scope-common")
    if (!commonRadio) throw new Error("scope-common radio not found")
    fireEvent.click(commonRadio)
    const checkbox = document.getElementById("enable_nmap")
    if (!checkbox) throw new Error("enable_nmap checkbox not found")
    expect((checkbox as HTMLInputElement).disabled).toBe(false)
  })

  it("nmap checkbox is enabled when custom is selected", () => {
    renderPage()
    const customRadio = document.getElementById("scope-custom")
    if (!customRadio) throw new Error("scope-custom radio not found")
    fireEvent.click(customRadio)
    const checkbox = document.getElementById("enable_nmap")
    if (!checkbox) throw new Error("enable_nmap checkbox not found")
    expect((checkbox as HTMLInputElement).disabled).toBe(false)
  })
})

import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ExecutiveVerdict } from "../ExecutiveVerdict"
import type { ScanLatestResponse } from "@/types/api"

function makeData(overrides: Partial<ScanLatestResponse> = {}): ScanLatestResponse {
  return {
    meta: { scan_id: "t1", total_endpoints: 10, total_findings: 3 },
    score: {
      score: 42,
      rating: "MODERATE",
      subscores: {
        hygiene: 10,
        modern_tls: 8,
        identity_trust: 12,
        agility_signals: 5,
        data_at_rest: 18,
        data_in_motion: 9,
      },
      drivers: [
        { id: "weak-cipher", impact: -10, description: "Weak cipher suites on 2 endpoints" },
        { id: "no-ear", impact: -8, description: "Database encryption at rest not confirmed" },
        { id: "good-thing", impact: 4, description: "Modern TLS on most hosts" },
      ],
    },
    confidence: { confidence_score: 85, confidence_rating: "HIGH", factor_breakdown: {} },
    findings: [
      { host: "a", port: 443, severity: "CRITICAL", title: "x", quantum_risk: "Vulnerable" },
      { host: "b", port: 443, severity: "HIGH", title: "y", quantum_risk: "At Risk" },
      { host: "c", port: 22, severity: "MEDIUM", title: "z", quantum_risk: "Vulnerable" },
    ],
    certificates: [],
    cbom_components: [],
    roadmap: {
      nodes: [
        { id: "n1", title: "Disable TLS 1.0/1.1", timeframe: "0-30 days", phase: "NOW", why: "Deprecated and exploitable." },
        { id: "n2", title: "Remove RC4", timeframe: "0-30 days", phase: "NOW", why: "Cryptographically broken." },
        { id: "n3", title: "PQC migration", timeframe: "90+ days", phase: "LATER", why: "Long-term." },
      ],
      edges: [],
    },
    identity_findings: [],
    motion_findings: [],
    dar_findings: [],
    ...overrides,
  }
}

describe("ExecutiveVerdict", () => {
  it("renders the score, band, and harvest-now framing", () => {
    render(<ExecutiveVerdict data={makeData()} />)
    expect(screen.getByText("42")).toBeInTheDocument()
    expect(screen.getByText("NOT QUANTUM-READY")).toBeInTheDocument()
    // 2 of 3 findings are "Vulnerable" → harvest-now count
    expect(screen.getByText(/exposed to harvest-now-decrypt-later/i)).toBeInTheDocument()
  })

  it("surfaces the top negative drivers, sorted, positives excluded", () => {
    render(<ExecutiveVerdict data={makeData()} />)
    expect(screen.getByText(/Weak cipher suites/)).toBeInTheDocument()
    expect(screen.getByText("-10 pts")).toBeInTheDocument()
    expect(screen.getByText("-8 pts")).toBeInTheDocument()
    // The positive driver must not be presented as a cost.
    expect(screen.queryByText(/Modern TLS on most hosts/)).not.toBeInTheDocument()
  })

  it("lists only NOW roadmap actions as 'start here' with cost-of-inaction", () => {
    render(<ExecutiveVerdict data={makeData()} />)
    expect(screen.getByText("Disable TLS 1.0/1.1")).toBeInTheDocument()
    expect(screen.getByText("Remove RC4")).toBeInTheDocument()
    expect(screen.queryByText("PQC migration")).not.toBeInTheDocument()
    expect(screen.getAllByText(/If you do nothing:/).length).toBe(2)
  })

  it("shows the resilient verdict when score is high and no harvest-now findings", () => {
    render(
      <ExecutiveVerdict
        data={makeData({
          score: { ...makeData().score, score: 88, rating: "STRONG" },
          findings: [{ host: "a", port: 443, severity: "LOW", title: "x", quantum_risk: "Safe" }],
        })}
      />,
    )
    expect(screen.getByText("QUANTUM-READY")).toBeInTheDocument()
    expect(screen.getByText(/largely resilient/i)).toBeInTheDocument()
  })
})

import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ExecutiveVerdict } from "../ExecutiveVerdict"
import type { ScanLatestResponse } from "@/types/api"

function makeData(overrides: Partial<ScanLatestResponse> = {}): ScanLatestResponse {
  return {
    meta: { scan_id: "t1", total_endpoints: 10, total_findings: 3 },
    score: {
      score: 42,
      rating: "POOR",
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
    // Phase 194 landing adaptation (Task 1, D-10): fields added to
    // ScanLatestResponse since this spike's test was written 7 months ago
    // (Phase 128 HWCOMPAT-07, Phase 134 CBOM-02, Phase 194 DASH-09).
    hardware_findings: [],
    hardware_devices: [],
    excluded_cert_count: 0,
    ...overrides,
  }
}

const HONEST_ABSENCE_TEXT = "Verdict not available for this scan (pre-v5.21 data)."

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

  it("shows the resilient verdict when rating is EXCELLENT and no harvest-now findings", () => {
    render(
      <ExecutiveVerdict
        data={makeData({
          score: { ...makeData().score, score: 88, rating: "EXCELLENT" },
          findings: [{ host: "a", port: 443, severity: "LOW", title: "x", quantum_risk: "Safe" }],
        })}
      />,
    )
    expect(screen.getByText("QUANTUM-READY")).toBeInTheDocument()
    expect(screen.getByText(/largely resilient/i)).toBeInTheDocument()
  })

  // D-07: band mapping — all six enum values must map to the correct
  // tone/label, and the band must be driven by `rating` alone.
  it.each([
    ["EXCELLENT", "QUANTUM-READY"],
    ["GOOD", "QUANTUM-READY"],
    ["MODERATE", "PARTIALLY READY"],
    ["FAIR", "PARTIALLY READY"],
    ["POOR", "NOT QUANTUM-READY"],
  ] as const)("maps rating %s to band label %s", (rating, label) => {
    render(<ExecutiveVerdict data={makeData({ score: { ...makeData().score, rating } })} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it("renders the honest-absence card for NOT_ASSESSED, with no band label", () => {
    render(
      <ExecutiveVerdict
        data={makeData({ score: { ...makeData().score, rating: "NOT_ASSESSED" } })}
      />,
    )
    expect(screen.getByText(HONEST_ABSENCE_TEXT)).toBeInTheDocument()
    expect(screen.queryByText("QUANTUM-READY")).not.toBeInTheDocument()
    expect(screen.queryByText("PARTIALLY READY")).not.toBeInTheDocument()
    expect(screen.queryByText("NOT QUANTUM-READY")).not.toBeInTheDocument()
  })

  // D-20 / RESEARCH Pitfall 3: `rating: null` (the genuinely-absent-key
  // case) must be tested independently from NOT_ASSESSED — a scan whose
  // rating was never computed is a distinct condition from one the backend
  // explicitly marked NOT_ASSESSED, even though both render the same card.
  it("renders the honest-absence card for rating: null, with no band label", () => {
    render(<ExecutiveVerdict data={makeData({ score: { ...makeData().score, rating: null } })} />)
    expect(screen.getByText(HONEST_ABSENCE_TEXT)).toBeInTheDocument()
    expect(screen.queryByText("QUANTUM-READY")).not.toBeInTheDocument()
    expect(screen.queryByText("PARTIALLY READY")).not.toBeInTheDocument()
    expect(screen.queryByText("NOT QUANTUM-READY")).not.toBeInTheDocument()
  })

  it("renders the honest-absence card for an unrecognized future rating value", () => {
    render(
      <ExecutiveVerdict data={makeData({ score: { ...makeData().score, rating: "SUPERB" } })} />,
    )
    expect(screen.getByText(HONEST_ABSENCE_TEXT)).toBeInTheDocument()
  })

  it("renders the cap-reason note when rating_cap_reason is present", () => {
    render(
      <ExecutiveVerdict
        data={makeData({
          score: {
            ...makeData().score,
            rating_cap_reason: "capped by unencrypted database traffic",
          },
        })}
      />,
    )
    expect(
      screen.getByText("Score capped: capped by unencrypted database traffic"),
    ).toBeInTheDocument()
  })

  it("renders no cap-reason text when rating_cap_reason is null", () => {
    render(
      <ExecutiveVerdict
        data={makeData({ score: { ...makeData().score, rating_cap_reason: undefined } })}
      />,
    )
    expect(screen.queryByText(/Score capped:/)).not.toBeInTheDocument()
  })

  // D-07 regression guard: a high raw score with a POOR rating must still
  // render the vulnerable band — proving the band follows `rating`, not
  // the score number.
  it("renders the vulnerable band for a high score paired with a POOR rating", () => {
    render(
      <ExecutiveVerdict data={makeData({ score: { ...makeData().score, score: 91, rating: "POOR" } })} />,
    )
    expect(screen.getByText("91")).toBeInTheDocument()
    expect(screen.getByText("NOT QUANTUM-READY")).toBeInTheDocument()
  })
})

import { useMemo } from "react"
import { ArrowRight, ShieldAlert, TrendingDown } from "lucide-react"
import type { ScanLatestResponse } from "@/types/api"

/**
 * ExecutiveVerdict — Executive Verdict layer (VERDICT-01).
 *
 * Turns the Executive page from "here is data" into "here is the call".
 * Renders ENTIRELY from the existing /api/scan/latest payload — no new
 * endpoints, no fabricated numbers:
 *   - headline verdict  ← score.score + ratingToTone(score.rating)
 *   - exposure framing   ← count of findings[].quantum_risk
 *   - "costing you most"  ← score.drivers[] (each carries {impact, description})
 *   - "start here"        ← roadmap.nodes filtered to phase === "NOW" (title + why)
 *
 * Renders unconditionally on the executive page (D-06 — no flag gate).
 * Band/tone are driven exclusively by the API's authoritative `rating`
 * field (D-07), never re-derived from the raw score. A scan whose payload
 * carries no rating (pre-v5.21 data, or an unrecognized future band) renders
 * the honest-absence card instead of a headline (D-08).
 */

interface DriverRow {
  id: string
  impact: number
  description: string
}

function parseDrivers(raw: Record<string, unknown>[]): DriverRow[] {
  return raw
    .map((d) => ({
      id: typeof d.id === "string" ? d.id : "",
      impact: typeof d.impact === "number" ? d.impact : 0,
      description: typeof d.description === "string" ? d.description : "",
    }))
    .filter((d) => d.description !== "")
}

type VerdictTone = "safe" | "at-risk" | "vulnerable" | "unavailable"

/**
 * D-07: band/tone derives ONLY from the API's authoritative `rating` enum
 * (EXCELLENT/GOOD/MODERATE/FAIR/POOR/NOT_ASSESSED, quirk/dashboard/api/
 * schemas.py:90) — never re-derived from the raw score. An explicit switch
 * with a default branch means an unrecognized future rating value is
 * honestly reported as "unavailable" rather than silently mis-colored.
 *
 * Not exported: this file must export only the ExecutiveVerdict component
 * (react-refresh/only-export-components). Band-mapping correctness is
 * locked by rendering ExecutiveVerdict with each rating value and asserting
 * on the resulting label/tone, not by importing this function directly.
 */
function ratingToTone(rating: string | null | undefined): VerdictTone {
  switch (rating) {
    case "EXCELLENT":
    case "GOOD":
      return "safe"
    case "MODERATE":
    case "FAIR":
      return "at-risk"
    case "POOR":
      return "vulnerable"
    default:
      // null, undefined, "", "NOT_ASSESSED", or any unrecognized future value.
      return "unavailable"
  }
}

const TONE_LABEL: Record<VerdictTone, string | null> = {
  safe: "QUANTUM-READY",
  "at-risk": "PARTIALLY READY",
  vulnerable: "NOT QUANTUM-READY",
  // D-08: the honest-absence card replaces the band label entirely.
  unavailable: null,
}

const TONE_HSL: Record<VerdictTone, string> = {
  vulnerable: "hsl(var(--quantum-vulnerable))",
  "at-risk": "hsl(var(--quantum-at-risk))",
  safe: "hsl(var(--quantum-safe))",
  // D-08: neutral honest-absence tone — never a vulnerable/safe color, since
  // no verdict was computed. --ds-medium is a hex value (not an HSL triple
  // like --quantum-*), so it is referenced directly, not wrapped in hsl().
  unavailable: "var(--ds-medium)",
}

export function ExecutiveVerdict({ data }: { data: ScanLatestResponse }) {
  const verdict = useMemo(() => {
    const score = data.score.score
    const rating = data.score.rating
    const capReason = data.score.rating_cap_reason
    const tone = ratingToTone(rating)

    const findings = data.findings ?? []
    // quantum_risk values in the payload look like "Vulnerable" / "At Risk".
    const harvestNow = findings.filter((f) =>
      (f.quantum_risk ?? "").toLowerCase().includes("vuln"),
    ).length
    const atRisk = findings.filter((f) =>
      (f.quantum_risk ?? "").toLowerCase().includes("risk"),
    ).length

    // Top score penalties (most negative impact first) — these are the
    // points you'd recover by fixing each item. Real numbers from the payload.
    const drivers = parseDrivers(data.score.drivers ?? [])
      .filter((d) => d.impact < 0)
      .sort((a, b) => a.impact - b.impact)
      .slice(0, 3)

    // "Start here" — the NOW phase of the existing roadmap, with `why` as
    // the cost-of-inaction line.
    const nowActions = (data.roadmap?.nodes ?? [])
      .filter((n) => (n.phase ?? "").toUpperCase() === "NOW")
      .slice(0, 3)

    return { score, tone, capReason, harvestNow, atRisk, total: findings.length, drivers, nowActions }
  }, [data])

  const { score, tone, capReason, harvestNow, atRisk, total, drivers, nowActions } = verdict
  const accent = TONE_HSL[tone]
  const label = TONE_LABEL[tone]

  // D-08: honest-absence card replaces the headline/score/band block
  // entirely when no verdict was computed — never hidden, never a
  // client-derived color.
  if (tone === "unavailable") {
    return (
      <div
        className="rounded-xl border p-6 mb-2"
        style={{
          borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`,
          background: `linear-gradient(135deg, color-mix(in srgb, ${accent} 12%, transparent), transparent)`,
        }}
        role="region"
        aria-label="Quantum readiness verdict"
      >
        <div style={{ fontSize: 14, color: accent, fontWeight: 600 }}>
          Verdict not available for this scan (pre-v5.21 data).
        </div>
      </div>
    )
  }

  // Lead sentence adapts to the actual posture.
  const lead =
    tone === "safe"
      ? "This environment is largely resilient to quantum-era threats."
      : harvestNow > 0
        ? "This environment is exposed to harvest-now-decrypt-later attacks today."
        : "This environment has quantum-readiness gaps to close."

  return (
    <div
      className="rounded-xl border p-6 mb-2"
      style={{
        borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`,
        background: `linear-gradient(135deg, color-mix(in srgb, ${accent} 12%, transparent), transparent)`,
      }}
      role="region"
      aria-label="Quantum readiness verdict"
    >
      {/* Headline row */}
      <div className="flex items-start gap-6">
        <div className="text-center shrink-0" style={{ width: 116 }}>
          <div style={{ fontSize: 52, fontWeight: 800, lineHeight: 1, color: accent }}>
            {score}
          </div>
          <div className="text-muted-foreground" style={{ fontSize: 12, marginTop: 2 }}>
            / 100
          </div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.06em",
              marginTop: 8,
              color: accent,
            }}
          >
            {label}
          </div>
          {/* D-09: cap-reason note, rendered inline directly beneath the
              band label, only when the score was capped. */}
          {capReason && (
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                marginTop: 4,
                color: "var(--ds-high)",
              }}
            >
              Score capped: {capReason}
            </div>
          )}
        </div>

        <div className="flex-1">
          <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.25 }}>{lead}</div>
          <p className="text-muted-foreground" style={{ fontSize: 14, marginTop: 8, lineHeight: 1.5 }}>
            {harvestNow > 0 ? (
              <>
                <span className="font-semibold text-foreground">{harvestNow}</span> of your{" "}
                <span className="font-semibold text-foreground">{total}</span> findings are{" "}
                <span className="font-semibold" style={{ color: accent }}>
                  harvest-now
                </span>{" "}
                risks — protected by classical crypto a quantum adversary could break
                retroactively.
                {atRisk > 0 && (
                  <>
                    {" "}
                    Another <span className="font-semibold text-foreground">{atRisk}</span> are
                    at-risk.
                  </>
                )}
              </>
            ) : (
              <>
                <span className="font-semibold text-foreground">{total}</span> findings across the
                inventory. No immediate harvest-now exposure detected.
              </>
            )}
          </p>
        </div>
      </div>

      {/* Two columns: what's costing you most + start here */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-6">
        {/* What's costing the most — drivers */}
        {drivers.length > 0 && (
          <div>
            <div
              className="flex items-center gap-2 text-muted-foreground"
              style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10 }}
            >
              <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
              What&apos;s costing you the most
            </div>
            <div className="flex flex-col gap-2">
              {drivers.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5"
                  style={{ background: "hsl(var(--card))" }}
                >
                  <div className="flex-1" style={{ fontSize: 13, lineHeight: 1.35 }}>
                    {d.description}
                  </div>
                  <div
                    className="shrink-0"
                    style={{ fontSize: 13, fontWeight: 700, color: "hsl(var(--quantum-vulnerable))" }}
                    title="Points this is subtracting from your readiness score"
                  >
                    {d.impact} pts
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Start here — NOW roadmap actions */}
        {nowActions.length > 0 && (
          <div>
            <div
              className="flex items-center justify-between text-muted-foreground"
              style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10 }}
            >
              <span className="flex items-center gap-2">
                <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                Start here
              </span>
              <a href="/roadmap" className="flex items-center gap-1" style={{ color: "hsl(var(--accent))", textTransform: "none", letterSpacing: 0 }}>
                Full roadmap <ArrowRight className="h-3 w-3" aria-hidden="true" />
              </a>
            </div>
            <div className="flex flex-col gap-2">
              {nowActions.map((n, i) => (
                <div
                  key={n.id}
                  className="rounded-lg border border-border px-3 py-2.5"
                  style={{ background: "hsl(var(--card))", borderLeft: "3px solid hsl(var(--quantum-vulnerable))" }}
                >
                  <div className="flex items-baseline gap-2.5">
                    <span style={{ fontSize: 15, fontWeight: 800, color: "hsl(var(--muted-foreground))" }}>
                      {i + 1}
                    </span>
                    <div className="flex-1">
                      <div style={{ fontSize: 13.5, fontWeight: 650, lineHeight: 1.3 }}>{n.title}</div>
                      {n.why && (
                        <div className="text-muted-foreground" style={{ fontSize: 12, marginTop: 4, lineHeight: 1.4 }}>
                          <span className="font-semibold">If you do nothing:</span> {n.why}
                        </div>
                      )}
                      {n.timeframe && (
                        <div className="text-muted-foreground" style={{ fontSize: 11, marginTop: 4 }}>
                          {n.timeframe}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

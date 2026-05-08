// Industry benchmark lookup for QRAMM scorecard.
// Source: representative community averages — approximate; based on CSNP QRAMM model documentation.
// Returned by getBenchmarks(industry) when the user has saved an Org Profile (D-12).
// When no profile is saved, the scorecard renders "—" for the benchmark column.

export interface DimensionBenchmarks {
  cvi: number
  sgrm: number
  dpe: number
  itr: number
}

export const INDUSTRY_BENCHMARKS: Record<string, DimensionBenchmarks> = {
  financial_services: { cvi: 3.1, sgrm: 2.8, dpe: 2.5, itr: 2.9 },
  healthcare:         { cvi: 2.6, sgrm: 2.4, dpe: 2.2, itr: 2.5 },
  government:         { cvi: 2.8, sgrm: 2.9, dpe: 2.4, itr: 2.7 },
  technology:         { cvi: 3.0, sgrm: 2.6, dpe: 2.7, itr: 3.1 },
  retail:             { cvi: 2.2, sgrm: 2.0, dpe: 2.3, itr: 2.1 },
  energy:             { cvi: 2.4, sgrm: 2.5, dpe: 2.1, itr: 2.3 },
  other:              { cvi: 2.0, sgrm: 2.0, dpe: 2.0, itr: 2.0 },
}

export function getBenchmarks(industry: string | null | undefined): DimensionBenchmarks | null {
  if (!industry) return null
  return INDUSTRY_BENCHMARKS[industry] ?? INDUSTRY_BENCHMARKS.other
}

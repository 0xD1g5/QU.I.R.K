// QRAMM static constants — practice area names, maturity labels, badge classes, dimension order.

export const DIMENSIONS = ["CVI", "SGRM", "DPE", "ITR"] as const
export type Dimension = typeof DIMENSIONS[number]

export const PRACTICE_AREA_NAMES: Record<string, string> = {
  "1.1": "Cryptographic Discovery & Inventory Management",
  "1.2": "Vulnerability Assessment & Classification",
  "1.3": "Cryptographic Dependency Mapping",
  "2.1": "Executive Leadership & Policy Management",
  "2.2": "Risk & Compliance Management",
  "2.3": "Third-Party Risk Management",
  "3.1": "Data Classification",
  "3.2": "Storage Security",
  "3.3": "Transit Security",
  "4.1": "Infrastructure",
  "4.2": "Implementation",
  "4.3": "Testing & Validation",
}

// Practice areas grouped by dimension (1.x = CVI, 2.x = SGRM, 3.x = DPE, 4.x = ITR)
export const DIMENSION_PRACTICE_AREAS: Record<Dimension, string[]> = {
  CVI:  ["1.1", "1.2", "1.3"],
  SGRM: ["2.1", "2.2", "2.3"],
  DPE:  ["3.1", "3.2", "3.3"],
  ITR:  ["4.1", "4.2", "4.3"],
}

export const MATURITY_LABEL: Record<number, string> = {
  1: "Basic",
  2: "Developing",
  3: "Established",
  4: "Optimizing",
}

// Maturity badge classes — semantic tokens from tailwind.config.ts
export const MATURITY_BADGE_CLASS: Record<number, string> = {
  4: "bg-quantum-safe/20 text-quantum-safe border border-quantum-safe/30",
  3: "bg-severity-low/20 text-severity-low border border-severity-low/30",
  2: "bg-quantum-at-risk/20 text-quantum-at-risk border border-quantum-at-risk/30",
  1: "bg-quantum-vulnerable/20 text-quantum-vulnerable border border-quantum-vulnerable/30",
}

// Org Profile wizard option lists (UI-SPEC §Component Interaction Contracts)
export const INDUSTRY_OPTIONS = [
  { value: "financial_services", label: "Financial Services" },
  { value: "healthcare",         label: "Healthcare" },
  { value: "government",         label: "Government" },
  { value: "technology",         label: "Technology" },
  { value: "retail",             label: "Retail" },
  { value: "energy",             label: "Energy" },
  { value: "other",              label: "Other" },
]
export const ORG_SIZE_OPTIONS = [
  { value: "1-50",     label: "1–50" },
  { value: "51-500",   label: "51–500" },
  { value: "501-5000", label: "501–5000" },
  { value: "5000+",    label: "5000+" },
]
export const GEOGRAPHIC_SCOPE_OPTIONS = [
  { value: "single_country", label: "Single Country" },
  { value: "multi_country",  label: "Multi-Country" },
  { value: "global",         label: "Global" },
]
export const DATA_SENSITIVITY_OPTIONS = [
  { value: "public",             label: "Public" },
  { value: "internal",           label: "Internal" },
  { value: "confidential",       label: "Confidential" },
  { value: "restricted_secret",  label: "Restricted / Secret" },
]
export const REGULATORY_OPTIONS = [
  "PCI-DSS", "HIPAA", "SOC2", "ISO 27001", "NIST CSF", "CMMC", "None",
]

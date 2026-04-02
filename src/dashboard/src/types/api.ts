export interface SubScores {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
}

export interface ScoreData {
  score: number
  rating: string
  subscores: SubScores
  drivers: Record<string, unknown>[]
}

export interface ConfidenceData {
  confidence_score: number
  confidence_rating: string
  factor_breakdown: Record<string, unknown>
}

export interface FindingItem {
  id?: number
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
}

export interface CertItem {
  host: string
  port: number
  cert_subject?: string
  cert_issuer?: string
  cert_not_after?: string
  cert_pubkey_alg?: string
  cert_pubkey_size?: number
  quantum_safety?: string
}

export interface CbomComponent {
  algorithm: string
  type?: string
  key_size?: number
  quantum_safety?: string
  source_systems: string[]
}

export interface RoadmapNode {
  id: string
  title: string
  timeframe: string
  why?: string
  phase: string
}

export interface RoadmapEdge {
  source: string
  target: string
  reason?: string
}

export interface RoadmapData {
  nodes: RoadmapNode[]
  edges: RoadmapEdge[]
}

export interface ScanMeta {
  scan_id: string
  scanned_at?: string
  total_endpoints: number
  total_findings: number
}

export interface ScanLatestResponse {
  meta: ScanMeta
  score: ScoreData
  confidence: ConfidenceData
  findings: FindingItem[]
  certificates: CertItem[]
  cbom_components: CbomComponent[]
  roadmap: RoadmapData
}

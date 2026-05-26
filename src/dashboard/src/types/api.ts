export interface SubScores {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number
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
  sensor_id?: string | null
  segment?: string | null
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
  sensor_id?: string | null
  segment?: string | null
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

export interface IdentityFinding {
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
  algorithm: string
}

export interface MotionFinding {
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
  tls_version?: string
  cipher_suite?: string
  cert_not_after?: string
  plaintext_exposed: boolean
  starttls_warning: boolean
}

// Phase 67 RESUME-02
export interface PartialFailureEntry {
  stage: string
  scanner: string
  error_category: string
  error_message: string
  endpoint_count: number
}

// Phase 39 GAP-04
export interface DarFinding {
  host: string
  port: number
  severity: string
  title: string
  protocol?: string
  description?: string
  remediation?: string
  quantum_risk?: string
  source?: string
  category: string            // "database" | "object_storage" | "kubernetes" | "vault"
  // Database
  encryption_at_rest?: boolean | null
  tls_in_transit?: boolean | null
  // Object Storage
  encryption_mode?: string | null
  kms_key_id?: string | null
  public_access?: boolean | null
  versioning?: boolean | null
  // Kubernetes
  namespace?: string | null
  secret_type?: string | null
  encryption_provider?: string | null
  // Vault
  seal_type?: string | null
  auto_unseal?: boolean | null
  mount_type?: string | null
}

export interface ScanSession {
  scan_id: string
  scanned_at: string
  total_endpoints: number
  score: number
  profile: string | null
  calibration: string | null
  target: string | null
  finding_counts: { high: number; medium: number; low: number }
}

export interface CompareScanSummary {
  scan_id: string
  scanned_at: string
  score: number
}

export interface SubscoreDelta {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number
}

export interface CompareFinding {
  host: string
  protocol?: string
  severity: string
  description?: string
}

export interface CompareEndpoint {
  host: string
  reason?: string
}

export interface CompareResponse {
  scan_a: CompareScanSummary
  scan_b: CompareScanSummary
  score_delta: number
  subscore_deltas: SubscoreDelta
  added_findings: CompareFinding[]
  removed_findings: CompareFinding[]
  endpoints_only_in_a: string[]
  endpoints_only_in_b: string[]
  changed_endpoints: CompareEndpoint[]
}

export interface ScanLatestResponse {
  meta: ScanMeta
  score: ScoreData
  confidence: ConfidenceData
  findings: FindingItem[]
  certificates: CertItem[]
  cbom_components: CbomComponent[]
  roadmap: RoadmapData
  identity_findings: IdentityFinding[]
  motion_findings: MotionFinding[]
  dar_findings: DarFinding[]
  partial_failures?: PartialFailureEntry[]  // Phase 67 RESUME-02
}

export interface SampleFinding {
  host: string
  port: number
  protocol: string
  severity: string
}

export interface TrendReport {
  current_session_ts: string | null
  previous_session_ts: string | null
  current_score: number | null
  previous_score: number | null
  score_delta: number | null
  new_high: number
  new_medium: number
  new_low: number
  resolved_high: number
  resolved_medium: number
  resolved_low: number
  scan_errors_new_count: number
  scan_errors_resolved_count: number
  new_findings_sample: SampleFinding[]
  resolved_findings_sample: SampleFinding[]
}

// Phase 64 TREND-01: timeline types
export interface TrendFindingCounts {
  high: number
  medium: number
  low: number
}

export interface TrendSessionPoint {
  session_ts: string       // ISO 8601 string
  score: number
  subscores: SubScores     // reuses existing SubScores interface
  finding_counts: TrendFindingCounts
}

export interface TrendTimeline {
  sessions: TrendSessionPoint[]
}

// ============== QRAMM (Phase 54) ==============

export interface QuestionItem {
  question_number: number
  dimension: string
  practice_area: string
  text: string
  maturity_labels: string[]
}

export type MaturityValue = 1 | 2 | 3 | 4

export interface QRAMMSessionSummary {
  session_id: number
  org_name: string | null
  created_at: string | null
  status: string | null
  answers_count: number
}

export interface QRAMMAnswerRead {
  question_number: number
  answer_value: number | null
  suggested_answer: number | null
  confirmed_at: string | null
  evidence_note: string | null
}

export interface QRAMMProfileResponse {
  profile_id: number
  session_id: number
  multiplier: number
}

export interface QRAMMScoreResponse {
  overall: number
  maturity: string
  dimensions: Record<string, { score: number; weighted: number }>
  profile_multiplier: number
}

// Phase 55 QRAMM-15: Compliance Map row returned by
// GET /api/qramm/sessions/{id}/compliance-map
export interface QRAMMComplianceMapRow {
  practice_number: string
  practice_area: string
  dimension: string
  framework: string
  static_weight: number
  relevance_score: number | null
  scanner_informed: boolean
}

// Phase 65 UI-SCAN-01/02: dashboard-initiated scan job types
export interface ScanSubmitRequest {
  targets: string
  profile: "quick" | "standard" | "deep"
  calibration: "strict" | "balanced" | "lenient"
  enable_nmap: boolean
}

export interface JobStatus {
  job_id: string
  status: "queued" | "running" | "completed" | "failed" | "cancelled"
  current_stage: string | null
  started_at: string | null
  completed_at: string | null
  scan_run_id: string | null
  error_message: string | null
  stage_index: number
  stage_total: number
}

// Phase 111 — Distributed On-Prem Scanner types

export interface SensorRegistryItem {
  sensor_id: string
  segment: string
  sensor_version?: string | null
  last_push_at?: string | null  // ISO datetime string
  status: "current" | "stale" | "unknown"
}

export interface SensorRegistryResponse {
  sensors: SensorRegistryItem[]
}

export interface MergeLatestData {
  scan_id?: string | null
  merged_at?: string | null   // ISO datetime string
  score?: number | null
  endpoint_count: number
  sensor_count: number
  coverage_warning?: Record<string, unknown> | null
  per_segment_scores: Record<string, number>
}

export interface MergeLatestResponse {
  merge: MergeLatestData | null
}

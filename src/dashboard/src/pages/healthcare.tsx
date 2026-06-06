import { useScanData } from "@/hooks/useScanData"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { PageSpinner } from "@/components/PageSpinner"
import { ShieldCheck, AlertTriangle, CheckCircle2, XCircle, HeartPulse } from "lucide-react"

// HIPAA Technical Safeguards (45 CFR § 164.312) mapped to QU.I.R.K. subscores
const HIPAA_SAFEGUARDS = [
  {
    code: "§ 164.312(a)",
    name: "Access Control",
    description: "Unique user ID, emergency access procedure, automatic logoff, encryption/decryption of ePHI",
    subscoreKeys: ["identity_trust"] as const,
    risk_note: "Weak identity cryptography enables unauthorized ePHI access",
  },
  {
    code: "§ 164.312(b)",
    name: "Audit Controls",
    description: "Hardware, software, and procedural mechanisms to record and examine system activity containing ePHI",
    subscoreKeys: ["hygiene"] as const,
    risk_note: "Expired certificates and weak algorithms undermine audit trail integrity",
  },
  {
    code: "§ 164.312(c)",
    name: "Integrity",
    description: "Protect ePHI from improper alteration or destruction; authenticate ePHI at rest",
    subscoreKeys: ["data_at_rest"] as const,
    risk_note: "At-risk encryption leaves stored ePHI vulnerable to harvest-now/decrypt-later attacks",
  },
  {
    code: "§ 164.312(d)",
    name: "Person / Entity Authentication",
    description: "Verify the identity of persons or entities seeking access to ePHI before granting access",
    subscoreKeys: ["identity_trust", "agility_signals"] as const,
    risk_note: "Quantum-vulnerable authentication tokens can be forged with sufficient compute",
  },
  {
    code: "§ 164.312(e)",
    name: "Transmission Security",
    description: "Guard against unauthorized access to ePHI transmitted over electronic communications networks",
    subscoreKeys: ["data_in_motion", "modern_tls"] as const,
    risk_note: "TLS sessions using classical key exchange expose ePHI in transit to future decryption",
  },
]

// Healthcare system categories relevant to quantum cryptographic risk
const HEALTHCARE_SYSTEM_TYPES = [
  {
    name: "EHR / EMR Platforms",
    examples: "Epic, Oracle Health, Meditech",
    risk_area: "Patient record confidentiality, audit log integrity",
    relevant_subscores: ["data_at_rest", "identity_trust"],
  },
  {
    name: "Telemedicine & Patient Portals",
    examples: "Web/API endpoints, FHIR R4 APIs",
    risk_area: "ePHI in transit, session token security",
    relevant_subscores: ["modern_tls", "data_in_motion"],
  },
  {
    name: "Medical Imaging (PACS / DICOM)",
    examples: "Radiology systems, DICOM endpoints",
    risk_area: "High-value image store encryption",
    relevant_subscores: ["data_at_rest", "modern_tls"],
  },
  {
    name: "Pharmacy & Clinical Systems",
    examples: "Order management, medication dispensing",
    risk_area: "Prescription integrity, controlled substance audit trails",
    relevant_subscores: ["data_at_rest", "hygiene"],
  },
  {
    name: "Connected Medical Devices",
    examples: "IoMT, infusion pumps, monitoring equipment",
    risk_area: "Firmware signing, command authentication",
    relevant_subscores: ["identity_trust", "agility_signals"],
  },
]

type Subscores = {
  hygiene: number
  modern_tls: number
  identity_trust: number
  agility_signals: number
  data_at_rest: number
  data_in_motion: number
}

function safeRisk(subscoreKeys: readonly (keyof Subscores)[], subscores: Subscores): "low" | "medium" | "high" {
  const vals = subscoreKeys.map((k) => subscores[k])
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length
  if (avg >= 18) return "low"
  if (avg >= 10) return "medium"
  return "high"
}

const RISK_BADGE: Record<string, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  low: {
    label: "Low Risk",
    className: "bg-quantum-safe/10 text-quantum-safe border border-quantum-safe/30",
    Icon: CheckCircle2,
  },
  medium: {
    label: "Review Required",
    className: "bg-quantum-at-risk/10 text-quantum-at-risk border border-quantum-at-risk/30",
    Icon: AlertTriangle,
  },
  high: {
    label: "High Risk",
    className: "bg-quantum-vulnerable/10 text-quantum-vulnerable border border-quantum-vulnerable/30",
    Icon: XCircle,
  },
}

export function HealthcarePage() {
  const { data, loading, error } = useScanData()

  if (loading) return <PageSpinner ariaLabel="Loading healthcare posture" />

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">{error}</p>
      </div>
    )
  }

  const subscores = data?.score?.subscores as Subscores | undefined

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-start gap-3">
        <HeartPulse className="h-6 w-6 mt-0.5 flex-shrink-0" style={{ color: "#4ba8a8" }} aria-hidden="true" />
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }} className="text-foreground">
            Healthcare Compliance Posture
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Quantum-readiness risk mapped to HIPAA Technical Safeguards (45 CFR § 164.312) and common healthcare
            system categories. Scores derived from the most recent QU.I.R.K. scan.
          </p>
        </div>
      </div>

      {/* HIPAA Technical Safeguards */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" style={{ color: "#4ba8a8" }} aria-hidden="true" />
            <CardTitle style={{ fontSize: 16, fontWeight: 600 }}>
              HIPAA Technical Safeguards — 45 CFR § 164.312
            </CardTitle>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Each safeguard requirement is rated against the relevant QU.I.R.K. subscore(s). Scores are on a
            0–25 scale per dimension.
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {HIPAA_SAFEGUARDS.map((sg) => {
              const risk = subscores ? safeRisk(sg.subscoreKeys, subscores) : null
              const scoreVals = subscores
                ? sg.subscoreKeys.map((k) => ({ key: k, val: subscores[k] }))
                : []
              const badge = risk ? RISK_BADGE[risk] : null

              return (
                <div
                  key={sg.code}
                  className="rounded-md border border-border p-4 space-y-2"
                  style={{ background: "var(--ds-bg-surface)" }}
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-muted-foreground">{sg.code}</span>
                      <span className="font-semibold text-sm">{sg.name}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      {scoreVals.map(({ key, val }) => (
                        <span
                          key={key}
                          className="text-xs font-mono px-2 py-0.5 rounded border border-border bg-card"
                          title={`${key}: ${val}/25`}
                        >
                          {key.replace(/_/g, " ")}: <span className="font-semibold">{val ?? "—"}</span>
                          <span className="text-muted-foreground">/25</span>
                        </span>
                      ))}
                      {!subscores && (
                        <span className="text-xs text-muted-foreground italic">No scan data</span>
                      )}
                      {badge && (
                        <Badge className={badge.className}>
                          <badge.Icon className="h-3 w-3 mr-1" aria-hidden="true" />
                          {badge.label}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{sg.description}</p>
                  {risk && risk !== "low" && (
                    <p className="text-xs flex items-center gap-1.5" style={{ color: risk === "high" ? "#e05555" : "#d4893a" }}>
                      <AlertTriangle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                      {sg.risk_note}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Healthcare System Coverage */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle style={{ fontSize: 16, fontWeight: 600 }}>
            Healthcare System Categories
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Common healthcare infrastructure types and the QU.I.R.K. risk dimensions most relevant to
            each. Include these endpoint types in your scan targets for comprehensive ePHI coverage.
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {HEALTHCARE_SYSTEM_TYPES.map((sys) => (
              <div
                key={sys.name}
                className="grid grid-cols-[1fr_1.4fr_auto] gap-4 items-start rounded-md border border-border px-4 py-3"
                style={{ background: "var(--ds-bg-surface)" }}
              >
                <div>
                  <p className="text-sm font-semibold">{sys.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{sys.examples}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{sys.risk_area}</p>
                </div>
                <div className="flex flex-wrap gap-1 justify-end">
                  {sys.relevant_subscores.map((s) => (
                    <span
                      key={s}
                      className="text-xs font-mono px-1.5 py-0.5 rounded border border-accent/30 text-accent bg-accent/5"
                    >
                      {s.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quantum Threat Context for Healthcare */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle style={{ fontSize: 16, fontWeight: 600 }}>
            Why Quantum Risk Matters for Healthcare
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-md border border-border p-4 space-y-1.5" style={{ background: "var(--ds-bg-surface)" }}>
              <p className="text-sm font-semibold">Harvest Now, Decrypt Later</p>
              <p className="text-xs text-muted-foreground">
                Adversaries are intercepting and archiving encrypted ePHI transmissions today, planning to
                decrypt them once cryptographically relevant quantum computers become available. Patient
                records have a 50–75 year sensitivity horizon — well within the quantum threat window.
              </p>
            </div>
            <div className="rounded-md border border-border p-4 space-y-1.5" style={{ background: "var(--ds-bg-surface)" }}>
              <p className="text-sm font-semibold">HIPAA Long-Term Compliance</p>
              <p className="text-xs text-muted-foreground">
                HIPAA requires covered entities to protect ePHI confidentiality and integrity for as long as
                data is retained. Classical encryption algorithms (RSA, ECC) are expected to be broken by
                quantum computers within the HIPAA records retention window for many organizations.
              </p>
            </div>
            <div className="rounded-md border border-border p-4 space-y-1.5" style={{ background: "var(--ds-bg-surface)" }}>
              <p className="text-sm font-semibold">Regulatory Momentum</p>
              <p className="text-xs text-muted-foreground">
                NIST finalized post-quantum cryptography standards (FIPS 203/204/205) in August 2024.
                HHS guidance is expected to align with NIST PQC migration timelines. Starting your
                cryptographic inventory now positions your organization ahead of mandated transitions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Compliance note */}
      <p className="text-xs text-muted-foreground">
        QU.I.R.K. scans technical cryptographic posture. HIPAA compliance requires additional administrative
        and physical safeguard assessments outside the scope of automated scanning. Consult qualified
        HIPAA counsel for a complete compliance determination.
      </p>
    </div>
  )
}

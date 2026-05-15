import { useContext, useState } from "react"
import { useNavigate } from "react-router-dom"
import { fetchApi } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { PageSpinner } from "@/components/PageSpinner"
import { QRAMMContext } from "@/context/QRAMMContext"
import { useQRAMMSession } from "@/hooks/useQRAMMSession"
import {
  INDUSTRY_OPTIONS,
  ORG_SIZE_OPTIONS,
  GEOGRAPHIC_SCOPE_OPTIONS,
  DATA_SENSITIVITY_OPTIONS,
  REGULATORY_OPTIONS,
} from "@/lib/qramm-constants"

export function OrgProfilePage() {
  const navigate = useNavigate()
  const ctx = useContext(QRAMMContext)
  const { session, loading, reload } = useQRAMMSession()

  // Form state
  const [industry, setIndustry] = useState("")
  const [orgSize, setOrgSize] = useState("")
  const [geographicScope, setGeographicScope] = useState("")
  const [dataSensitivity, setDataSensitivity] = useState("")
  const [selectedRegulatory, setSelectedRegulatory] = useState<string[]>([])

  // Submission state
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // New Assessment flow state
  const [showNewConfirm, setShowNewConfirm] = useState(false)
  const [archiving, setArchiving] = useState(false)

  // ── State A: loading ─────────────────────────────────────────────────────
  if (loading) return <PageSpinner ariaLabel="Loading QRAMM assessment" />

  // ── State B: session exists (auto-resume per D-01) ───────────────────────
  if (session !== null) {
    async function handleConfirmNew() {
      setArchiving(true)
      try {
        if (ctx.sessionId != null) {
          const resp = await fetchApi(`/api/qramm/sessions/${ctx.sessionId}`, { method: "DELETE" })
          if (!resp.ok && resp.status !== 404) {
            // Server still has the session — do NOT reset context so the user
            // can retry rather than ending up with diverged client/server state.
            return
          }
        }
        ctx.setSessionId(null)
        ctx.setProfile(null)
        ctx.setScoreResult(null)
        ctx.resetAnswers(new Map())
        setShowNewConfirm(false)
        reload()
      } catch {
        // Network error — leave context intact so the user can retry.
      } finally {
        setArchiving(false)
      }
    }

    return (
      <div className="space-y-6 py-8 max-w-xl">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Resume Your Assessment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              You have an in-progress assessment. Pick up where you left off.
            </p>
            <p className="text-sm text-muted-foreground">
              {session.org_name ?? "Untitled assessment"} — {session.answers_count} of 120 answered
            </p>
            <div className="flex gap-3">
              <Button
                variant="default"
                onClick={() => navigate("/qramm/assessment")}
              >
                Continue Assessment
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowNewConfirm(v => !v)}
              >
                New Assessment
              </Button>
            </div>

            {showNewConfirm && (
              <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 p-4 space-y-3">
                <p className="text-base font-semibold">Start a New Assessment?</p>
                <p className="text-sm text-muted-foreground">
                  Starting a new assessment will archive your current progress. This cannot be undone.
                </p>
                <div className="flex gap-3">
                  <Button
                    variant="destructive"
                    onClick={handleConfirmNew}
                    disabled={archiving}
                  >
                    {archiving ? "Archiving…" : "Confirm New Assessment"}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setShowNewConfirm(false)}
                    disabled={archiving}
                  >
                    Keep Current Assessment
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── State C: no session — show the org profile form ──────────────────────
  function toggleRegulatory(option: string) {
    setSelectedRegulatory(prev =>
      prev.includes(option) ? prev.filter(o => o !== option) : [...prev, option]
    )
  }

  // D-04 (WR-08): extract API error body via D-02-style coercion so the
  // operator sees the real reason ("Organization Name required") instead
  // of a generic connectivity hint.
  async function readApiError(resp: Response, fallback: string): Promise<string> {
    let body: unknown = null
    const text = await resp.text().catch(() => "")
    if (text) {
      try {
        body = JSON.parse(text)
      } catch {
        body = text
      }
    }
    if (body && typeof body === "object" && typeof (body as {detail?: unknown}).detail === 'string') {
      return (body as { detail: string }).detail
    }
    if (typeof body === "string" && body.length > 0) {
      return body
    }
    return fallback
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitError(null)
    setSubmitting(true)
    try {
      // Step 1: Create session
      const sessionResp = await fetchApi("/api/qramm/sessions", {
        method: "POST",
        body: JSON.stringify({ org_name: null }),
      })
      if (!sessionResp.ok) {
        const detail = await readApiError(sessionResp, "Could not start assessment — check your connection and try again")
        setSubmitError(detail)
        return
      }
      const sessionBody = await sessionResp.json()
      const sessionId: number = sessionBody.session_id

      // Step 2: Create profile
      const profileResp = await fetchApi("/api/qramm/profiles", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId,
          industry,
          org_size: orgSize,
          geographic_scope: geographicScope,
          data_sensitivity: dataSensitivity,
          regulatory_obligations: selectedRegulatory,
        }),
      })
      if (!profileResp.ok) {
        const detail = await readApiError(profileResp, "Could not start assessment — check your connection and try again")
        setSubmitError(detail)
        return
      }
      const profileBody = await profileResp.json()
      const multiplier: number = profileBody.multiplier

      // Step 3: Update context
      ctx.setSessionId(sessionId)
      ctx.setProfile({
        industry,
        org_size: orgSize,
        geographic_scope: geographicScope,
        data_sensitivity: dataSensitivity,
        regulatory_obligations: selectedRegulatory,
        multiplier,
      })

      // Step 4: Navigate
      navigate("/qramm/assessment")
    } catch {
      setSubmitError("Could not start assessment — check your connection and try again")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="py-8 max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">QRAMM Org Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Industry */}
            <div className="space-y-2">
              <Label htmlFor="industry">Industry</Label>
              <Select value={industry} onValueChange={setIndustry} required>
                <SelectTrigger id="industry">
                  <SelectValue placeholder="Select industry…" />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRY_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Org Size */}
            <div className="space-y-2">
              <Label htmlFor="org-size">Organization Size</Label>
              <Select value={orgSize} onValueChange={setOrgSize} required>
                <SelectTrigger id="org-size">
                  <SelectValue placeholder="Select size…" />
                </SelectTrigger>
                <SelectContent>
                  {ORG_SIZE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Geographic Scope */}
            <div className="space-y-2">
              <Label htmlFor="geographic-scope">Geographic Scope</Label>
              <Select value={geographicScope} onValueChange={setGeographicScope} required>
                <SelectTrigger id="geographic-scope">
                  <SelectValue placeholder="Select scope…" />
                </SelectTrigger>
                <SelectContent>
                  {GEOGRAPHIC_SCOPE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Data Sensitivity */}
            <div className="space-y-2">
              <Label htmlFor="data-sensitivity">Data Sensitivity</Label>
              <Select value={dataSensitivity} onValueChange={setDataSensitivity} required>
                <SelectTrigger id="data-sensitivity">
                  <SelectValue placeholder="Select sensitivity…" />
                </SelectTrigger>
                <SelectContent>
                  {DATA_SENSITIVITY_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Regulatory Obligations (badge multi-select) */}
            <div className="space-y-2">
              <Label>Regulatory Obligations</Label>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Regulatory obligations">
                {REGULATORY_OPTIONS.map(option => {
                  const selected = selectedRegulatory.includes(option)
                  return (
                    <button
                      key={option}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => toggleRegulatory(option)}
                      className={[
                        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors cursor-pointer",
                        selected
                          ? "bg-accent/15 text-accent border-accent"
                          : "bg-transparent text-muted-foreground border-border hover:border-accent/50 hover:text-foreground",
                      ].join(" ")}
                    >
                      {option}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Submit error */}
            {submitError && (
              <p className="text-sm text-destructive">{submitError}</p>
            )}

            {/* Submit */}
            <Button
              type="submit"
              variant="default"
              disabled={submitting || !industry || !orgSize || !geographicScope || !dataSensitivity}
              className="w-full"
            >
              {submitting ? "Starting…" : "Start Assessment"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

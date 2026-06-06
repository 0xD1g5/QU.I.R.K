import { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { fetchApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import type { ScanSubmitRequest } from "@/types/api"
import { HeartPulse } from "lucide-react"

export function ScanNewPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isReconstructed = searchParams.get("reconstructed") === "1"
  const [targets, setTargets] = useState(() => searchParams.get("target") ?? "")
  const [profile, setProfile] = useState<ScanSubmitRequest["profile"]>(
    () => (searchParams.get("profile") as ScanSubmitRequest["profile"]) ?? "standard",
  )
  const [calibration, setCalibration] = useState<ScanSubmitRequest["calibration"]>(
    () => (searchParams.get("calibration") as ScanSubmitRequest["calibration"]) ?? "balanced",
  )
  const [enableNmap, setEnableNmap] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const trimmed = targets.trim()
    if (!trimmed) {
      setError("Targets field is required.")
      return
    }
    setSubmitting(true)
    try {
      const resp = await fetchApi("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targets: trimmed,
          profile,
          calibration,
          enable_nmap: enableNmap,
        } satisfies ScanSubmitRequest),
      })
      if (resp.status === 422) {
        const body = await resp.json().catch(() => ({}))
        const detail = body?.detail
        if (Array.isArray(detail) && detail.length > 0) {
          const msg = detail[0]?.msg ?? "Validation failed."
          if (trimmed.startsWith("@")) {
            setError("@file paths are not supported from the dashboard. Use the CLI to run file-based scans.")
          } else {
            setError(msg)
          }
        } else {
          setError("Validation failed.")
        }
        return
      }
      if (!resp.ok) {
        setError(`Scan could not be started: API returned ${resp.status}. Check the targets format and try again.`)
        return
      }
      const data: { job_id: string; status: string } = await resp.json()
      navigate(`/scan/job/${data.job_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error.")
    } finally {
      setSubmitting(false)
    }
  }

  function applyHealthcarePreset() {
    setTargets("ehr.hospital.internal, pacs.hospital.internal, portal.hospital.internal, pharmacy.hospital.internal")
    setProfile("standard")
    setCalibration("strict")
  }

  return (
    <Card className="max-w-[640px] mx-auto mt-16 px-6 py-6">
      <h1 className="text-xl font-semibold">New Scan</h1>
      <p className="text-sm text-muted-foreground mt-1">Configure and run a scan from the dashboard.</p>

      {/* Healthcare preset */}
      <div
        className="flex items-center justify-between gap-3 rounded-md border px-3 py-2.5 mt-3"
        style={{ background: "var(--ds-accent-dim)", borderColor: "var(--ds-accent-bdr)" }}
      >
        <div className="flex items-center gap-2">
          <HeartPulse className="h-4 w-4 flex-shrink-0" style={{ color: "#4ba8a8" }} aria-hidden="true" />
          <span className="text-xs text-muted-foreground">
            <span className="font-semibold" style={{ color: "#4ba8a8" }}>Healthcare preset</span>
            {" — "}Standard depth, strict calibration, EHR / PACS / portal targets
          </span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="flex-shrink-0 text-xs h-7 px-2 border-accent/40 hover:bg-accent/10"
          style={{ color: "#4ba8a8" }}
          onClick={applyHealthcarePreset}
        >
          Apply
        </Button>
      </div>

      <Separator className="my-4" />

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Targets field */}
        <div className="space-y-2">
          {isReconstructed && (
            <div
              role="status"
              className="rounded-md border px-4 py-3 text-sm mb-2"
              style={{
                backgroundColor: "hsl(var(--ds-high-dim, 30 80% 50% / 0.10))",
                borderColor: "hsl(var(--ds-high-bdr, 30 80% 50% / 0.30))",
                color: "hsl(var(--ds-high, 30 80% 50%))",
              }}
            >
              <p className="font-semibold">Targets reconstructed from scan results</p>
              <p className="text-xs mt-1">This clone was launched from the CLI. Review the target list before submitting.</p>
            </div>
          )}
          <Label htmlFor="targets">Targets</Label>
          <textarea
            id="targets"
            rows={4}
            value={targets}
            onChange={(e) => setTargets(e.target.value)}
            placeholder="192.168.1.0/24, api.example.com"
            className={[
              "flex w-full rounded-md border border-input bg-transparent px-3 py-2",
              "text-sm font-mono shadow-sm placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
              "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
            ].join(" ")}
            disabled={submitting}
            aria-describedby="targets-help"
          />
          <p id="targets-help" className="text-xs text-muted-foreground">
            Enter a hostname, IP address, CIDR range, or comma-separated list. Example: 192.168.1.0/24, api.example.com
          </p>
        </div>

        {/* Profile selector */}
        <div className="space-y-2">
          <Label>Scan Profile</Label>
          <RadioGroup
            value={profile}
            onValueChange={(v) => setProfile(v as ScanSubmitRequest["profile"])}
            className="space-y-2"
          >
            <div className="flex items-start gap-3">
              <RadioGroupItem value="quick" id="profile-quick" className="mt-0.5" />
              <div>
                <Label htmlFor="profile-quick" className="font-medium cursor-pointer">Quick</Label>
                <p className="text-xs text-muted-foreground">Fast surface scan, reduced scanner depth</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="standard" id="profile-standard" className="mt-0.5" />
              <div>
                <Label htmlFor="profile-standard" className="font-medium cursor-pointer">Standard</Label>
                <p className="text-xs text-muted-foreground">Full scan, balanced depth (recommended)</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="deep" id="profile-deep" className="mt-0.5" />
              <div>
                <Label htmlFor="profile-deep" className="font-medium cursor-pointer">Deep</Label>
                <p className="text-xs text-muted-foreground">Maximum scanner depth, slower runtime</p>
              </div>
            </div>
          </RadioGroup>
        </div>

        {/* Calibration selector */}
        <div className="space-y-2">
          <Label>Calibration</Label>
          <RadioGroup
            value={calibration}
            onValueChange={(v) => setCalibration(v as ScanSubmitRequest["calibration"])}
            className="space-y-2"
          >
            <div className="flex items-start gap-3">
              <RadioGroupItem value="strict" id="calibration-strict" className="mt-0.5" />
              <div>
                <Label htmlFor="calibration-strict" className="font-medium cursor-pointer">Strict</Label>
                <p className="text-xs text-muted-foreground">Fail on partial evidence</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="balanced" id="calibration-balanced" className="mt-0.5" />
              <div>
                <Label htmlFor="calibration-balanced" className="font-medium cursor-pointer">Balanced</Label>
                <p className="text-xs text-muted-foreground">Recommended for most environments</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="lenient" id="calibration-lenient" className="mt-0.5" />
              <div>
                <Label htmlFor="calibration-lenient" className="font-medium cursor-pointer">Lenient</Label>
                <p className="text-xs text-muted-foreground">Pass with limited evidence</p>
              </div>
            </div>
          </RadioGroup>
        </div>

        {/* Options: nmap */}
        <div className="space-y-2">
          <Label>Options</Label>
          <div className="flex items-start gap-3">
            <Checkbox
              id="enable_nmap"
              checked={enableNmap}
              onCheckedChange={(checked: boolean | "indeterminate") => setEnableNmap(checked === true)}
              className="mt-0.5"
            />
            <div>
              <Label htmlFor="enable_nmap" className="font-medium cursor-pointer">Enable nmap discovery</Label>
              <p className="text-xs text-muted-foreground">
                Requires nmap installed on the server. Adds network-layer host discovery.
              </p>
            </div>
          </div>
        </div>

        <Separator />

        <Button
          type="submit"
          variant="default"
          className="w-full h-11"
          disabled={submitting}
        >
          {submitting ? "Starting scan..." : "Run Scan"}
        </Button>

        {error && (
          <p className="text-sm text-destructive mt-2">{error}</p>
        )}
      </form>
    </Card>
  )
}

import { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { fetchApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import type { ScanSubmitRequest } from "@/types/api"
import { useVertical } from "@/context/vertical-context"

export function ScanNewPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const vertical = useVertical()
  const isReconstructed = searchParams.get("reconstructed") === "1"
  const [targets, setTargets] = useState(() => searchParams.get("target") ?? "")
  const [profile, setProfile] = useState<ScanSubmitRequest["profile"]>(
    () => (searchParams.get("profile") as ScanSubmitRequest["profile"]) ?? "standard",
  )
  const [calibration, setCalibration] = useState<ScanSubmitRequest["calibration"]>(
    () => (searchParams.get("calibration") as ScanSubmitRequest["calibration"]) ?? "balanced",
  )
  const [portScope, setPortScope] = useState<ScanSubmitRequest["port_scope"]>("top1000")
  const [customPorts, setCustomPorts] = useState("")
  const [customPortsError, setCustomPortsError] = useState<string | null>(null)
  const [enableNmap, setEnableNmap] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const nmapForced = portScope === "top1000" || portScope === "all"

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setCustomPortsError(null)
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
          enable_nmap: enableNmap || nmapForced,
          port_scope: portScope,
          ...(portScope === "custom" ? { custom_ports: customPorts } : {}),
        } satisfies ScanSubmitRequest),
      })
      if (resp.status === 422) {
        const body = await resp.json().catch(() => ({}))
        const detail = body?.detail
        if (Array.isArray(detail) && detail.length > 0) {
          const msg = detail[0]?.msg ?? "Validation failed."
          if (trimmed.startsWith("@")) {
            setError("@file paths are not supported from the dashboard. Use the CLI to run file-based scans.")
          } else if (detail[0]?.loc?.includes("custom_ports") || msg.toLowerCase().includes("custom_ports")) {
            setCustomPortsError(msg)
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

  function applyPreset() {
    if (!vertical.preset) return
    setTargets(vertical.preset.targets)
    setProfile(vertical.preset.profile as ScanSubmitRequest["profile"])
    setCalibration(vertical.preset.calibration as ScanSubmitRequest["calibration"])
  }

  return (
    <Card className="max-w-[640px] mx-auto mt-16 px-6 py-6">
      <h1 className="text-xl font-semibold">New Scan</h1>
      <p className="text-sm text-muted-foreground mt-1">Configure and run a scan from the dashboard.</p>

      {/* Vertical preset banner — only rendered when active vertical has a preset */}
      {vertical.preset != null && (
        <div
          className="flex items-center justify-between gap-3 rounded-md border px-3 py-2.5 mt-3"
          style={{ background: "var(--ds-accent-dim)", borderColor: "var(--ds-accent-bdr)" }}
        >
          <div className="flex items-center gap-2">
            <vertical.Icon
              className="h-4 w-4 flex-shrink-0"
              style={{ color: vertical.accentColor }}
              aria-hidden="true"
            />
            <span className="text-xs text-muted-foreground">
              <span className="font-semibold" style={{ color: vertical.accentColor }}>
                {vertical.label} preset
              </span>
              {" — "}{vertical.preset.description}
            </span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="flex-shrink-0 text-xs h-7 px-2 border-accent/40 hover:bg-accent/10"
            style={{ color: vertical.accentColor }}
            onClick={applyPreset}
          >
            Apply
          </Button>
        </div>
      )}

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

        {/* Port Scope selector */}
        <div className="space-y-2">
          <Label>Port Scope</Label>
          <RadioGroup
            value={portScope}
            onValueChange={(v) => setPortScope(v as ScanSubmitRequest["port_scope"])}
            className="space-y-2"
          >
            <div className="flex items-start gap-3">
              <RadioGroupItem value="top1000" id="scope-top1000" className="mt-0.5" />
              <div>
                <Label htmlFor="scope-top1000" className="font-medium cursor-pointer">Top 1000 ports</Label>
                <p className="text-xs text-muted-foreground">nmap --top-ports 1000; recommended default</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="common" id="scope-common" className="mt-0.5" />
              <div>
                <Label htmlFor="scope-common" className="font-medium cursor-pointer">Common TLS ports</Label>
                <p className="text-xs text-muted-foreground">17 curated TLS ports; fast, no nmap required</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="all" id="scope-all" className="mt-0.5" />
              <div>
                <Label htmlFor="scope-all" className="font-medium cursor-pointer">All ports</Label>
                <p className="text-xs text-muted-foreground">All 65535 TCP ports (-p-); exhaustive, slow</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <RadioGroupItem value="custom" id="scope-custom" className="mt-0.5" />
              <div>
                <Label htmlFor="scope-custom" className="font-medium cursor-pointer">Custom</Label>
                <p className="text-xs text-muted-foreground">Specify ports, e.g. 443,8000-9000,15449</p>
              </div>
            </div>
          </RadioGroup>
          {portScope === "custom" && (
            <div className="mt-2">
              <Input
                id="custom_ports"
                placeholder="443,8000-9000,15449"
                value={customPorts}
                onChange={(e) => setCustomPorts(e.target.value)}
                disabled={submitting}
              />
              {customPortsError && (
                <p className="text-sm text-destructive mt-1">{customPortsError}</p>
              )}
            </div>
          )}
        </div>

        {/* Options: nmap */}
        <div className="space-y-2">
          <Label>Options</Label>
          <div className="flex items-start gap-3">
            <Checkbox
              id="enable_nmap"
              checked={enableNmap || nmapForced}
              onCheckedChange={(checked: boolean | "indeterminate") => {
                if (!nmapForced) setEnableNmap(checked === true)
              }}
              disabled={submitting || nmapForced}
              className="mt-0.5"
            />
            <div>
              <Label htmlFor="enable_nmap" className="font-medium cursor-pointer">Enable nmap discovery</Label>
              <p className="text-xs text-muted-foreground">
                {nmapForced
                  ? "Required for Top 1000 / All ports coverage"
                  : "Requires nmap installed on the server. Adds network-layer host discovery."}
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

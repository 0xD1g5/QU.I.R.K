import { ChevronDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { useState } from "react"
import type { AdvancedScanFields } from "@/types/api"

/**
 * Phase 194 Plan 05 (PARITY-04 — D-01..D-04, D-19, D-21): "Advanced" scan
 * fields panel on the scan-submit form. Structural analog of
 * ConnectorsPanel.tsx's collapsible shell and delta-only toggle pattern,
 * minus the availability fetch — there is no server-side "advanced field
 * availability" probe, every field here is always settable.
 *
 * D-02: every change handler writes ONLY the touched key into the delta
 * map via `setField()`, which also DELETES a key when the operator clears
 * a field back to empty rather than sending "" / NaN. A field the operator
 * never touched never appears in the map, so an untouched form submits the
 * byte-identical body it submitted before this phase.
 *
 * D-19: the TLS Enumeration Mode select offers exactly Fast/Deep — no
 * "Off" option, since the scanner silently coerces anything else to
 * "fast". D-21: Data Classification offers exactly
 * Public/Internal/Confidential/Regulated — never the legacy value that
 * exists nowhere in the codebase.
 *
 * D-18 / backlog 999.106: `ports_ssh` has no backend counterpart and is
 * explicitly out of scope — no field for it is rendered here. Do not add
 * one without first landing the backend field.
 */

interface AdvancedPanelProps {
  advanced: AdvancedScanFields
  onAdvancedChange: (next: AdvancedScanFields) => void
  presetState: AdvancedScanFields | null
  disabled?: boolean
}

const PORT_SPEC_HINT_RE = /^[0-9,\-\s]*$/

// Phase 198 Plan 02 (PARITY-08/PARITY-09, D-07): the 11 per-scanner
// timeouts, in TimeoutsCfg declaration order — short visual label + full
// aria-label phrase (the compact grid's visual label omits "(seconds)").
const TIMEOUT_SCANNER_FIELDS: {
  key: keyof AdvancedScanFields
  short: string
  aria: string
}[] = [
  { key: "timeout_fingerprint_seconds", short: "Fingerprint", aria: "Fingerprint scanner timeout, seconds" },
  { key: "timeout_jwt_seconds", short: "JWT", aria: "JWT scanner timeout, seconds" },
  { key: "timeout_container_seconds", short: "Container", aria: "Container scanner timeout, seconds" },
  { key: "timeout_source_seconds", short: "Source", aria: "Source scanner timeout, seconds" },
  { key: "timeout_dnssec_seconds", short: "DNSSEC", aria: "DNSSEC scanner timeout, seconds" },
  { key: "timeout_saml_seconds", short: "SAML", aria: "SAML scanner timeout, seconds" },
  { key: "timeout_kerberos_seconds", short: "Kerberos", aria: "Kerberos scanner timeout, seconds" },
  { key: "timeout_vault_seconds", short: "Vault", aria: "Vault scanner timeout, seconds" },
  { key: "timeout_db_connect_seconds", short: "DB Connect", aria: "DB Connect scanner timeout, seconds" },
  { key: "timeout_broker_seconds", short: "Broker", aria: "Broker scanner timeout, seconds" },
  { key: "timeout_email_seconds", short: "Email", aria: "Email scanner timeout, seconds" },
]

// Phase 198 Plan 02 (PARITY-08/PARITY-09, D-02): 5 live-enumerated
// concurrency knobs, in ScanCfg declaration order.
const CONCURRENCY_FIELDS: {
  key: keyof AdvancedScanFields
  label: string
  helper?: string
}[] = [
  { key: "scan_concurrency", label: "Scan concurrency" },
  { key: "fingerprint_concurrency", label: "Fingerprint concurrency" },
  { key: "tls_concurrency", label: "TLS concurrency" },
  { key: "ssh_concurrency", label: "SSH concurrency" },
  {
    key: "motion_concurrency",
    label: "Motion concurrency",
    helper: "Shared worker pool for email and broker connector scanning.",
  },
]

function isEmptyValue(value: unknown): boolean {
  if (value === "" || value === null || value === undefined) return true
  if (typeof value === "number" && Number.isNaN(value)) return true
  return false
}

export function AdvancedPanel(props: AdvancedPanelProps) {
  const { advanced, onAdvancedChange, presetState, disabled } = props
  const [open, setOpen] = useState(false)

  function setField<K extends keyof AdvancedScanFields>(key: K, value: AdvancedScanFields[K]) {
    if (isEmptyValue(value)) {
      // D-02: clearing a field back to empty DELETES the key from the
      // delta map rather than sending "" / NaN.
      const next = { ...advanced }
      delete next[key]
      onAdvancedChange(next)
      return
    }
    onAdvancedChange({ ...advanced, [key]: value })
  }

  function isSet(key: keyof AdvancedScanFields): boolean {
    return key in advanced
  }

  // Not a component (lowercase, invoked as a plain function via {}) —
  // avoids the react-hooks/static-components lint rule that flags a
  // component defined inside another component's render body.
  function renderSetBadge(field: keyof AdvancedScanFields) {
    if (!isSet(field)) return null
    return (
      <Badge variant="outline" className="text-[var(--ds-accent)] border-[var(--ds-accent)] ml-2">
        Set
      </Badge>
    )
  }

  const portsTlsValue = advanced.ports_tls ?? ""
  const portsTlsInvalid = portsTlsValue.length > 0 && !PORT_SPEC_HINT_RE.test(portsTlsValue)

  // Phase 198 / D-03: tls_designated_ports clones ports_tls's format check.
  const tlsDesignatedPortsValue = advanced.tls_designated_ports ?? ""
  const tlsDesignatedPortsInvalid =
    tlsDesignatedPortsValue.length > 0 && !PORT_SPEC_HINT_RE.test(tlsDesignatedPortsValue)

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mb-6">
      <CollapsibleTrigger className="flex items-center gap-1 text-sm text-muted-foreground hover:text-[var(--ds-accent)] data-[state=open]:text-[var(--ds-accent)]">
        Advanced
        <ChevronDown
          className="h-3.5 w-3.5 transition-transform duration-200 data-[state=open]:rotate-180"
          aria-hidden="true"
        />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Card className="mt-2 p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* TLS Ports */}
            <div>
              <Label htmlFor="advanced-ports-tls" className="text-xs flex items-center">
                TLS Ports
                {renderSetBadge("ports_tls")}
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Comma-separated ports or ranges, e.g. 443,8443,9000-9010
              </p>
              <Input
                id="advanced-ports-tls"
                value={portsTlsValue}
                onChange={(e) => setField("ports_tls", e.target.value)}
                disabled={disabled}
                placeholder={presetState?.ports_tls}
                className="mt-1"
              />
              {portsTlsInvalid && (
                <p className="text-xs mt-1" style={{ color: "var(--ds-high)" }}>
                  Ports must be numbers, ranges, or commas.
                </p>
              )}
            </div>

            {/* TLS-Designated Ports — Phase 198 D-03: clones ports_tls wholesale */}
            <div>
              <Label htmlFor="advanced-tls-designated-ports" className="text-xs flex items-center">
                TLS-Designated Ports
                {renderSetBadge("tls_designated_ports")}
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Ports to treat as TLS even when plaintext is detected — overrides the
                plaintext-on-TLS-port classifier. Comma-separated ports or ranges, e.g. 8443,9443.
              </p>
              <Input
                id="advanced-tls-designated-ports"
                aria-label="TLS-Designated Ports"
                value={tlsDesignatedPortsValue}
                onChange={(e) => setField("tls_designated_ports", e.target.value)}
                disabled={disabled}
                placeholder={presetState?.tls_designated_ports}
                className="mt-1"
              />
              {tlsDesignatedPortsInvalid && (
                <p className="text-xs mt-1" style={{ color: "var(--ds-high)" }}>
                  Ports must be numbers, ranges, or commas.
                </p>
              )}
            </div>

            {/* TLS Enumeration Mode — D-19: Fast/Deep only, disabled mode excluded */}
            <div>
              <Label className="text-xs flex items-center">
                TLS Enumeration Mode
                {renderSetBadge("tls_enum_mode")}
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                The scanner has no off mode — anything other than Fast or Deep is silently
                coerced to Fast.
              </p>
              <Select
                value={advanced.tls_enum_mode ?? ""}
                onValueChange={(v) => setField("tls_enum_mode", v as AdvancedScanFields["tls_enum_mode"])}
                disabled={disabled}
              >
                <SelectTrigger className="mt-1" aria-label="TLS Enumeration Mode">
                  <SelectValue placeholder={presetState?.tls_enum_mode ?? "Select mode"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fast">Fast</SelectItem>
                  <SelectItem value="deep">Deep</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Discovery Options — include_sni only; enable_nmap has its own top-level checkbox */}
            <div>
              <Label className="text-xs flex items-center">
                Discovery Options
                {renderSetBadge("include_sni")}
              </Label>
              <div className="flex items-center gap-2 mt-2">
                <Switch
                  checked={advanced.include_sni ?? presetState?.include_sni ?? false}
                  onCheckedChange={(checked) => setField("include_sni", checked === true)}
                  disabled={disabled}
                  aria-label="Send SNI during TLS probes"
                />
                <span className="text-sm">Send SNI during TLS probes</span>
              </div>
            </div>

            {/* Timeouts & Retry */}
            <div>
              <Label className="text-xs flex items-center">
                Timeouts &amp; Retry
              </Label>
              <div className="space-y-2 mt-1">
                <div>
                  <Label htmlFor="advanced-timeout-default" className="text-xs text-muted-foreground flex items-center">
                    Default timeout (seconds)
                    {renderSetBadge("timeout_default_seconds")}
                  </Label>
                  <Input
                    id="advanced-timeout-default"
                    type="number"
                    min={1}
                    max={300}
                    value={advanced.timeout_default_seconds ?? ""}
                    onChange={(e) => setField(
                      "timeout_default_seconds",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )}
                    disabled={disabled}
                    placeholder={presetState?.timeout_default_seconds?.toString()}
                  />
                </div>
                <div>
                  <Label htmlFor="advanced-timeout-tls" className="text-xs text-muted-foreground flex items-center">
                    TLS timeout (seconds)
                    {renderSetBadge("timeout_tls_seconds")}
                  </Label>
                  <Input
                    id="advanced-timeout-tls"
                    type="number"
                    min={1}
                    max={300}
                    value={advanced.timeout_tls_seconds ?? ""}
                    onChange={(e) => setField(
                      "timeout_tls_seconds",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )}
                    disabled={disabled}
                    placeholder={presetState?.timeout_tls_seconds?.toString()}
                  />
                </div>
                <div>
                  <Label htmlFor="advanced-timeout-ssh" className="text-xs text-muted-foreground flex items-center">
                    SSH timeout (seconds)
                    {renderSetBadge("timeout_ssh_seconds")}
                  </Label>
                  <Input
                    id="advanced-timeout-ssh"
                    type="number"
                    min={1}
                    max={300}
                    value={advanced.timeout_ssh_seconds ?? ""}
                    onChange={(e) => setField(
                      "timeout_ssh_seconds",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )}
                    disabled={disabled}
                    placeholder={presetState?.timeout_ssh_seconds?.toString()}
                  />
                </div>
                <div>
                  <Label htmlFor="advanced-retry-count" className="text-xs text-muted-foreground flex items-center">
                    Retry count (attempts)
                    {renderSetBadge("retry_count")}
                  </Label>
                  <Input
                    id="advanced-retry-count"
                    type="number"
                    min={0}
                    max={10}
                    value={advanced.retry_count ?? ""}
                    onChange={(e) => setField(
                      "retry_count",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )}
                    disabled={disabled}
                    placeholder={presetState?.retry_count?.toString()}
                  />
                </div>
                <div>
                  <Label htmlFor="advanced-retry-backoff-base" className="text-xs text-muted-foreground flex items-center">
                    Backoff base (seconds)
                    {renderSetBadge("retry_backoff_base_seconds")}
                  </Label>
                  <Input
                    id="advanced-retry-backoff-base"
                    type="number"
                    step={0.1}
                    min={0.1}
                    value={advanced.retry_backoff_base_seconds ?? ""}
                    onChange={(e) => setField(
                      "retry_backoff_base_seconds",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )}
                    disabled={disabled}
                    placeholder={presetState?.retry_backoff_base_seconds?.toString()}
                  />
                </div>
                <div>
                  <Label htmlFor="advanced-retry-backoff-max" className="text-xs text-muted-foreground flex items-center">
                    Backoff max (seconds)
                    {renderSetBadge("retry_backoff_max_seconds")}
                  </Label>
                  <Input
                    id="advanced-retry-backoff-max"
                    type="number"
                    step={0.1}
                    min={0.1}
                    value={advanced.retry_backoff_max_seconds ?? ""}
                    onChange={(e) => setField(
                      "retry_backoff_max_seconds",
                      e.target.value === "" ? undefined : Number(e.target.value),
                    )}
                    disabled={disabled}
                    placeholder={presetState?.retry_backoff_max_seconds?.toString()}
                  />
                </div>
              </div>
            </div>

            {/* Per-Scanner Timeouts — Phase 198 D-07: compact nested grid */}
            <div>
              <Label className="text-xs flex items-center">
                Per-Scanner Timeouts
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Overrides the default timeout above for specific scanner types (seconds).
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-2 mt-1">
                {TIMEOUT_SCANNER_FIELDS.map((field) => (
                  <div key={field.key}>
                    <Label htmlFor={`advanced-${field.key}`} className="text-xs text-muted-foreground flex items-center">
                      {field.short}
                      {renderSetBadge(field.key)}
                    </Label>
                    <Input
                      id={`advanced-${field.key}`}
                      aria-label={field.aria}
                      type="number"
                      min={1}
                      max={600}
                      value={(advanced[field.key] as number | undefined) ?? ""}
                      onChange={(e) => setField(
                        field.key,
                        e.target.value === "" ? undefined : Number(e.target.value),
                      )}
                      disabled={disabled}
                      placeholder={(presetState?.[field.key] as number | undefined)?.toString()}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Concurrency — Phase 198 D-02: stacked fields, not the compact grid */}
            <div>
              <Label className="text-xs flex items-center">
                Concurrency
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Worker pool sizes for parallel scanning (higher = faster, more load).
              </p>
              <div className="space-y-2 mt-1">
                {CONCURRENCY_FIELDS.map((field) => (
                  <div key={field.key}>
                    <Label htmlFor={`advanced-${field.key}`} className="text-xs text-muted-foreground flex items-center">
                      {field.label}
                      {renderSetBadge(field.key)}
                    </Label>
                    {field.helper && (
                      <p className="text-xs text-muted-foreground">{field.helper}</p>
                    )}
                    <Input
                      id={`advanced-${field.key}`}
                      type="number"
                      min={1}
                      max={500}
                      value={(advanced[field.key] as number | undefined) ?? ""}
                      onChange={(e) => setField(
                        field.key,
                        e.target.value === "" ? undefined : Number(e.target.value),
                      )}
                      disabled={disabled}
                      placeholder={(presetState?.[field.key] as number | undefined)?.toString()}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Data Classification — D-21: public/internal/confidential/regulated only */}
            <div>
              <Label className="text-xs flex items-center">
                Data Classification
                {renderSetBadge("data_classification")}
              </Label>
              <Select
                value={advanced.data_classification ?? ""}
                onValueChange={(v) => setField(
                  "data_classification",
                  v as AdvancedScanFields["data_classification"],
                )}
                disabled={disabled}
              >
                <SelectTrigger className="mt-1" aria-label="Data Classification">
                  <SelectValue placeholder={presetState?.data_classification ?? "Select classification"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                  <SelectItem value="confidential">Confidential</SelectItem>
                  <SelectItem value="regulated">Regulated</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          {/* D-18: ports_ssh has no backend counterpart, so no field for it
              is rendered here. See backlog item 999.106 before adding one. */}
        </Card>
      </CollapsibleContent>
    </Collapsible>
  )
}

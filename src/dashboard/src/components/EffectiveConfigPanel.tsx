import { useEffect, useState } from "react"
import { ChevronDown } from "lucide-react"
import { fetchApi } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { useVertical } from "@/context/vertical-context"
import type { ScanSubmitRequest } from "@/types/api"

/**
 * Phase 192 Plan 10 (PARITY-01 / D-01..D-05): "Effective config" pre-flight
 * panel on the scan-submit surface. Fetches GET /api/config/effective with
 * the LIVE form selections (not the server's base config) lazily, on first
 * expand only — never on mount — so operators who never open it pay zero
 * fetch cost.
 *
 * Grouped and Raw YAML tabs render the exact same server-redacted payload
 * (single serialization path, D-07 / T-192-35): the raw view is `data.raw`
 * JSON-stringified, never a second, less-redacted fetch. Credential fields
 * are display-only Badges — never any editable form control (T-192-37,
 * Phase 193's edit-form scope).
 *
 * A failed fetch renders an inline notice and NEVER disables or intercepts
 * the form (T-192-38) — scan submission is unaffected by preview failure.
 */

interface ConfigField {
  name: string
  value: unknown
  provenance: "default" | "user" | "preset"
  redacted: boolean
  credential_status: "set" | "not set" | null
}

interface ConfigSection {
  name: string
  title: string
  fields: ConfigField[]
}

interface ConfigEffectiveResponse {
  vertical: string
  profile: string
  sections: ConfigSection[]
  raw: Record<string, unknown>
  redacted_field_count: number
}

interface EffectiveConfigPanelProps {
  targets: string
  profile: ScanSubmitRequest["profile"]
  calibration: ScanSubmitRequest["calibration"]
  enableNmap: boolean
  portScope: ScanSubmitRequest["port_scope"]
  customPorts: string
  // Phase 193 Plan 07 (PARITY-02, D-16): the operator's connector toggle
  // delta from ConnectorsPanel. Optional and query-additive only — an
  // empty/undefined delta must produce the identical query string Phase 192
  // produced, so cached responses and existing behavior are unchanged.
  connectors?: Record<string, boolean>
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "boolean") return value ? "true" : "false"
  return String(value)
}

function buildQuery(props: EffectiveConfigPanelProps, vertical: string): string {
  const params = new URLSearchParams()
  const trimmedTargets = props.targets.trim()
  if (trimmedTargets) params.set("targets", trimmedTargets)
  params.set("profile", props.profile)
  params.set("calibration", props.calibration)
  params.set("enable_nmap", String(props.enableNmap))
  params.set("port_scope", props.portScope)
  if (props.portScope === "custom" && props.customPorts.trim()) {
    params.set("custom_ports", props.customPorts.trim())
  }
  if (vertical) params.set("vertical", vertical)
  // D-16: only append when the operator has touched at least one connector
  // toggle — Object.keys(props.connectors ?? {}).length === 0 must produce
  // the exact same query string as before this field existed.
  if (props.connectors && Object.keys(props.connectors).length > 0) {
    params.set("connectors", JSON.stringify(props.connectors))
  }
  return params.toString()
}

export function EffectiveConfigPanel(props: EffectiveConfigPanelProps) {
  const vertical = useVertical()
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<ConfigEffectiveResponse | null>(null)
  const [failed, setFailed] = useState(false)

  const query = buildQuery(props, vertical.id)

  useEffect(() => {
    // Lazy fetch — only after the panel has been expanded at least once, and
    // only re-fetches on subsequent selection changes while it stays open.
    if (!open) return
    let cancelled = false

    async function load() {
      try {
        const resp = await fetchApi(`/api/config/effective?${query}`)
        if (!resp.ok) {
          if (!cancelled) {
            setFailed(true)
            setData(null)
          }
          return
        }
        const json: ConfigEffectiveResponse = await resp.json()
        if (!cancelled) {
          setData(json)
          setFailed(false)
        }
      } catch {
        if (!cancelled) {
          setFailed(true)
          setData(null)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [open, query])

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mb-6">
      <CollapsibleTrigger className="flex items-center gap-1 text-sm text-muted-foreground hover:text-[var(--ds-accent)] data-[state=open]:text-[var(--ds-accent)]">
        Effective config
        <ChevronDown
          className="h-3.5 w-3.5 transition-transform duration-200 data-[state=open]:rotate-180"
          aria-hidden="true"
        />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Card className="mt-2 p-4">
          {failed && (
            <div>
              <p className="text-sm font-semibold">Effective config unavailable</p>
              <p className="text-sm text-muted-foreground mt-1">
                Could not resolve the config preview. Check your connection and try again, or
                submit the scan — this does not block scanning.
              </p>
            </div>
          )}

          {!failed && data && (
            <Tabs defaultValue="grouped">
              <TabsList>
                <TabsTrigger value="grouped">Grouped</TabsTrigger>
                <TabsTrigger value="raw">Raw YAML</TabsTrigger>
              </TabsList>

              <TabsContent value="grouped">
                {data.sections.map((section) => (
                  <div key={section.name} className="mb-4">
                    <h3 className="text-sm font-semibold mb-1">{section.title}</h3>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Field</TableHead>
                          <TableHead>Value</TableHead>
                          <TableHead>Provenance</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {section.fields.map((field) => (
                          <TableRow key={field.name}>
                            <TableCell className="text-sm font-mono">{field.name}</TableCell>
                            <TableCell className="text-sm">
                              {field.redacted ? (
                                <Badge
                                  variant="secondary"
                                  className={
                                    field.credential_status === "set"
                                      ? "text-[var(--ds-ok)]"
                                      : "text-[var(--ds-medium)]"
                                  }
                                >
                                  {formatValue(field.value)}
                                </Badge>
                              ) : (
                                formatValue(field.value)
                              )}
                            </TableCell>
                            <TableCell>
                              {field.provenance === "user" && (
                                <Badge
                                  variant="outline"
                                  className="text-[var(--ds-accent)] border-[var(--ds-accent)]"
                                >
                                  Overridden
                                </Badge>
                              )}
                              {/* Review WR-05: preset provenance is computed from
                                  apply_profile(cfg, profile) server-side — label with
                                  the scan profile, not the vertical. */}
                              {field.provenance === "preset" && (
                                <Badge variant="secondary">Preset: {data.profile}</Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ))}
              </TabsContent>

              <TabsContent value="raw">
                <pre className="text-xs font-mono whitespace-pre-wrap p-3 rounded-md bg-muted overflow-auto">
                  {JSON.stringify(data.raw, null, 2)}
                </pre>
              </TabsContent>
            </Tabs>
          )}
        </Card>
      </CollapsibleContent>
    </Collapsible>
  )
}

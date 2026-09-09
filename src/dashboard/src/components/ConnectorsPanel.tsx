import { useEffect, useState } from "react"
import { ChevronDown } from "lucide-react"
import { fetchApi } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useVertical } from "@/context/vertical-context"
import type { ConnectorAvailabilityEntry, ConnectorAvailabilityResponse } from "@/types/api"

/**
 * Phase 193 Plan 07 (PARITY-02 / PARITY-03 — D-01..D-04, D-10, D-12, D-15,
 * D-16): "Connectors" panel on the scan-submit form. Fetches
 * GET /api/connectors/availability lazily, on first expand only (identical
 * open/data/failed/cancelled lifecycle to EffectiveConfigPanel), groups the
 * 25 returned connectors into the six 193-UI-SPEC categories (never
 * dropping an unrecognized category — rendered last instead), renders
 * availability-gated toggles with visible (never tooltip-only) reason +
 * verbatim install hint (D-02), and per-connector masked credential inputs
 * that are held only in React state passed up via props — never any
 * browser-persisted storage or a module-level variable (D-12).
 *
 * D-13: only flags the operator actually clicked enter the `connectors`
 * delta — the panel never seeds it with a full 25-key snapshot from
 * `presetState`.
 */

const CATEGORY_ORDER = [
  "Identity",
  "Cloud",
  "Database",
  "Email & Broker",
  "OT/ICS",
  "Source & API",
]

// D-10: ambient-auth connectors use SDK environment/instance credentials —
// no credential input is ever rendered for these, even when a
// CONNECTOR_CREDENTIAL_FIELDS entry existed (it never does for these flags).
const AMBIENT_AUTH_FLAGS = new Set([
  "enable_aws",
  "enable_azure",
  "enable_gcp",
  "enable_s3",
  "enable_blob",
])

interface CredentialFieldSpec {
  key: string
  label: string
  // Phase 193 review CR-03: usernames are identifiers, not secrets — they
  // render as plain text inputs and land inline in the job YAML fragment
  // (per the BrokerCredential/SnmpV3Credential config contract), while
  // secret fields (default) render masked and ride env-var injection only.
  secret?: boolean
}

// D-10: config-declared credential fields per connector, mirroring
// quirk/config_redaction.py's CREDENTIAL_REGISTRY (flat fields) and
// quirk/dashboard/api/routes/jobs.py::_build_credential_env's key shapes.
// Broker / SNMPv3 credentials are per-host on the wire (`broker:<host>`,
// `snmpv3:<host>:auth`, `snmpv3:<host>:priv`) — this panel simplifies that
// to a single "default" host slot with DOCUMENTED fallback semantics
// (Phase 193 review CR-03): the scanners use the "default" entry for any
// host lacking a host-specific entry. Username fields are required for
// authentication (broker auth needs BOTH user and pass_env; SNMPv3 USM
// cannot authenticate with an empty username). Full multi-host credential
// management is out of this plan's scope.
const CONNECTOR_CREDENTIAL_FIELDS: Record<string, CredentialFieldSpec[]> = {
  enable_vault: [{ key: "vault_token", label: "Vault Token" }],
  enable_adcs: [{ key: "adcs_password", label: "AD CS Password" }],
  enable_db: [
    { key: "pg_scanner_password", label: "PostgreSQL Password" },
    { key: "mysql_scanner_password", label: "MySQL Password" },
  ],
  enable_snmp: [
    { key: "snmp_community", label: "SNMP Community String" },
    { key: "snmpv3:default:username", label: "SNMPv3 Username (default host)", secret: false },
    { key: "snmpv3:default:auth", label: "SNMPv3 Auth Password (default host)" },
    { key: "snmpv3:default:priv", label: "SNMPv3 Priv Password (default host)" },
  ],
  enable_broker: [
    { key: "broker:default:user", label: "Broker Username (default host)", secret: false },
    { key: "broker:default", label: "Broker Password (default host)" },
  ],
}

interface ConnectorsPanelProps {
  connectors: Record<string, boolean>
  onConnectorsChange: (next: Record<string, boolean>) => void
  credentials: Record<string, string>
  onCredentialsChange: (next: Record<string, string>) => void
  presetState: Record<string, boolean> | null
}

function groupByCategory(
  entries: ConnectorAvailabilityEntry[],
): { category: string; entries: ConnectorAvailabilityEntry[] }[] {
  const byCategory = new Map<string, ConnectorAvailabilityEntry[]>()
  for (const entry of entries) {
    const list = byCategory.get(entry.category) ?? []
    list.push(entry)
    byCategory.set(entry.category, list)
  }
  const ordered: { category: string; entries: ConnectorAvailabilityEntry[] }[] = []
  for (const category of CATEGORY_ORDER) {
    const list = byCategory.get(category)
    if (list) {
      ordered.push({ category, entries: list })
      byCategory.delete(category)
    }
  }
  // Never drop an unrecognized category (defensive) — render it last.
  for (const [category, list] of byCategory) {
    ordered.push({ category, entries: list })
  }
  return ordered
}

export function ConnectorsPanel(props: ConnectorsPanelProps) {
  const { connectors, onConnectorsChange, credentials, onCredentialsChange, presetState } = props
  const vertical = useVertical()
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<ConnectorAvailabilityResponse | null>(null)
  const [failed, setFailed] = useState(false)
  const [failedStatus, setFailedStatus] = useState<number | string>("network error")

  useEffect(() => {
    // Lazy fetch — only after the panel has been expanded at least once.
    if (!open) return
    let cancelled = false

    async function load() {
      try {
        const resp = await fetchApi("/api/connectors/availability")
        if (!resp.ok) {
          if (!cancelled) {
            setFailed(true)
            setFailedStatus(resp.status)
            setData(null)
          }
          return
        }
        const json: ConnectorAvailabilityResponse = await resp.json()
        if (!cancelled) {
          setData(json)
          setFailed(false)
        }
      } catch {
        if (!cancelled) {
          setFailed(true)
          setFailedStatus("network error")
          setData(null)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [open])

  function isOn(flag: string): boolean {
    if (flag in connectors) return connectors[flag]
    return presetState?.[flag] ?? false
  }

  function toggle(flag: string, nextValue: boolean) {
    // D-13: delta-only — only the flag the operator touched enters the map.
    onConnectorsChange({ ...connectors, [flag]: nextValue })
  }

  function setCredential(key: string, value: string) {
    onCredentialsChange({ ...credentials, [key]: value })
  }

  const groups = data ? groupByCategory(data.connectors) : []

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mb-6">
      <CollapsibleTrigger className="flex items-center gap-1 text-sm text-muted-foreground hover:text-[var(--ds-accent)] data-[state=open]:text-[var(--ds-accent)]">
        Connectors
        <ChevronDown
          className="h-3.5 w-3.5 transition-transform duration-200 data-[state=open]:rotate-180"
          aria-hidden="true"
        />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <Card className="mt-2 p-4">
          {failed && (
            <div>
              <p className="text-sm font-semibold">
                Connector availability failed to load ({failedStatus})
              </p>
              <p className="text-sm text-[var(--ds-medium)] mt-1">
                Toggling connectors is unavailable until this resolves — the scan can still be
                submitted with default connectors.
              </p>
            </div>
          )}

          {!failed && data && groups.length === 0 && (
            <div>
              <h3 className="text-base font-semibold">No connectors available</h3>
              <p className="text-sm text-[var(--ds-medium)] mt-1">
                None of the 25 connectors are installed in this environment. See the install
                hints above, or run with default TLS/SSH/JWT coverage only.
              </p>
            </div>
          )}

          {!failed && data && groups.map((group, groupIdx) => (
            <div key={group.category} className={groupIdx > 0 ? "mt-4" : ""}>
              {groupIdx > 0 && <Separator className="mb-4" />}
              <h4 className="text-xs font-semibold mb-2">{group.category}</h4>
              <div className="space-y-3">
                {group.entries.map((entry) => {
                  const on = isOn(entry.flag)
                  const isUserSet = entry.flag in connectors
                  const isPreset = !isUserSet && presetState != null && presetState[entry.flag] === true
                  const isAmbientAuth = AMBIENT_AUTH_FLAGS.has(entry.flag)
                  const credentialFields = isAmbientAuth ? [] : (CONNECTOR_CREDENTIAL_FIELDS[entry.flag] ?? [])
                  const allCredentialsBlank =
                    credentialFields.length > 0 &&
                    credentialFields.every((f) => !(credentials[f.key] ?? "").trim())

                  return (
                    <div key={entry.flag}>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={on}
                          disabled={!entry.available}
                          onCheckedChange={(checked) => toggle(entry.flag, checked === true)}
                          aria-label={entry.label}
                        />
                        <span className="text-sm">{entry.label}</span>
                        <span className="ml-auto flex-shrink-0">
                          {isUserSet && (
                            <Badge
                              variant="outline"
                              className="text-[var(--ds-accent)] border-[var(--ds-accent)]"
                            >
                              Set
                            </Badge>
                          )}
                          {isPreset && (
                            <Badge variant="secondary">Preset: {vertical.label}</Badge>
                          )}
                        </span>
                      </div>

                      {!entry.available && (
                        <p className="text-xs text-[var(--ds-medium)] mt-0.5 pl-11">
                          {entry.label} — unavailable: {entry.reason}
                          {entry.install_hint && <>. {entry.install_hint}</>}
                        </p>
                      )}

                      {entry.available && on && isAmbientAuth && (
                        <p className="text-xs text-[var(--ds-medium)] mt-1 pl-11">
                          {entry.label} uses environment or instance credentials — no field
                          needed here.
                        </p>
                      )}

                      {entry.available && on && !isAmbientAuth && credentialFields.length > 0 && (
                        <div className="pl-11 mt-2 space-y-2">
                          {credentialFields.map((field) => (
                            <div key={field.key}>
                              <Label htmlFor={`cred-${field.key}`} className="text-xs">
                                {field.label}
                              </Label>
                              <Input
                                id={`cred-${field.key}`}
                                type={field.secret === false ? "text" : "password"}
                                placeholder={field.secret === false ? "" : "••••••••"}
                                value={credentials[field.key] ?? ""}
                                onChange={(e) => setCredential(field.key, e.target.value)}
                                className="mt-1"
                              />
                              <p className="text-xs text-[var(--ds-medium)] mt-1">
                                Not saved — cleared after this scan. Re-enter on every
                                submission.
                              </p>
                            </div>
                          ))}
                          {allCredentialsBlank && (
                            <p className="text-xs mt-1" style={{ color: "var(--ds-high)" }}>
                              {entry.label} is enabled with no credentials supplied. The scan
                              will run and record a missing-credentials skip for this connector
                              if it can&apos;t authenticate. Submit anyway, or add credentials
                              above.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </Card>
      </CollapsibleContent>
    </Collapsible>
  )
}

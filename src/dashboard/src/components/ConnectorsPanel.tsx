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
import type {
  ConnectorAvailabilityEntry, ConnectorAvailabilityResponse, ConnectorOverlayValue,
} from "@/types/api"

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

// Phase 197 Plan 02 (PARITY-05/PARITY-06, D-05..D-08): the 37 residual
// connectors.* target/endpoint/identifier/timeout detail fields (999.104
// Tier 2), keyed by the enable_* flag that gates their visibility (D-06).
// Mirrors quirk/dashboard/api/schemas.py::_CONNECTOR_DETAIL_KEY_TYPES field
// set exactly — see 197-01-SUMMARY.md for the authoritative backend list.
interface DetailFieldSpec {
  key: string
  label: string
  kind: "list" | "text" | "number" | "boolean" | "pairlist"
  placeholder?: string
  helper?: string
  // pairlist only — which second half of the `name@X` pair this field
  // parses to (GKE: location, AKS: resource_group).
  pairKey?: "location" | "resource_group"
}

const LIST_HELPER = "Comma or newline-separated. Leave blank to skip."
const TARGETS_PLACEHOLDER = "api.example.com, auth.example.com"

const CONNECTOR_DETAIL_FIELDS: Record<string, DetailFieldSpec[]> = {
  enable_kerberos: [
    { key: "kerberos_targets", label: "Kerberos Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
  ],
  enable_saml: [
    { key: "saml_targets", label: "SAML Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
  ],
  enable_dnssec: [
    { key: "dnssec_targets", label: "DNSSEC Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
    { key: "dnssec_resolver", label: "DNSSEC Resolver", kind: "text" },
  ],
  enable_smime: [
    { key: "smime_targets", label: "S/MIME Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
    { key: "smime_search_base", label: "S/MIME Search Base", kind: "text" },
    { key: "smime_timeout", label: "S/MIME Timeout (seconds)", kind: "number" },
  ],
  enable_adcs: [
    { key: "adcs_targets", label: "AD CS Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
    { key: "adcs_search_base", label: "AD CS Search Base", kind: "text" },
    { key: "adcs_user", label: "AD CS Username", kind: "text" },
    { key: "adcs_timeout", label: "AD CS Timeout (seconds)", kind: "number" },
  ],
  enable_aws: [
    { key: "aws_region", label: "AWS Region", kind: "text" },
    { key: "aws_profile", label: "AWS Profile", kind: "text" },
  ],
  enable_s3: [
    { key: "aws_endpoint_url", label: "AWS S3/MinIO Endpoint URL", kind: "text" },
  ],
  enable_azure: [
    { key: "azure_subscription_id", label: "Azure Subscription ID", kind: "text" },
  ],
  enable_blob: [
    { key: "azure_keyvault_urls", label: "Azure Key Vault URLs", kind: "list", placeholder: "https://vault.example.com/v1/kv", helper: LIST_HELPER },
  ],
  enable_gcp: [
    { key: "gcp_project_id", label: "GCP Project ID", kind: "text" },
  ],
  // D-06 / RESEARCH Pitfall 3: enable_k8s is the SINGLE flag gating all 7
  // k8s fields — there is no separate enable_gke/enable_aks flag
  // (quirk/config.py:321, confirmed live in plan 01).
  enable_k8s: [
    { key: "k8s_provider", label: "K8s Provider", kind: "text" },
    { key: "k8s_cluster_name", label: "K8s Cluster Name", kind: "text" },
    { key: "k8s_namespace", label: "K8s Namespace", kind: "text" },
    {
      key: "k8s_kubeconfig",
      label: "K8s Kubeconfig Path",
      kind: "text",
      helper: "Path to a kubeconfig file readable by the QU.I.R.K. server process. Not a file upload — enter the server-side path.",
    },
    { key: "k8s_context", label: "K8s Context", kind: "text" },
    {
      key: "gke_clusters",
      label: "GKE Clusters",
      kind: "pairlist",
      pairKey: "location",
      placeholder: "prod-cluster-1@us-east1, prod-cluster-2@europe-west1",
      helper: "Comma or newline-separated name@location pairs. Leave blank to skip.",
    },
    {
      key: "aks_clusters",
      label: "AKS Clusters",
      kind: "pairlist",
      pairKey: "resource_group",
      placeholder: "prod-aks@rg-prod",
      helper: "Comma or newline-separated name@resource-group pairs. Leave blank to skip.",
    },
  ],
  enable_vault: [
    { key: "vault_addr", label: "Vault Address", kind: "text" },
    { key: "vault_transit_mount", label: "Vault Transit Mount", kind: "text" },
    { key: "vault_tls_verify", label: "Verify Vault TLS certificate", kind: "boolean" },
  ],
  enable_db: [
    { key: "pg_targets", label: "PostgreSQL Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
    { key: "pg_scanner_user", label: "PostgreSQL Username", kind: "text" },
    { key: "mysql_targets", label: "MySQL Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
    { key: "mysql_scanner_user", label: "MySQL Username", kind: "text" },
  ],
  enable_broker: [
    { key: "broker_targets", label: "Additional Broker Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
    { key: "broker_azure_namespaces", label: "Broker Azure Namespaces", kind: "list", placeholder: "prod-eastus, prod-westus", helper: LIST_HELPER },
    { key: "broker_sqs_regions", label: "Broker SQS Regions", kind: "list", placeholder: "us-east-1, us-west-2", helper: LIST_HELPER },
  ],
  enable_jwt: [
    { key: "jwt_targets", label: "JWT Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
  ],
  enable_container: [
    { key: "container_targets", label: "Container Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
  ],
  enable_source: [
    { key: "source_targets", label: "Source Targets", kind: "list", placeholder: TARGETS_PLACEHOLDER, helper: LIST_HELPER },
  ],
}

// D-07: comma/newline-separated free text parsed to a string array — plain
// text, never a chip/tag input.
function parseTargetList(raw: string): string[] {
  return raw
    .split(/[,\n]/)
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
}

// Pairlist entries are written `name@location` (GKE) / `name@resource_group`
// (AKS) — an entry missing "@" is a client-side blocked entry (the backend
// 422s it too per plan 01); it is dropped from the parsed array (so a
// half-typed entry never silently reaches the submit payload) but flagged
// via the returned `invalidCount` so the caller can render a visible notice
// instead of pretending nothing happened.
function parsePairList(
  raw: string,
  pairKey: "location" | "resource_group",
): { refs: { name: string; location?: string; resource_group?: string }[]; invalidCount: number } {
  const entries = raw.split(/[,\n]/).map((e) => e.trim()).filter((e) => e.length > 0)
  const refs: { name: string; location?: string; resource_group?: string }[] = []
  let invalidCount = 0
  for (const entry of entries) {
    const atIdx = entry.indexOf("@")
    if (atIdx <= 0 || atIdx === entry.length - 1) {
      invalidCount += 1
      continue
    }
    const name = entry.slice(0, atIdx).trim()
    const value = entry.slice(atIdx + 1).trim()
    refs.push({ name, [pairKey]: value })
  }
  return { refs, invalidCount }
}

// D-08: undefined/blank-string/empty-array are blank and DELETE the key.
// `false` and `0` are real values and must NEVER be treated as blank — this
// is a deliberate non-truthiness predicate (the bug vault_tls_verify would
// otherwise hit).
function isBlankDetailValue(value: unknown): boolean {
  if (value === undefined) return true
  if (typeof value === "string") return value.trim().length === 0
  if (Array.isArray(value)) return value.length === 0
  return false
}

interface ConnectorsPanelProps {
  // Phase 197 Plan 02 (PARITY-05/PARITY-06): widened from
  // Record<string, boolean> to also carry the 37 connector detail fields
  // (D-05..D-08). `presetState` intentionally stays boolean-only below —
  // see the comment on that field.
  connectors: Record<string, ConnectorOverlayValue>
  onConnectorsChange: (next: Record<string, ConnectorOverlayValue>) => void
  credentials: Record<string, string>
  onCredentialsChange: (next: Record<string, string>) => void
  // Presets only ever set enable_* boolean toggles — locked by Phase 197
  // Plan 01's `test_a1_no_preset_writes_any_detail_field` against
  // quirk/engine/profiles.py — so no detail field ever carries a "Preset"
  // badge. Stays Record<string, boolean> | null; do not widen this one.
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
    // enable_* toggle flags are always boolean-valued in the overlay — the
    // widened ConnectorOverlayValue union only applies to detail fields.
    if (flag in connectors) return connectors[flag] === true
    return presetState?.[flag] ?? false
  }

  function toggle(flag: string, nextValue: boolean) {
    // D-13: delta-only — only the flag the operator touched enters the map.
    onConnectorsChange({ ...connectors, [flag]: nextValue })
  }

  function setCredential(key: string, value: string) {
    onCredentialsChange({ ...credentials, [key]: value })
  }

  // Phase 197 Plan 02 (D-08): the submitted delta stores list/pairlist
  // fields as parsed arrays, not raw text — this local state preserves the
  // operator's exact keystrokes (including in-progress trailing commas or
  // newlines) between renders without affecting what is submitted.
  const [detailRawText, setDetailRawText] = useState<Record<string, string>>({})
  const [pairlistInvalidCount, setPairlistInvalidCount] = useState<Record<string, number>>({})

  function setDetailField(key: string, value: ConnectorOverlayValue | undefined) {
    if (isBlankDetailValue(value)) {
      const next = { ...connectors }
      delete next[key]
      onConnectorsChange(next)
      return
    }
    onConnectorsChange({ ...connectors, [key]: value as ConnectorOverlayValue })
  }

  function listFieldRawValue(field: DetailFieldSpec): string {
    if (field.key in detailRawText) return detailRawText[field.key]
    const existing = connectors[field.key]
    if (!Array.isArray(existing)) return ""
    if (field.kind === "pairlist") {
      return (existing as { name: string; location?: string; resource_group?: string }[])
        .map((ref) => `${ref.name}@${(field.pairKey ? ref[field.pairKey] : undefined) ?? ""}`)
        .join(", ")
    }
    return (existing as string[]).join(", ")
  }

  function handleListChange(field: DetailFieldSpec, raw: string) {
    setDetailRawText((prev) => ({ ...prev, [field.key]: raw }))
    if (field.kind === "pairlist" && field.pairKey) {
      const { refs, invalidCount } = parsePairList(raw, field.pairKey)
      setPairlistInvalidCount((prev) => ({ ...prev, [field.key]: invalidCount }))
      setDetailField(field.key, refs.length > 0 ? refs : undefined)
      return
    }
    const parsed = parseTargetList(raw)
    setDetailField(field.key, parsed.length > 0 ? parsed : undefined)
  }

  function isDetailFieldSet(key: string): boolean {
    return key in connectors
  }

  // Not a component (lowercase, invoked as a plain function call via {}) —
  // avoids the react-hooks/static-components lint rule that flags a
  // component defined inside another component's render body (194-05).
  function renderDetailSetBadge(key: string) {
    if (!isDetailFieldSet(key)) return null
    return (
      <Badge variant="outline" className="text-[var(--ds-accent)] border-[var(--ds-accent)] ml-2">
        Set
      </Badge>
    )
  }

  function renderDetailField(field: DetailFieldSpec) {
    const inputId = `detail-${field.key}`
    if (field.kind === "list" || field.kind === "pairlist") {
      const invalidCount = pairlistInvalidCount[field.key] ?? 0
      return (
        <div key={field.key}>
          <Label htmlFor={inputId} className="text-xs flex items-center">
            {field.label}
            {renderDetailSetBadge(field.key)}
          </Label>
          {field.helper && (
            <p className="text-xs text-[var(--ds-medium)] mt-1">{field.helper}</p>
          )}
          <textarea
            id={inputId}
            rows={2}
            value={listFieldRawValue(field)}
            onChange={(e) => handleListChange(field, e.target.value)}
            placeholder={field.placeholder}
            className={[
              "flex w-full rounded-md border border-input bg-transparent px-3 py-2 mt-1",
              "text-sm font-mono shadow-sm placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
              "disabled:cursor-not-allowed disabled:opacity-50 resize-none",
            ].join(" ")}
          />
          {invalidCount > 0 && (
            <p className="text-xs mt-1" style={{ color: "var(--ds-high)" }}>
              {invalidCount === 1 ? "One entry is" : `${invalidCount} entries are`} missing the
              required <code>name@{field.pairKey === "resource_group" ? "resource-group" : "location"}</code> format
              and will not be submitted. Fix or remove {invalidCount === 1 ? "it" : "them"} above.
            </p>
          )}
        </div>
      )
    }
    if (field.kind === "number") {
      const raw = connectors[field.key]
      return (
        <div key={field.key}>
          <Label htmlFor={inputId} className="text-xs flex items-center">
            {field.label}
            {renderDetailSetBadge(field.key)}
          </Label>
          <Input
            id={inputId}
            type="number"
            min={1}
            max={300}
            value={typeof raw === "number" ? raw : ""}
            onChange={(e) => setDetailField(
              field.key,
              e.target.value === "" ? undefined : Number(e.target.value),
            )}
            className="mt-1"
          />
        </div>
      )
    }
    if (field.kind === "boolean") {
      // Pitfall 6: vault_tls_verify defaults to True in ConnectorsCfg —
      // absent-from-state must render CHECKED, never unchecked-by-default.
      const checked = connectors[field.key] === undefined ? true : connectors[field.key] === true
      return (
        <div key={field.key} className="flex items-center gap-2">
          <Switch
            id={inputId}
            checked={checked}
            onCheckedChange={(next) => setDetailField(field.key, next === true)}
            aria-label={field.label}
          />
          <span className="text-sm">{field.label}</span>
          {renderDetailSetBadge(field.key)}
        </div>
      )
    }
    // text
    const raw = connectors[field.key]
    return (
      <div key={field.key}>
        <Label htmlFor={inputId} className="text-xs flex items-center">
          {field.label}
          {renderDetailSetBadge(field.key)}
        </Label>
        {field.helper && (
          <p className="text-xs text-[var(--ds-medium)] mt-1">{field.helper}</p>
        )}
        <Input
          id={inputId}
          type="text"
          value={typeof raw === "string" ? raw : ""}
          onChange={(e) => setDetailField(field.key, e.target.value === "" ? undefined : e.target.value)}
          className="mt-1"
        />
      </div>
    )
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
                  // Phase 197 Plan 02: detail fields are NOT gated on
                  // !isAmbientAuth — enable_aws/azure/gcp/s3/blob are
                  // ambient-auth for credentials only, and still have
                  // detail fields (UI-SPEC "Placement within a connector's
                  // row"), so the ambient-auth note and detail block
                  // coexist.
                  const detailFields = CONNECTOR_DETAIL_FIELDS[entry.flag] ?? []
                  const listFields = detailFields.filter((f) => f.kind === "list" || f.kind === "pairlist")
                  const allTargetListsBlank =
                    listFields.length > 0 &&
                    listFields.every((f) => {
                      const v = connectors[f.key]
                      return !(Array.isArray(v) && v.length > 0)
                    })

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
                                // Phase 193 review WR-04 / D-12: keep the browser
                                // itself from becoming the persistence layer.
                                // "new-password" is the most reliably honored
                                // save/autofill suppressor; the data-* attributes
                                // opt out of 1Password/LastPass extensions.
                                autoComplete={field.secret === false ? "off" : "new-password"}
                                data-1p-ignore
                                data-lpignore="true"
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

                      {entry.available && on && detailFields.length > 0 && (
                        <div className="pl-11 mt-2 space-y-2">
                          {detailFields.map((field) => renderDetailField(field))}
                          {allTargetListsBlank && (
                            <p className="text-xs mt-1" style={{ color: "var(--ds-high)" }}>
                              {entry.label} is enabled but has no targets configured. The scan
                              will run but this connector&apos;s list is empty, so it has nothing
                              to check. Add targets above, or submit anyway.
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

import { useEffect, useState } from "react"
import { fetchApi } from "@/lib/api"
import type { ConnectorOverlayValue, InternalTargetCheckResponse } from "@/types/api"

/**
 * Phase 235.3 (D-11 / COVTRUTH-05): non-blocking pre-submit warning when a
 * connector URL will be refused by the server's internal-target policy. Calls
 * GET /api/config/internal-target-check (debounced, cancelled on
 * change/unmount) whenever the URL-bearing connector fields change,
 * independent of the Effective config panel. C-WR-01: plain scan targets are
 * TLS / SSH, which the policy never refuses, so they are not sent. Warning only: the policy is
 * server-side config (security.allow_internal_targets) and there is no toggle
 * here (deferred, 999.121). A failed fetch renders nothing and never blocks.
 */

const DEBOUNCE_MS = 500
// C-WR-03: the connector URL lists the server policy gates. openapi_spec_path
// is a ScanCfg field the form cannot set (the overlay rejects it with a 422),
// so it is never sent.
const CHECKED_KEYS = ["jwt_targets", "saml_targets"] as const
const FIELD_LABELS: Record<string, string> = { jwt_targets: "JWT", saml_targets: "SAML" }

/** Connector names derived from the entries the server actually returned. */
function connectorNames(fields: string[]): string {
  const names = [...new Set(fields.map((f) => FIELD_LABELS[f] ?? f))]
  return names.join(" and ")
}

interface InternalTargetWarningProps {
  connectors?: Record<string, ConnectorOverlayValue>
}

function buildQuery(props: InternalTargetWarningProps): string {
  const params = new URLSearchParams()
  const picked: Record<string, ConnectorOverlayValue> = {}
  for (const key of CHECKED_KEYS) {
    const v = props.connectors?.[key]
    if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) continue
    picked[key] = v
  }
  if (Object.keys(picked).length > 0) params.set("connectors", JSON.stringify(picked))
  return params.toString()
}

export function InternalTargetWarning(props: InternalTargetWarningProps) {
  // Result is keyed by the query it answers, so a stale answer (form edited
  // since) or an empty form renders nothing without a synchronous reset.
  const [answer, setAnswer] = useState<{
    query: string
    result: InternalTargetCheckResponse | null
  } | null>(null)
  const query = buildQuery(props)

  useEffect(() => {
    if (!query) return
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const resp = await fetchApi(`/api/config/internal-target-check?${query}`)
        if (!resp.ok) {
          if (!cancelled) setAnswer({ query, result: null })
          return
        }
        const json: InternalTargetCheckResponse = await resp.json()
        if (!cancelled) setAnswer({ query, result: json })
      } catch {
        if (!cancelled) setAnswer({ query, result: null })
      }
    }, DEBOUNCE_MS)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query])

  const result = query && answer?.query === query ? answer.result : null
  if (!result) return null
  const internal = Array.isArray(result.internal) ? result.internal : []
  const configError = typeof result.config_error === "string" && result.config_error !== ""
  if (!configError && (result.allow_internal_targets || internal.length === 0)) return null

  return (
    <div
      role="status"
      className="rounded-md border px-4 py-3 text-sm"
      style={{
        backgroundColor: "hsl(var(--ds-high-dim, 30 80% 50% / 0.10))",
        borderColor: "hsl(var(--ds-high-bdr, 30 80% 50% / 0.30))",
        color: "hsl(var(--ds-high, 30 80% 50%))",
      }}
    >
      {configError ? (
        <p className="font-semibold">
          Server policy could not be read, so internal JWT and SAML URLs may be skipped.
        </p>
      ) : (
        <>
          <p className="font-semibold">
            Server policy refuses internal URLs, so these {connectorNames(internal.map((item) => item.field))} targets will not be scanned:
          </p>
          <ul className="text-xs mt-1 list-disc pl-5">
            {internal.map((item, i) => (
              <li key={`${item.field}-${i}`}>
                {item.preview} ({item.field}, {item.reason})
              </li>
            ))}
          </ul>
          {result.truncated && <p className="text-xs mt-1">and more not listed</p>}
          <p className="text-xs mt-1">
            Set security.allow_internal_targets: true in the server&apos;s config.yaml to scan them.
            That is server policy and cannot be changed from this form. TLS and SSH scanning is not affected.
          </p>
        </>
      )}
    </div>
  )
}

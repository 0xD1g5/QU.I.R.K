import { useState, useEffect } from "react"
import type { HardwareDriftResponse } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseHardwareDriftResult {
  data: HardwareDriftResponse | null
  loading: boolean
  error: string | null
}

// Phase 156 HWLC-10 — fetches GET /api/hardware/drift, following the
// useScanData fetch idiom (cancelled flag, synchronous pre-await state
// resets, hoisted url, per-status error copy).
export function useHardwareDrift(): UseHardwareDriftResult {
  const [data, setData] = useState<HardwareDriftResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    setData(null)
    setLoading(true)
    setError(null)

    const url = "/api/hardware/drift"

    async function fetchData() {
      try {
        const resp = await fetchApi(url)
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) {
              setError("Authentication required")
              return
            }
            if (resp.status === 403) {
              setError("Request blocked")
              return
            }
            if (resp.status === 429) {
              const retryAfter = resp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            if (resp.status === 404) {
              setError("Could not load lifecycle changes. The dashboard server may be unreachable — try refreshing.")
            } else {
              setError("Could not load lifecycle changes. The dashboard server may be unreachable — try refreshing.")
            }
          }
          return
        }
        const json: HardwareDriftResponse = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch {
        if (!cancelled) {
          setError("Could not load lifecycle changes. The dashboard server may be unreachable — try refreshing.")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [])

  return { data, loading, error }
}

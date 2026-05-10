import { useState, useEffect } from "react"
import type { ScanLatestResponse } from "@/types/api"
import { useSelectedScan } from "@/hooks/useSelectedScan"
import { fetchApi } from "@/lib/api"

interface UseScanDataResult {
  data: ScanLatestResponse | null
  loading: boolean
  error: string | null
}

export function useScanData(): UseScanDataResult {
  const { selectedScanId } = useSelectedScan()
  const [data, setData] = useState<ScanLatestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    // BR-04 (D-02): clear stale data synchronously before initiating new fetch.
    // These setters run BEFORE any await so no !cancelled guard is needed.
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const url = selectedScanId
          ? `/api/scan/latest?scan_id=${encodeURIComponent(selectedScanId)}`
          : "/api/scan/latest"
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
              setError("No scan data available. Run a scan first: quirk scan <target>")
            } else {
              setError(`API error: ${resp.status} ${resp.statusText}`)
            }
          }
          return
        }
        const json: ScanLatestResponse = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load scan data")
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
  }, [selectedScanId])

  return { data, loading, error }
}

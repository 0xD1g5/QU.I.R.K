import { useState, useEffect } from "react"
import type { ScanLatestResponse } from "@/types/api"
import { useSelectedScan } from "@/hooks/useSelectedScan"

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

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const url = selectedScanId
          ? `/api/scan/latest?scan_id=${encodeURIComponent(selectedScanId)}`
          : "/api/scan/latest"
        const resp = await fetch(url)
        if (!resp.ok) {
          if (resp.status === 404) {
            setError("No scan data available. Run a scan first: quirk scan <target>")
          } else {
            setError(`API error: ${resp.status} ${resp.statusText}`)
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

import { useState, useEffect } from "react"
import type { SensorRegistryItem } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseSensorRegistryResult {
  sensors: SensorRegistryItem[]
  loading: boolean
  error: string | null
}

export function useSensorRegistry(): UseSensorRegistryResult {
  const [sensors, setSensors] = useState<SensorRegistryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    // Clear stale data synchronously before initiating new fetch.
    setSensors([])
    setLoading(true)
    setError(null)

    const url = "/api/sensor/registry"

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
            if (resp.status === 404) {
              // Route not registered or prefix mismatch — treat as clean empty
              // state with an actionable hint, consistent with useScanData 404
              // pattern (WR-05).
              setSensors([])
              setError("Sensor registry endpoint not found. Check dashboard routing configuration.")
              return
            }
            setError(`Failed to fetch ${url}: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json = await resp.json()
        if (!cancelled) {
          setSensors(json.sensors ?? [])
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            `Failed to fetch ${url}: ${err instanceof Error ? err.message : String(err)}`,
          )
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

  return { sensors, loading, error }
}

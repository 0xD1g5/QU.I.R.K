import { useState, useEffect, useCallback } from "react"
import type { FindingStoryline } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface FindingStorylineTarget {
  id: number | null
  title: string
}

interface UseFindingStorylineResult {
  data: FindingStoryline | null
  loading: boolean
  error: string | null
  retry: () => void
}

// Phase 202-02 / STORY-01 / D-02, D-06, D-07 — lazy per-finding storyline
// fetch. Mirrors useHardwareDrift's idiom (cancelled flag, synchronous
// pre-await state resets, finally { setLoading(false) }), with three
// deliberate differences:
//
//   - The fetch key is the (endpoint id, title) PAIR, not id alone —
//     FindingItem.id is CryptoEndpoint.id and is shared across every
//     finding derived from the same endpoint (D-06). Effect deps are
//     therefore keyed on both finding?.id AND finding?.title.
//   - A finding with a null id (or no finding selected at all) issues NO
//     request — this is the A6 disabled-trigger guard, not a fetch that
//     is expected to fail.
//   - Error is a single fixed operator-facing string for every failure
//     cause (D-07, UI-SPEC Copywriting Contract) and is representationally
//     distinct from absence: a failed fetch NEVER leaves data as a
//     null-filled FindingStoryline — data stays null and error is set.
//     (A 401 is not special-cased here: the whole dashboard is auth-gated
//     and the app's auth layer already handles the unauthenticated case
//     globally via fetchApi's _onUnauthorized hook.)
export function useFindingStoryline(
  finding: FindingStorylineTarget | null,
): UseFindingStorylineResult {
  const [data, setData] = useState<FindingStoryline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)

  const retry = useCallback(() => {
    setNonce((n) => n + 1)
  }, [])

  useEffect(() => {
    // A6 guard: no finding selected, or the finding has no stable id —
    // issue no request at all. This is a guard, not a fetch that fails.
    if (finding == null || finding.id == null) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }

    const { id, title } = finding
    let cancelled = false

    setData(null)
    setLoading(true)
    setError(null)

    async function fetchStoryline() {
      try {
        const resp = await fetchApi(
          `/api/findings/${id}/storyline?title=${encodeURIComponent(title)}`,
        )
        if (!resp.ok) {
          if (!cancelled) {
            setError("Could not load the storyline for this finding.")
          }
          return
        }
        const json: FindingStoryline = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch {
        if (!cancelled) {
          setError("Could not load the storyline for this finding.")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchStoryline()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finding?.id, finding?.title, nonce])

  return { data, loading, error, retry }
}

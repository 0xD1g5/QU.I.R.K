/**
 * VerticalProvider — mirrors AuthProvider pattern.
 *
 * Provider component only. VerticalContext + useVertical hook live in
 * ./vertical-context so this file exports a single component (keeps
 * react-refresh / Fast Refresh happy).
 *
 * On mount, fetches GET /api/config (an unauth route) to determine the active vertical.
 *
 * Defaults to "general" while loading and on any fetch failure, so the dashboard
 * is always in a valid state and general installs see no healthcare UI.
 */
import { useEffect, useState } from "react"
import type { ReactNode } from "react"
import { getVertical } from "@/lib/verticals"
import type { VerticalDescriptor } from "@/lib/verticals"
import { VerticalContext } from "@/context/vertical-context"

export function VerticalProvider({ children }: { children: ReactNode }) {
  const [descriptor, setDescriptor] = useState<VerticalDescriptor>(
    getVertical("general"),
  )

  useEffect(() => {
    fetch("/api/config")
      .then((res) => res.json())
      .then((data: { vertical?: string }) => {
        setDescriptor(getVertical(data.vertical ?? "general"))
      })
      .catch(() => {
        // Network error or parse failure — stay on general
        setDescriptor(getVertical("general"))
      })
  }, [])

  return (
    <VerticalContext.Provider value={descriptor}>
      {children}
    </VerticalContext.Provider>
  )
}

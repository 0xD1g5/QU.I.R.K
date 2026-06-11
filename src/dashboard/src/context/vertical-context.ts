/**
 * Vertical context + hook — quick task 260611-g0b.
 *
 * Split out from VerticalProvider.tsx so that VerticalProvider.tsx only
 * exports a React component. This keeps the
 * `react-refresh/only-export-components` lint rule (and Fast Refresh) happy:
 * contexts and hooks live here, the provider component lives there.
 * Mirrors the AuthContext / auth-context.ts split.
 */

import { createContext, useContext } from "react"
import { getVertical } from "@/lib/verticals"
import type { VerticalDescriptor } from "@/lib/verticals"

export const VerticalContext = createContext<VerticalDescriptor>(
  getVertical("general"),
)

export function useVertical(): VerticalDescriptor {
  return useContext(VerticalContext)
}

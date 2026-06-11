/**
 * Vertical descriptor registry.
 *
 * Each entry in VERTICALS describes one "edition" of the dashboard.
 * Adding a new vertical requires only:
 *   1. A new entry in VERTICALS below.
 *   2. A page component (HealthcarePage pattern).
 * No scattered conditionals needed — all UI reads from the active descriptor.
 */
import type { ComponentType } from "react"
import type { LucideIcon } from "lucide-react"
import { Shield } from "lucide-react"
import { HeartPulse } from "lucide-react"
import { HealthcarePage } from "@/pages/healthcare"

export interface VerticalDescriptor {
  id: string
  label: string
  Icon: LucideIcon
  accentColor: string
  /** Nav item to inject into Sidebar, or null if not needed. */
  navItem: { path: string; label: string } | null
  /** Scan preset to surface in scan-new.tsx, or null if not needed. */
  preset: {
    targets: string
    profile: string
    calibration: string
    description: string
  } | null
  /** Page component for the vertical-specific route, or null if not needed. */
  PageComponent: ComponentType | null
}

export const VERTICALS: Record<string, VerticalDescriptor> = {
  general: {
    id: "general",
    label: "General",
    Icon: Shield,
    accentColor: "hsl(var(--accent))",
    navItem: null,
    preset: null,
    PageComponent: null,
  },
  healthcare: {
    id: "healthcare",
    label: "Healthcare Edition",
    Icon: HeartPulse,
    accentColor: "#4ba8a8",
    navItem: {
      path: "/healthcare",
      label: "Healthcare Posture",
    },
    preset: {
      targets:
        "ehr.hospital.internal, pacs.hospital.internal, portal.hospital.internal, pharmacy.hospital.internal",
      profile: "standard",
      calibration: "strict",
      description: "Standard depth, strict calibration, EHR / PACS / portal targets",
    },
    PageComponent: HealthcarePage,
  },
}

/**
 * Resolve a vertical id to its descriptor.
 * Falls back to VERTICALS.general for any unknown id.
 */
export function getVertical(id: string): VerticalDescriptor {
  return VERTICALS[id] ?? VERTICALS.general
}

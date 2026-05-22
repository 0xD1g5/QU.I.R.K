import { createContext } from "react"

// D-05 (WR-04): allowlist of accepted theme values. localStorage can be
// tampered with or carry stale values from older app builds; cast the raw
// string through this allowlist so non-canonical values silently fall back
// to defaultTheme. Theme is QoL, not security — no console.warn.
export const VALID_THEMES = ["light", "dark", "system"] as const
export type Theme = typeof VALID_THEMES[number]

export function getStoredTheme(storageKey: string, defaultTheme: Theme): Theme {
  const raw = typeof window === "undefined" ? null : localStorage.getItem(storageKey)
  return (VALID_THEMES as readonly string[]).includes(raw ?? "")
    ? (raw as Theme)
    : defaultTheme
}

export type ThemeProviderState = {
  theme: Theme
  setTheme: (theme: Theme) => void
}

export const ThemeProviderContext = createContext<ThemeProviderState>({
  theme: "system",
  setTheme: () => null,
})

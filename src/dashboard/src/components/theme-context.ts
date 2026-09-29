import { createContext } from "react"

// D-05 (WR-04): allowlist of accepted theme values. localStorage can be
// tampered with or carry stale values from older app builds; cast the raw
// string through this allowlist so non-canonical values silently fall back
// to defaultTheme. Theme is QoL, not security — no console.warn.
export const VALID_THEMES = ["light", "dark", "system"] as const
export type Theme = typeof VALID_THEMES[number]

// 216 D-01: the a11y harness (tests/a11y/run-a11y.mjs) seeds this exact localStorage key
// before navigation to exercise the real theme-provider path instead of forcing a class.
// A change here silently breaks the light sweep unless run-a11y.mjs's own literal copy and
// tests/a11y/theme-sweep-contract.test.ts (which fails if the two ever drift) move with it.
export const THEME_STORAGE_KEY = "quirk-ui-theme"

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

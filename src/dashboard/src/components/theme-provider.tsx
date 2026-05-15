import { useEffect, useState } from "react"
import { ThemeProviderContext, type ThemeProviderState } from "./theme-context"

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

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

export function ThemeProvider({
  children,
  defaultTheme = "dark",
  storageKey = "quirk-ui-theme",
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme(storageKey, defaultTheme))

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove("light", "dark")
    if (theme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      root.classList.add(systemTheme)
    } else {
      root.classList.add(theme)
    }
  }, [theme])

  // BR-06 (D-07): wire MediaQueryList listener so OS dark/light toggle is reflected
  // while the app is running. Listener is only active when theme === "system".
  useEffect(() => {
    if (theme !== "system") return
    const mql = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = (e: MediaQueryListEvent) => {
      const root = window.document.documentElement
      root.classList.remove("light", "dark")
      root.classList.add(e.matches ? "dark" : "light")
    }
    mql.addEventListener("change", handler)
    return () => mql.removeEventListener("change", handler)
  }, [theme])

  const value: ThemeProviderState = {
    theme,
    setTheme: (t: Theme) => {
      localStorage.setItem(storageKey, t)
      setTheme(t)
    },
  }

  return (
    <ThemeProviderContext.Provider value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

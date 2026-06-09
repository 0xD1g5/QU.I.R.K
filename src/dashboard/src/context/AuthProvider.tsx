/**
 * AuthProvider — Phase 102 / AUTH-03.
 *
 * Provider component only. AuthContext + useAuth hook live in ./auth-context
 * so this file exports a single component (keeps react-refresh / Fast Refresh happy).
 *
 * On mount, probes GET /api/scans (a protected route) with the stored localStorage
 * token as X-API-Key:
 *   - 200 → status = "authenticated"  (covers auth-disabled passthrough: no token + 200)
 *   - 401 → clear stale token from localStorage, status = "unauthenticated"
 *
 * Registers logout as the lib/api setUnauthorizedHandler on mount so any fetchApi
 * 401 (while a token is present) automatically bounces the user back to the login form.
 * Unregisters on unmount to prevent stale callbacks.
 *
 * NOTE: The probe uses raw fetch() — NOT fetchApi() — to avoid triggering the
 * _onUnauthorized callback registered in the second useEffect.  Both useEffect
 * callbacks fire synchronously after the first render (before any async response
 * arrives), so the handler IS registered before the probe 401 response arrives.
 * Correctness is safe regardless of ordering because the probe bypasses fetchApi
 * entirely and therefore never invokes _onUnauthorized.
 * (setUnauthorizedHandler IS imported for the handler registration, not for the probe.)
 */

import { useCallback, useEffect, useState } from "react"
import type { ReactNode } from "react"
import { setUnauthorizedHandler } from "@/lib/api"
import { AuthContext } from "@/context/auth-context"
import type { AuthStatus } from "@/context/auth-context"

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading")

  // setToken: write localStorage + set status to authenticated
  const setToken = useCallback((token: string) => {
    try {
      localStorage.setItem("quirk_api_token", token)
    } catch {
      // localStorage unavailable — still transition state in memory
    }
    setStatus("authenticated")
  }, [])

  // logout: clear localStorage + set status to unauthenticated
  const logout = useCallback(() => {
    try {
      localStorage.removeItem("quirk_api_token")
    } catch {
      // ignore
    }
    setStatus("unauthenticated")
  }, [])

  // Mount probe: determine initial auth status by hitting a protected route.
  // Uses raw fetch() (not fetchApi) to avoid ordering issues with handler registration.
  // Target: /api/scans (protected) — NOT /api/health (auth-exempt, always 200).
  useEffect(() => {
    const storedToken = (() => {
      try {
        return localStorage.getItem("quirk_api_token") ?? ""
      } catch {
        return ""
      }
    })()

    const headers: Record<string, string> = {
      "X-Quirk-Request": "1",
    }
    if (storedToken) {
      headers["X-API-Key"] = storedToken
    }

    fetch("/api/scans", { headers })
      .then((res) => {
        if (res.status === 401) {
          // Stale/invalid token — clear it
          try {
            localStorage.removeItem("quirk_api_token")
          } catch {
            // ignore
          }
          setStatus("unauthenticated")
        } else {
          // 200 (with valid token) OR 200 (auth disabled, no token) — both authenticated
          setStatus("authenticated")
        }
      })
      .catch(() => {
        // Network error — treat as unauthenticated to avoid stuck loading state
        setStatus("unauthenticated")
      })
  }, [])

  // Register logout as the mid-session 401 handler.
  // logout is useCallback-stable so this effect does not thrash.
  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => {
      setUnauthorizedHandler(null)
    }
  }, [logout])

  return (
    <AuthContext.Provider value={{ status, setToken, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

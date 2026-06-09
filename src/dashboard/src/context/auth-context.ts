/**
 * Auth context + hook — Phase 102 / AUTH-03.
 *
 * Split out from AuthProvider.tsx so that AuthProvider.tsx only exports a
 * React component. This keeps the `react-refresh/only-export-components`
 * lint rule (and Fast Refresh) happy: contexts, hooks, and types live here,
 * the provider component lives there.
 */

import { createContext, useContext } from "react"

export type AuthStatus = "loading" | "authenticated" | "unauthenticated"

export interface AuthState {
  status: AuthStatus
  setToken: (token: string) => void
  logout: () => void
}

export const AuthContext = createContext<AuthState>({
  status: "loading",
  setToken: () => {},
  logout: () => {},
})

export function useAuth(): AuthState {
  return useContext(AuthContext)
}

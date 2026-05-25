/**
 * Shared fetch wrapper — Phase 58 / HARDEN-API-01 / D-08.
 * Updated Phase 102 / AUTH-03: localStorage token source + X-API-Key header + 401 handler.
 *
 * Single enforcement point for:
 *   - X-Quirk-Request: 1 (CSRF header — injected on every call)
 *   - Content-Type: application/json (injected on mutating calls if not set)
 *   - X-API-Key: {token} (injected when token is configured — AUTH-03)
 *
 * All components MUST call fetchApi() instead of fetch() directly.
 * The token is resolved from localStorage.getItem("quirk_api_token") at call time.
 * fetchApi() does NOT accept a token parameter — prevents token scatter (D-08).
 */

declare global {
  interface Window {
    __QUIRK_CONFIG__?: Record<string, unknown>
  }
}

const CSRF_HEADER = "X-Quirk-Request"
const _MUTATING_METHODS = new Set(["POST", "PUT", "DELETE", "PATCH"])

/**
 * Resolve API token from localStorage.
 * Falls back to "" in SSR/test environments where localStorage is unavailable.
 */
function _resolveToken(): string {
  try {
    return localStorage.getItem("quirk_api_token") ?? ""
  } catch {
    return ""
  }
}

/**
 * Module-level registration for a 401 callback.
 * AuthProvider registers logout() here on mount and unregisters on unmount.
 * This avoids importing AuthContext into api.ts (no circular dependency).
 */
let _onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  _onUnauthorized = fn
}

/**
 * Fetch wrapper that injects CSRF and auth headers on every API call.
 *
 * @param path - API path (e.g. "/api/qramm/sessions")
 * @param options - Standard RequestInit options (method, body, headers, etc.)
 * @returns Promise<Response> — same as native fetch()
 */
export async function fetchApi(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const method = ((options.method ?? "GET") as string).toUpperCase()
  const isMutating = _MUTATING_METHODS.has(method)

  const existingHeaders: Record<string, string> =
    options.headers instanceof Headers
      ? Object.fromEntries(options.headers.entries())
      : (options.headers as Record<string, string>) ?? {}

  const headers: Record<string, string> = { ...existingHeaders }

  // CSRF header — always set (D-07, UI-SPEC header table)
  headers[CSRF_HEADER] = "1"

  // Content-Type — set on mutating calls if not already provided
  if (isMutating && !headers["Content-Type"] && !headers["content-type"]) {
    headers["Content-Type"] = "application/json"
  }

  // X-API-Key — set when token is configured (AUTH-03: localStorage source)
  const token = _resolveToken()
  if (token) {
    headers["X-API-Key"] = token
  }

  const response = await fetch(path, { ...options, headers })

  // Mid-session 401 handling: only fire when a token was sent (preserves auth-disabled passthrough)
  if (response.status === 401 && token && _onUnauthorized) {
    _onUnauthorized()
  }

  return response
}

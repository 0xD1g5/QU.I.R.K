/**
 * Shared fetch wrapper — Phase 58 / HARDEN-API-01 / D-08.
 *
 * Single enforcement point for:
 *   - X-Quirk-Request: 1 (CSRF header — injected on every call)
 *   - Content-Type: application/json (injected on mutating calls if not set)
 *   - Authorization: Bearer {token} (injected when token is configured)
 *
 * All components MUST call fetchApi() instead of fetch() directly.
 * The token is resolved from window.__QUIRK_CONFIG__.apiToken at call time.
 * fetchApi() does NOT accept a token parameter — prevents token scatter (D-08).
 */

declare global {
  interface Window {
    __QUIRK_CONFIG__?: {
      apiToken?: string
    }
  }
}

const CSRF_HEADER = "X-Quirk-Request"
const _MUTATING_METHODS = new Set(["POST", "PUT", "DELETE", "PATCH"])

/**
 * Resolve API token from runtime config.
 * Priority: window.__QUIRK_CONFIG__.apiToken -> "" (auth disabled).
 */
function _resolveToken(): string {
  try {
    return window.__QUIRK_CONFIG__?.apiToken ?? ""
  } catch {
    return ""
  }
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
  options: RequestInit = {}
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

  // Authorization — set when token is configured
  const token = _resolveToken()
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  return fetch(path, { ...options, headers })
}

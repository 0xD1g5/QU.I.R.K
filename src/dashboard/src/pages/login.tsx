/**
 * LoginPage — Phase 102 / AUTH-03.
 *
 * Rendered when AuthContext status === "unauthenticated".
 * Probes GET /api/scans with the entered token as X-API-Key:
 *   - 200 → calls useAuth().setToken(token) → transitions to authenticated
 *   - 401 → shows inline error, clears input, refocuses
 *
 * Design contract: 102-UI-SPEC.md (LOCKED).
 * Font weights: font-normal (400) and font-semibold (600) only.
 * Accent color: teal (--primary) on submit button only.
 * Error color: --destructive on inline error text only.
 */

import { useRef, useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/context/AuthProvider"

export function LoginPage() {
  const { setToken } = useAuth()
  const [error, setError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()

    const form = e.currentTarget
    const tokenValue = (
      form.elements.namedItem("token-input") as HTMLInputElement
    ).value.trim()

    if (!tokenValue) return

    try {
      const res = await fetch("/api/scans", {
        headers: {
          "X-Quirk-Request": "1",
          "X-API-Key": tokenValue,
        },
      })

      if (res.ok) {
        // Successful authentication — hand off to AuthProvider
        setToken(tokenValue)
      } else {
        // 401 (or other non-OK): token was sent but rejected — clear + refocus
        setError("Invalid token. Check your token and try again.")
        if (inputRef.current) {
          inputRef.current.value = ""
          inputRef.current.focus()
        }
      }
    } catch {
      // Network/fetch error (server down, DNS, CORS) — token may still be valid;
      // preserve the input value so the user can retry without re-typing.
      setError(
        "Could not reach the dashboard server. Check that it is running and try again.",
      )
      if (inputRef.current) {
        inputRef.current.focus()
      }
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader>
          {/* Product wordmark — teal accent, font-semibold (600) */}
          <span className="text-accent font-semibold text-base tracking-widest font-mono">
            QU.I.R.K.
          </span>
          {/* Page heading — text-xl font-semibold (600) */}
          <CardTitle className="text-xl font-semibold mt-2">
            Dashboard Login
          </CardTitle>
          {/* Description — font-normal (400) via CardDescription default */}
          <CardDescription>
            Enter your dashboard token to continue.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form
            aria-label="Dashboard login"
            onSubmit={handleSubmit}
            className="space-y-4"
          >
            <div className="space-y-2">
              {/* Label: font-medium is the shadcn labelVariants default — not overridden */}
              <Label htmlFor="token-input">API Token</Label>
              <Input
                ref={inputRef}
                id="token-input"
                name="token-input"
                type="password"
                autoFocus
                autoComplete="current-password"
                placeholder="Paste your token"
              />
            </div>

            {/* Error slot: always in DOM to avoid layout shift; empty string when no error */}
            <p
              role="alert"
              aria-live="polite"
              className="text-sm font-normal text-destructive"
            >
              {error}
            </p>

            {/* Submit: teal bg-primary via default Button variant */}
            <Button type="submit" className="w-full">
              Unlock Dashboard
            </Button>
          </form>
        </CardContent>

        <CardFooter>
          <p className="text-xs text-muted-foreground">
            Generate a token with:{" "}
            <code className="font-mono">quirk token generate</code>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}

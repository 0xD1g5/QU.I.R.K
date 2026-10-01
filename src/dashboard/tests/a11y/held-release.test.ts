// @vitest-environment node
/**
 * 221 WR-06: behavioural proof that a `loading`-variant held response cannot hang the preview
 * server's shutdown. Replaces a string-containment contract ("held" / "destroy" in vite.config.ts)
 * that stayed green with the release mechanism removed.
 *
 * The real preview server is started through vite's own `preview()` API with this repo's
 * vite.config.ts and the a11y fixture env, a request to a holding endpoint is left open, and
 * `server.close()` must resolve promptly while the client sees its socket end. The mechanism is
 * vite's createServerCloseFn (it destroys every open socket before server.close()); if that ever
 * stops, close() waits for the held socket forever and this node times out red.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest"
import http from "node:http"
import path from "node:path"
import type { AddressInfo } from "node:net"
import { preview, type PreviewServer } from "vite"

const ENV_KEYS = ["VITE_A11Y_FIXTURE", "VITE_A11Y_FIXTURE_VARIANT"] as const
const saved: Record<string, string | undefined> = {}
let server: PreviewServer | undefined

beforeAll(() => {
  for (const k of ENV_KEYS) saved[k] = process.env[k]
  process.env.VITE_A11Y_FIXTURE = "1"
  process.env.VITE_A11Y_FIXTURE_VARIANT = "loading"
})

afterAll(async () => {
  await server?.close().catch(() => {})
  for (const k of ENV_KEYS) {
    if (saved[k] === undefined) delete process.env[k]
    else process.env[k] = saved[k]
  }
})

describe("held loading responses (221 WR-06)", () => {
  it("a held /api/scan/latest request does not delay preview close, and its socket is ended", async () => {
    server = await preview({
      configFile: path.resolve(__dirname, "../../vite.config.ts"),
      logLevel: "silent",
      preview: { host: "127.0.0.1", port: 0, strictPort: false, open: false },
    })
    const port = (server.httpServer.address() as AddressInfo).port
    expect(port).toBeGreaterThan(0)
    // Anti-vacuity: the held request must actually reach THIS server (a refused connection also
    // "gets no response" and "ends", which is how an earlier draft of this node passed vacuously).
    const arrived: string[] = []
    server.httpServer.on("request", (req: http.IncomingMessage) => arrived.push(req.url ?? ""))

    let responded = false
    const ended = new Promise<string>((resolve) => {
      const req = http.get({ host: "127.0.0.1", port, path: "/api/scan/latest" }, (res) => {
        responded = true
        res.resume()
        res.on("close", () => resolve("response-closed"))
      })
      req.on("error", (e) => resolve(`error:${(e as NodeJS.ErrnoException).code ?? e.message}`))
      req.on("close", () => resolve("request-closed"))
    })

    // The request is genuinely held: no response arrives while the server is up.
    await new Promise((r) => setTimeout(r, 400))
    expect(arrived, "the held request never reached the preview server").toContain("/api/scan/latest")
    expect(responded, "loading variant answered a holding endpoint instead of holding it").toBe(false)

    const t0 = Date.now()
    await server.close()
    const closeMs = Date.now() - t0
    server = undefined
    expect(closeMs, `preview close took ${closeMs}ms with a held request open`).toBeLessThan(2_000)

    const outcome = await Promise.race([ended, new Promise<string>((r) => setTimeout(() => r("still-open"), 2_000))])
    expect(outcome, "held client socket was never ended by close").not.toBe("still-open")
    expect(outcome, "the held request failed to connect rather than being held").not.toMatch(/ECONNREFUSED/)
  }, 8_000)
})

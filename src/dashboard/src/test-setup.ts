import "@testing-library/jest-dom/vitest"

// ResizeObserver is used by Radix UI components (RadioGroup, Checkbox, etc.)
// but is not available in jsdom. Provide a no-op stub so component tests
// that render Radix UI controls can run without crashing.
if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(globalThis, "ResizeObserver", {
    value: ResizeObserverStub,
    writable: true,
    configurable: true,
  })
}

// Radix UI's Select (and other pointer-capture-driven primitives) call
// Element.hasPointerCapture()/setPointerCapture()/releasePointerCapture()
// during pointer-down handling; jsdom does not implement the Pointer
// Capture API at all. Without this stub, opening a Select in a jsdom test
// throws `TypeError: target.hasPointerCapture is not a function`
// (confirmed live, 206-01 Task 2 probe against FindingsPage's severity
// Select — see 206-RED-PROOF.md's red-proof/README.md Wave 1 shim verdict).
if (typeof Element !== "undefined" && typeof Element.prototype.hasPointerCapture === "undefined") {
  Object.defineProperty(Element.prototype, "hasPointerCapture", {
    value: () => false,
    writable: true,
    configurable: true,
  })
  Object.defineProperty(Element.prototype, "setPointerCapture", {
    value: () => {},
    writable: true,
    configurable: true,
  })
  Object.defineProperty(Element.prototype, "releasePointerCapture", {
    value: () => {},
    writable: true,
    configurable: true,
  })
}

// Radix UI's Select also calls Element.scrollIntoView() to keep the
// highlighted SelectItem in view once its content is open; jsdom does not
// implement layout, so scrollIntoView is entirely absent. Without this
// stub, opening a Select's content throws
// `TypeError: candidate?.scrollIntoView is not a function` (confirmed
// live, 206-01 Task 2 probe, one step past the hasPointerCapture failure
// above — see red-proof/README.md Wave 1 shim verdict).
if (typeof Element !== "undefined" && typeof Element.prototype.scrollIntoView === "undefined") {
  Object.defineProperty(Element.prototype, "scrollIntoView", {
    value: () => {},
    writable: true,
    configurable: true,
  })
}

// jsdom 25 does not expose `localStorage` on the global by default (it's
// flagged behind --localstorage-file). Provide a minimal in-memory shim so
// tests that exercise localStorage-backed code (theme-provider, regression
// chip dismissal, etc.) can run without per-file boilerplate.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>()
  const shim: Storage = {
    get length() { return store.size },
    clear: () => { store.clear() },
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (key: string) => { store.delete(key) },
    setItem: (key: string, value: string) => { store.set(key, String(value)) },
  }
  Object.defineProperty(globalThis, "localStorage", {
    value: shim,
    writable: true,
    configurable: true,
  })
}

// jsdom 25 does not expose `sessionStorage` on the global by default.
// Provide a minimal in-memory shim so tests that exercise sessionStorage-backed
// code (auth token migration, AUDIT-14) can run without per-file boilerplate.
if (typeof globalThis.sessionStorage === "undefined") {
  const store = new Map<string, string>()
  const shim: Storage = {
    get length() { return store.size },
    clear: () => { store.clear() },
    getItem: (key: string) => (store.has(key) ? store.get(key)! : null),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (key: string) => { store.delete(key) },
    setItem: (key: string, value: string) => { store.set(key, String(value)) },
  }
  Object.defineProperty(globalThis, "sessionStorage", {
    value: shim,
    writable: true,
    configurable: true,
  })
}

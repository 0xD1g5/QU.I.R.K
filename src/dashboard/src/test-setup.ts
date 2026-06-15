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

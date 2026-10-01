import * as React from "react"
import { act, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"
import {
  Table,
  TableBody,
  TableCell,
  TableRow,
} from "@/components/ui/table"

type Dims = {
  scrollWidth: number
  clientWidth: number
  scrollHeight: number
  clientHeight: number
}

function mockDims({ scrollWidth, clientWidth, scrollHeight, clientHeight }: Dims) {
  Object.defineProperty(HTMLDivElement.prototype, "scrollWidth", {
    configurable: true,
    value: scrollWidth,
  })
  Object.defineProperty(HTMLDivElement.prototype, "clientWidth", {
    configurable: true,
    value: clientWidth,
  })
  Object.defineProperty(HTMLDivElement.prototype, "scrollHeight", {
    configurable: true,
    value: scrollHeight,
  })
  Object.defineProperty(HTMLDivElement.prototype, "clientHeight", {
    configurable: true,
    value: clientHeight,
  })
}

function restoreDims() {
  delete (HTMLDivElement.prototype as unknown as Record<string, unknown>).scrollWidth
  delete (HTMLDivElement.prototype as unknown as Record<string, unknown>).clientWidth
  delete (HTMLDivElement.prototype as unknown as Record<string, unknown>).scrollHeight
  delete (HTMLDivElement.prototype as unknown as Record<string, unknown>).clientHeight
}

const NO_OVERFLOW: Dims = {
  scrollWidth: 800,
  clientWidth: 800,
  scrollHeight: 300,
  clientHeight: 300,
}

const OVERFLOW_HORIZONTAL: Dims = {
  scrollWidth: 2000,
  clientWidth: 800,
  scrollHeight: 300,
  clientHeight: 300,
}

const OVERFLOW_VERTICAL: Dims = {
  scrollWidth: 800,
  clientWidth: 800,
  scrollHeight: 900,
  clientHeight: 300,
}

function renderTable(props: { regionLabel?: string; "aria-label"?: string } = {}, rowCount = 1) {
  const rows = Array.from({ length: rowCount }, (_, i) => (
    <TableRow key={i}>
      <TableCell>row {i}</TableCell>
    </TableRow>
  ))
  return render(
    <Table {...props}>
      <TableBody>{rows}</TableBody>
    </Table>
  )
}

describe("Table wrapper conditional keyboard focusability", () => {
  afterEach(() => {
    restoreDims()
  })

  it("adds tabIndex 0, role region and the default name when the wrapper overflows horizontally", () => {
    mockDims(OVERFLOW_HORIZONTAL)
    renderTable()
    const region = screen.getByRole("region", { name: "Scrollable table" })
    expect(region).toHaveAttribute("tabindex", "0")
  })

  it("adds tabIndex 0 and role region when the wrapper overflows vertically", () => {
    mockDims(OVERFLOW_VERTICAL)
    renderTable()
    const region = screen.getByRole("region")
    expect(region).toHaveAttribute("tabindex", "0")
  })

  it("adds no tabindex, role or aria-label when the wrapper does not overflow", () => {
    mockDims(NO_OVERFLOW)
    renderTable()
    expect(screen.queryByRole("region")).toBeNull()
    const table = screen.getByRole("table")
    const wrapper = table.parentElement as HTMLElement
    expect(wrapper.hasAttribute("tabindex")).toBe(false)
    expect(wrapper.hasAttribute("role")).toBe(false)
    expect(wrapper.hasAttribute("aria-label")).toBe(false)
  })

  it("forwards regionLabel as the region's accessible name", () => {
    mockDims(OVERFLOW_HORIZONTAL)
    renderTable({ regionLabel: "Vault encryption findings" })
    const region = screen.getByRole("region", { name: "Vault encryption findings" })
    expect(region).toBeTruthy()
  })

  it.each(["", "   "])("falls back to the default name when regionLabel is blank (%j) — never a nameless region", (blank) => {
    mockDims(OVERFLOW_HORIZONTAL)
    renderTable({ regionLabel: blank })
    expect(screen.getByRole("region", { name: "Scrollable table" })).toBeTruthy()
  })

  it("does not spread regionLabel onto the table element and keeps aria-label on the table", () => {
    mockDims(OVERFLOW_HORIZONTAL)
    renderTable({ regionLabel: "X", "aria-label": "Y" })
    const table = screen.getByRole("table")
    expect(table).toHaveAttribute("aria-label", "Y")
    expect(table.hasAttribute("regionlabel")).toBe(false)
    const wrapper = table.parentElement as HTMLElement
    expect(wrapper).toHaveAttribute("aria-label", "X")
  })

  it("re-measures when children change", () => {
    mockDims(NO_OVERFLOW)
    const { rerender } = renderTable({}, 1)
    expect(screen.queryByRole("region")).toBeNull()

    mockDims(OVERFLOW_HORIZONTAL)
    rerender(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>row 0</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>row 1</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )

    expect(screen.getByRole("region")).toBeTruthy()
  })

  it("re-measures when the ResizeObserver fires", () => {
    mockDims(NO_OVERFLOW)
    let storedCallback: ResizeObserverCallback | null = null
    const OriginalResizeObserver = globalThis.ResizeObserver

    class CapturingResizeObserver {
      constructor(cb: ResizeObserverCallback) {
        storedCallback = cb
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    }

    globalThis.ResizeObserver = CapturingResizeObserver as unknown as typeof ResizeObserver

    try {
      renderTable()
      expect(screen.queryByRole("region")).toBeNull()

      mockDims(OVERFLOW_HORIZONTAL)
      act(() => {
        storedCallback?.([], {} as ResizeObserver)
      })

      expect(screen.getByRole("region")).toBeTruthy()
    } finally {
      globalThis.ResizeObserver = OriginalResizeObserver
    }
  })

  it("carries the ring-2 focus-visible classes and keeps the original wrapper classes", () => {
    mockDims(NO_OVERFLOW)
    renderTable()
    const table = screen.getByRole("table")
    const wrapper = table.parentElement as HTMLElement
    for (const cls of [
      "relative",
      "w-full",
      "overflow-auto",
      "focus-visible:outline-none",
      "focus-visible:ring-2",
      "focus-visible:ring-ring",
    ]) {
      expect(wrapper.className).toContain(cls)
    }
  })

  it("forwards the ref to the table element", () => {
    mockDims(NO_OVERFLOW)
    const ref = React.createRef<HTMLTableElement>()
    render(
      <Table ref={ref}>
        <TableBody>
          <TableRow>
            <TableCell>row 0</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )
    expect(ref.current).toBeInstanceOf(HTMLTableElement)
  })
})

export type FixtureSource =
  | { file: string }
  | { json: unknown }
  | { qrammKey: string; fallback: unknown }

export interface FixtureHandler {
  id: string
  match: { prefix?: string; regex?: string; subpaths?: string; example?: string }
  default: FixtureSource
  empty: { body: unknown } | { emptyFrom: string } | { na: string }
  loading: { hold: true } | { na: string }
  scope?: string
  scopeReason?: string
}

export const FIXTURE_HANDLERS: readonly FixtureHandler[]
export function prefixMatches(match: FixtureHandler["match"], url: string): boolean
export function matchHandler(url: string | undefined): FixtureHandler | undefined
export function compareZeroDiff(fixture: Record<string, unknown>): Record<string, unknown>

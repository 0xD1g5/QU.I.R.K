import { Card, CardContent } from "@/components/ui/card"

// 221 WR-02/WR-13: `emptyFor` is the fixture handler id whose EMPTY response this card proves
// (variant-guard.mjs emptyWitnessSelector). Opt-in per call site, never unconditional: a card
// rendered by an error branch carries no witness, and a card cannot witness an endpoint other
// than the one its caller names. variant-contract.test.ts enforces both at every call site.
export function EmptyStateCard({ message, emptyFor }: { message: string; emptyFor?: string }) {
  return (
    <Card role="status" data-a11y-empty={emptyFor}>
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}

import { Card, CardContent } from "@/components/ui/card"

export function EmptyStateCard({ message }: { message: string }) {
  return (
    // 221 WR-02: positive witness for the a11y `empty` fixture leg (variant-guard.mjs
    // DEFAULT_EMPTY_SELECTOR). Without it, a crashed or not-yet-rendered page also has
    // "every marker absent" and would pass the leg.
    <Card role="status" data-testid="empty-state">
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}

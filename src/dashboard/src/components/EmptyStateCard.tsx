import { Card, CardContent } from "@/components/ui/card"

export function EmptyStateCard({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}

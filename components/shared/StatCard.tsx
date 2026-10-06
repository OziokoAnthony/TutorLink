import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'

/** Summary card: a number with a label, optionally linking somewhere. */
export default function StatCard({ label, value, href }: { label: string; value: number | string | null; href?: string }) {
  const body = (
    <Card className={href ? 'transition-colors hover:border-primary/50 hover:bg-accent/40' : undefined}>
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-3xl font-bold tabular-nums">{value ?? '–'}</p>
      </CardContent>
    </Card>
  )
  return href ? <Link href={href} className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{body}</Link> : body
}

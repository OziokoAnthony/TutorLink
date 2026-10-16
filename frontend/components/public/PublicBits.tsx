import Link from 'next/link'
import { Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatNaira } from '@/lib/format'
import type { PublicReview } from '@/types'

/** Spec 14 R4.2: what parents pay per lesson, TutorLink's fee included; "Prices vary" under 3 offers. */
export function priceText(min: number | null, max: number | null): string {
  if (min === null || max === null) return 'Prices vary'
  return min === max ? `${formatNaira(min)} per lesson` : `${formatNaira(min)} to ${formatNaira(max)} per lesson`
}

export function tutorsText(n: number): string {
  return n === 1 ? '1 verified tutor' : `${n} verified tutors`
}

export function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex text-amber-500" aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} className={`h-4 w-4 ${i < rating ? 'fill-current' : 'opacity-30'}`} aria-hidden />
      ))}
    </span>
  )
}

/** R3.1: the parent's first name, the stars and the comment. */
export function ReviewList({ reviews }: { reviews: PublicReview[] }) {
  if (reviews.length === 0) return null
  return (
    <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {reviews.map((r, i) => (
        <li key={i} className="rounded-lg border bg-card p-5">
          <Stars rating={r.rating} />
          <p className="mt-3 text-sm">&ldquo;{r.comment}&rdquo;</p>
          <p className="mt-3 text-sm font-medium">{r.first_name}, a TutorLink parent</p>
        </li>
      ))}
    </ul>
  )
}

/** R4.3: visitors sign up to see and book tutors, or to post a request. */
export function SignUpButtons() {
  return (
    <div className="flex flex-wrap gap-3">
      <Button asChild size="lg"><Link href="/register">Sign up to see tutors</Link></Button>
      <Button asChild size="lg" variant="outline"><Link href="/register">Post a request</Link></Button>
    </div>
  )
}

/** The three steps, as on the home page (R4.3). */
export function Steps() {
  const steps = [
    ['Sign up free', 'Create a parent account in a minute, with your email or Google.'],
    ['Choose a tutor', 'See verified tutors, their prices, times and parents’ reviews, or post a request.'],
    ['Pay and start', 'Pay into your own TutorLink account number before lessons; report a problem and we can refund it.'],
  ]
  return (
    <ol className="grid gap-4 md:grid-cols-3">
      {steps.map(([title, text], i) => (
        <li key={title} className="rounded-lg border bg-card p-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">{i + 1}</span>
          <h3 className="mt-3 font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{text}</p>
        </li>
      ))}
    </ol>
  )
}

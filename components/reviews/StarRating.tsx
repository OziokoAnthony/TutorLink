'use client'

import { Star } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Read-only stars, e.g. ★★★★☆ for 4.2. */
export function Stars({ value, className }: { value: number; className?: string }) {
  return (
    <span className={cn('inline-flex', className)} aria-hidden>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} className={cn('h-4 w-4', n <= Math.round(value) ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground/40')} />
      ))}
    </span>
  )
}

/** "★ 4.5 (12 ratings)", or "New tutor" when unrated. */
export function RatingSummary({ average, count, className }: { average: number | null; count: number; className?: string }) {
  if (average === null || count === 0) {
    return <span className={cn('text-sm text-muted-foreground', className)}>New tutor, no ratings yet</span>
  }
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-sm', className)}>
      <Stars value={average} />
      <span className="font-semibold">{average.toFixed(1)}</span>
      <span className="text-muted-foreground">({count} {count === 1 ? 'rating' : 'ratings'})</span>
    </span>
  )
}

/** Clickable 1–5 star input (keyboard: radio group). */
export function StarInput({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  return (
    <div role="radiogroup" aria-label="Rating" className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} star${n > 1 ? 's' : ''}`}
          onClick={() => onChange(n)}
          className="rounded p-1 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Star className={cn('h-8 w-8', n <= value ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground/40')} />
        </button>
      ))}
    </div>
  )
}

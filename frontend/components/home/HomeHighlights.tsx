'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ReviewList, Stars } from '@/components/public/PublicBits'
import { publicReviews, publicStats } from '@/lib/public'
import type { PublicReview, PublicStats } from '@/types'

/** Spec 14 R2, R3: real numbers and parents' reviews on the home page, loaded after the page shows. */
export default function HomeHighlights() {
  const [stats, setStats] = useState<PublicStats | null>(null)
  const [reviews, setReviews] = useState<PublicReview[]>([])
  useEffect(() => {
    publicStats().then(setStats).catch(() => {})
    publicReviews().then(setReviews).catch(() => {})
  }, [])

  return (
    <section className="mx-auto max-w-5xl space-y-10 px-4 pb-16">
      {stats && stats.verified_tutors > 0 && (
        <dl className="grid gap-4 rounded-lg border bg-card p-6 text-center sm:grid-cols-3">
          <div><dt className="text-sm text-muted-foreground">Verified tutors</dt><dd className="text-3xl font-bold">{stats.verified_tutors.toLocaleString()}</dd></div>
          <div><dt className="text-sm text-muted-foreground">Lessons taught</dt><dd className="text-3xl font-bold">{stats.lessons_taught.toLocaleString()}</dd></div>
          <div>
            <dt className="text-sm text-muted-foreground">Parents&apos; rating</dt>
            <dd className="text-3xl font-bold">
              {stats.average_rating ?? '–'}
              {stats.average_rating !== null && <span className="ml-2 align-middle"><Stars rating={Math.round(stats.average_rating)} /></span>}
            </dd>
            {stats.rating_count > 0 && <dd className="text-xs text-muted-foreground">from {stats.rating_count.toLocaleString()} ratings</dd>}
          </div>
        </dl>
      )}
      {reviews.length > 0 && (
        <div>
          <h2 className="mb-4 text-center text-2xl font-bold tracking-tight">What parents say</h2>
          <ReviewList reviews={reviews} />
        </div>
      )}
      <div className="text-center">
        <Button asChild variant="outline"><Link href="/subjects">Browse tutors by subject and see prices</Link></Button>
      </div>
    </section>
  )
}

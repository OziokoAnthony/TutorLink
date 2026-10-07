'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import AvailabilityView from '@/components/tutors/AvailabilityView'
import BookingForm from '@/components/tutors/BookingForm'
import Avatar from '@/components/shared/Avatar'
import ReviewList from '@/components/reviews/ReviewList'
import { RatingSummary } from '@/components/reviews/StarRating'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage, errorStatus } from '@/lib/api'
import { formatNaira, levelLabel, slotText } from '@/lib/format'
import { getReviews } from '@/lib/reviews'
import { getAvailability, getTutor } from '@/lib/tutors'
import type { Review, TutorAvailability, TutorProfile } from '@/types'

export default function TutorProfilePage({ params }: { params: { id: string } }) {
  const { user } = useAuth()
  const [tutor, setTutor] = useState<TutorProfile | null>(null)
  const [reviews, setReviews] = useState<Review[]>([])
  const [availability, setAvailability] = useState<TutorAvailability | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [bookingOpen, setBookingOpen] = useState(false)

  useEffect(() => {
    Promise.all([getTutor(params.id), getReviews(params.id), getAvailability(params.id)])
      .then(([t, r, a]) => { setTutor(t); setReviews(r); setAvailability(a) })
      .catch((e) => setError(errorStatus(e) === 404 ? 'This tutor is not available.' : errorMessage(e)))
  }, [params.id])

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <EmptyState message={error} action={<Button variant="outline" asChild><Link href="/tutors">Browse tutors</Link></Button>} />
      </div>
    )
  }
  if (!tutor) return <LoadingSpinner />

  const isParent = user?.role === 'parent'

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <Link href="/tutors" className="text-sm text-muted-foreground hover:text-foreground">← All tutors</Link>

      <Card>
        <CardContent className="flex flex-col gap-6 pt-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-4">
            <Avatar name={tutor.full_name} photoUrl={tutor.photo_url} size="lg" />
            <div className="space-y-2">
              <h1 className="text-2xl font-bold tracking-tight">{tutor.full_name}</h1>
              <p className="flex items-center gap-1 text-muted-foreground"><MapPin className="h-4 w-4" aria-hidden />{tutor.area}</p>
              <RatingSummary average={tutor.average_rating} count={tutor.rating_count} />
            </div>
          </div>
          <div className="space-y-3 sm:text-right">
            {tutor.price_from !== null && (
              <p><span className="text-muted-foreground">From </span><span className="text-2xl font-bold">{formatNaira(tutor.price_from)}</span> <span className="text-muted-foreground">per lesson</span></p>
            )}
            {isParent && <Button size="lg" onClick={() => setBookingOpen(true)} disabled={tutor.offers.length === 0}>Book this tutor</Button>}
            {!user && (
              <p className="text-sm text-muted-foreground">
                <Link href="/login" className="font-medium text-primary hover:underline">Log in as a parent</Link> to book.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader><CardTitle className="text-lg">About</CardTitle></CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm text-muted-foreground">{tutor.bio || 'This tutor has not added a bio yet.'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-lg">When they&apos;re free</CardTitle></CardHeader>
          <CardContent>
            {availability ? <AvailabilityView availability={availability} /> : <p className="text-sm text-muted-foreground">Loading…</p>}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">What they teach</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {tutor.offers.length === 0 && <p className="text-sm text-muted-foreground">Nothing listed yet.</p>}
          {tutor.offers.map((o) => (
            <div key={o.id} className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1.5">
                <div className="flex flex-wrap gap-1.5">
                  {o.subjects.map((s) => <Badge key={s} variant="secondary">{s}</Badge>)}
                  <Badge variant="outline">{levelLabel(o.level)}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">{o.windows.map(slotText).join(' • ')}</p>
              </div>
              <p className="shrink-0 font-semibold">{formatNaira(o.price)} <span className="text-sm font-normal text-muted-foreground">per lesson</span></p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">Reviews from parents</CardTitle></CardHeader>
        <CardContent><ReviewList reviews={reviews} /></CardContent>
      </Card>

      {isParent && bookingOpen && <BookingForm tutor={tutor} availability={availability} open={bookingOpen} onOpenChange={setBookingOpen} />}
    </div>
  )
}

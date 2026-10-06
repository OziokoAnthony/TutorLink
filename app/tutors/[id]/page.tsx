'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import BookingForm from '@/components/tutors/BookingForm'
import { TutorAvatar } from '@/components/tutors/TutorCard'
import ReviewList from '@/components/reviews/ReviewList'
import { RatingSummary } from '@/components/reviews/StarRating'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage, errorStatus } from '@/lib/api'
import { formatNaira, levelLabel } from '@/lib/format'
import { getReviews } from '@/lib/reviews'
import { getTutor } from '@/lib/tutors'
import type { Review, TutorProfile } from '@/types'

export default function TutorProfilePage({ params }: { params: { id: string } }) {
  const { user } = useAuth()
  const [tutor, setTutor] = useState<TutorProfile | null>(null)
  const [reviews, setReviews] = useState<Review[]>([])
  const [error, setError] = useState<string | null>(null)
  const [bookingOpen, setBookingOpen] = useState(false)

  useEffect(() => {
    Promise.all([getTutor(params.id), getReviews(params.id)])
      .then(([t, r]) => { setTutor(t); setReviews(r) })
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
            <TutorAvatar name={tutor.full_name} size="lg" />
            <div className="space-y-2">
              <h1 className="text-2xl font-bold tracking-tight">{tutor.full_name}</h1>
              <p className="flex items-center gap-1 text-muted-foreground"><MapPin className="h-4 w-4" aria-hidden />{tutor.area}</p>
              <RatingSummary average={tutor.average_rating} count={tutor.rating_count} />
            </div>
          </div>
          <div className="space-y-3 sm:text-right">
            <p><span className="text-2xl font-bold">{formatNaira(tutor.rate_per_session)}</span> <span className="text-muted-foreground">per session</span></p>
            {isParent && <Button size="lg" onClick={() => setBookingOpen(true)} disabled={tutor.subjects.length === 0}>Book a Session</Button>}
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
          <CardHeader><CardTitle className="text-lg">Subjects</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-1.5">
            {tutor.subjects.length === 0
              ? <p className="text-sm text-muted-foreground">No subjects listed yet.</p>
              : tutor.subjects.map((s) => <Badge key={s.id} variant="secondary">{s.subject} • {levelLabel(s.level)}</Badge>)}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">Reviews from parents</CardTitle></CardHeader>
        <CardContent><ReviewList reviews={reviews} /></CardContent>
      </Card>

      {isParent && <BookingForm tutor={tutor} open={bookingOpen} onOpenChange={setBookingOpen} />}
    </div>
  )
}

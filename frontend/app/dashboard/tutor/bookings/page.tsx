'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import BookingCard from '@/components/bookings/BookingCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { acceptBooking, declineBooking, endBooking, getTutorBookings } from '@/lib/bookings'
import { formatDateTime } from '@/lib/format'
import type { Booking } from '@/types'

const ANSWER_WITHIN_MS = 72 * 60 * 60 * 1000

export default function TutorBookingsPage() {
  const toast = useToast()
  const [bookings, setBookings] = useState<Booking[] | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [action, setAction] = useState<{ booking: Booking; kind: 'decline' | 'end' } | null>(null)

  const load = useCallback(() => {
    getTutorBookings().then(setBookings).catch((e) => { toast.error(errorMessage(e)); setBookings([]) })
  }, [toast])
  useEffect(load, [load])

  async function accept(booking: Booking) {
    setBusyId(booking.id)
    try {
      await acceptBooking(booking.id)
      toast.success('Accepted! The parent has been asked to pay before the first lesson.')
      load()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusyId(null)
    }
  }

  async function confirm(note: string) {
    if (!action) return
    try {
      if (action.kind === 'decline') await declineBooking(action.booking.id, note)
      else await endBooking(action.booking.id, note)
      toast.success(action.kind === 'decline' ? 'Request declined' : "The booking won't renew")
      load()
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  if (!bookings) return <LoadingSpinner />
  const requests = bookings.filter((b) => b.status === 'requested')
  const current = bookings.filter((b) => ['accepted', 'active', 'paused'].includes(b.status))
  const past = bookings.filter((b) => !requests.includes(b) && !current.includes(b))

  return (
    <>
      <PageHeader title="Bookings" description="Answer requests within 72 hours. Once you accept, the parent pays before the first lesson." />

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Requests</h2>
      {requests.length === 0 ? <EmptyState message="No requests waiting." /> : (
        <div className="space-y-4">
          {requests.map((b) => (
            <BookingCard key={b.id} booking={b} viewer="tutor" actions={(
              <>
                <Button size="sm" onClick={() => accept(b)} disabled={busyId === b.id}>{busyId === b.id ? 'Accepting…' : 'Accept'}</Button>
                <Button size="sm" variant="outline" onClick={() => setAction({ booking: b, kind: 'decline' })}>Decline</Button>
                <span className="self-center text-xs text-muted-foreground">
                  Answer by {formatDateTime(new Date(new Date(b.created_at).getTime() + ANSWER_WITHIN_MS).toISOString())}
                </span>
              </>
            )} />
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Current</h2>
      {current.length === 0 ? <EmptyState message="No current bookings." /> : (
        <div className="space-y-4">
          {current.map((b) => (
            <BookingCard key={b.id} booking={b} viewer="tutor" actions={
              <Button size="sm" variant="outline" onClick={() => setAction({ booking: b, kind: 'end' })}>Stop renewing</Button>
            } />
          ))}
        </div>
      )}

      {past.length > 0 && (
        <details className="mt-8">
          <summary className="cursor-pointer text-sm font-medium text-muted-foreground">Past ({past.length})</summary>
          <div className="mt-4 space-y-4">{past.map((b) => <BookingCard key={b.id} booking={b} viewer="tutor" />)}</div>
        </details>
      )}

      <NoteDialog
        open={!!action}
        onOpenChange={(o) => !o && setAction(null)}
        title={action?.kind === 'decline' ? 'Decline this request?' : 'Stop this booking renewing?'}
        description={action?.kind === 'decline'
          ? 'The parent will be told you can’t take it.'
          : 'No new lessons will be added. Lessons already paid for still go ahead.'}
        confirmLabel={action?.kind === 'decline' ? 'Decline' : 'Stop renewing'}
        onConfirm={confirm}
      />
    </>
  )
}

'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import BookingCard from '@/components/bookings/BookingCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { cancelBooking, endBooking, getMyBookings } from '@/lib/bookings'
import type { Booking } from '@/types'

const OPEN = ['requested', 'accepted', 'active', 'paused']

export default function ParentBookingsPage() {
  const toast = useToast()
  const [bookings, setBookings] = useState<Booking[] | null>(null)
  const [action, setAction] = useState<{ booking: Booking; kind: 'cancel' | 'end' } | null>(null)

  const load = useCallback(() => {
    getMyBookings().then(setBookings).catch((e) => { toast.error(errorMessage(e)); setBookings([]) })
  }, [toast])
  useEffect(load, [load])

  async function confirm(note: string) {
    if (!action) return
    try {
      if (action.kind === 'cancel') {
        await cancelBooking(action.booking.id, note)
        toast.success('Booking cancelled. Lessons at least 48 hours away will be refunded once approved.')
      } else {
        await endBooking(action.booking.id, note)
        toast.success("The booking won't renew. Lessons already paid for still go ahead.")
      }
      load()
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  if (!bookings) return <LoadingSpinner />
  const open = bookings.filter((b) => OPEN.includes(b.status))
  const closed = bookings.filter((b) => !OPEN.includes(b.status))

  return (
    <>
      <PageHeader title="My bookings" description="Requests, active bookings and their payments."
        action={<Button asChild><Link href="/tutors">Book a tutor</Link></Button>} />
      {bookings.length === 0 && <EmptyState message="You haven't booked a tutor yet." action={<Button asChild><Link href="/tutors">Find a tutor</Link></Button>} />}
      <div className="space-y-4">
        {open.map((b) => (
          <BookingCard key={b.id} booking={b} viewer="parent" actions={(
            <>
              {b.status === 'accepted' && <Button asChild size="sm"><Link href="/dashboard/parent/wallet">Pay now</Link></Button>}
              {b.status !== 'requested' && <Button size="sm" variant="outline" onClick={() => setAction({ booking: b, kind: 'end' })}>Stop renewing</Button>}
              <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setAction({ booking: b, kind: 'cancel' })}>
                {b.status === 'requested' ? 'Withdraw request' : 'Cancel booking'}
              </Button>
            </>
          )} />
        ))}
      </div>
      {closed.length > 0 && (
        <details className="mt-8">
          <summary className="cursor-pointer text-sm font-medium text-muted-foreground">Past bookings ({closed.length})</summary>
          <div className="mt-4 space-y-4">{closed.map((b) => <BookingCard key={b.id} booking={b} viewer="parent" />)}</div>
        </details>
      )}

      <NoteDialog
        open={!!action}
        onOpenChange={(o) => !o && setAction(null)}
        title={action?.kind === 'end' ? 'Stop this booking renewing?' : 'Cancel this booking?'}
        description={action?.kind === 'end'
          ? "No new lessons will be added. Lessons you've already paid for still go ahead."
          : 'Paid lessons at least 48 hours away are cancelled and their agreed price (without the service fee) goes back to your TutorLink balance once TutorLink approves it. Lessons sooner than that still go ahead.'}
        confirmLabel={action?.kind === 'end' ? 'Stop renewing' : 'Cancel booking'}
        destructive={action?.kind === 'cancel'}
        onConfirm={confirm}
      />
    </>
  )
}

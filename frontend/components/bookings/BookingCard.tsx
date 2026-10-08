import type { ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import MeetingLinkEditor from '@/components/bookings/MeetingLinkEditor'
import Avatar from '@/components/shared/Avatar'
import { BookingStatusBadge, PeriodStatusBadge } from '@/components/shared/StatusBadge'
import { BILLING_PERIODS, formatDate, formatDateTime, formatNaira, formatPercent, levelLabel, slotText } from '@/lib/format'
import type { Booking } from '@/types'

/** A booking as the parent, tutor or admin sees it. Each reader only receives their own money fields. */
export default function BookingCard({ booking, viewer, actions, onChange }: {
  booking: Booking
  viewer: 'parent' | 'tutor' | 'admin'
  actions?: ReactNode
  onChange?: (booking: Booking) => void
}) {
  const live = ['accepted', 'active', 'paused'].includes(booking.status)
  const other = viewer === 'parent'
    ? { name: booking.tutor_name, photo: booking.tutor_photo_url, role: 'Tutor' }
    : { name: booking.parent_name, photo: booking.parent_photo_url, role: 'Parent' }
  const billing = BILLING_PERIODS.find((b) => b.value === booking.billing_period)?.label

  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <Avatar name={other.name} photoUrl={other.photo} />
            <div>
              <p className="font-semibold">{other.name ?? other.role}</p>
              <p className="text-sm text-muted-foreground">
                {booking.subjects.join(', ')} • {levelLabel(booking.level)} • {booking.mode === 'online' ? 'Online' : 'At home'}
              </p>
            </div>
          </div>
          <BookingStatusBadge status={booking.status} />
        </div>

        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <p className="text-muted-foreground">Every week</p>
            <p>{booking.slots.map(slotText).join('; ')}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Dates</p>
            <p>From {formatDate(booking.start_date)}{booking.end_date ? ` to ${formatDate(booking.end_date)}` : ''} • paid {billing?.toLowerCase()}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Price per lesson</p>
            {viewer === 'parent' && <p><span className="font-semibold">{formatNaira(booking.parent_price_per_lesson ?? booking.price)}</span> <span className="text-muted-foreground">(agreed {formatNaira(booking.price)} + service fee)</span></p>}
            {viewer === 'tutor' && (
              <p>
                Agreed {formatNaira(booking.price)} − TutorLink fee {formatPercent(booking.tutor_fee_rate ?? 0)} ={' '}
                <span className="font-semibold">{formatNaira(booking.tutor_earning_per_lesson ?? 0)}</span> to you
              </p>
            )}
            {viewer === 'admin' && (
              <p>
                Agreed {formatNaira(booking.price)} • parent pays {formatNaira(booking.parent_price_per_lesson ?? 0)} ({formatPercent(booking.parent_fee_rate ?? 0)})
                {' '}• tutor gets {formatNaira(booking.tutor_earning_per_lesson ?? 0)} ({formatPercent(booking.tutor_fee_rate ?? 0)})
                {' '}• TutorLink keeps <span className="font-semibold">{formatNaira(booking.platform_margin_per_lesson ?? 0)}</span>
              </p>
            )}
          </div>
          {booking.close_note && (
            <div>
              <p className="text-muted-foreground">Note</p>
              <p>{booking.close_note}</p>
            </div>
          )}
        </div>

        {booking.mode === 'online' && live && (
          <div className="rounded-md border p-3 text-sm">
            <p className="font-medium">Online lessons</p>
            {viewer === 'tutor' && onChange ? <MeetingLinkEditor booking={booking} onChange={onChange} />
              : booking.meeting_link
                ? <a href={booking.meeting_link} target="_blank" rel="noopener noreferrer" className="break-all font-medium text-primary underline">Join the lesson: {booking.meeting_link}</a>
                : <p className="text-muted-foreground">{viewer === 'parent'
                  ? "The tutor's meeting link appears here once the first lessons are paid for."
                  : 'No meeting link yet.'}</p>}
            <p className="mt-1 text-xs text-muted-foreground">Lessons are recorded and kept for review.</p>
          </div>
        )}

        {booking.mode === 'offline' && live && viewer !== 'parent' && (
          <div className="rounded-md border p-3 text-sm">
            <p className="font-medium">Lesson address</p>
            <p className="text-muted-foreground">{booking.parent_address
              ?? (booking.status === 'accepted' ? "The parent's address appears here once the first lessons are paid for."
                : "The parent hasn't added an address. Ask them through TutorLink support.")}</p>
          </div>
        )}

        {viewer !== 'parent' && (
          <div className="grid gap-3 rounded-md bg-muted/50 p-3 text-sm sm:grid-cols-2">
            <div><p className="font-medium">Child&apos;s strengths</p><p className="text-muted-foreground">{booking.child_strengths}</p></div>
            <div><p className="font-medium">What the child finds hard</p><p className="text-muted-foreground">{booking.child_weaknesses}</p></div>
          </div>
        )}

        {booking.periods && booking.periods.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Payments</p>
            {booking.periods.map((p) => (
              <div key={p.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                <span>{formatDate(p.starts_on)} – {formatDate(p.ends_on)} • {p.lesson_count} lesson(s)</span>
                <span className="flex items-center gap-2">
                  <span className="font-semibold">{formatNaira(p.amount)}</span>
                  {p.status === 'due' && <Badge variant="outline">Pay before {formatDateTime(p.due_at)}</Badge>}
                  <PeriodStatusBadge status={p.status} />
                </span>
              </div>
            ))}
          </div>
        )}

        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </CardContent>
    </Card>
  )
}

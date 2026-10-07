'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import PageHeader from '@/components/shared/PageHeader'
import StatCard from '@/components/shared/StatCard'
import { useAuth } from '@/hooks/useAuth'
import { getTutorBookings } from '@/lib/bookings'
import { formatDateTime, formatNaira } from '@/lib/format'
import { getTutorLessons } from '@/lib/lessons'
import { getEarnings } from '@/lib/payouts'
import type { Booking, EarningsSummary, Lesson, TutorProfile } from '@/types'

export default function TutorOverviewPage() {
  const { user } = useAuth()
  const profile = user?.profile as TutorProfile | null
  const [bookings, setBookings] = useState<Booking[] | null>(null)
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [earnings, setEarnings] = useState<EarningsSummary | null>(null)

  useEffect(() => {
    getTutorBookings().then(setBookings).catch(() => setBookings([]))
    getTutorLessons().then(setLessons).catch(() => setLessons([]))
    getEarnings().then(setEarnings).catch(() => undefined)
  }, [])

  const now = new Date()
  const requests = bookings?.filter((b) => b.status === 'requested').length ?? null
  const toReport = lessons?.filter((l) => l.status === 'confirmed' && new Date(l.ends_at) <= now).length ?? null
  const next = (lessons ?? []).filter((l) => l.status === 'confirmed' && new Date(l.starts_at) > now)
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at)).slice(0, 5)

  return (
    <>
      <PageHeader title={profile ? `Welcome, ${profile.full_name.split(' ')[0]}` : 'Dashboard'} />

      {profile?.vetting_status === 'pending' && (
        <p role="status" className="mb-6 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          Your profile is under review. You&apos;ll be notified once you&apos;re approved.
        </p>
      )}
      {profile?.vetting_status === 'rejected' && (
        <p role="status" className="mb-6 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-950">
          Your application was not approved.{profile.vetting_note ? ` ${profile.vetting_note}` : ''}
        </p>
      )}
      {user && !user.photo_url && (
        <p className="mb-6 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          Add a profile picture so parents can see who they&apos;re booking. <Link href="/dashboard/tutor/profile" className="font-medium underline">Add it on your profile</Link>.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Requests to answer" value={requests} href="/dashboard/tutor/bookings" />
        <StatCard label="Lessons to report" value={toReport} href="/dashboard/tutor/lessons" />
        <StatCard label="To be paid" value={earnings ? formatNaira(earnings.payable) : null} href="/dashboard/tutor/earnings" />
        <StatCard label="Paid to you" value={earnings ? formatNaira(earnings.paid) : null} href="/dashboard/tutor/earnings" />
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-lg">Next lessons</CardTitle></CardHeader>
        <CardContent>
          {next.length === 0 ? <p className="text-sm text-muted-foreground">No paid lessons coming up.</p> : (
            <ul className="space-y-2 text-sm">
              {next.map((l) => (
                <li key={l.id} className="flex justify-between gap-3">
                  <span>{formatDateTime(l.starts_at)} • {l.subjects.join(', ')}{l.mode === 'online' ? ' • Online' : ''}</span>
                  <span className="text-muted-foreground">{l.parent_name}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="mt-8 flex flex-wrap gap-2">
        <Button asChild><Link href="/dashboard/tutor/bookings">Booking requests</Link></Button>
        <Button variant="outline" asChild><Link href="/dashboard/tutor/lessons">Report lessons</Link></Button>
        <Button variant="outline" asChild><Link href="/dashboard/tutor/profile">Profile &amp; what I teach</Link></Button>
      </div>
    </>
  )
}

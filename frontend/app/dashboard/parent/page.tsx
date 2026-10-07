'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import AccountNumberCard from '@/components/payments/AccountNumberCard'
import RateTutorDialog from '@/components/reviews/RateTutorDialog'
import PageHeader from '@/components/shared/PageHeader'
import PhotoUploader from '@/components/shared/PhotoUploader'
import StatCard from '@/components/shared/StatCard'
import { useAuth } from '@/hooks/useAuth'
import { getMyBookings } from '@/lib/bookings'
import { formatDateTime, formatNaira } from '@/lib/format'
import { getMyLessons } from '@/lib/lessons'
import { getWallet } from '@/lib/wallet'
import type { Booking, Lesson, ParentProfile, TutorToRate, Wallet } from '@/types'

export default function ParentOverviewPage() {
  const { user, refresh } = useAuth()
  const [wallet, setWallet] = useState<Wallet | null>(null)
  const [bookings, setBookings] = useState<Booking[] | null>(null)
  const [upcoming, setUpcoming] = useState<Lesson[]>([])
  const [rating, setRating] = useState<TutorToRate | null>(null)

  const load = useCallback(() => {
    getWallet().then(setWallet).catch(() => undefined)
    getMyBookings().then(setBookings).catch(() => setBookings([]))
    getMyLessons('confirmed').then((l) => setUpcoming(l.filter((x) => new Date(x.starts_at) > new Date())
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at)).slice(0, 5))).catch(() => undefined)
  }, [])
  useEffect(load, [load])

  const name = (user?.profile as ParentProfile | null)?.full_name ?? ''
  const toRate = user?.tutors_to_rate ?? []
  const active = bookings?.filter((b) => ['active', 'accepted', 'paused', 'requested'].includes(b.status)).length ?? null

  return (
    <>
      <PageHeader title={name ? `Welcome, ${name.split(' ')[0]}` : 'Dashboard'} description="Here's what needs your attention." />

      {user && !user.photo_url && (
        <Card className="mb-6 border-amber-300 bg-amber-50">
          <CardHeader>
            <CardTitle className="text-lg">Add your profile picture</CardTitle>
            <CardDescription>You need one before booking. Tutors see it on your requests, and you see theirs.</CardDescription>
          </CardHeader>
          <CardContent><PhotoUploader name={name} /></CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="TutorLink balance" value={wallet ? formatNaira(wallet.balance) : null} href="/dashboard/parent/wallet" />
        <StatCard label="To pay" value={wallet ? formatNaira(wallet.amount_due) : null} href="/dashboard/parent/wallet" />
        <StatCard label="Bookings" value={active} href="/dashboard/parent/bookings" />
      </div>

      {wallet && wallet.amount_due > 0 && (
        <div className="mt-6"><AccountNumberCard account={wallet.virtual_account} onCreated={load} /></div>
      )}

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-lg">Next lessons</CardTitle></CardHeader>
        <CardContent>
          {upcoming.length === 0
            ? <p className="text-sm text-muted-foreground">No paid lessons coming up.</p>
            : <ul className="space-y-2 text-sm">
              {upcoming.map((l) => (
                <li key={l.id} className="flex justify-between gap-3">
                  <span>{formatDateTime(l.starts_at)} • {l.subjects.join(', ')}</span>
                  <span className="text-muted-foreground">{l.tutor_name}</span>
                </li>
              ))}
            </ul>}
        </CardContent>
      </Card>

      {toRate.length > 0 && (
        <Card className="mt-6 border-amber-300 bg-amber-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Star className="h-5 w-5 fill-amber-400 text-amber-400" aria-hidden /> Rate your tutors
            </CardTitle>
            <CardDescription>Your rating helps other parents find the best tutors.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {toRate.map((t) => (
              <Button key={t.tutor_id} variant="outline" onClick={() => setRating(t)}>Rate {t.full_name}</Button>
            ))}
          </CardContent>
        </Card>
      )}

      {user?.photo_url && (
        <Card className="mt-6">
          <CardHeader><CardTitle className="text-lg">Profile picture</CardTitle></CardHeader>
          <CardContent><PhotoUploader name={name} /></CardContent>
        </Card>
      )}

      <div className="mt-8 flex flex-wrap gap-2">
        <Button asChild><Link href="/tutors">Find a tutor</Link></Button>
        <Button variant="outline" asChild><Link href="/dashboard/parent/lessons">My lessons</Link></Button>
        <Button variant="outline" asChild><Link href="/dashboard/parent/wallet">Payments &amp; receipts</Link></Button>
      </div>

      {rating && (
        <RateTutorDialog
          tutorId={rating.tutor_id}
          tutorName={rating.full_name}
          open
          onOpenChange={(open) => !open && setRating(null)}
          onRated={refresh}
        />
      )}
    </>
  )
}

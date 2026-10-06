'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import RateTutorDialog from '@/components/reviews/RateTutorDialog'
import PageHeader from '@/components/shared/PageHeader'
import StatCard from '@/components/shared/StatCard'
import { useAuth } from '@/hooks/useAuth'
import { getMyInvoices } from '@/lib/billing'
import { getMySchedules } from '@/lib/schedules'
import { getMySessions } from '@/lib/sessions'
import type { ParentProfile, TutorToRate } from '@/types'

export default function ParentOverviewPage() {
  const { user, refresh } = useAuth()
  const [counts, setCounts] = useState<{ schedules: number; toConfirm: number; unpaid: number } | null>(null)
  const [rating, setRating] = useState<TutorToRate | null>(null)

  useEffect(() => {
    Promise.all([getMySchedules(), getMySessions({ status: 'logged' }), getMyInvoices()])
      .then(([schedules, sessions, invoices]) => setCounts({
        schedules: schedules.length,
        toConfirm: sessions.length,
        unpaid: invoices.filter((i) => i.status === 'pending').length,
      }))
      .catch(() => setCounts({ schedules: 0, toConfirm: 0, unpaid: 0 }))
  }, [])

  const firstName = (user?.profile as ParentProfile | null)?.full_name?.split(' ')[0]
  const toRate = user?.tutors_to_rate ?? []

  return (
    <>
      <PageHeader title={firstName ? `Welcome, ${firstName}` : 'Dashboard'} description="Here's what needs your attention." />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Active Schedules" value={counts?.schedules ?? null} href="/dashboard/parent/schedules" />
        <StatCard label="Sessions to Confirm" value={counts?.toConfirm ?? null} href="/dashboard/parent/sessions" />
        <StatCard label="Unpaid Invoices" value={counts?.unpaid ?? null} href="/dashboard/parent/invoices" />
      </div>

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

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Quick links</h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild><Link href="/dashboard/parent/schedules">My schedules</Link></Button>
          <Button variant="outline" asChild><Link href="/dashboard/parent/sessions">Confirm sessions</Link></Button>
          <Button variant="outline" asChild><Link href="/dashboard/parent/invoices">Invoices</Link></Button>
          <Button asChild><Link href="/tutors">Find a tutor</Link></Button>
        </div>
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

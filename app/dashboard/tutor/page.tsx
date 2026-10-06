'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import StatCard from '@/components/shared/StatCard'
import { useAuth } from '@/hooks/useAuth'
import { todayDayOfWeek } from '@/lib/format'
import { getTutorSchedules } from '@/lib/schedules'
import { getTutorSessions } from '@/lib/sessions'
import type { TutorProfile } from '@/types'

function VettingBanner({ profile }: { profile: TutorProfile }) {
  if (profile.vetting_status === 'pending') {
    return (
      <div role="status" className="mb-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Your profile is under review. You&apos;ll be notified once approved.
      </div>
    )
  }
  if (profile.vetting_status === 'rejected') {
    return (
      <div role="alert" className="mb-6 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">
        Your application was not approved. {profile.vetting_note}
      </div>
    )
  }
  return null // approved: no banner
}

export default function TutorOverviewPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<{ thisMonth: number; today: number } | null>(null)

  useEffect(() => {
    const now = new Date()
    Promise.all([getTutorSessions({ month: now.getMonth() + 1, year: now.getFullYear() }), getTutorSchedules()])
      .then(([sessions, schedules]) => setStats({
        thisMonth: sessions.filter((s) => s.status !== 'cancelled').length,
        today: schedules.filter((s) => s.day_of_week === todayDayOfWeek()).length,
      }))
      .catch(() => setStats({ thisMonth: 0, today: 0 }))
  }, [])

  const profile = user?.profile as TutorProfile | null | undefined
  if (!user) return <LoadingSpinner />

  return (
    <>
      {profile && <VettingBanner profile={profile} />}
      <PageHeader title={profile ? `Welcome, ${profile.full_name.split(' ')[0]}` : 'Dashboard'} />
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="Sessions This Month" value={stats?.thisMonth ?? null} href="/dashboard/tutor/sessions" />
        <StatCard label="Upcoming Sessions Today" value={stats?.today ?? null} href="/dashboard/tutor/sessions" />
      </div>
      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Quick links</h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild><Link href="/dashboard/tutor/profile">Edit profile & subjects</Link></Button>
          <Button asChild><Link href="/dashboard/tutor/sessions">Log a session</Link></Button>
        </div>
      </div>
    </>
  )
}

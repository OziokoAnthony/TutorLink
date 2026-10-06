'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import LogSessionForm from '@/components/sessions/LogSessionForm'
import SessionCard from '@/components/sessions/SessionCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getTutorSchedules } from '@/lib/schedules'
import { getTutorSessions } from '@/lib/sessions'
import type { Schedule, Session } from '@/types'

const RECENT = 10

export default function TutorLogSessionPage() {
  const toast = useToast()
  const [schedules, setSchedules] = useState<Schedule[] | null>(null)
  const [recent, setRecent] = useState<Session[] | null>(null)

  useEffect(() => {
    getTutorSchedules().then(setSchedules).catch((e) => { toast.error(errorMessage(e)); setSchedules([]) })
    getTutorSessions().then((s) => setRecent(s.slice(0, RECENT))).catch(() => setRecent([]))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <PageHeader title="Log a session" description="Log each lesson after you teach it. The parent then confirms it." />
      <div className="space-y-6">
        <Card>
          <CardHeader><CardTitle className="text-lg">New session</CardTitle></CardHeader>
          <CardContent>
            {schedules === null ? <LoadingSpinner /> : schedules.length === 0 ? (
              <EmptyState
                message="You have no active schedules yet. Once a parent books you, their weekly slot appears here."
                action={<Button variant="outline" asChild><Link href="/dashboard/tutor/profile">Check your profile</Link></Button>}
              />
            ) : (
              <LogSessionForm schedules={schedules} onLogged={(s) => setRecent((list) => [s, ...(list ?? [])].slice(0, RECENT))} />
            )}
          </CardContent>
        </Card>

        <section>
          <h2 className="mb-3 text-lg font-semibold">Recently logged</h2>
          {recent === null ? <LoadingSpinner /> : recent.length === 0 ? (
            <EmptyState message="No sessions logged yet." />
          ) : (
            <div className="space-y-3">{recent.map((s) => <SessionCard key={s.id} session={s} viewer="tutor" />)}</div>
          )}
        </section>
      </div>
    </>
  )
}

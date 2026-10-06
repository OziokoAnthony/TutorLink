'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import RateTutorDialog from '@/components/reviews/RateTutorDialog'
import SessionCard from '@/components/sessions/SessionCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { confirmSession, getMySessions } from '@/lib/sessions'
import type { Session, TutorToRate } from '@/types'

export default function ParentSessionsPage() {
  const toast = useToast()
  const { user, refresh } = useAuth()
  const [sessions, setSessions] = useState<Session[] | null>(null)
  const [tab, setTab] = useState('to-confirm')
  const [rating, setRating] = useState<TutorToRate | null>(null)

  useEffect(() => {
    getMySessions().then(setSessions).catch((e) => { toast.error(errorMessage(e)); setSessions([]) })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function confirm(session: Session) {
    try {
      const updated = await confirmSession(session.id)
      setSessions((list) => list?.map((s) => (s.id === updated.id ? updated : s)) ?? null)
      toast.success('Session confirmed!')
      await refresh() // may add this tutor to "tutors to rate"
    } catch (e) {
      toast.error(errorMessage(e))
    }
  }

  const toRate = new Map((user?.tutors_to_rate ?? []).map((t) => [t.tutor_id, t]))
  const rateButton = (session: Session) => {
    const tutor = session.tutor_id ? toRate.get(session.tutor_id) : undefined
    return tutor ? <Button size="sm" variant="outline" onClick={() => setRating(tutor)}>Rate tutor</Button> : undefined
  }

  if (sessions === null) return <><PageHeader title="Sessions" /><LoadingSpinner /></>

  const toConfirm = sessions.filter((s) => s.status === 'logged')
  const confirmed = sessions.filter((s) => s.status === 'confirmed')

  return (
    <>
      <PageHeader title="Sessions" description="Confirm each lesson after it happens. Only confirmed lessons are billed." />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="to-confirm">To Confirm{toConfirm.length > 0 && ` (${toConfirm.length})`}</TabsTrigger>
          <TabsTrigger value="confirmed">Confirmed</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
        <TabsContent value="to-confirm" className="space-y-3">
          {toConfirm.length === 0
            ? <EmptyState message="All sessions confirmed. Great job!" />
            : toConfirm.map((s) => <SessionCard key={s.id} session={s} onConfirm={confirm} />)}
        </TabsContent>
        <TabsContent value="confirmed" className="space-y-3">
          {confirmed.length === 0
            ? <EmptyState message="No confirmed sessions yet." />
            : confirmed.map((s) => <SessionCard key={s.id} session={s} action={rateButton(s)} />)}
        </TabsContent>
        <TabsContent value="all" className="space-y-3">
          {sessions.length === 0
            ? <EmptyState message="No sessions yet. Your tutor logs each lesson after it happens." />
            : sessions.map((s) => <SessionCard key={s.id} session={s} />)}
        </TabsContent>
      </Tabs>
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

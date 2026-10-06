'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { DAYS, formatTime, levelLabel } from '@/lib/format'
import { cancelSchedule, getMySchedules } from '@/lib/schedules'
import type { Schedule } from '@/types'

export default function ParentSchedulesPage() {
  const toast = useToast()
  const [schedules, setSchedules] = useState<Schedule[] | null>(null)
  const [cancelling, setCancelling] = useState<Schedule | null>(null)

  useEffect(() => {
    getMySchedules().then(setSchedules).catch((e) => { toast.error(errorMessage(e)); setSchedules([]) })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function cancel(schedule: Schedule) {
    try {
      await cancelSchedule(schedule.id)
      setSchedules((list) => list?.filter((s) => s.id !== schedule.id) ?? null)
      toast.success('Schedule cancelled')
    } catch (e) {
      toast.error(errorMessage(e))
      throw e // keep the dialog open
    }
  }

  return (
    <>
      <PageHeader
        title="My schedules"
        description="Your recurring weekly lessons."
        action={<Button asChild><Link href="/tutors">Book another tutor</Link></Button>}
      />
      {schedules === null ? <LoadingSpinner /> : schedules.length === 0 ? (
        <EmptyState message="You have no active schedules." action={<Button variant="outline" asChild><Link href="/tutors">Find a tutor</Link></Button>} />
      ) : (
        <div className="space-y-3">
          {schedules.map((s) => (
            <Card key={s.id}>
              <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-semibold">{s.tutor_name ?? 'Tutor'}</p>
                  <p className="text-sm text-muted-foreground">{s.subject} • {levelLabel(s.level)}</p>
                  <p className="text-sm">Every {DAYS[s.day_of_week]}, {formatTime(s.start_time)}–{formatTime(s.end_time)}</p>
                </div>
                <Button variant="outline" className="text-destructive hover:text-destructive" onClick={() => setCancelling(s)}>Cancel</Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <ConfirmDialog
        open={cancelling !== null}
        onOpenChange={(open) => !open && setCancelling(null)}
        title="Cancel schedule?"
        description="Are you sure you want to cancel this recurring session?"
        confirmLabel="Cancel schedule"
        destructive
        onConfirm={() => cancel(cancelling!)}
      />
    </>
  )
}

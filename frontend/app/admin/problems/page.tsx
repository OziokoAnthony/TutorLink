'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import LessonCard from '@/components/lessons/LessonCard'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatNaira, toISODate } from '@/lib/format'
import { getIssues, resolveIssue } from '@/lib/lessons'
import type { IssueResolution, Lesson } from '@/types'

const OUTCOME: Record<IssueResolution, { title: string; description: (l: Lesson) => string; confirm: string }> = {
  refund: {
    title: 'Refund this lesson',
    description: (l) => `${formatNaira(l.price)} (the agreed price, without the parent fee) goes back to the parent's TutorLink balance. The tutor earns nothing for this lesson.`,
    confirm: 'Refund',
  },
  reschedule: {
    title: 'Move this lesson',
    description: () => 'The paid lesson moves to the new date and time. Both sides are told.',
    confirm: 'Reschedule',
  },
  reject: {
    title: 'Let the lesson stand',
    description: () => "The problem report is closed and the tutor's earning becomes payable.",
    confirm: 'Lesson stands',
  },
}

function ResolveDialog({ lesson, resolution, onClose, onResolved }: {
  lesson: Lesson | null
  resolution: IssueResolution | null
  onClose: () => void
  onResolved: (lesson: Lesson) => void
}) {
  const toast = useToast()
  const [note, setNote] = useState('')
  const [date, setDate] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setNote('')
    setDate('')
    setStart(lesson?.start_time.slice(0, 5) ?? '')
    setEnd(lesson?.end_time.slice(0, 5) ?? '')
  }, [lesson, resolution])

  const outcome = resolution ? OUTCOME[resolution] : null
  const rescheduleReady = resolution !== 'reschedule' || (date !== '' && start !== '' && end !== '' && end > start)

  async function submit() {
    if (!lesson || !resolution) return
    setBusy(true)
    try {
      const updated = await resolveIssue(lesson.id, {
        resolution, note,
        ...(resolution === 'reschedule' ? { new_date: date, new_start_time: start, new_end_time: end } : {}),
      })
      toast.success('Problem resolved. The parent and tutor have been told.')
      onResolved(updated)
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={!!lesson && !!outcome} onOpenChange={(open) => !open && !busy && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{outcome?.title}</DialogTitle>
          <DialogDescription>{lesson && outcome?.description(lesson)}</DialogDescription>
        </DialogHeader>
        {resolution === 'reschedule' && (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="new-date">New date</Label>
              <Input id="new-date" type="date" min={toISODate(new Date())} value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-start">Starts</Label>
              <Input id="new-start" type="time" value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="new-end">Ends</Label>
              <Input id="new-end" type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
        )}
        <div className="space-y-1.5">
          <Label htmlFor="resolve-note">Note to both sides (optional)</Label>
          <Textarea id="resolve-note" rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>Back</Button>
          <Button variant={resolution === 'refund' ? 'destructive' : 'default'} onClick={submit} disabled={busy || !rescheduleReady}>
            {busy ? 'Working…' : outcome?.confirm}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function AdminProblemsPage() {
  const toast = useToast()
  const [openOnly, setOpenOnly] = useState(true)
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [selected, setSelected] = useState<{ lesson: Lesson; resolution: IssueResolution } | null>(null)

  const load = useCallback(() => {
    setLessons(null)
    getIssues(openOnly).then(setLessons).catch((e) => { toast.error(errorMessage(e)); setLessons([]) })
  }, [openOnly, toast])
  useEffect(load, [load])

  function resolved(updated: Lesson) {
    setLessons((list) => list && (openOnly ? list.filter((l) => l.id !== updated.id) : list.map((l) => l.id === updated.id ? updated : l)))
    setSelected(null)
  }

  return (
    <>
      <PageHeader title="Problems" description="Lessons a parent reported, and lessons the tutor didn't report within 24 hours. The tutor's earning is on hold until you decide." />
      <Tabs value={openOnly ? 'open' : 'all'} onValueChange={(v) => setOpenOnly(v === 'open')} className="mb-4">
        <TabsList>
          <TabsTrigger value="open">Open</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {lessons === null ? <LoadingSpinner /> : lessons.length === 0 ? (
        <EmptyState message={openOnly ? 'No open problems.' : 'No problems reported yet.'} />
      ) : (
        <div className="space-y-4">
          {lessons.map((l) => (
            <LessonCard key={l.id} lesson={l} viewer="admin" actions={l.issue && !l.issue.resolution && (
              <>
                <Button size="sm" variant="destructive" onClick={() => setSelected({ lesson: l, resolution: 'refund' })}>Refund</Button>
                <Button size="sm" variant="outline" onClick={() => setSelected({ lesson: l, resolution: 'reschedule' })}>Reschedule</Button>
                <Button size="sm" variant="outline" onClick={() => setSelected({ lesson: l, resolution: 'reject' })}>Lesson stands</Button>
              </>
            )} />
          ))}
        </div>
      )}

      <ResolveDialog lesson={selected?.lesson ?? null} resolution={selected?.resolution ?? null}
        onClose={() => setSelected(null)} onResolved={resolved} />
    </>
  )
}

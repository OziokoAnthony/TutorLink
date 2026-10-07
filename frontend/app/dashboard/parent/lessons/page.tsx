'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import LessonCard from '@/components/lessons/LessonCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime, ISSUE_KINDS } from '@/lib/format'
import { getMyLessons, reportProblem } from '@/lib/lessons'
import type { IssueKind, Lesson } from '@/types'

/** Whether the parent can report a problem with this lesson now (spec 1 R5.1). */
function canReport(l: Lesson, now: Date): boolean {
  if (l.status === 'flagged') return true
  if (l.status === 'reported') return !!l.problem_window_ends_at && new Date(l.problem_window_ends_at) > now
  return l.status === 'confirmed' && new Date(l.ends_at) <= now
}

export default function ParentLessonsPage() {
  const toast = useToast()
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [problemFor, setProblemFor] = useState<Lesson | null>(null)
  const [kind, setKind] = useState<IssueKind>('tutor_absent')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    getMyLessons().then(setLessons).catch((e) => { toast.error(errorMessage(e)); setLessons([]) })
  }, [toast])
  useEffect(load, [load])

  async function submitProblem() {
    if (!problemFor) return
    setBusy(true)
    try {
      await reportProblem(problemFor.id, kind, description.trim())
      toast.success('Thanks. TutorLink will review it, and the tutor is not paid for this lesson until then.')
      setProblemFor(null)
      setDescription('')
      load()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  if (!lessons) return <LoadingSpinner />
  const now = new Date()
  const upcoming = lessons.filter((l) => l.status === 'confirmed' && new Date(l.ends_at) > now).reverse()
  const past = lessons.filter((l) => !upcoming.includes(l))

  const card = (l: Lesson) => (
    <LessonCard key={l.id} lesson={l} viewer="parent" actions={canReport(l, now) && (
      <Button size="sm" variant="outline" onClick={() => setProblemFor(l)}>
        Report a problem{l.problem_window_ends_at && l.status === 'reported' ? ` (until ${formatDateTime(l.problem_window_ends_at)})` : ''}
      </Button>
    )} />
  )

  return (
    <>
      <PageHeader title="My lessons" description="Paid lessons are confirmed. After each lesson you have 24 hours from the tutor's report to tell us if something went wrong." />
      <Tabs defaultValue="past">
        <TabsList>
          <TabsTrigger value="past">Taught ({past.length})</TabsTrigger>
          <TabsTrigger value="upcoming">Coming up ({upcoming.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="past" className="space-y-3">
          {past.length === 0 ? <EmptyState message="No lessons taught yet." /> : past.map(card)}
        </TabsContent>
        <TabsContent value="upcoming" className="space-y-3">
          {upcoming.length === 0 ? <EmptyState message="No paid lessons coming up." /> : upcoming.map(card)}
        </TabsContent>
      </Tabs>

      <Dialog open={!!problemFor} onOpenChange={(o) => !busy && !o && setProblemFor(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Report a problem</DialogTitle>
            <DialogDescription>
              TutorLink reviews every report. If the lesson didn&apos;t happen as agreed, it can be refunded to your TutorLink balance or rescheduled.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="problem-kind">What happened?</Label>
              <Select value={kind} onValueChange={(v) => setKind(v as IssueKind)}>
                <SelectTrigger id="problem-kind"><SelectValue /></SelectTrigger>
                <SelectContent>{ISSUE_KINDS.map((k) => <SelectItem key={k.value} value={k.value}>{k.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="problem-text">Tell us more</Label>
              <Textarea id="problem-text" rows={4} maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setProblemFor(null)} disabled={busy}>Back</Button>
            <Button onClick={submitProblem} disabled={busy || description.trim().length < 10}>{busy ? 'Sending…' : 'Report problem'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

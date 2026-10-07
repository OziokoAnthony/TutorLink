'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import LessonCard from '@/components/lessons/LessonCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { getTutorLessons, submitReport } from '@/lib/lessons'
import type { Lesson } from '@/types'

const REPORT_WITHIN_MS = 24 * 60 * 60 * 1000

export default function TutorLessonsPage() {
  const toast = useToast()
  const [lessons, setLessons] = useState<Lesson[] | null>(null)
  const [reporting, setReporting] = useState<Lesson | null>(null)
  const [topic, setTopic] = useState('')
  const [homework, setHomework] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    getTutorLessons().then(setLessons).catch((e) => { toast.error(errorMessage(e)); setLessons([]) })
  }, [toast])
  useEffect(load, [load])

  async function report() {
    if (!reporting) return
    setBusy(true)
    try {
      await submitReport(reporting.id, topic.trim(), homework.trim())
      toast.success('Report submitted. You’re paid once the parent’s 24-hour window closes.')
      setReporting(null)
      setTopic('')
      setHomework('')
      load()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  if (!lessons) return <LoadingSpinner />
  const now = new Date()
  const canReport = (l: Lesson) => (l.status === 'confirmed' && new Date(l.ends_at) <= now
    && now.getTime() <= new Date(l.ends_at).getTime() + REPORT_WITHIN_MS)
    || (l.status === 'disputed' && !l.reported_at)
  const toReport = lessons.filter(canReport)
  const upcoming = lessons.filter((l) => l.status === 'confirmed' && new Date(l.ends_at) > now).reverse()
  const done = lessons.filter((l) => !toReport.includes(l) && !upcoming.includes(l))

  return (
    <>
      <PageHeader title="Lessons" description="Report each lesson within 24 hours of it ending, or it's held for review before you're paid." />
      <Tabs defaultValue={toReport.length ? 'report' : 'upcoming'}>
        <TabsList>
          <TabsTrigger value="report">To report ({toReport.length})</TabsTrigger>
          <TabsTrigger value="upcoming">Coming up ({upcoming.length})</TabsTrigger>
          <TabsTrigger value="done">Reported ({done.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="report" className="space-y-3">
          {toReport.length === 0 ? <EmptyState message="Nothing to report. Great job!" /> : toReport.map((l) => (
            <LessonCard key={l.id} lesson={l} viewer="tutor" actions={(
              <Button size="sm" onClick={() => setReporting(l)}>
                Submit report{l.status === 'confirmed' ? ` (by ${formatDateTime(new Date(new Date(l.ends_at).getTime() + REPORT_WITHIN_MS).toISOString())})` : ''}
              </Button>
            )} />
          ))}
        </TabsContent>
        <TabsContent value="upcoming" className="space-y-3">
          {upcoming.length === 0 ? <EmptyState message="No paid lessons coming up." /> : upcoming.map((l) => <LessonCard key={l.id} lesson={l} viewer="tutor" />)}
        </TabsContent>
        <TabsContent value="done" className="space-y-3">
          {done.length === 0 ? <EmptyState message="No reported lessons yet." /> : done.map((l) => <LessonCard key={l.id} lesson={l} viewer="tutor" />)}
        </TabsContent>
      </Tabs>

      <Dialog open={!!reporting} onOpenChange={(o) => !busy && !o && setReporting(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Lesson report</DialogTitle>
            <DialogDescription>The parent sees this and has 24 hours to raise a problem.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="report-topic">Topic covered</Label>
              <Textarea id="report-topic" rows={3} maxLength={2000} value={topic} onChange={(e) => setTopic(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="report-homework">Homework (optional)</Label>
              <Textarea id="report-homework" rows={2} maxLength={2000} value={homework} onChange={(e) => setHomework(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReporting(null)} disabled={busy}>Back</Button>
            <Button onClick={report} disabled={busy || !topic.trim()}>{busy ? 'Submitting…' : 'Submit report'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

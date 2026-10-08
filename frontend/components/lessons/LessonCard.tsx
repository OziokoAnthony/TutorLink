import type { ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import RecordingPlayer from '@/components/lessons/RecordingPlayer'
import { EarningStatusBadge, LessonStatusBadge } from '@/components/shared/StatusBadge'
import { formatDate, formatDateTime, formatNaira, formatTime, ISSUE_KIND_LABEL } from '@/lib/format'
import type { Lesson } from '@/types'

/** One lesson: when, what, the tutor's report, any problem, and the viewer's own money figure. */
export default function LessonCard({ lesson, viewer, actions }: {
  lesson: Lesson
  viewer: 'parent' | 'tutor' | 'admin'
  actions?: ReactNode
}) {
  const who = viewer === 'parent' ? `Tutor: ${lesson.tutor_name ?? ''}`
    : viewer === 'tutor' ? `Parent: ${lesson.parent_name ?? ''}`
    : `Parent: ${lesson.parent_name ?? ''} • Tutor: ${lesson.tutor_name ?? ''}`
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="font-semibold">{formatDate(lesson.lesson_date)}, {formatTime(lesson.start_time)}–{formatTime(lesson.end_time)}</p>
            <p className="text-sm text-muted-foreground">{lesson.subjects.join(', ')} • {who}{lesson.mode === 'online' ? ' • Online' : ''}</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <LessonStatusBadge status={lesson.status} />
            {viewer !== 'parent' && lesson.earning_status && <EarningStatusBadge status={lesson.earning_status} />}
          </div>
        </div>

        {lesson.topic_covered && (
          <div className="text-sm">
            <p><span className="font-medium">Topic:</span> {lesson.topic_covered}</p>
            {lesson.homework && <p><span className="font-medium">Homework:</span> {lesson.homework}</p>}
          </div>
        )}

        {lesson.has_recording && <RecordingPlayer lessonId={lesson.id} />}

        {lesson.issue && (
          <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-950">
            <p className="font-medium">{ISSUE_KIND_LABEL[lesson.issue.kind]}</p>
            {lesson.issue.description && <p>{lesson.issue.description}</p>}
            {lesson.issue.resolution
              ? <p className="mt-1">Outcome: {lesson.issue.resolution === 'refund' ? 'refunded' : lesson.issue.resolution === 'reschedule' ? 'rescheduled' : 'lesson stands'}{lesson.issue.resolution_note ? ` — ${lesson.issue.resolution_note}` : ''}</p>
              : <p className="mt-1">TutorLink is reviewing this.</p>}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-muted-foreground">
            {viewer === 'parent' && lesson.parent_price !== undefined && <>You paid {formatNaira(lesson.parent_price)}</>}
            {viewer === 'tutor' && lesson.tutor_earning !== undefined && (
              <>Your earning {formatNaira(lesson.tutor_earning)}{lesson.earning_status === 'payable' && lesson.payout_due_at ? ` • to be paid by ${formatDateTime(lesson.payout_due_at)}` : ''}</>
            )}
            {viewer === 'admin' && <>Parent paid {formatNaira(lesson.parent_price ?? 0)} • tutor earns {formatNaira(lesson.tutor_earning ?? 0)}</>}
          </span>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
      </CardContent>
    </Card>
  )
}

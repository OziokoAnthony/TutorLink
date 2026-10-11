import type { ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { FEEDBACK_KIND_LABEL, formatDateTime } from '@/lib/format'
import type { Feedback } from '@/types'

/** One piece of feedback with its help chat conversation, if any, and TutorLink's reply (spec 6). */
export default function FeedbackCard({ feedback, header, actions }: {
  feedback: Feedback
  header?: ReactNode
  actions?: ReactNode
}) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="secondary">{FEEDBACK_KIND_LABEL[feedback.kind]}</Badge>
          <span>{formatDateTime(feedback.created_at)}</span>
          {header}
        </div>
        <p className="whitespace-pre-wrap text-sm">{feedback.message}</p>
        {feedback.transcript && (
          <details className="rounded-md border p-3 text-sm">
            <summary className="cursor-pointer font-medium">Help chat conversation</summary>
            <div className="mt-3 space-y-2">
              {feedback.transcript.map((m, i) => (
                <p key={i} className="whitespace-pre-wrap">
                  <span className="font-medium">{m.role === 'user' ? 'Them: ' : 'Assistant: '}</span>{m.content}
                </p>
              ))}
            </div>
          </details>
        )}
        {feedback.reply ? (
          <div className="rounded-md bg-muted p-3 text-sm">
            <p className="mb-1 font-medium">
              TutorLink replied{feedback.replied_at && <> • {formatDateTime(feedback.replied_at)}</>}
            </p>
            <p className="whitespace-pre-wrap">{feedback.reply}</p>
          </div>
        ) : actions}
      </CardContent>
    </Card>
  )
}

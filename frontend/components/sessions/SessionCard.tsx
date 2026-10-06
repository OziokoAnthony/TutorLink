'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { SessionStatusBadge } from '@/components/shared/StatusBadge'
import { formatDate, levelLabel } from '@/lib/format'
import type { Session } from '@/types'

interface SessionCardProps {
  session: Session
  /** Who the card is shown to: a parent sees the tutor's name, a tutor sees the parent's. */
  viewer?: 'parent' | 'tutor'
  onConfirm?: (session: Session) => Promise<void>
  /** Extra action, e.g. "Rate tutor". */
  action?: React.ReactNode
}

/** Session row with confirm button. */
export default function SessionCard({ session, viewer = 'parent', onConfirm, action }: SessionCardProps) {
  const [busy, setBusy] = useState(false)
  const person = viewer === 'parent' ? `Tutor: ${session.tutor_name ?? 'Unknown'}` : `Parent: ${session.parent_name ?? 'Unknown'}`

  async function confirm() {
    if (!onConfirm) return
    setBusy(true)
    try { await onConfirm(session) } finally { setBusy(false) }
  }

  return (
    <Card>
      <CardContent className="space-y-2 pt-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-semibold">{formatDate(session.session_date)}</p>
          <SessionStatusBadge status={session.status} />
        </div>
        <p className="text-sm">
          {session.subject}{session.level && ` (${levelLabel(session.level)})`} — {person}
        </p>
        <dl className="space-y-1 text-sm text-muted-foreground">
          <div><dt className="inline font-medium text-foreground">Topic: </dt><dd className="inline">{session.topic_covered || '—'}</dd></div>
          <div><dt className="inline font-medium text-foreground">Homework: </dt><dd className="inline">{session.homework || '—'}</dd></div>
        </dl>
        {(onConfirm || action) && (
          <div className="flex justify-end gap-2 pt-1">
            {action}
            {onConfirm && <Button size="sm" onClick={confirm} disabled={busy}>{busy ? 'Confirming…' : 'Confirm'}</Button>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

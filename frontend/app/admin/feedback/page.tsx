'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import FeedbackCard from '@/components/feedback/FeedbackCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getAdminFeedback, replyToFeedback } from '@/lib/feedback'
import type { Feedback } from '@/types'

/** Spec 6 R2: feedback from parents and tutors, answered once each. */
export default function AdminFeedbackPage() {
  const toast = useToast()
  const [answered, setAnswered] = useState(false)
  const [items, setItems] = useState<Feedback[] | null>(null)
  const [replying, setReplying] = useState<Feedback | null>(null)

  const load = useCallback(() => {
    setItems(null)
    getAdminFeedback(answered).then(setItems).catch((e) => { toast.error(errorMessage(e)); setItems([]) })
  }, [answered, toast])
  useEffect(load, [load])

  async function reply(feedback: Feedback, text: string) {
    try {
      await replyToFeedback(feedback.id, text)
      toast.success('Reply sent. They are told in the app and by email.')
      setItems((list) => list && list.filter((f) => f.id !== feedback.id))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Feedback"
        description="Problems, suggestions, questions and praise from parents and tutors, including help chats they sent to the team." />
      <Tabs value={answered ? 'answered' : 'waiting'} onValueChange={(v) => setAnswered(v === 'answered')} className="mb-4">
        <TabsList>
          <TabsTrigger value="waiting">Waiting</TabsTrigger>
          <TabsTrigger value="answered">Answered</TabsTrigger>
        </TabsList>
      </Tabs>

      {items === null ? <LoadingSpinner /> : items.length === 0 ? (
        <EmptyState message={answered ? 'No answered feedback yet.' : 'No feedback waiting for a reply.'} />
      ) : (
        <div className="space-y-4">
          {items.map((f) => (
            <FeedbackCard key={f.id} feedback={f}
              header={<span>• <span className="font-medium text-foreground">{f.user_name ?? f.user_email}</span>
                {' '}({f.user_role}) • {f.user_email}</span>}
              actions={<Button size="sm" onClick={() => setReplying(f)}>Reply</Button>} />
          ))}
        </div>
      )}

      <NoteDialog
        open={replying !== null}
        onOpenChange={(open) => { if (!open) setReplying(null) }}
        title="Reply to this feedback"
        description="They see your reply under Help & feedback and get it by email. You can reply once."
        confirmLabel="Send reply"
        noteLabel="Your reply"
        noteRequired
        onConfirm={(text) => replying ? reply(replying, text) : undefined}
      />
    </>
  )
}

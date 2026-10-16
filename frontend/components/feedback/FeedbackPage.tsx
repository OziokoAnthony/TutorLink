'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import FeedbackCard from '@/components/feedback/FeedbackCard'
import Choice from '@/components/shared/Choice'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getMyFeedback, sendFeedback } from '@/lib/feedback'
import { FEEDBACK_KINDS } from '@/lib/format'
import type { Feedback, FeedbackKind } from '@/types'

/** Spec 6 R1: send feedback to TutorLink and read the replies. The same page for parents and tutors. */
export default function FeedbackPage() {
  const toast = useToast()
  const [items, setItems] = useState<Feedback[] | null>(null)
  const [kind, setKind] = useState<FeedbackKind>('problem')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getMyFeedback().then(setItems).catch((e) => { toast.error(errorMessage(e)); setItems([]) })
  }, [toast])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      const sent = await sendFeedback(kind, message.trim())
      setItems((list) => [sent, ...(list ?? [])])
      setMessage('')
      toast.success("Thank you. We'll reply here and by email.")
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const length = message.trim().length
  return (
    <>
      <PageHeader title="Help & feedback"
        description="Tell us what's wrong, what you'd like, or ask a question. For quick answers, use the help chat at the bottom right." />
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-lg">Send feedback</CardTitle>
          <CardDescription>The TutorLink team reads every message and replies here and by email.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <Choice label="What is it about?" value={kind} options={FEEDBACK_KINDS} onChange={setKind} />
            <div className="space-y-1.5">
              <Label htmlFor="feedback-message">Your message</Label>
              <Textarea id="feedback-message" rows={5} maxLength={2000} value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Tell us what happened, which page you were on, and anything else that helps." />
              <p className="text-xs text-muted-foreground">
                {length < 10 ? 'At least 10 characters.' : `${length} of 2,000 characters.`}
              </p>
            </div>
            <Button type="submit" disabled={busy || length < 10}>{busy ? 'Sending…' : 'Send feedback'}</Button>
          </form>
        </CardContent>
      </Card>

      <h2 className="mb-3 text-lg font-semibold">What you&apos;ve sent</h2>
      {items === null ? <LoadingSpinner /> : items.length === 0 ? (
        <EmptyState message="You haven't sent any feedback yet." />
      ) : (
        <div className="space-y-4">
          {items.map((f) => (
            <FeedbackCard key={f.id} feedback={f}
              actions={<p className="text-sm text-muted-foreground">Waiting for a reply from TutorLink.</p>} />
          ))}
        </div>
      )}
    </>
  )
}

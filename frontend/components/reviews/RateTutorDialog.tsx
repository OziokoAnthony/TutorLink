'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { StarInput } from '@/components/reviews/StarRating'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { rateTutor } from '@/lib/reviews'

interface RateTutorDialogProps {
  tutorId: string
  tutorName: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onRated?: () => void
}

export default function RateTutorDialog({ tutorId, tutorName, open, onOpenChange, onRated }: RateTutorDialogProps) {
  const toast = useToast()
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    try {
      await rateTutor(tutorId, rating, comment)
      toast.success(`Thanks! Your rating of ${tutorName} helps other parents.`)
      onOpenChange(false)
      setRating(0)
      setComment('')
      onRated?.()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>How was {tutorName}?</DialogTitle>
          <DialogDescription>Your rating appears on their profile so other parents can choose well.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <StarInput value={rating} onChange={setRating} />
          <div className="space-y-1.5">
            <Label htmlFor="review-comment">Comment (optional)</Label>
            <Textarea
              id="review-comment"
              rows={3}
              maxLength={1000}
              placeholder="What went well? Anything to improve?"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Later</Button>
          <Button onClick={submit} disabled={busy || rating === 0}>{busy ? 'Saving…' : 'Submit rating'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

/** A confirmation with a note field (optional unless `noteRequired`). Stays open until onConfirm settles. */
export default function NoteDialog({
  open, onOpenChange, title, description, confirmLabel, destructive, noteLabel = 'Note (optional)', noteRequired,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmLabel: string
  destructive?: boolean
  noteLabel?: string
  noteRequired?: boolean
  onConfirm: (note: string) => Promise<void> | void
}) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  async function confirm() {
    setBusy(true)
    try {
      await onConfirm(note.trim())
      setNote('')
      onOpenChange(false)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="note-dialog-text">{noteLabel}</Label>
          <Textarea id="note-dialog-text" rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Back</Button>
          <Button variant={destructive ? 'destructive' : 'default'} onClick={confirm}
            disabled={busy || (noteRequired && note.trim().length < 3)}>
            {busy ? 'Working…' : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

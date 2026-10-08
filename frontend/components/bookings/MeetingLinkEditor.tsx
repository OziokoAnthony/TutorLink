'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { setMeetingLink } from '@/lib/bookings'
import type { Booking } from '@/types'

/** Tutor: set the video call link for an online booking. The parent sees it once they've paid. */
export default function MeetingLinkEditor({ booking, onChange }: { booking: Booking; onChange: (booking: Booking) => void }) {
  const toast = useToast()
  const [link, setLink] = useState(booking.meeting_link ?? '')
  const [busy, setBusy] = useState(false)
  const valid = /^https:\/\/\S+$/.test(link.trim())

  async function save() {
    setBusy(true)
    try {
      onChange(await setMeetingLink(booking.id, link.trim()))
      toast.success('Meeting link saved')
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-1 space-y-1">
      <div className="flex flex-wrap gap-2">
        <Input aria-label="Meeting link" className="min-w-0 flex-1" placeholder="https://meet.google.com/…" value={link}
          onChange={(e) => setLink(e.target.value)} />
        <Button size="sm" onClick={save} disabled={busy || !valid || link.trim() === booking.meeting_link}>
          {busy ? 'Saving…' : 'Save link'}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">A Google Meet, Zoom or similar link starting with https://. The parent sees it once they&apos;ve paid.</p>
    </div>
  )
}

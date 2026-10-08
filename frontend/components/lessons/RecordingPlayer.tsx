'use client'

import { useState } from 'react'
import { Video } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getRecordingLink } from '@/lib/lessons'

/** Plays an online lesson's recording. The link is fetched on demand and expires after 15 minutes. */
export default function RecordingPlayer({ lessonId }: { lessonId: string }) {
  const toast = useToast()
  const [url, setUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function open() {
    setBusy(true)
    try {
      setUrl((await getRecordingLink(lessonId)).url)
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  if (url) {
    return (
      <video controls preload="metadata" src={url} className="w-full max-w-xl rounded-md border bg-black"
        onError={() => setUrl(null)}>
        <track kind="captions" />
      </video>
    )
  }
  return (
    <Button size="sm" variant="outline" onClick={open} disabled={busy}>
      <Video className="mr-1.5 h-4 w-4" aria-hidden />{busy ? 'Loading…' : 'Watch the lesson recording'}
    </Button>
  )
}

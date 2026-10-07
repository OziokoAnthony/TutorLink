'use client'

import { useRef, useState } from 'react'
import { Camera } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Avatar from '@/components/shared/Avatar'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { uploadPhoto } from '@/lib/auth'

const MAX_BYTES = 5 * 1024 * 1024

/** The signed-in user's profile picture with an upload/change button. */
export default function PhotoUploader({ name }: { name: string }) {
  const { user, refresh } = useAuth()
  const toast = useToast()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  async function onFile(file: File | undefined) {
    if (!file) return
    if (file.size > MAX_BYTES) {
      toast.error('Profile pictures can be at most 5 MB.')
      return
    }
    setBusy(true)
    try {
      await uploadPhoto(file)
      await refresh()
      toast.success('Profile picture saved')
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  return (
    <div className="flex items-center gap-4">
      <Avatar name={name} photoUrl={user?.photo_url} size="lg" />
      <div className="space-y-1">
        <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only"
          id="photo-input" onChange={(e) => onFile(e.target.files?.[0])} />
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => input.current?.click()}>
          <Camera className="mr-2 h-4 w-4" aria-hidden />
          {busy ? 'Uploading…' : user?.photo_url ? 'Change picture' : 'Add a profile picture'}
        </Button>
        <p className="text-xs text-muted-foreground">JPG, PNG or WebP, up to 5 MB.</p>
      </div>
    </div>
  )
}

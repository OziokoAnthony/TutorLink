'use client'

import { useEffect, useRef, useState } from 'react'
import { Camera, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'

/** Takes a selfie with the front camera for the NIN check (spec 4 R3.2). Where the browser can't open
 *  the camera, the phone's camera (or a photo) is picked through a file input instead. */
export default function SelfieCamera({ onChange }: { onChange: (selfie: Blob | null) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<'starting' | 'live' | 'unavailable'>('starting')
  const [preview, setPreview] = useState<string | null>(null)

  function stop() {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  async function start() {
    setState('starting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 720, height: 720 } })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
      setState('live')
    } catch {
      setState('unavailable')
    }
  }

  useEffect(() => {
    // mediaDevices is missing outside a secure context (plain http on a phone), though TypeScript says otherwise.
    if ('mediaDevices' in navigator && typeof navigator.mediaDevices?.getUserMedia === 'function') start()
    else setState('unavailable')
    return stop
  }, [])

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  function choose(blob: Blob | null) {
    setPreview(blob ? URL.createObjectURL(blob) : null)
    onChange(blob)
  }

  function capture() {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    canvas.toBlob((blob) => { if (blob) { choose(blob); stop() } }, 'image/jpeg', 0.9)
  }

  function retake() {
    choose(null)
    if (state === 'live') start()
  }

  if (preview) {
    return (
      <div className="space-y-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={preview} alt="Your selfie" className="aspect-square w-48 rounded-lg object-cover" />
        <Button type="button" variant="outline" size="sm" onClick={retake}><RotateCcw className="mr-1.5 h-4 w-4" />Retake</Button>
      </div>
    )
  }

  if (state === 'unavailable') {
    return (
      <div className="space-y-1.5">
        <label htmlFor="selfie-file" className="text-sm font-medium">Selfie</label>
        <input id="selfie-file" type="file" accept="image/jpeg,image/png,image/webp" capture="user"
          className="block text-sm" onChange={(e) => choose(e.target.files?.[0] ?? null)} />
        <p className="text-xs text-muted-foreground">We couldn&apos;t open your camera here. Take a clear photo of your face instead.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <video ref={videoRef} autoPlay playsInline muted aria-label="Camera preview"
        className="aspect-square w-48 -scale-x-100 rounded-lg bg-muted object-cover" />
      <Button type="button" size="sm" onClick={capture} disabled={state !== 'live'}>
        <Camera className="mr-1.5 h-4 w-4" />{state === 'live' ? 'Take selfie' : 'Opening camera…'}
      </Button>
      <p className="text-xs text-muted-foreground">Face the camera in good light, without glasses or a hat.</p>
    </div>
  )
}

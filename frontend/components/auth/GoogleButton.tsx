'use client'

import { useEffect, useRef, useState } from 'react'
import { GOOGLE_CLIENT_ID } from '@/lib/google'

const SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

interface GoogleIdentityServices {
  accounts: {
    id: {
      initialize: (options: { client_id: string; callback: (response: { credential: string }) => void }) => void
      renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void
    }
  }
}

declare global {
  interface Window {
    google?: GoogleIdentityServices
  }
}

let scriptLoading: Promise<void> | null = null

function loadScript(): Promise<void> {
  if (window.google?.accounts) return Promise.resolve()
  scriptLoading ??= new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = SCRIPT_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      scriptLoading = null
      reject(new Error('Google sign-in could not load'))
    }
    document.head.appendChild(script)
  })
  return scriptLoading
}

/**
 * Google's own "Continue with Google" button. `onCredential` receives the Google ID token, which the
 * backend verifies. Without NEXT_PUBLIC_GOOGLE_CLIENT_ID it says Google sign-in isn't available.
 */
export default function GoogleButton({ onCredential, text = 'continue_with' }: {
  onCredential: (idToken: string) => void
  text?: 'continue_with' | 'signin_with' | 'signup_with'
}) {
  const container = useRef<HTMLDivElement>(null)
  const callback = useRef(onCredential)
  callback.current = onCredential
  const [failed, setFailed] = useState(!GOOGLE_CLIENT_ID)

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return
    let cancelled = false
    loadScript()
      .then(() => {
        if (cancelled || !container.current || !window.google) return
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => callback.current(response.credential),
        })
        window.google.accounts.id.renderButton(container.current, {
          type: 'standard', theme: 'outline', size: 'large', shape: 'rectangular', text,
          width: Math.min(container.current.offsetWidth || 400, 400),
        })
      })
      .catch(() => !cancelled && setFailed(true))
    return () => { cancelled = true }
  }, [text])

  if (failed) {
    return (
      <p className="rounded-md border border-dashed px-3 py-2 text-center text-sm text-muted-foreground">
        Google sign-in isn&apos;t available right now. Please try again later.
      </p>
    )
  }
  return <div ref={container} className="flex min-h-[44px] w-full justify-center" />
}

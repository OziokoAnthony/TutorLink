'use client'

import { toast } from 'sonner'

// One shared object, so pages can list it as an effect dependency without re-running the effect.
const TOASTS = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  info: (message: string) => toast(message),
}

/** Toast notification helper (backed by sonner, shadcn/ui's toast component). */
export function useToast() {
  return TOASTS
}

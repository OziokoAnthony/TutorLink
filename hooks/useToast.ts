'use client'

import { toast } from 'sonner'

/** Toast notification helper (backed by sonner, shadcn/ui's toast component). */
export function useToast() {
  return {
    success: (message: string) => toast.success(message),
    error: (message: string) => toast.error(message),
    info: (message: string) => toast(message),
  }
}

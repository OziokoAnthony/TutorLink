'use client'

import { MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { supportWhatsApp, whatsAppLink } from '@/lib/whatsapp'

/** Spec 13: opens WhatsApp with TutorLink's support number; hidden while no number is set. */
export default function WhatsAppButton({ variant = 'button', label = 'Chat with us on WhatsApp' }:
  { variant?: 'button' | 'link'; label?: string }) {
  const { user } = useAuth()
  const number = supportWhatsApp()
  if (!number) return null
  const href = whatsAppLink(number, user)
  if (variant === 'link') {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer"
        className="inline-flex items-center gap-1 font-medium text-emerald-700 underline-offset-4 hover:underline">
        <MessageCircle className="h-3.5 w-3.5" aria-hidden />{label}
      </a>
    )
  }
  return (
    <Button asChild className="bg-emerald-600 text-white hover:bg-emerald-700">
      <a href={href} target="_blank" rel="noopener noreferrer">
        <MessageCircle className="mr-2 h-4 w-4" aria-hidden />{label}
      </a>
    </Button>
  )
}

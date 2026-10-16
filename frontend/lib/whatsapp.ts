import type { UserMe } from '@/types'

/** TutorLink's WhatsApp Business number in international form, digits only (e.g. 2348012345678), from
 * NEXT_PUBLIC_SUPPORT_WHATSAPP. Null when it isn't set: the buttons stay hidden (spec 13 R1.3). */
export function supportWhatsApp(): string | null {
  const digits = (process.env.NEXT_PUBLIC_SUPPORT_WHATSAPP ?? '').replace(/\D/g, '')
  return digits.length >= 10 ? digits : null
}

/** A wa.me link that opens a chat with TutorLink, the message already saying who is writing (spec 13 R1.2). */
export function whatsAppLink(number: string, user: UserMe | null): string {
  const name = user?.profile && 'full_name' in user.profile ? user.profile.full_name : null
  const who = user ? `I'm a ${user.role}${name ? `, ${name}` : ''} (${user.email})` : "I'm visiting TutorLink"
  return `https://wa.me/${number}?text=${encodeURIComponent(`Hi TutorLink, ${who}. I need help with: `)}`
}

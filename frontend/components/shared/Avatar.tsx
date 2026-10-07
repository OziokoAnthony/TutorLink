/* eslint-disable @next/next/no-img-element -- photos are short-lived signed links, not static assets */
import { cn } from '@/lib/utils'

const SIZES = { sm: 'h-9 w-9 text-sm', md: 'h-12 w-12 text-base', lg: 'h-20 w-20 text-2xl' }

/** A profile picture, or the person's initials when there isn't one. */
export default function Avatar({ name, photoUrl, size = 'md', className }: {
  name: string | null | undefined
  photoUrl?: string | null
  size?: keyof typeof SIZES
  className?: string
}) {
  const initials = (name || '?').split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
  if (photoUrl) {
    return <img src={photoUrl} alt={name ? `Photo of ${name}` : 'Profile photo'}
      className={cn('shrink-0 rounded-full object-cover', SIZES[size], className)} />
  }
  return (
    <div aria-hidden className={cn('flex shrink-0 items-center justify-center rounded-full bg-accent font-semibold text-accent-foreground',
      SIZES[size], className)}>
      {initials}
    </div>
  )
}

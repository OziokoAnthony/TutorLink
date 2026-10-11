'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import type { Role } from '@/types'

export const LINKS: Record<Role, { href: string; label: string }[]> = {
  parent: [
    { href: '/dashboard/parent', label: 'Overview' },
    { href: '/dashboard/parent/bookings', label: 'My Bookings' },
    { href: '/dashboard/parent/jobs', label: 'My Jobs' },
    { href: '/dashboard/parent/lessons', label: 'Lessons' },
    { href: '/dashboard/parent/wallet', label: 'Payments & Receipts' },
    { href: '/tutors', label: 'Find Tutors' },
    { href: '/dashboard/parent/feedback', label: 'Help & feedback' },
  ],
  tutor: [
    { href: '/dashboard/tutor', label: 'Overview' },
    { href: '/dashboard/tutor/bookings', label: 'Bookings' },
    { href: '/dashboard/tutor/jobs', label: 'Find Jobs' },
    { href: '/dashboard/tutor/lessons', label: 'Lessons' },
    { href: '/dashboard/tutor/earnings', label: 'Earnings & Receipts' },
    { href: '/dashboard/tutor/profile', label: 'Profile & Offers' },
    { href: '/dashboard/tutor/feedback', label: 'Help & feedback' },
  ],
  admin: [
    { href: '/admin/tutors', label: 'Vet Tutors' },
    { href: '/admin/certificates', label: 'Certificates' },
    { href: '/admin/jobs', label: 'Job Posts' },
    { href: '/admin/exam', label: 'Exam' },
    { href: '/admin/payouts', label: 'Tutor Payouts' },
    { href: '/admin/problems', label: 'Problems' },
    { href: '/admin/refunds', label: 'Refunds' },
    { href: '/admin/withdrawals', label: 'Withdrawals' },
    { href: '/admin/fees', label: 'Fees' },
    { href: '/admin/feedback', label: 'Feedback' },
  ],
}

/** Dashboard sidebar; on small screens it becomes a horizontal scrolling tab bar. */
export default function Sidebar({ role }: { role: Role }) {
  const pathname = usePathname()
  return (
    <aside className="md:w-56 md:shrink-0">
      <nav className="flex gap-1 overflow-x-auto pb-2 md:flex-col md:pb-0">
        {LINKS[role].map((link) => {
          const active = pathname === link.href || (link.href.endsWith('/jobs') && pathname.startsWith(link.href + '/'))
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              {link.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

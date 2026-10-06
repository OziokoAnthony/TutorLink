'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import type { Role } from '@/types'

const LINKS: Record<Role, { href: string; label: string }[]> = {
  parent: [
    { href: '/dashboard/parent', label: 'Overview' },
    { href: '/dashboard/parent/schedules', label: 'My Schedules' },
    { href: '/dashboard/parent/sessions', label: 'Sessions' },
    { href: '/dashboard/parent/invoices', label: 'Invoices' },
    { href: '/tutors', label: 'Find Tutors' },
  ],
  tutor: [
    { href: '/dashboard/tutor', label: 'Overview' },
    { href: '/dashboard/tutor/profile', label: 'Profile & Subjects' },
    { href: '/dashboard/tutor/sessions', label: 'Log a Session' },
  ],
  admin: [
    { href: '/admin/tutors', label: 'Vet Tutors' },
    { href: '/admin/invoices', label: 'Generate Invoices' },
  ],
}

/** Dashboard sidebar; on small screens it becomes a horizontal scrolling tab bar. */
export default function Sidebar({ role }: { role: Role }) {
  const pathname = usePathname()
  return (
    <aside className="md:w-56 md:shrink-0">
      <nav className="flex gap-1 overflow-x-auto pb-2 md:flex-col md:pb-0">
        {LINKS[role].map((link) => {
          const active = pathname === link.href
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

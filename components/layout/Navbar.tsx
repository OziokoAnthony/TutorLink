'use client'

import Link from 'next/link'
import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/useAuth'

const DASHBOARD_LINKS = {
  parent: [
    { href: '/dashboard/parent', label: 'Overview' },
    { href: '/dashboard/parent/schedules', label: 'Schedules' },
    { href: '/dashboard/parent/sessions', label: 'Sessions' },
    { href: '/dashboard/parent/invoices', label: 'Invoices' },
  ],
  tutor: [
    { href: '/dashboard/tutor', label: 'Overview' },
    { href: '/dashboard/tutor/profile', label: 'Profile' },
    { href: '/dashboard/tutor/sessions', label: 'Log Session' },
  ],
}

function DashboardMenu({ links }: { links: { href: string; label: string }[] }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">Dashboard <ChevronDown className="ml-1 h-4 w-4" aria-hidden /></Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {links.map((link) => (
          <DropdownMenuItem key={link.href} asChild><Link href={link.href}>{link.label}</Link></DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default function Navbar() {
  const { user, loading, logout } = useAuth()

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="text-lg font-bold tracking-tight text-primary">TutorLink</Link>

        {!loading && (
          <div className="flex items-center gap-1">
            {!user && (
              <>
                <Button variant="ghost" size="sm" asChild><Link href="/tutors">Browse Tutors</Link></Button>
                <Button variant="ghost" size="sm" asChild><Link href="/login">Login</Link></Button>
                <Button size="sm" asChild><Link href="/register">Register</Link></Button>
              </>
            )}
            {user?.role === 'parent' && (
              <>
                <Button variant="ghost" size="sm" asChild><Link href="/tutors">Find Tutors</Link></Button>
                <DashboardMenu links={DASHBOARD_LINKS.parent} />
              </>
            )}
            {user?.role === 'tutor' && <DashboardMenu links={DASHBOARD_LINKS.tutor} />}
            {user?.role === 'admin' && (
              <>
                <Button variant="ghost" size="sm" asChild><Link href="/admin/tutors">Vet Tutors</Link></Button>
                <Button variant="ghost" size="sm" asChild><Link href="/admin/invoices">Invoices</Link></Button>
              </>
            )}
            {user && <Button variant="outline" size="sm" className="ml-2" onClick={logout}>Logout</Button>}
          </div>
        )}
      </nav>
    </header>
  )
}

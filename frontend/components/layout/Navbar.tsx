'use client'

import Link from 'next/link'
import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/useAuth'
import NotificationBell from '@/components/layout/NotificationBell'
import { LINKS } from '@/components/layout/Sidebar'

function DashboardMenu({ links, label = 'Dashboard' }: { links: { href: string; label: string }[]; label?: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm">{label} <ChevronDown className="ml-1 h-4 w-4" aria-hidden /></Button>
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
                <DashboardMenu links={LINKS.parent.filter((l) => l.href !== '/tutors')} />
              </>
            )}
            {user?.role === 'tutor' && <DashboardMenu links={LINKS.tutor} />}
            {user?.role === 'admin' && <DashboardMenu links={LINKS.admin} label="Admin" />}
            {user && <NotificationBell />}
            {user && <Button variant="outline" size="sm" className="ml-2" onClick={logout}>Logout</Button>}
          </div>
        )}
      </nav>
    </header>
  )
}

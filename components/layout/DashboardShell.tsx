import type { ReactNode } from 'react'
import Sidebar from '@/components/layout/Sidebar'
import type { Role } from '@/types'

/** Sidebar + content area shared by the parent, tutor and admin layouts. */
export default function DashboardShell({ role, children }: { role: Role; children: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:flex-row md:py-10">
      <Sidebar role={role} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

'use client'

import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { formatDayOf } from '@/lib/format'

/** Spec 10 R5.2: while a removal notice runs, the person sees when and why, and how to keep their account. */
export default function RemovalNoticeBanner() {
  const { user } = useAuth()
  if (!user?.removal_due_at || user.role === 'admin') return null
  return (
    <div role="alert" className="mb-6 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <p className="font-medium">We plan to close your TutorLink account on {formatDayOf(user.removal_due_at)}.</p>
      {user.removal_reason && <p className="mt-1">Reason: {user.removal_reason}</p>}
      <p className="mt-1">
        Want to keep it?{' '}
        <Link href={`/dashboard/${user.role}/feedback`} className="font-medium underline">
          Reply through Help &amp; feedback
        </Link>{' '}
        before then.
      </p>
    </div>
  )
}

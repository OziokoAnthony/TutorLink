'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import TutorCard from '@/components/tutors/TutorCard'
import TutorFilters from '@/components/tutors/TutorFilters'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage } from '@/lib/api'
import { getTutors } from '@/lib/tutors'
import type { TutorFiltersValue, TutorProfile } from '@/types'

export default function BrowseTutorsPage() {
  const [filters, setFilters] = useState<TutorFiltersValue>({ sort: 'name' })
  const [tutors, setTutors] = useState<TutorProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()
  const isParent = user?.role === 'parent'

  // Post a request with what they searched for, so a tutor who fits can apply (spec 2).
  const search = new URLSearchParams()
  if (filters.subject) search.set('subject', filters.subject)
  if (filters.level) search.set('level', filters.level)
  if (filters.area) search.set('area', filters.area)
  const requestHref = `/dashboard/parent/jobs/new${search.size ? `?${search}` : ''}`

  useEffect(() => {
    let cancelled = false
    // Debounce so typing in "Area" doesn't fire a request per keystroke.
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const result = await getTutors(filters)
        if (!cancelled) { setTutors(result); setError(null) }
      } catch (e) {
        if (!cancelled) setError(errorMessage(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 300)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [filters])

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader title="Find a tutor" description="Every tutor here has been vetted by the TutorLink team." />
      <TutorFilters value={filters} onChange={setFilters} />
      <div className="mt-6">
        {loading ? (
          <LoadingSpinner label="Finding tutors…" />
        ) : error ? (
          <EmptyState message={error} />
        ) : tutors.length === 0 ? (
          <EmptyState
            message={isParent
              ? "No tutor matches your search yet. Post a request and tutors who fit can apply to you."
              : 'No tutors found. Try different filters.'}
            action={isParent && <Button asChild><Link href={requestHref}>Post a request</Link></Button>} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tutors.map((tutor) => <TutorCard key={tutor.id} tutor={tutor} />)}
          </div>
        )}
        {isParent && !loading && !error && tutors.length > 0 && (
          <div className="mt-8 flex flex-col items-center gap-3 rounded-lg border bg-muted/40 px-6 py-6 text-center sm:flex-row sm:justify-between sm:text-left">
            <div>
              <p className="font-medium">Didn&apos;t find the right tutor?</p>
              <p className="text-sm text-muted-foreground">
                Post a request with your subject, times and price. TutorLink checks it, then tutors who fit apply to you.
              </p>
            </div>
            <Button asChild variant="outline" className="shrink-0"><Link href={requestHref}>Post a request</Link></Button>
          </div>
        )}
      </div>
    </div>
  )
}

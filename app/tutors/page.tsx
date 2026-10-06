'use client'

import { useEffect, useState } from 'react'
import TutorCard from '@/components/tutors/TutorCard'
import TutorFilters from '@/components/tutors/TutorFilters'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { errorMessage } from '@/lib/api'
import { getTutors } from '@/lib/tutors'
import type { TutorFiltersValue, TutorProfile } from '@/types'

export default function BrowseTutorsPage() {
  const [filters, setFilters] = useState<TutorFiltersValue>({ sort: 'name' })
  const [tutors, setTutors] = useState<TutorProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
          <EmptyState message="No tutors found. Try different filters." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tutors.map((tutor) => <TutorCard key={tutor.id} tutor={tutor} />)}
          </div>
        )}
      </div>
    </div>
  )
}

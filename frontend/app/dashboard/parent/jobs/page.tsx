'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import JobSummary from '@/components/jobs/JobSummary'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getMyJobs } from '@/lib/jobs'
import type { Job } from '@/types'

export default function ParentJobsPage() {
  const toast = useToast()
  const [jobs, setJobs] = useState<Job[] | null>(null)

  useEffect(() => {
    getMyJobs().then(setJobs).catch((e) => { toast.error(errorMessage(e)); setJobs([]) })
  }, [toast])

  if (!jobs) return <LoadingSpinner />
  const current = jobs.filter((j) => j.status === 'open' || j.status === 'ongoing')
  const past = jobs.filter((j) => !current.includes(j))
  const post = <Button asChild><Link href="/dashboard/parent/jobs/new">Post a job</Link></Button>

  return (
    <>
      <PageHeader title="My Jobs" description="Describe what your child needs and the price you'll pay. Tutors apply, and you choose one."
        action={post} />
      {current.length === 0 ? <EmptyState message="You have no open jobs." action={post} /> : (
        <div className="space-y-4">
          {current.map((j) => (
            <JobSummary key={j.id} job={j} href={`/dashboard/parent/jobs/${j.id}`} actions={(
              <Button size="sm" variant="outline" asChild>
                <Link href={`/dashboard/parent/jobs/${j.id}`}>
                  {j.status === 'open' ? `See applicants (${j.applicant_count ?? 0})` : 'View'}
                </Link>
              </Button>
            )} />
          ))}
        </div>
      )}
      {past.length > 0 && (
        <details className="mt-8">
          <summary className="cursor-pointer text-sm font-medium text-muted-foreground">Past ({past.length})</summary>
          <div className="mt-4 space-y-4">
            {past.map((j) => <JobSummary key={j.id} job={j} href={`/dashboard/parent/jobs/${j.id}`} />)}
          </div>
        </details>
      )}
    </>
  )
}

'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import JobSummary from '@/components/jobs/JobSummary'
import TutorJobActions from '@/components/jobs/TutorJobActions'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { errorMessage } from '@/lib/api'
import { getJob } from '@/lib/jobs'
import type { Job } from '@/types'
import { useParams } from 'next/navigation'

export default function TutorJobPage() {
  const params = useParams<{ id: string }>()
  const [job, setJob] = useState<Job | null>(null)
  const [problem, setProblem] = useState<string | null>(null)

  useEffect(() => {
    getJob(params.id).then(setJob).catch((e) => setProblem(errorMessage(e)))
  }, [params.id])

  const back = <Button variant="outline" asChild><Link href="/dashboard/tutor/jobs">All jobs</Link></Button>
  if (problem) return <><PageHeader title="Job" action={back} /><EmptyState message={problem} /></>
  if (!job) return <LoadingSpinner />
  return (
    <>
      <PageHeader title="Job" description="The parent sees your profile, reviews and note when you apply." action={back} />
      <JobSummary job={job} full actions={<TutorJobActions job={job} onChange={setJob} />} />
    </>
  )
}

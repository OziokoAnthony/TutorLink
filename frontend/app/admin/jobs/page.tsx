'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import JobSummary from '@/components/jobs/JobSummary'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { getAdminJobs, reviewJob } from '@/lib/jobs'
import type { Job } from '@/types'

/** Spec 2 R1.4: every new or edited job waits here until an admin approves it, or rejects it with a note. */
export default function AdminJobsPage() {
  const toast = useToast()
  const [pendingOnly, setPendingOnly] = useState(true)
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [reviewing, setReviewing] = useState<{ job: Job; approve: boolean } | null>(null)

  const load = useCallback(() => {
    setJobs(null)
    getAdminJobs(pendingOnly ? 'pending' : undefined)
      .then(setJobs).catch((e) => { toast.error(errorMessage(e)); setJobs([]) })
  }, [pendingOnly, toast])
  useEffect(load, [load])

  async function review(job: Job, approve: boolean, note: string) {
    try {
      const updated = await reviewJob(job.id, approve ? 'open' : 'rejected', note)
      toast.success(approve ? 'Job approved. Tutors can now see it.' : 'Job rejected. The parent has been told why.')
      setJobs((list) => list && (pendingOnly ? list.filter((j) => j.id !== job.id)
        : list.map((j) => j.id === job.id ? updated : j)))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Job posts"
        description="Check each job before tutors see it: no contact details, nothing unsafe or misleading, and a sensible price. Edited jobs come back here too." />
      <Tabs value={pendingOnly ? 'pending' : 'all'} onValueChange={(v) => setPendingOnly(v === 'pending')} className="mb-4">
        <TabsList>
          <TabsTrigger value="pending">Waiting</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {jobs === null ? <LoadingSpinner /> : jobs.length === 0 ? (
        <EmptyState message={pendingOnly ? 'No jobs waiting for review.' : 'No jobs yet.'} />
      ) : (
        <div className="space-y-4">
          {jobs.map((j) => (
            <div key={j.id} className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Posted by <span className="font-medium text-foreground">{j.parent_name ?? 'a parent'}</span>
                {j.updated_at && <> • last changed {formatDateTime(j.updated_at)}</>}
                {j.review_note && <> • rejected: {j.review_note}</>}
              </p>
              <JobSummary job={j} full actions={j.status === 'pending' && (
                <>
                  <Button size="sm" className="bg-emerald-600 text-white hover:bg-emerald-700"
                    onClick={() => setReviewing({ job: j, approve: true })}>Approve</Button>
                  <Button size="sm" variant="destructive" onClick={() => setReviewing({ job: j, approve: false })}>Reject</Button>
                </>
              )} />
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={reviewing?.approve === true}
        onOpenChange={(open) => { if (!open) setReviewing(null) }}
        title="Approve this job?"
        description="Approved tutors will see it and can apply. The parent is told it is live."
        confirmLabel="Approve"
        onConfirm={() => reviewing ? review(reviewing.job, true, '') : undefined}
      />
      <NoteDialog
        open={reviewing?.approve === false}
        onOpenChange={(open) => { if (!open) setReviewing(null) }}
        title="Reject this job?"
        description="The parent sees your note and can edit the job to send it back for review."
        confirmLabel="Reject"
        destructive
        noteLabel="Why it is rejected"
        noteRequired
        onConfirm={(note) => reviewing ? review(reviewing.job, false, note) : undefined}
      />
    </>
  )
}

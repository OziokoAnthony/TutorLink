'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import JobForm from '@/components/jobs/JobForm'
import JobSummary from '@/components/jobs/JobSummary'
import { RatingSummary } from '@/components/reviews/StarRating'
import Avatar from '@/components/shared/Avatar'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { ApplicationStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { chooseApplicant, closeJob, getApplicants, getJob, updateJob } from '@/lib/jobs'
import type { Applicant, Job, JobInput } from '@/types'

export default function ParentJobPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const toast = useToast()
  const [job, setJob] = useState<Job | null>(null)
  const [applicants, setApplicants] = useState<Applicant[] | null>(null)
  const [editing, setEditing] = useState(false)
  const [closing, setClosing] = useState(false)
  const [choosing, setChoosing] = useState<Applicant | null>(null)

  const load = useCallback(() => {
    Promise.all([getJob(params.id), getApplicants(params.id)])
      .then(([j, a]) => { setJob(j); setApplicants(a) })
      .catch((e) => toast.error(errorMessage(e)))
  }, [params.id, toast])
  useEffect(load, [load])

  async function save(input: JobInput) {
    try {
      setJob(await updateJob(params.id, input))
      toast.success("Job updated. We'll check the changes before tutors see it again.")
      setEditing(false)
      load()
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  async function close() {
    try {
      setJob(await closeJob(params.id))
      toast.success('Job closed')
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  async function choose() {
    if (!choosing) return
    try {
      await chooseApplicant(params.id, choosing.id)
      toast.success(`${choosing.tutor_name ?? 'The tutor'} is booked. Pay before the first lesson to confirm it.`)
      router.push('/dashboard/parent/wallet')
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  if (!job || !applicants) return <LoadingSpinner />
  const open = job.status === 'open'
  // Editable and closable until a tutor is chosen; an edit goes back for review.
  const editable = open || job.status === 'pending' || job.status === 'rejected'

  return (
    <>
      <PageHeader title="Your job" description={open ? 'Tutors can apply until you choose one or close the job.' : undefined}
        action={<Button variant="outline" asChild><Link href="/dashboard/parent/jobs">All my jobs</Link></Button>} />
      <div className="space-y-6">
        {job.status === 'pending' && (
          <p className="rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-900">
            TutorLink is checking your job. Tutors will see it once it&apos;s approved, and we&apos;ll let you know.
          </p>
        )}
        {job.status === 'rejected' && (
          <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <p className="font-medium">Your job wasn&apos;t approved.</p>
            {job.review_note && <p className="mt-1">Reason: {job.review_note}</p>}
            <p className="mt-1">Edit it to fix the problem and it will be checked again.</p>
          </div>
        )}
        {editing ? (
          <Card><CardContent className="pt-6">
            <JobForm initial={job} submitLabel="Save changes" onSubmit={save} onCancel={() => setEditing(false)} />
          </CardContent></Card>
        ) : (
          <JobSummary job={job} full actions={editable && (
            <>
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>Edit</Button>
              <Button size="sm" variant="outline" onClick={() => setClosing(true)}>Close job</Button>
            </>
          )} />
        )}

        {job.booking_id && (
          <p className="rounded-md bg-accent px-4 py-3 text-sm">
            You chose a tutor for this job. <Link href="/dashboard/parent/bookings" className="font-medium underline">See the booking</Link>
          </p>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Applicants</CardTitle>
            <CardDescription>Open a tutor&apos;s profile to see their reviews and offers, then choose the one you want.</CardDescription>
          </CardHeader>
          <CardContent>
            {applicants.length === 0 ? <EmptyState message="No applicants yet. You'll be notified when a tutor applies." /> : (
              <ul className="divide-y">
                {applicants.map((a) => (
                  <li key={a.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
                    <div className="flex gap-3">
                      <Avatar name={a.tutor_name} photoUrl={a.tutor_photo_url} />
                      <div className="space-y-1">
                        <p className="font-medium">{a.tutor_name}</p>
                        <RatingSummary average={a.average_rating} count={a.rating_count} />
                        {a.note && <p className="text-sm text-muted-foreground">&ldquo;{a.note}&rdquo;</p>}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <ApplicationStatusBadge status={a.status} />
                      <Button size="sm" variant="outline" asChild><Link href={`/tutors/${a.tutor_id}`}>View profile</Link></Button>
                      {open && a.status === 'applied' && <Button size="sm" onClick={() => setChoosing(a)}>Choose</Button>}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog open={closing} onOpenChange={setClosing} title="Close this job?"
        description="Tutors will no longer see it or be able to apply." confirmLabel="Close job" destructive onConfirm={close} />
      <ConfirmDialog open={!!choosing} onOpenChange={(o) => !o && setChoosing(null)}
        title={`Choose ${choosing?.tutor_name ?? 'this tutor'}?`}
        description="They're booked at once for your job's times and price. You'll then pay before the first lesson, by bank transfer to your TutorLink account number."
        confirmLabel="Choose and book" onConfirm={choose} />
    </>
  )
}

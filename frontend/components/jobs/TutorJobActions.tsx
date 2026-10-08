'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import NoteDialog from '@/components/shared/NoteDialog'
import { ApplicationStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { applyToJob, withdrawFromJob } from '@/lib/jobs'
import type { Job } from '@/types'

/** Apply (with an optional note) or withdraw, and the tutor's application status. */
export default function TutorJobActions({ job, onChange }: { job: Job; onChange: (job: Job) => void }) {
  const toast = useToast()
  const [applying, setApplying] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const mine = job.my_application

  async function apply(note: string) {
    try {
      onChange(await applyToJob(job.id, note))
      toast.success("Applied! The parent will be told, and you'll hear if they choose you.")
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  async function withdraw() {
    try {
      onChange(await withdrawFromJob(job.id))
      toast.success('Application withdrawn')
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  return (
    <>
      {mine && <ApplicationStatusBadge status={mine.status} />}
      {mine?.withdrawn_reason && <span className="self-center text-xs text-muted-foreground">{mine.withdrawn_reason}</span>}
      {!mine && job.status === 'open' && <Button size="sm" onClick={() => setApplying(true)}>Apply</Button>}
      {mine?.status === 'applied' && job.status === 'open' && (
        <Button size="sm" variant="outline" onClick={() => setWithdrawing(true)}>Withdraw</Button>
      )}
      <NoteDialog open={applying} onOpenChange={setApplying} title="Apply to this job"
        description="The parent sees your profile, reviews and this note. You can apply once per job."
        noteLabel="Note to the parent (optional)" confirmLabel="Apply" onConfirm={apply} />
      <ConfirmDialog open={withdrawing} onOpenChange={setWithdrawing} title="Withdraw your application?"
        description="The parent won't be able to choose you for this job, and you can't apply to it again."
        confirmLabel="Withdraw" destructive onConfirm={withdraw} />
    </>
  )
}

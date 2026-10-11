'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import JobForm from '@/components/jobs/JobForm'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { postJob } from '@/lib/jobs'
import type { JobInput } from '@/types'

export default function NewJobPage() {
  const router = useRouter()
  const toast = useToast()
  const { user } = useAuth()

  async function submit(input: JobInput) {
    try {
      const job = await postJob(input)
      toast.success("Job posted! We'll check it and let you know when tutors can see it.")
      router.push(`/dashboard/parent/jobs/${job.id}`)
    } catch (error) {
      toast.error(errorMessage(error))
      throw error
    }
  }

  if (!user) return <LoadingSpinner />
  return (
    <>
      <PageHeader title="Post a job" description="Tutors see your first name, picture and area, never your contact details." />
      {!user.photo_url ? (
        <EmptyState message="Tutors see your picture on your job posts. Add one first."
          action={<Button asChild><Link href="/dashboard/parent">Add my picture</Link></Button>} />
      ) : (
        <Card><CardContent className="pt-6">
          <JobForm submitLabel="Post job" onSubmit={submit} onCancel={() => router.push('/dashboard/parent/jobs')} />
        </CardContent></Card>
      )}
    </>
  )
}

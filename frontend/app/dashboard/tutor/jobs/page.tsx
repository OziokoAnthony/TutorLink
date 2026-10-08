'use client'

import { useCallback, useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import JobSummary from '@/components/jobs/JobSummary'
import TutorJobActions from '@/components/jobs/TutorJobActions'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { LEVELS, SUBJECTS } from '@/lib/format'
import { browseJobs, getMyApplications } from '@/lib/jobs'
import type { Job, JobFiltersValue, LessonMode, Level } from '@/types'

const ANY = 'any'

export default function TutorJobsPage() {
  const toast = useToast()
  const [tab, setTab] = useState<'browse' | 'mine'>('browse')
  const [filters, setFilters] = useState<JobFiltersValue>({})
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [notApproved, setNotApproved] = useState(false)

  const load = useCallback(() => {
    setJobs(null)
    const request = tab === 'browse' ? browseJobs(filters) : getMyApplications()
    request.then(setJobs).catch((e) => {
      if (errorStatus(e) === 403) setNotApproved(true)
      else toast.error(errorMessage(e))
      setJobs([])
    })
  }, [tab, filters, toast])
  useEffect(() => {
    const timer = setTimeout(load, 300) // wait for typing in the area box to pause
    return () => clearTimeout(timer)
  }, [load])

  const replace = (job: Job) => setJobs((list) => list?.map((j) => (j.id === job.id ? job : j)) ?? null)

  if (notApproved) {
    return (
      <>
        <PageHeader title="Find Jobs" />
        <EmptyState message="Jobs open up once your profile is approved. We'll email you when it is." />
      </>
    )
  }

  return (
    <>
      <PageHeader title="Find Jobs" description="Parents' jobs with their price per lesson. You see what you'd earn after TutorLink's fee." />
      <Tabs value={tab} onValueChange={(v) => setTab(v as 'browse' | 'mine')} className="mb-4">
        <TabsList>
          <TabsTrigger value="browse">Open jobs</TabsTrigger>
          <TabsTrigger value="mine">My applications</TabsTrigger>
        </TabsList>
      </Tabs>

      {tab === 'browse' && (
        <div className="mb-6 grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5">
            <Label htmlFor="jobs-subject">Subject</Label>
            <Select value={filters.subject ?? ANY} onValueChange={(v) => setFilters({ ...filters, subject: v === ANY ? undefined : v })}>
              <SelectTrigger id="jobs-subject"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>All subjects</SelectItem>
                {SUBJECTS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="jobs-level">Level</Label>
            <Select value={filters.level ?? ANY} onValueChange={(v) => setFilters({ ...filters, level: v === ANY ? undefined : (v as Level) })}>
              <SelectTrigger id="jobs-level"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>All levels</SelectItem>
                {LEVELS.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="jobs-mode">Lessons</Label>
            <Select value={filters.mode ?? ANY} onValueChange={(v) => setFilters({ ...filters, mode: v === ANY ? undefined : (v as LessonMode) })}>
              <SelectTrigger id="jobs-mode"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Online or at home</SelectItem>
                <SelectItem value="offline">At home</SelectItem>
                <SelectItem value="online">Online</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="jobs-area">Area</Label>
            <Input id="jobs-area" placeholder="e.g. Lekki" value={filters.area ?? ''}
              onChange={(e) => setFilters({ ...filters, area: e.target.value || undefined })} />
          </div>
        </div>
      )}

      {!jobs ? <LoadingSpinner /> : jobs.length === 0 ? (
        <EmptyState message={tab === 'browse' ? 'No open jobs match. Try fewer filters.' : "You haven't applied to any jobs yet."} />
      ) : (
        <div className="space-y-4">
          {jobs.map((j) => (
            <JobSummary key={j.id} job={j} href={`/dashboard/tutor/jobs/${j.id}`}
              actions={<TutorJobActions job={j} onChange={replace} />} />
          ))}
        </div>
      )}
    </>
  )
}

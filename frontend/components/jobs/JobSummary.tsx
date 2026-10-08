import type { ReactNode } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import Avatar from '@/components/shared/Avatar'
import { JobStatusBadge } from '@/components/shared/StatusBadge'
import { BILLING_PERIODS, formatDate, formatNaira, formatPercent, levelLabel, slotText } from '@/lib/format'
import type { Job } from '@/types'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[10rem_1fr]">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

/** A job's details. Money rows show only what the response carries for this reader (spec 1 R1). */
export default function JobSummary({ job, href, actions, full = false }: {
  job: Job
  href?: string
  actions?: ReactNode
  full?: boolean
}) {
  const title = `${job.subjects.join(', ')} • ${levelLabel(job.level)}`
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="flex items-center gap-3">
          {job.parent_first_name && <Avatar name={job.parent_first_name} photoUrl={job.parent_photo_url} size="sm" />}
          <div>
            <CardTitle className="text-base">{href ? <Link href={href} className="hover:underline">{title}</Link> : title}</CardTitle>
            <p className="text-xs text-muted-foreground">
              {job.parent_first_name ? `${job.parent_first_name} • ` : ''}
              {job.mode === 'online' ? 'Online' : `At home in ${job.area}`}
            </p>
          </div>
        </div>
        <JobStatusBadge status={job.status} />
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="space-y-2">
          <Row label="Price per lesson">
            {formatNaira(job.price)}
            {job.parent_price_per_lesson !== undefined && (
              <span className="text-muted-foreground"> • you pay {formatNaira(job.parent_price_per_lesson)} with TutorLink&apos;s fee</span>
            )}
            {job.tutor_earning_per_lesson !== undefined && job.tutor_fee_rate !== undefined && (
              <span className="text-muted-foreground"> • you earn {formatNaira(job.tutor_earning_per_lesson)} after TutorLink&apos;s {formatPercent(job.tutor_fee_rate)} fee</span>
            )}
          </Row>
          <Row label="Weekly times">{job.slots.map(slotText).join('; ')}</Row>
          <Row label="Dates">
            From {formatDate(job.start_date)}{job.end_date ? ` to ${formatDate(job.end_date)}` : ', no end date'}
            {' • '}{BILLING_PERIODS.find((b) => b.value === job.billing_period)?.label} payments
          </Row>
          {full && (
            <>
              <Row label="Qualifications">
                {job.qualifications}
                {job.min_certificate && <span className="text-muted-foreground"> • at least {job.min_certificate}</span>}
              </Row>
              {job.other_requirements && <Row label="Other requirements">{job.other_requirements}</Row>}
              <Row label="Child's strengths">{job.child_strengths}</Row>
              <Row label="Finds hard">{job.child_weaknesses}</Row>
            </>
          )}
        </dl>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </CardContent>
    </Card>
  )
}

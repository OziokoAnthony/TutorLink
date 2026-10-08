import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  APPLICATION_STATUS_LABEL, BOOKING_STATUS_LABEL, CERTIFICATE_STATUS_LABEL, JOB_STATUS_LABEL, EARNING_STATUS_LABEL, LESSON_STATUS_LABEL, PERIOD_STATUS_LABEL, REFUND_STATUS_LABEL,
  TRANSFER_STATUS_LABEL, VETTING_STATUS_LABEL,
} from '@/lib/format'
import type {
  ApplicationStatus, BookingStatus, CertificateStatus, JobStatus, EarningStatus, LessonStatus, PeriodStatus, RefundStatus, TransferStatus, VettingStatus,
} from '@/types'

type Tone = 'yellow' | 'green' | 'red' | 'blue' | 'gray'

const TONE_CLASS: Record<Tone, string> = {
  yellow: 'border-amber-300 bg-amber-100 text-amber-900',
  green: 'border-emerald-300 bg-emerald-100 text-emerald-900',
  red: 'border-red-300 bg-red-100 text-red-900',
  blue: 'border-sky-300 bg-sky-100 text-sky-900',
  gray: 'border-zinc-300 bg-zinc-100 text-zinc-700',
}

const BOOKING_TONE: Record<BookingStatus, Tone> = {
  requested: 'blue', accepted: 'yellow', active: 'green', paused: 'red', ended: 'gray', declined: 'gray',
  expired: 'gray', released: 'gray', cancelled: 'gray',
}
const PERIOD_TONE: Record<PeriodStatus, Tone> = { due: 'yellow', paid: 'green', missed: 'red', expired: 'gray', void: 'gray' }
const LESSON_TONE: Record<LessonStatus, Tone> = {
  confirmed: 'blue', reported: 'blue', completed: 'green', disputed: 'yellow', flagged: 'red', refunded: 'gray',
  cancelled: 'gray',
}
const EARNING_TONE: Record<EarningStatus, Tone> = { pending: 'gray', on_hold: 'yellow', payable: 'blue', paid: 'green', void: 'gray' }
const TRANSFER_TONE: Record<TransferStatus, Tone> = { pending: 'yellow', processing: 'blue', paid: 'green', failed: 'red', rejected: 'gray' }
const REFUND_TONE: Record<RefundStatus, Tone> = { pending: 'yellow', approved: 'green', rejected: 'gray' }
const JOB_TONE: Record<JobStatus, Tone> = { open: 'blue', ongoing: 'yellow', completed: 'green', closed: 'gray' }
const APPLICATION_TONE: Record<ApplicationStatus, Tone> = { applied: 'blue', withdrawn: 'gray', chosen: 'green' }
const VETTING_TONE: Record<VettingStatus, Tone> = { pending: 'yellow', approved: 'green', rejected: 'red' }
const CERTIFICATE_TONE: Record<CertificateStatus, Tone> = { pending: 'yellow', verified: 'green', rejected: 'red' }

function ToneBadge({ tone, children }: { tone: Tone; children: string }) {
  return <Badge variant="outline" className={cn('font-medium', TONE_CLASS[tone])}>{children}</Badge>
}

export function BookingStatusBadge({ status }: { status: BookingStatus }) {
  return <ToneBadge tone={BOOKING_TONE[status]}>{BOOKING_STATUS_LABEL[status]}</ToneBadge>
}

export function PeriodStatusBadge({ status }: { status: PeriodStatus }) {
  return <ToneBadge tone={PERIOD_TONE[status]}>{PERIOD_STATUS_LABEL[status]}</ToneBadge>
}

export function LessonStatusBadge({ status }: { status: LessonStatus }) {
  return <ToneBadge tone={LESSON_TONE[status]}>{LESSON_STATUS_LABEL[status]}</ToneBadge>
}

export function EarningStatusBadge({ status }: { status: EarningStatus }) {
  return <ToneBadge tone={EARNING_TONE[status]}>{EARNING_STATUS_LABEL[status]}</ToneBadge>
}

export function TransferStatusBadge({ status }: { status: TransferStatus }) {
  return <ToneBadge tone={TRANSFER_TONE[status]}>{TRANSFER_STATUS_LABEL[status]}</ToneBadge>
}

export function RefundStatusBadge({ status }: { status: RefundStatus }) {
  return <ToneBadge tone={REFUND_TONE[status]}>{REFUND_STATUS_LABEL[status]}</ToneBadge>
}

export function VettingStatusBadge({ status }: { status: VettingStatus }) {
  return <ToneBadge tone={VETTING_TONE[status]}>{VETTING_STATUS_LABEL[status]}</ToneBadge>
}

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <ToneBadge tone={JOB_TONE[status]}>{JOB_STATUS_LABEL[status]}</ToneBadge>
}

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  return <ToneBadge tone={APPLICATION_TONE[status]}>{APPLICATION_STATUS_LABEL[status]}</ToneBadge>
}

export function CertificateStatusBadge({ status }: { status: CertificateStatus }) {
  return <ToneBadge tone={CERTIFICATE_TONE[status]}>{CERTIFICATE_STATUS_LABEL[status]}</ToneBadge>
}

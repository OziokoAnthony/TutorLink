import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { INVOICE_STATUS_LABEL, SESSION_STATUS_LABEL, VETTING_STATUS_LABEL } from '@/lib/format'
import type { InvoiceStatus, SessionStatus, VettingStatus } from '@/types'

type Tone = 'yellow' | 'green' | 'red' | 'blue' | 'gray'

const TONE_CLASS: Record<Tone, string> = {
  yellow: 'border-amber-300 bg-amber-100 text-amber-900',
  green: 'border-emerald-300 bg-emerald-100 text-emerald-900',
  red: 'border-red-300 bg-red-100 text-red-900',
  blue: 'border-sky-300 bg-sky-100 text-sky-900',
  gray: 'border-zinc-300 bg-zinc-100 text-zinc-700',
}

const SESSION_TONE: Record<SessionStatus, Tone> = { scheduled: 'gray', logged: 'blue', confirmed: 'green', cancelled: 'gray' }
// CLAUDE.md: Pending (yellow), Paid (green), Failed (red)
const INVOICE_TONE: Record<InvoiceStatus, Tone> = { pending: 'yellow', paid: 'green', failed: 'red' }
const VETTING_TONE: Record<VettingStatus, Tone> = { pending: 'yellow', approved: 'green', rejected: 'red' }

function ToneBadge({ tone, children }: { tone: Tone; children: string }) {
  return <Badge variant="outline" className={cn('font-medium', TONE_CLASS[tone])}>{children}</Badge>
}

export function SessionStatusBadge({ status }: { status: SessionStatus }) {
  return <ToneBadge tone={SESSION_TONE[status]}>{SESSION_STATUS_LABEL[status]}</ToneBadge>
}

export function InvoiceStatusBadge({ status }: { status: InvoiceStatus }) {
  return <ToneBadge tone={INVOICE_TONE[status]}>{INVOICE_STATUS_LABEL[status]}</ToneBadge>
}

export function VettingStatusBadge({ status }: { status: VettingStatus }) {
  return <ToneBadge tone={VETTING_TONE[status]}>{VETTING_STATUS_LABEL[status]}</ToneBadge>
}

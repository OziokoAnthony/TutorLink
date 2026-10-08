'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Receipt } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { TransferStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime, formatNaira } from '@/lib/format'
import { createPayout, getPayouts, getPayoutsDue, overrideBankAccount } from '@/lib/payouts'
import { cn } from '@/lib/utils'
import type { Payout, PayoutDue } from '@/types'

type Action = { kind: 'send' | 'manual' | 'override'; due: PayoutDue }

export default function AdminPayoutsPage() {
  const toast = useToast()
  const [due, setDue] = useState<PayoutDue[] | null>(null)
  const [history, setHistory] = useState<Payout[]>([])
  const [action, setAction] = useState<Action | null>(null)

  const load = useCallback(() => {
    getPayoutsDue().then(setDue).catch((e) => { toast.error(errorMessage(e)); setDue([]) })
    getPayouts().then(setHistory).catch(() => undefined)
  }, [toast])
  useEffect(load, [load])

  async function pay(d: PayoutDue, method: Payout['method'], note?: string) {
    try {
      const payout = await createPayout(d.tutor_id, method, note)
      toast.success(method === 'paystack'
        ? `Sending ${formatNaira(payout.amount)} to ${d.tutor_name}. The result arrives from Paystack shortly.`
        : `${formatNaira(payout.amount)} marked as paid to ${d.tutor_name}`)
      load()
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  async function override(d: PayoutDue, note: string) {
    try {
      await overrideBankAccount(d.tutor_id, note)
      toast.success(`${d.tutor_name}'s bank account approved for payouts`)
      load()
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  if (due === null) return <LoadingSpinner />

  return (
    <>
      <PageHeader title="Tutor payouts" description="Tutors are due 48 hours after the last lesson of each billing period. Earnings under review aren't included." />

      {due.length === 0 ? <EmptyState message="No tutor is waiting to be paid." /> : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tutor</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Due by</TableHead>
                <TableHead className="min-w-[200px]">Bank account</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {due.map((d) => {
                const bank = d.bank_account
                const needsOverride = bank !== null && !bank.name_matches && !bank.override_note
                return (
                  <TableRow key={d.tutor_id} className={cn(d.overdue && 'bg-red-50')}>
                    <TableCell className="font-medium">{d.tutor_name}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      <span className="font-semibold tabular-nums">{formatNaira(d.amount)}</span>
                      <span className="block text-xs text-muted-foreground">{d.lesson_count} lesson(s)</span>
                    </TableCell>
                    <TableCell className={cn('whitespace-nowrap', d.overdue && 'font-semibold text-red-700')}>
                      {formatDateTime(d.due_at)}{d.overdue && <span className="block text-xs">Overdue</span>}
                    </TableCell>
                    <TableCell className="text-sm">
                      {bank === null ? <span className="text-amber-700">No bank details yet</span> : (
                        <>
                          <p>{bank.bank_name} {bank.account_number}</p>
                          <p className="text-muted-foreground">{bank.account_name}</p>
                          {needsOverride && <p className="text-amber-700">Name doesn&apos;t match the tutor&apos;s</p>}
                          {bank.override_note && <p className="text-xs text-muted-foreground">Approved: {bank.override_note}</p>}
                        </>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap justify-end gap-2">
                        {needsOverride && (
                          <Button size="sm" variant="outline" onClick={() => setAction({ kind: 'override', due: d })}>Approve account</Button>
                        )}
                        <Button size="sm" disabled={!d.can_send} onClick={() => setAction({ kind: 'send', due: d })}>Send via Paystack</Button>
                        <Button size="sm" variant="outline" onClick={() => setAction({ kind: 'manual', due: d })}>Mark as paid</Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-lg">Payout history</CardTitle></CardHeader>
        <CardContent>
          {history.length === 0 ? <EmptyState message="No payouts yet." /> : (
            <ul className="divide-y text-sm">
              {history.map((p) => (
                <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <span>
                    <span className="font-medium">{p.tutor_name}</span> • {formatNaira(p.amount)} for {p.lesson_count} lesson(s) •{' '}
                    {p.method === 'paystack' ? 'Paystack' : 'Paid outside the app'} • {formatDateTime(p.paid_at ?? p.created_at)}
                    {p.note && <span className="block text-xs text-muted-foreground">{p.note}</span>}
                  </span>
                  <span className="flex items-center gap-2">
                    <TransferStatusBadge status={p.status} />
                    {p.status !== 'failed' && (
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/receipts/payouts/${p.id}`}><Receipt className="mr-1 h-4 w-4" aria-hidden />Receipt</Link>
                      </Button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={action?.kind === 'send'}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Send ${action ? formatNaira(action.due.amount) : ''} to ${action?.due.tutor_name ?? ''}?`}
        description={`Paystack transfers the money to ${action?.due.bank_account?.bank_name ?? ''} ${action?.due.bank_account?.account_number ?? ''}. If the transfer fails, the earnings become payable again.`}
        confirmLabel="Send"
        onConfirm={() => action ? pay(action.due, 'paystack') : undefined}
      />
      <NoteDialog
        open={action?.kind === 'manual'}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Mark ${action ? formatNaira(action.due.amount) : ''} as paid to ${action?.due.tutor_name ?? ''}?`}
        description="Use this when you paid the tutor outside the app. Their earnings are marked paid and they get a receipt."
        confirmLabel="Mark as paid"
        noteLabel="Transfer reference"
        noteRequired
        onConfirm={(note) => action ? pay(action.due, 'manual', note) : undefined}
      />
      <NoteDialog
        open={action?.kind === 'override'}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Approve ${action?.due.tutor_name ?? ''}'s bank account?`}
        description={`The account name "${action?.due.bank_account?.account_name ?? ''}" doesn't match the tutor's name. Approve it only if you've checked it belongs to them.`}
        confirmLabel="Approve account"
        noteLabel="How you checked it"
        noteRequired
        onConfirm={(note) => action ? override(action.due, note) : undefined}
      />
    </>
  )
}

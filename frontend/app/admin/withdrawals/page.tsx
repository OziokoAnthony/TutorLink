'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { TransferStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime, formatNaira } from '@/lib/format'
import { getAllWithdrawals, processWithdrawal } from '@/lib/wallet'
import type { Withdrawal } from '@/types'

type Action = { kind: 'send' | 'mark-paid' | 'reject'; withdrawal: Withdrawal }

export default function AdminWithdrawalsPage() {
  const toast = useToast()
  const [pendingOnly, setPendingOnly] = useState(true)
  const [withdrawals, setWithdrawals] = useState<Withdrawal[] | null>(null)
  const [action, setAction] = useState<Action | null>(null)

  const load = useCallback(() => {
    setWithdrawals(null)
    getAllWithdrawals(pendingOnly ? 'pending' : undefined)
      .then(setWithdrawals).catch((e) => { toast.error(errorMessage(e)); setWithdrawals([]) })
  }, [pendingOnly, toast])
  useEffect(load, [load])

  async function process(w: Withdrawal, kind: Action['kind'], note?: string) {
    try {
      const updated = await processWithdrawal(w.id, kind, note)
      toast.success(kind === 'send' ? `Sending ${formatNaira(w.amount)} to ${w.parent_name}`
        : kind === 'mark-paid' ? 'Withdrawal marked as paid'
        : `Withdrawal rejected; ${formatNaira(w.amount)} is back in ${w.parent_name}'s balance`)
      setWithdrawals((list) => list && (pendingOnly ? list.filter((x) => x.id !== w.id) : list.map((x) => x.id === w.id ? updated : x)))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  const w = action?.withdrawal
  return (
    <>
      <PageHeader title="Parent withdrawals" description="Parents asking for their TutorLink balance back. The amount has already been taken from their balance; rejecting puts it back." />
      <Tabs value={pendingOnly ? 'pending' : 'all'} onValueChange={(v) => setPendingOnly(v === 'pending')} className="mb-4">
        <TabsList>
          <TabsTrigger value="pending">Waiting</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {withdrawals === null ? <LoadingSpinner /> : withdrawals.length === 0 ? (
        <EmptyState message={pendingOnly ? 'No withdrawals waiting.' : 'No withdrawals yet.'} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Parent</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead className="min-w-[180px]">To</TableHead>
                <TableHead>Requested</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {withdrawals.map((x) => (
                <TableRow key={x.id}>
                  <TableCell className="font-medium">{x.parent_name}</TableCell>
                  <TableCell className="whitespace-nowrap font-semibold tabular-nums">{formatNaira(x.amount)}</TableCell>
                  <TableCell className="text-sm">
                    <p>{x.bank_name} {x.account_number}</p>
                    <p className="text-muted-foreground">{x.account_name}</p>
                    {x.note && <p className="text-xs text-muted-foreground">{x.note}</p>}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-sm">{formatDateTime(x.created_at)}</TableCell>
                  <TableCell><TransferStatusBadge status={x.status} /></TableCell>
                  <TableCell>
                    {x.status === 'pending' && (
                      <div className="flex flex-wrap justify-end gap-2">
                        <Button size="sm" onClick={() => setAction({ kind: 'send', withdrawal: x })}>Send via Paystack</Button>
                        <Button size="sm" variant="outline" onClick={() => setAction({ kind: 'mark-paid', withdrawal: x })}>Mark as paid</Button>
                        <Button size="sm" variant="ghost" onClick={() => setAction({ kind: 'reject', withdrawal: x })}>Reject</Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ConfirmDialog
        open={action?.kind === 'send'}
        onOpenChange={(open) => !open && setAction(null)}
        title={`Send ${w ? formatNaira(w.amount) : ''} to ${w?.parent_name ?? ''}?`}
        description={`Paystack transfers the money to ${w?.bank_name ?? ''} ${w?.account_number ?? ''} (${w?.account_name ?? ''}).`}
        confirmLabel="Send"
        onConfirm={() => w ? process(w, 'send') : undefined}
      />
      <NoteDialog
        open={action?.kind === 'mark-paid'}
        onOpenChange={(open) => !open && setAction(null)}
        title="Mark as paid?"
        description="Use this when you paid the parent outside the app."
        confirmLabel="Mark as paid"
        noteLabel="Transfer reference"
        noteRequired
        onConfirm={(note) => w ? process(w, 'mark-paid', note) : undefined}
      />
      <NoteDialog
        open={action?.kind === 'reject'}
        onOpenChange={(open) => !open && setAction(null)}
        title="Reject this withdrawal?"
        description="The amount goes back to the parent's TutorLink balance and they're told why."
        confirmLabel="Reject"
        destructive
        noteLabel="Reason"
        noteRequired
        onConfirm={(note) => w ? process(w, 'reject', note) : undefined}
      />
    </>
  )
}

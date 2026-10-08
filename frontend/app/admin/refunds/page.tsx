'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { RefundStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { decideRefund, getRefunds } from '@/lib/bookings'
import { formatDateTime, formatNaira } from '@/lib/format'
import type { Refund } from '@/types'

export default function AdminRefundsPage() {
  const toast = useToast()
  const [pendingOnly, setPendingOnly] = useState(true)
  const [refunds, setRefunds] = useState<Refund[] | null>(null)
  const [deciding, setDeciding] = useState<{ refund: Refund; approve: boolean } | null>(null)

  const load = useCallback(() => {
    setRefunds(null)
    getRefunds(pendingOnly ? 'pending' : undefined).then(setRefunds).catch((e) => { toast.error(errorMessage(e)); setRefunds([]) })
  }, [pendingOnly, toast])
  useEffect(load, [load])

  async function decide(refund: Refund, approve: boolean, note: string) {
    try {
      const updated = await decideRefund(refund.id, approve, note)
      toast.success(approve ? `${formatNaira(updated.amount)} credited to ${refund.parent_name}'s balance` : 'Refund rejected')
      setRefunds((list) => list && (pendingOnly ? list.filter((r) => r.id !== refund.id) : list.map((r) => r.id === refund.id ? updated : r)))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Refunds" description="Cancelled lessons at least 48 hours away. Approving credits the agreed price per lesson (without the parent fee) to the parent's TutorLink balance." />
      <Tabs value={pendingOnly ? 'pending' : 'all'} onValueChange={(v) => setPendingOnly(v === 'pending')} className="mb-4">
        <TabsList>
          <TabsTrigger value="pending">Waiting</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {refunds === null ? <LoadingSpinner /> : refunds.length === 0 ? (
        <EmptyState message={pendingOnly ? 'No refunds waiting for approval.' : 'No refunds yet.'} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Parent</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Requested</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {refunds.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.parent_name}</TableCell>
                  <TableCell className="text-sm">
                    {r.reason === 'cancellation' ? 'Booking cancelled' : 'Lesson problem'}
                    {r.note && <span className="block text-xs text-muted-foreground">{r.note}</span>}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <span className="font-semibold tabular-nums">{formatNaira(r.amount)}</span>
                    <span className="block text-xs text-muted-foreground">{r.lesson_count} lesson(s)</span>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-sm">{formatDateTime(r.created_at)}</TableCell>
                  <TableCell><RefundStatusBadge status={r.status} /></TableCell>
                  <TableCell>
                    {r.status === 'pending' && (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" onClick={() => setDeciding({ refund: r, approve: true })}>Approve</Button>
                        <Button size="sm" variant="outline" onClick={() => setDeciding({ refund: r, approve: false })}>Reject</Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <NoteDialog
        open={deciding !== null}
        onOpenChange={(open) => !open && setDeciding(null)}
        title={deciding?.approve ? `Refund ${formatNaira(deciding.refund.amount)} to ${deciding.refund.parent_name}?` : 'Reject this refund?'}
        description={deciding?.approve
          ? "The money goes to the parent's TutorLink balance, and the tutor earns nothing for these lessons."
          : 'The parent is told, with your note.'}
        confirmLabel={deciding?.approve ? 'Approve refund' : 'Reject refund'}
        destructive={deciding?.approve === false}
        noteRequired={deciding?.approve === false}
        noteLabel={deciding?.approve ? 'Note (optional)' : 'Reason'}
        onConfirm={(note) => deciding ? decide(deciding.refund, deciding.approve, note) : undefined}
      />
    </>
  )
}

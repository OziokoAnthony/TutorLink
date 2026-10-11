'use client'

import { useEffect, useState } from 'react'
import ReceiptShell from '@/components/receipts/ReceiptShell'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { errorMessage } from '@/lib/api'
import { formatNaira } from '@/lib/format'
import { getReceipt } from '@/lib/wallet'
import type { ParentReceipt } from '@/types'
import { useParams } from 'next/navigation'

export default function ParentReceiptPage() {
  const params = useParams<{ id: string }>()
  const [receipt, setReceipt] = useState<ParentReceipt | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getReceipt(params.id).then(setReceipt).catch((e) => setError(errorMessage(e)))
  }, [params.id])

  if (error) return <div className="mx-auto max-w-2xl px-4 py-12"><EmptyState message={error} /></div>
  if (!receipt) return <LoadingSpinner />

  const moneyIn = receipt.kind === 'deposit' || receipt.kind === 'refund' || receipt.kind === 'withdrawal_reversal'
  return (
    <ReceiptShell title={receipt.title} number={receipt.receipt_number} issuedAt={receipt.issued_at}
      to={{ name: receipt.parent_name, email: receipt.parent_email }}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground"><th className="py-2 font-medium">Description</th><th className="py-2 text-right font-medium">Amount</th></tr>
        </thead>
        <tbody>
          {receipt.lines.map((line, i) => (
            <tr key={i} className="border-b last:border-0">
              <td className="py-2 pr-4">{line.description}</td>
              <td className="py-2 text-right tabular-nums">{formatNaira(line.amount)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2">
            <td className="py-2 font-semibold">{moneyIn ? 'Total received' : 'Total paid'}</td>
            <td className="py-2 text-right text-lg font-bold tabular-nums">{formatNaira(receipt.total)}</td>
          </tr>
          <tr>
            <td className="text-muted-foreground">TutorLink balance after this</td>
            <td className="text-right tabular-nums text-muted-foreground">{formatNaira(receipt.balance_after)}</td>
          </tr>
        </tfoot>
      </table>
    </ReceiptShell>
  )
}

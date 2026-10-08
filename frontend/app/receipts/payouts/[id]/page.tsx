'use client'

import { useEffect, useState } from 'react'
import ReceiptShell from '@/components/receipts/ReceiptShell'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { errorMessage } from '@/lib/api'
import { formatDate, formatNaira, formatPercent } from '@/lib/format'
import { getPayoutReceipt } from '@/lib/payouts'
import type { PayoutReceipt } from '@/types'

export default function PayoutReceiptPage({ params }: { params: { id: string } }) {
  const [receipt, setReceipt] = useState<PayoutReceipt | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getPayoutReceipt(params.id).then(setReceipt).catch((e) => setError(errorMessage(e)))
  }, [params.id])

  if (error) return <div className="mx-auto max-w-2xl px-4 py-12"><EmptyState message={error} /></div>
  if (!receipt) return <LoadingSpinner />

  const fee = receipt.tutor_fee_rate !== null ? ` (${formatPercent(receipt.tutor_fee_rate)})` : ''
  return (
    <ReceiptShell title={receipt.status === 'paid' ? 'Payment to you' : 'Payment to you (being sent)'}
      number={receipt.receipt_number} issuedAt={receipt.issued_at}
      to={{ name: receipt.tutor_name, email: receipt.tutor_email }}>
      <p className="text-sm text-muted-foreground">
        {receipt.method === 'paystack' && receipt.bank ? `Sent to ${receipt.bank}.` : 'Paid by bank transfer from TutorLink.'}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 font-medium">Lesson</th>
              <th className="py-2 text-right font-medium">Agreed price</th>
              <th className="py-2 text-right font-medium">TutorLink fee{fee}</th>
              <th className="py-2 text-right font-medium">You receive</th>
            </tr>
          </thead>
          <tbody>
            {receipt.lines.map((line, i) => (
              <tr key={i} className="border-b last:border-0">
                <td className="py-2 pr-4">{formatDate(line.lesson_date)} • {line.subjects.join(', ')} • {line.parent_first_name}</td>
                <td className="py-2 text-right tabular-nums">{formatNaira(line.price)}</td>
                <td className="py-2 text-right tabular-nums">−{formatNaira(line.tutor_fee)}</td>
                <td className="py-2 text-right tabular-nums">{formatNaira(line.earning)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 font-semibold">
              <td className="py-2">Total</td>
              <td className="py-2 text-right tabular-nums">{formatNaira(receipt.total_price)}</td>
              <td className="py-2 text-right tabular-nums">−{formatNaira(receipt.total_fee)}</td>
              <td className="py-2 text-right text-lg font-bold tabular-nums">{formatNaira(receipt.total)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </ReceiptShell>
  )
}

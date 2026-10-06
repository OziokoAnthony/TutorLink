'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { InvoiceStatusBadge } from '@/components/shared/StatusBadge'
import { formatNaira, monthYear } from '@/lib/format'
import type { Invoice } from '@/types'

/** Invoice summary card + pay button. Never offers payment on a paid invoice. */
export default function InvoiceCard({ invoice, onPay, processing }: {
  invoice: Invoice
  onPay: (invoice: Invoice) => Promise<void>
  /** True right after returning from Paystack, until the webhook marks it paid. */
  processing?: boolean
}) {
  const [busy, setBusy] = useState(false)
  // Pending can be paid; a failed payment can be retried. Paid never shows the button.
  const payable = invoice.status === 'pending' || invoice.status === 'failed'

  async function pay() {
    setBusy(true)
    try { await onPay(invoice) } finally { setBusy(false) }
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{monthYear(invoice.billing_month, invoice.billing_year)}</h3>
            <InvoiceStatusBadge status={invoice.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            {invoice.total_sessions} confirmed {invoice.total_sessions === 1 ? 'session' : 'sessions'}
          </p>
          <p className="font-medium">Total: {formatNaira(invoice.total_amount)}</p>
          {invoice.status === 'paid' && invoice.paid_at && (
            <p className="text-xs text-muted-foreground">Paid on {new Date(invoice.paid_at).toLocaleDateString('en-GB')}</p>
          )}
          {processing && invoice.status !== 'paid' && (
            <p className="text-xs text-muted-foreground">Payment processing… this updates once Paystack confirms it.</p>
          )}
        </div>
        {payable && (
          <Button onClick={pay} disabled={busy || processing}>
            {busy ? 'Opening Paystack…' : invoice.status === 'failed' ? 'Try again' : 'Pay Now'}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

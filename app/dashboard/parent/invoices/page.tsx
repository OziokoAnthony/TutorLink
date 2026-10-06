'use client'

import { useCallback, useEffect, useRef, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import InvoiceCard from '@/components/invoices/InvoiceCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getMyInvoices, payInvoice } from '@/lib/billing'
import type { Invoice } from '@/types'

const POLL_MS = 3000
const POLL_LIMIT = 20 // ~1 minute

function InvoicesContent() {
  const toast = useToast()
  const searchParams = useSearchParams()
  // Paystack sends the parent back here with ?invoice=<id> (and its own ?reference=...).
  const returnedInvoiceId = searchParams.get('invoice')
  const [invoices, setInvoices] = useState<Invoice[] | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(returnedInvoiceId)
  const polls = useRef(0)

  const load = useCallback(async () => {
    try {
      const list = await getMyInvoices()
      setInvoices(list)
      return list
    } catch (e) {
      toast.error(errorMessage(e))
      setInvoices((current) => current ?? [])
      return null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  // After returning from Paystack, refresh until the webhook has marked the invoice paid.
  useEffect(() => {
    if (!processingId || invoices === null) return
    const invoice = invoices.find((i) => i.id === processingId)
    if (!invoice || invoice.status === 'paid') {
      if (invoice?.status === 'paid') toast.success('Payment received. Thank you!')
      setProcessingId(null)
      return
    }
    if (polls.current >= POLL_LIMIT) {
      setProcessingId(null)
      toast.info("We haven't received confirmation from Paystack yet. Refresh this page in a few minutes.")
      return
    }
    const timer = setTimeout(() => { polls.current += 1; load() }, POLL_MS)
    return () => clearTimeout(timer)
  }, [processingId, invoices, load]) // eslint-disable-line react-hooks/exhaustive-deps

  async function pay(invoice: Invoice) {
    try {
      const { authorization_url } = await payInvoice(invoice.id)
      window.location.href = authorization_url // Paystack checkout
    } catch (e) {
      toast.error(errorMessage(e, 'Could not start the payment. Please try again.'))
    }
  }

  if (invoices === null) return <LoadingSpinner />
  if (invoices.length === 0) {
    return <EmptyState message="No invoices yet. Invoices are generated monthly for your confirmed sessions." />
  }
  return (
    <div className="space-y-3">
      {invoices.map((invoice) => (
        <InvoiceCard key={invoice.id} invoice={invoice} onPay={pay} processing={invoice.id === processingId} />
      ))}
    </div>
  )
}

export default function ParentInvoicesPage() {
  return (
    <>
      <PageHeader title="Invoices" description="Monthly invoices for your confirmed sessions." />
      <Suspense fallback={<LoadingSpinner />}>
        <InvoicesContent />
      </Suspense>
    </>
  )
}

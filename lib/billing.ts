import api from '@/lib/api'
import type { GenerateInvoicesResult, Invoice, InvoiceItem } from '@/types'

type Money = 'subtotal' | 'commission_rate' | 'commission_amount' | 'total_amount'
type RawInvoiceItem = Omit<InvoiceItem, 'amount' | 'commission_amount'> & { amount: string; commission_amount: string }
type RawInvoice = Omit<Invoice, Money | 'items'> & Record<Money, string> & { items?: RawInvoiceItem[] }

function toInvoice(raw: RawInvoice): Invoice {
  return {
    ...raw,
    paid_at: raw.paid_at ?? undefined,
    subtotal: Number(raw.subtotal),
    commission_rate: Number(raw.commission_rate),
    commission_amount: Number(raw.commission_amount),
    total_amount: Number(raw.total_amount),
    items: (raw.items ?? []).map((item) => ({
      ...item,
      amount: Number(item.amount),
      commission_amount: Number(item.commission_amount),
    })),
  }
}

export async function getMyInvoices(): Promise<Invoice[]> {
  const { data } = await api.get<RawInvoice[]>('/invoices/me')
  return data.map(toInvoice)
}

export async function getInvoice(id: string): Promise<Invoice> {
  const { data } = await api.get<RawInvoice>(`/invoices/${id}`)
  return toInvoice(data)
}

/** Starts a Paystack payment; returns the checkout URL to send the browser to. */
export async function payInvoice(id: string): Promise<{ authorization_url: string; reference: string }> {
  const { data } = await api.post<{ authorization_url: string; reference: string }>(`/invoices/${id}/pay`)
  return data
}

export async function generateInvoices(month: number, year: number): Promise<GenerateInvoicesResult> {
  const { data } = await api.post<Omit<GenerateInvoicesResult, 'invoices'> & { invoices: RawInvoice[] }>(
    '/invoices/generate', { month, year },
  )
  return { ...data, invoices: data.invoices.map(toInvoice) }
}

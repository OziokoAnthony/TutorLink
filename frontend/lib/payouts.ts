import api from '@/lib/api'
import { numbers } from '@/lib/convert'
import type {
  BankAccountTutorView, EarningsSummary, Fees, Payout, PayoutDue, PayoutReceipt, PayoutReceiptLine,
} from '@/types'

export async function getEarnings(): Promise<EarningsSummary> {
  const { data } = await api.get('/earnings/me')
  return numbers<EarningsSummary>(data, ['pending', 'on_hold', 'payable', 'paid'])
}

export async function getMyBankAccount(): Promise<BankAccountTutorView | null> {
  const { data } = await api.get<BankAccountTutorView | null>('/earnings/me/bank-account')
  return data
}

export async function setMyBankAccount(bank_code: string, account_number: string): Promise<BankAccountTutorView> {
  const { data } = await api.put<BankAccountTutorView>('/earnings/me/bank-account', { bank_code, account_number })
  return data
}

export async function getPayoutsDue(): Promise<PayoutDue[]> {
  const { data } = await api.get<unknown[]>('/admin/payouts/due')
  return data.map((d) => numbers<PayoutDue>(d, ['amount']))
}

export async function getPayouts(): Promise<Payout[]> {
  const { data } = await api.get<unknown[]>('/admin/payouts')
  return data.map((p) => numbers<Payout>(p, ['amount']))
}

export async function createPayout(tutor_id: string, method: Payout['method'], note?: string): Promise<Payout> {
  const { data } = await api.post('/admin/payouts', { tutor_id, method, note: note || null })
  return numbers<Payout>(data, ['amount'])
}

export async function overrideBankAccount(tutorId: string, note: string): Promise<void> {
  await api.post(`/admin/tutors/${tutorId}/bank-account/override`, { note })
}

export async function getFees(): Promise<Fees> {
  const { data } = await api.get('/admin/fees')
  return numbers<Fees>(data, ['parent_fee_rate', 'tutor_fee_rate'])
}

/** Rates as fractions, e.g. 0.1 for 10%. */
export async function updateFees(parent_fee_rate: number, tutor_fee_rate: number): Promise<Fees> {
  const { data } = await api.put('/admin/fees', {
    parent_fee_rate: parent_fee_rate.toFixed(4), tutor_fee_rate: tutor_fee_rate.toFixed(4),
  })
  return numbers<Fees>(data, ['parent_fee_rate', 'tutor_fee_rate'])
}

/** Tutor: my payouts. */
export async function getMyPayouts(): Promise<Payout[]> {
  const { data } = await api.get<unknown[]>('/earnings/me/payouts')
  return data.map((p) => numbers<Payout>(p, ['amount']))
}

export async function getPayoutReceipt(payoutId: string): Promise<PayoutReceipt> {
  const { data } = await api.get(`/earnings/payouts/${payoutId}/receipt`)
  const r = numbers<PayoutReceipt>(data, ['tutor_fee_rate', 'total_price', 'total_fee', 'total'])
  return { ...r, lines: r.lines.map((l) => numbers<PayoutReceiptLine>(l, ['price', 'tutor_fee', 'earning'])) }
}

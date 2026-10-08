import api from '@/lib/api'
import { numbers } from '@/lib/convert'
import type { Bank, ParentReceipt, ReceiptLine, VirtualAccount, Wallet, WalletEntry, Withdrawal } from '@/types'

export function toWithdrawal(raw: unknown): Withdrawal {
  return numbers<Withdrawal>(raw, ['amount'])
}

export async function getWallet(): Promise<Wallet> {
  const { data } = await api.get('/wallet/me')
  const w = numbers<Wallet>(data, ['balance', 'amount_due'])
  return { ...w, entries: w.entries.map((e) => numbers<WalletEntry>(e, ['amount'])) }
}

/** Creates the parent's own account number if they don't have one yet. */
export async function requestAccountNumber(): Promise<VirtualAccount> {
  const { data } = await api.post<VirtualAccount>('/wallet/me/account-number')
  return data
}

export async function getBanks(): Promise<Bank[]> {
  const { data } = await api.get<Bank[]>('/banks')
  return data
}

export async function requestWithdrawal(amount: number, bank_code: string, account_number: string): Promise<Withdrawal> {
  const { data } = await api.post('/wallet/me/withdrawals', { amount: amount.toFixed(2), bank_code, account_number })
  return toWithdrawal(data)
}

export async function getMyWithdrawals(): Promise<Withdrawal[]> {
  const { data } = await api.get<unknown[]>('/wallet/me/withdrawals')
  return data.map(toWithdrawal)
}

export async function getAllWithdrawals(status?: Withdrawal['status']): Promise<Withdrawal[]> {
  const { data } = await api.get<unknown[]>('/admin/withdrawals', { params: status ? { status } : {} })
  return data.map(toWithdrawal)
}

export async function processWithdrawal(id: string, action: 'send' | 'mark-paid' | 'reject', note?: string): Promise<Withdrawal> {
  const body = action === 'send' ? undefined : { note: note || null }
  const { data } = await api.post(`/admin/withdrawals/${id}/${action}`, body)
  return toWithdrawal(data)
}

export async function getReceipt(entryId: string): Promise<ParentReceipt> {
  const { data } = await api.get(`/wallet/me/receipts/${entryId}`)
  const r = numbers<ParentReceipt>(data, ['total', 'balance_after'])
  return { ...r, lines: r.lines.map((l) => numbers<ReceiptLine>(l, ['amount'])) }
}

'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Receipt } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import AccountNumberCard from '@/components/payments/AccountNumberCard'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import StatCard from '@/components/shared/StatCard'
import { TransferStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getMyBookings } from '@/lib/bookings'
import { formatDateTime, formatNaira } from '@/lib/format'
import { getBanks, getMyWithdrawals, getWallet, requestWithdrawal } from '@/lib/wallet'
import { cn } from '@/lib/utils'
import type { Bank, Booking, Period, Wallet, Withdrawal } from '@/types'

export default function ParentWalletPage() {
  const toast = useToast()
  const [wallet, setWallet] = useState<Wallet | null>(null)
  const [due, setDue] = useState<{ booking: Booking; period: Period }[]>([])
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([])
  const [banks, setBanks] = useState<Bank[]>([])
  const [withdrawOpen, setWithdrawOpen] = useState(false)
  const [form, setForm] = useState({ amount: '', bank_code: '', account_number: '' })
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    getWallet().then(setWallet).catch((e) => toast.error(errorMessage(e)))
    getMyBookings().then((bookings) => setDue(bookings.flatMap((b) => (b.periods ?? [])
      .filter((p) => p.status === 'due').map((period) => ({ booking: b, period })))
      .sort((a, b) => a.period.due_at.localeCompare(b.period.due_at)))).catch(() => undefined)
    getMyWithdrawals().then(setWithdrawals).catch(() => undefined)
  }, [toast])
  useEffect(load, [load])

  async function openWithdraw() {
    setWithdrawOpen(true)
    if (banks.length === 0) getBanks().then(setBanks).catch((e) => toast.error(errorMessage(e)))
  }

  async function withdraw() {
    setBusy(true)
    try {
      await requestWithdrawal(Number(form.amount), form.bank_code, form.account_number)
      toast.success('Withdrawal requested. TutorLink will send it to your bank.')
      setWithdrawOpen(false)
      setForm({ amount: '', bank_code: '', account_number: '' })
      load()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  if (!wallet) return <LoadingSpinner />

  return (
    <>
      <PageHeader title="Payments & receipts" description="You pay before lessons start. Everything you've paid, and every refund, is listed with its receipt."
        action={<Button variant="outline" onClick={openWithdraw} disabled={wallet.balance <= 0}>Withdraw to my bank</Button>} />

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="TutorLink balance" value={formatNaira(wallet.balance)} />
        <StatCard label="To pay now" value={formatNaira(wallet.amount_due)} />
      </div>

      <div className="mt-6"><AccountNumberCard account={wallet.virtual_account} onCreated={load} /></div>

      {due.length > 0 && (
        <Card className="mt-6 border-amber-300">
          <CardHeader><CardTitle className="text-lg">Waiting for payment</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {due.map(({ booking, period }) => (
              <div key={period.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                <span>{booking.subjects.join(', ')} with {booking.tutor_name} • {period.lesson_count} lesson(s)</span>
                <span><span className="font-semibold">{formatNaira(period.amount)}</span> before {formatDateTime(period.due_at)}</span>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              Transfer the amount to your account number above. It&apos;s paid from your balance automatically; lessons not paid 24 hours before they start don&apos;t go ahead.
            </p>
          </CardContent>
        </Card>
      )}

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-lg">History</CardTitle></CardHeader>
        <CardContent>
          {wallet.entries.length === 0 ? <EmptyState message="No payments yet." /> : (
            <ul className="divide-y text-sm">
              {wallet.entries.map((e) => (
                <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <div>
                    <p>{e.description}</p>
                    <p className="text-xs text-muted-foreground">{formatDateTime(e.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn('font-semibold tabular-nums', e.amount > 0 ? 'text-emerald-700' : '')}>
                      {e.amount > 0 ? '+' : '−'}{formatNaira(Math.abs(e.amount))}
                    </span>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/receipts/wallet/${e.id}`}><Receipt className="mr-1 h-4 w-4" aria-hidden />Receipt</Link>
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {withdrawals.length > 0 && (
        <Card className="mt-6">
          <CardHeader><CardTitle className="text-lg">Withdrawals</CardTitle></CardHeader>
          <CardContent>
            <ul className="divide-y text-sm">
              {withdrawals.map((w) => (
                <li key={w.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <span>{formatNaira(w.amount)} to {w.bank_name} ****{w.account_number.slice(-4)} • {formatDateTime(w.created_at)}</span>
                  <TransferStatusBadge status={w.status} />
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Dialog open={withdrawOpen} onOpenChange={(o) => !busy && setWithdrawOpen(o)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Withdraw to your bank</DialogTitle>
            <DialogDescription>Up to {formatNaira(wallet.balance)}. TutorLink sends it to your bank account.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="wd-amount">Amount (₦)</Label>
              <Input id="wd-amount" type="number" min={1} max={wallet.balance} value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="wd-bank">Bank</Label>
              <Select value={form.bank_code} onValueChange={(v) => setForm({ ...form, bank_code: v })}>
                <SelectTrigger id="wd-bank"><SelectValue placeholder={banks.length ? 'Choose your bank' : 'Loading banks…'} /></SelectTrigger>
                <SelectContent>{banks.map((b) => <SelectItem key={b.code} value={b.code}>{b.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="wd-account">Account number</Label>
              <Input id="wd-account" inputMode="numeric" maxLength={10} value={form.account_number}
                onChange={(e) => setForm({ ...form, account_number: e.target.value.replace(/\D/g, '') })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWithdrawOpen(false)} disabled={busy}>Back</Button>
            <Button onClick={withdraw} disabled={busy || !(Number(form.amount) > 0) || Number(form.amount) > wallet.balance
              || !form.bank_code || form.account_number.length !== 10}>
              {busy ? 'Requesting…' : 'Request withdrawal'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

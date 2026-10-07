'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Receipt } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import StatCard from '@/components/shared/StatCard'
import { EarningStatusBadge, TransferStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDate, formatDateTime, formatNaira } from '@/lib/format'
import { getTutorLessons } from '@/lib/lessons'
import { getEarnings, getMyBankAccount, getMyPayouts, setMyBankAccount } from '@/lib/payouts'
import { getBanks } from '@/lib/wallet'
import type { Bank, BankAccountTutorView, EarningsSummary, Lesson, Payout } from '@/types'

function BankAccountCard({ account, onSaved }: { account: BankAccountTutorView | null; onSaved: () => void }) {
  const toast = useToast()
  const [editing, setEditing] = useState(!account)
  const [banks, setBanks] = useState<Bank[]>([])
  const [bankCode, setBankCode] = useState('')
  const [number, setNumber] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (editing && banks.length === 0) getBanks().then(setBanks).catch((e) => toast.error(errorMessage(e)))
  }, [editing, banks.length, toast])

  async function save() {
    setBusy(true)
    try {
      const saved = await setMyBankAccount(bankCode, number)
      toast.success(saved.name_matches ? 'Bank details saved' : "Saved, but the account name doesn't match your name. TutorLink will review it.")
      setEditing(false)
      onSaved()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Where you&apos;re paid</CardTitle>
        <CardDescription>Only TutorLink&apos;s admin sees your full account number. The account name must match your name.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {account && !editing && (
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div>
              <p className="font-medium">{account.bank_name} ****{account.account_last4}</p>
              <p className="text-muted-foreground">{account.account_name}</p>
              {!account.approved_for_payouts && <p className="text-amber-700">Name doesn&apos;t match: waiting for TutorLink to check it.</p>}
            </div>
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>Change</Button>
          </div>
        )}
        {editing && (
          <div className="grid gap-3 sm:grid-cols-[1fr_180px_auto] sm:items-end">
            <div className="space-y-1.5">
              <Label htmlFor="bank">Bank</Label>
              <Select value={bankCode} onValueChange={setBankCode}>
                <SelectTrigger id="bank"><SelectValue placeholder={banks.length ? 'Choose your bank' : 'Loading banks…'} /></SelectTrigger>
                <SelectContent>{banks.map((b) => <SelectItem key={b.code} value={b.code}>{b.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="account-number">Account number</Label>
              <Input id="account-number" inputMode="numeric" maxLength={10} value={number} onChange={(e) => setNumber(e.target.value.replace(/\D/g, ''))} />
            </div>
            <Button onClick={save} disabled={busy || !bankCode || number.length !== 10}>{busy ? 'Checking…' : 'Save'}</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function TutorEarningsPage() {
  const toast = useToast()
  const [summary, setSummary] = useState<EarningsSummary | null>(null)
  const [account, setAccount] = useState<BankAccountTutorView | null | undefined>(undefined)
  const [payouts, setPayouts] = useState<Payout[]>([])
  const [lessons, setLessons] = useState<Lesson[]>([])

  const load = useCallback(() => {
    getEarnings().then(setSummary).catch((e) => toast.error(errorMessage(e)))
    getMyBankAccount().then(setAccount).catch(() => setAccount(null))
    getMyPayouts().then(setPayouts).catch(() => undefined)
    getTutorLessons().then((l) => setLessons(l.filter((x) => x.earning_status && x.earning_status !== 'pending'))).catch(() => undefined)
  }, [toast])
  useEffect(load, [load])

  if (!summary || account === undefined) return <LoadingSpinner />

  return (
    <>
      <PageHeader title="Earnings" description="You earn the agreed price minus TutorLink's fee for every lesson. You're paid 48 hours after the last lesson of each billing period." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="To be paid" value={formatNaira(summary.payable)} />
        <StatCard label="Paid to you" value={formatNaira(summary.paid)} />
        <StatCard label="Upcoming lessons" value={formatNaira(summary.pending)} />
        <StatCard label="On hold (under review)" value={formatNaira(summary.on_hold)} />
      </div>

      <div className="mt-6"><BankAccountCard key={account?.account_last4 ?? 'none'} account={account} onSaved={load} /></div>

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-lg">Payouts</CardTitle></CardHeader>
        <CardContent>
          {payouts.length === 0 ? <EmptyState message="No payouts yet." /> : (
            <ul className="divide-y text-sm">
              {payouts.map((p) => (
                <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <span>{formatNaira(p.amount)} for {p.lesson_count} lesson(s) • {formatDateTime(p.paid_at ?? p.created_at)}</span>
                  <span className="flex items-center gap-2">
                    <TransferStatusBadge status={p.status} />
                    {p.status !== 'failed' && (
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/receipts/payouts/${p.id}`}><Receipt className="mr-1 h-4 w-4" aria-hidden />Receipt</Link>
                      </Button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-lg">Earnings by lesson</CardTitle></CardHeader>
        <CardContent>
          {lessons.length === 0 ? <EmptyState message="No finished lessons yet." /> : (
            <ul className="divide-y text-sm">
              {lessons.map((l) => (
                <li key={l.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                  <span>{formatDate(l.lesson_date)} • {l.subjects.join(', ')} • {l.parent_name}</span>
                  <span className="flex items-center gap-2">
                    <span className="font-semibold tabular-nums">{formatNaira(l.tutor_earning ?? 0)}</span>
                    {l.earning_status && <EarningStatusBadge status={l.earning_status} />}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  )
}

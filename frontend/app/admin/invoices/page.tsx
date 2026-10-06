'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import FormField from '@/components/shared/FormField'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { generateInvoices } from '@/lib/billing'
import { MONTHS, formatNaira, monthYear } from '@/lib/format'
import type { GenerateInvoicesResult } from '@/types'

export default function AdminInvoicesPage() {
  const toast = useToast()
  const now = new Date()
  const [month, setMonth] = useState(String(now.getMonth() + 1))
  const [year, setYear] = useState(String(now.getFullYear()))
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<(GenerateInvoicesResult & { period: string }) | null>(null)

  const yearNumber = Number(year)
  const yearValid = Number.isInteger(yearNumber) && yearNumber >= 2000 && yearNumber <= 2100

  async function generate(e: React.FormEvent) {
    e.preventDefault()
    if (!yearValid) return
    setBusy(true)
    try {
      const data = await generateInvoices(Number(month), yearNumber)
      setResult({ ...data, period: monthYear(Number(month), yearNumber) })
      toast.success(`${data.created} ${data.created === 1 ? 'invoice' : 'invoices'} generated`)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Generate invoices" description="Bill parents for the sessions they confirmed in a month." />
      <Card>
        <CardContent className="pt-5">
          <form onSubmit={generate} className="grid gap-3 sm:grid-cols-[200px_140px_auto] sm:items-end" noValidate>
            <FormField id="month" label="Month">
              <Select value={month} onValueChange={setMonth}>
                <SelectTrigger id="month"><SelectValue /></SelectTrigger>
                <SelectContent>{MONTHS.map((m, i) => <SelectItem key={m} value={String(i + 1)}>{m}</SelectItem>)}</SelectContent>
              </Select>
            </FormField>
            <FormField id="year" label="Year" error={yearValid ? undefined : 'Enter a year between 2000 and 2100'}>
              <Input id="year" type="number" min={2000} max={2100} value={year} onChange={(e) => setYear(e.target.value)} aria-invalid={!yearValid} />
            </FormField>
            <Button type="submit" disabled={busy || !yearValid}>{busy ? 'Generating…' : 'Generate Invoices'}</Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <section className="mt-6 space-y-4" aria-live="polite">
          <div className="rounded-lg border bg-accent/40 px-4 py-3 text-sm">
            <p className="font-medium">
              {result.created} invoices generated. {result.parents_without_sessions} parents had no confirmed sessions.
            </p>
            {result.skipped_existing > 0 && (
              <p className="mt-1 text-muted-foreground">
                {result.skipped_existing} {result.skipped_existing === 1 ? 'parent already had an invoice' : 'parents already had invoices'} for {result.period}, so they were skipped.
              </p>
            )}
          </div>
          {result.invoices.length > 0 && (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Parent</TableHead>
                    <TableHead className="text-right">Sessions</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-right">Commission</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.invoices.map((inv) => (
                    <TableRow key={inv.id}>
                      <TableCell className="font-medium">{inv.parent_name ?? 'Parent'}</TableCell>
                      <TableCell className="text-right tabular-nums">{inv.total_sessions}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatNaira(inv.total_amount)}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{formatNaira(inv.commission_amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </section>
      )}
    </>
  )
}

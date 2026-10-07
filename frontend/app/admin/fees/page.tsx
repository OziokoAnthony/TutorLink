'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime, formatNaira } from '@/lib/format'
import { getFees, updateFees } from '@/lib/payouts'
import type { Fees } from '@/types'

const EXAMPLE_PRICE = 5000

/** "10" -> 0.1, or null when it isn't a percentage from 0 to 50. */
function toRate(percent: string): number | null {
  const n = Number(percent)
  return percent.trim() !== '' && Number.isFinite(n) && n >= 0 && n <= 50 ? n / 100 : null
}

export default function AdminFeesPage() {
  const toast = useToast()
  const [fees, setFees] = useState<Fees | null>(null)
  const [parentPercent, setParentPercent] = useState('')
  const [tutorPercent, setTutorPercent] = useState('')
  const [busy, setBusy] = useState(false)

  function show(f: Fees) {
    setFees(f)
    setParentPercent(String(Math.round(f.parent_fee_rate * 10000) / 100))
    setTutorPercent(String(Math.round(f.tutor_fee_rate * 10000) / 100))
  }

  useEffect(() => {
    getFees().then(show).catch((e) => toast.error(errorMessage(e)))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const parentRate = toRate(parentPercent)
  const tutorRate = toRate(tutorPercent)
  const valid = parentRate !== null && tutorRate !== null
  const changed = fees !== null && valid && (parentRate !== fees.parent_fee_rate || tutorRate !== fees.tutor_fee_rate)

  async function save() {
    if (parentRate === null || tutorRate === null) return
    setBusy(true)
    try {
      show(await updateFees(parentRate, tutorRate))
      toast.success('Fees updated. They apply to bookings accepted from now on.')
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  if (!fees) return <LoadingSpinner />

  return (
    <>
      <PageHeader title="Fees" description="Parents never see either percentage; tutors only see their own fee. Changes apply to bookings accepted afterwards." />
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle className="text-lg">Platform fees</CardTitle>
          <CardDescription>Last changed {formatDateTime(fees.updated_at)}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="parent-fee">Parent fee (%)</Label>
              <Input id="parent-fee" type="number" min={0} max={50} step={0.01} value={parentPercent}
                onChange={(e) => setParentPercent(e.target.value)} />
              <p className="text-xs text-muted-foreground">Added on top of the agreed price.</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tutor-fee">Tutor fee (%)</Label>
              <Input id="tutor-fee" type="number" min={0} max={50} step={0.01} value={tutorPercent}
                onChange={(e) => setTutorPercent(e.target.value)} />
              <p className="text-xs text-muted-foreground">Taken from the agreed price.</p>
            </div>
          </div>
          {!valid && <p className="text-sm text-destructive">Each fee must be between 0% and 50%.</p>}
          {valid && (
            <div className="rounded-md bg-muted p-3 text-sm">
              <p className="font-medium">For a {formatNaira(EXAMPLE_PRICE)} lesson:</p>
              <p>The parent pays {formatNaira(Math.round(EXAMPLE_PRICE * (1 + parentRate) * 100) / 100)}</p>
              <p>The tutor receives {formatNaira(Math.round(EXAMPLE_PRICE * (1 - tutorRate) * 100) / 100)}</p>
              <p>TutorLink keeps {formatNaira(Math.round(EXAMPLE_PRICE * (parentRate + tutorRate) * 100) / 100)}</p>
            </div>
          )}
          <Button onClick={save} disabled={busy || !changed}>{busy ? 'Saving…' : 'Save fees'}</Button>
        </CardContent>
      </Card>
    </>
  )
}

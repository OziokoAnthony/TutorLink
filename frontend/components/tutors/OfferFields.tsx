'use client'

import { useId, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DAYS, LEVELS, SUBJECTS, listedSubject } from '@/lib/format'
import type { OfferInput } from '@/lib/tutors'

export const EMPTY_OFFER: OfferInput = {
  subjects: [],
  level: 'senior_secondary',
  windows: [{ day_of_week: 0, start_time: '16:00', end_time: '18:00' }],
  price: 0,
}

/** null when the offer is complete, otherwise what's missing. */
export function offerProblem(offer: OfferInput): string | null {
  if (offer.subjects.length === 0) return 'Add at least one subject'
  if (offer.windows.length === 0) return 'Add at least one time you can teach'
  if (offer.windows.some((w) => !w.start_time || !w.end_time || w.end_time <= w.start_time)) {
    return 'Each time must end after it starts'
  }
  if (!(offer.price > 0)) return 'Enter your price per lesson'
  return null
}

/** Editor for one offer: subjects (one or more), level, weekly times, one price per lesson. */
export default function OfferFields({ value, onChange }: { value: OfferInput; onChange: (next: OfferInput) => void }) {
  const id = useId()
  const [subjectText, setSubjectText] = useState('')
  const [subjectProblem, setSubjectProblem] = useState<string | null>(null)

  function addSubject(name: string) {
    if (!name.trim()) return
    const listed = listedSubject(name)
    if (!listed) {
      setSubjectProblem('Choose a subject from the list.')
      return
    }
    if (!value.subjects.includes(listed)) onChange({ ...value, subjects: [...value.subjects, listed] })
    setSubjectProblem(null)
    setSubjectText('')
  }

  function setWindow(index: number, patch: Partial<OfferInput['windows'][number]>) {
    onChange({ ...value, windows: value.windows.map((w, i) => (i === index ? { ...w, ...patch } : w)) })
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor={`${id}-subject`}>Subjects taught together in one lesson</Label>
        <div className="flex flex-wrap gap-1.5">
          {value.subjects.map((s) => (
            <Badge key={s} variant="secondary" className="gap-1">
              {s}
              <button type="button" aria-label={`Remove ${s}`}
                onClick={() => onChange({ ...value, subjects: value.subjects.filter((x) => x !== s) })}>
                <X className="h-3 w-3" aria-hidden />
              </button>
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input id={`${id}-subject`} list={`${id}-subjects`} placeholder="e.g. Mathematics" value={subjectText}
            onChange={(e) => setSubjectText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSubject(subjectText) } }} />
          <datalist id={`${id}-subjects`}>{SUBJECTS.map((s) => <option key={s} value={s} />)}</datalist>
          <Button type="button" variant="outline" onClick={() => addSubject(subjectText)}>Add</Button>
        </div>
        {subjectProblem && <p role="alert" className="text-xs text-destructive">{subjectProblem}</p>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor={`${id}-level`}>Level</Label>
          <Select value={value.level} onValueChange={(level) => onChange({ ...value, level: level as OfferInput['level'] })}>
            <SelectTrigger id={`${id}-level`}><SelectValue /></SelectTrigger>
            <SelectContent>{LEVELS.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`${id}-price`}>Price per lesson (₦)</Label>
          <Input id={`${id}-price`} type="number" min={1} step={100} inputMode="numeric"
            value={value.price || ''} onChange={(e) => onChange({ ...value, price: Number(e.target.value) })} />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Times you can teach every week</Label>
        {value.windows.map((w, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2">
            <Select value={String(w.day_of_week)} onValueChange={(d) => setWindow(i, { day_of_week: Number(d) })}>
              <SelectTrigger className="w-36" aria-label="Day"><SelectValue /></SelectTrigger>
              <SelectContent>{DAYS.map((d, n) => <SelectItem key={d} value={String(n)}>{d}</SelectItem>)}</SelectContent>
            </Select>
            <Input type="time" className="w-28" aria-label="From" value={w.start_time.slice(0, 5)}
              onChange={(e) => setWindow(i, { start_time: e.target.value })} />
            <span className="text-sm text-muted-foreground">to</span>
            <Input type="time" className="w-28" aria-label="To" value={w.end_time.slice(0, 5)}
              onChange={(e) => setWindow(i, { end_time: e.target.value })} />
            {value.windows.length > 1 && (
              <Button type="button" variant="ghost" size="sm" aria-label="Remove this time"
                onClick={() => onChange({ ...value, windows: value.windows.filter((_, n) => n !== i) })}>
                <X className="h-4 w-4" aria-hidden />
              </Button>
            )}
          </div>
        ))}
        <Button type="button" variant="outline" size="sm"
          onClick={() => onChange({ ...value, windows: [...value.windows, { ...value.windows[value.windows.length - 1] ?? EMPTY_OFFER.windows[0] }] })}>
          <Plus className="mr-1 h-4 w-4" aria-hidden />Add another time
        </Button>
      </div>
    </div>
  )
}

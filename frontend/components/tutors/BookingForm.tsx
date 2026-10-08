'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Choice from '@/components/shared/Choice'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { requestBooking } from '@/lib/bookings'
import { BILLING_PERIODS, DAYS, formatNaira, levelLabel, slotText, toISODate } from '@/lib/format'
import type { BillingPeriod, LessonMode, TutorAvailability, TutorProfile, WeeklyTime } from '@/types'

const CLASH_MESSAGE = 'This tutor is already booked at one of those times. Please choose another time.'
const toMinutes = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))

function fitsWindow(slot: WeeklyTime, windows: WeeklyTime[]) {
  return windows.some((w) => w.day_of_week === slot.day_of_week
    && toMinutes(slot.start_time) >= toMinutes(w.start_time) && toMinutes(slot.end_time) <= toMinutes(w.end_time))
}

function overlaps(a: WeeklyTime, b: WeeklyTime) {
  return a.day_of_week === b.day_of_week
    && toMinutes(a.start_time) < toMinutes(b.end_time) && toMinutes(a.end_time) > toMinutes(b.start_time)
}

/** "Request a booking" modal: offer, subjects, weekly times, dates, billing period, mode, about the child. */
export default function BookingForm({ tutor, availability, open, onOpenChange }: {
  tutor: TutorProfile
  availability: TutorAvailability | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()
  const toast = useToast()
  const { user } = useAuth()
  const tomorrow = useMemo(() => { const d = new Date(); d.setDate(d.getDate() + 1); return toISODate(d) }, [])

  const [offerId, setOfferId] = useState(tutor.offers[0]?.id ?? '')
  const offer = tutor.offers.find((o) => o.id === offerId)
  const [subjects, setSubjects] = useState<string[]>(tutor.offers[0]?.subjects ?? [])
  const firstWindow = offer?.windows[0]
  const [slots, setSlots] = useState<WeeklyTime[]>(firstWindow
    ? [{ day_of_week: firstWindow.day_of_week, start_time: firstWindow.start_time.slice(0, 5), end_time: '' }] : [])
  const [startDate, setStartDate] = useState(tomorrow)
  const [endDate, setEndDate] = useState('')
  const [billing, setBilling] = useState<BillingPeriod>('weekly')
  const [mode, setMode] = useState<LessonMode>('offline')
  const [strengths, setStrengths] = useState('')
  const [weaknesses, setWeaknesses] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function chooseOffer(id: string) {
    const next = tutor.offers.find((o) => o.id === id)!
    setOfferId(id)
    setSubjects(next.subjects)
    const w = next.windows[0]
    setSlots([{ day_of_week: w.day_of_week, start_time: w.start_time.slice(0, 5), end_time: '' }])
  }

  function setSlot(i: number, patch: Partial<WeeklyTime>) {
    setProblem(null)
    setSlots(slots.map((s, n) => (n === i ? { ...s, ...patch } : s)))
  }

  function check(): string | null {
    if (!offer) return 'Choose what you want taught'
    if (subjects.length === 0) return 'Choose at least one subject'
    if (slots.length === 0) return 'Add at least one lesson time'
    for (const s of slots) {
      if (!s.start_time || !s.end_time || toMinutes(s.end_time) <= toMinutes(s.start_time)) return 'Each lesson must end after it starts'
      if (!fitsWindow(s, offer.windows)) return `${slotText(s)} is outside the times this tutor offers`
      if (availability?.busy.some((b) => overlaps(s, b))) return CLASH_MESSAGE
    }
    if (slots.some((s, i) => slots.slice(i + 1).some((t) => overlaps(s, t)))) return 'Two of your lesson times overlap'
    if (!startDate) return 'Choose a start date'
    if (endDate && endDate < startDate) return 'The end date must be after the start date'
    if (strengths.trim().length < 10) return "Tell the tutor your child's strengths (at least 10 characters)"
    if (weaknesses.trim().length < 10) return "Tell the tutor what your child finds hard (at least 10 characters)"
    return null
  }

  async function submit() {
    const issue = check()
    setProblem(issue)
    if (issue) return
    setBusy(true)
    try {
      await requestBooking({
        tutor_id: tutor.user_id, offer_id: offerId, subjects, slots, start_date: startDate, end_date: endDate || null,
        billing_period: billing, mode, child_strengths: strengths.trim(), child_weaknesses: weaknesses.trim(),
      })
      toast.success('Request sent! The tutor has 72 hours to accept.')
      router.push('/dashboard/parent/bookings')
    } catch (error) {
      setProblem(errorStatus(error) === 409 && !errorMessage(error).includes('picture') ? CLASH_MESSAGE : errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  if (open && user && !user.photo_url) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a profile picture first</DialogTitle>
            <DialogDescription>Tutors see your picture on your booking requests. Add one, then come back to book.</DialogDescription>
          </DialogHeader>
          <DialogFooter><Button asChild><Link href="/dashboard/parent">Add my picture</Link></Button></DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Book {tutor.full_name}</DialogTitle>
          <DialogDescription>
            The tutor has 72 hours to accept. Once they do, you pay before the lessons start, by bank transfer to your own TutorLink account number.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="booking-offer">What you want taught</Label>
            <Select value={offerId} onValueChange={chooseOffer}>
              <SelectTrigger id="booking-offer"><SelectValue /></SelectTrigger>
              <SelectContent>
                {tutor.offers.map((o) => (
                  <SelectItem key={o.id} value={o.id}>
                    {o.subjects.join(', ')} • {levelLabel(o.level)} • {formatNaira(o.price)} per lesson
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {offer && offer.subjects.length > 1 && (
              <div className="flex flex-wrap gap-3 pt-1">
                {offer.subjects.map((s) => (
                  <label key={s} className="flex items-center gap-1.5 text-sm">
                    <input type="checkbox" className="h-4 w-4 accent-primary" checked={subjects.includes(s)}
                      onChange={(e) => setSubjects(e.target.checked ? [...subjects, s] : subjects.filter((x) => x !== s))} />
                    {s}
                  </label>
                ))}
              </div>
            )}
            {offer && <p className="text-xs text-muted-foreground">
              Agreed price: {formatNaira(offer.price)} per lesson, whatever the number of subjects. Your total, including TutorLink&apos;s service fee, is shown before you pay.
            </p>}
          </div>

          <div className="space-y-2">
            <Label>Weekly lesson times</Label>
            {offer && <p className="text-xs text-muted-foreground">This tutor teaches this at: {offer.windows.map(slotText).join('; ')}</p>}
            {slots.map((s, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2">
                <Select value={String(s.day_of_week)} onValueChange={(d) => setSlot(i, { day_of_week: Number(d) })}>
                  <SelectTrigger className="w-36" aria-label="Day"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {DAYS.map((d, n) => offer?.windows.some((w) => w.day_of_week === n)
                      ? <SelectItem key={d} value={String(n)}>{d}</SelectItem> : null)}
                  </SelectContent>
                </Select>
                <Input type="time" className="w-28" aria-label="Start" value={s.start_time} onChange={(e) => setSlot(i, { start_time: e.target.value })} />
                <span className="text-sm text-muted-foreground">to</span>
                <Input type="time" className="w-28" aria-label="End" value={s.end_time} onChange={(e) => setSlot(i, { end_time: e.target.value })} />
                {slots.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" aria-label="Remove this time" onClick={() => setSlots(slots.filter((_, n) => n !== i))}>
                    <X className="h-4 w-4" aria-hidden />
                  </Button>
                )}
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={() => setSlots([...slots, { ...slots[slots.length - 1] }])}>
              <Plus className="mr-1 h-4 w-4" aria-hidden />Add another lesson each week
            </Button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="booking-start">Start date</Label>
              <Input id="booking-start" type="date" min={tomorrow} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="booking-end">End date (optional)</Label>
              <Input id="booking-end" type="date" min={startDate} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>How often you pay</Label>
            <Choice label="How often you pay" value={billing} onChange={setBilling} options={BILLING_PERIODS} />
          </div>

          <div className="space-y-1.5">
            <Label>Lessons</Label>
            <Choice label="Lesson mode" value={mode} onChange={setMode} options={[
              { value: 'offline', label: 'At home (offline)' }, { value: 'online', label: 'Online' },
            ]} />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="booking-strengths">Your child&apos;s strengths</Label>
              <Textarea id="booking-strengths" rows={3} maxLength={1000} value={strengths} onChange={(e) => setStrengths(e.target.value)}
                placeholder="e.g. Quick with mental arithmetic, loves reading" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="booking-weaknesses">What your child finds hard</Label>
              <Textarea id="booking-weaknesses" rows={3} maxLength={1000} value={weaknesses} onChange={(e) => setWeaknesses(e.target.value)}
                placeholder="e.g. Word problems and fractions" />
            </div>
          </div>

          {problem && <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{problem}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
          <Button onClick={submit} disabled={busy}>{busy ? 'Sending…' : 'Send booking request'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

'use client'

import { useMemo, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import Choice from '@/components/shared/Choice'
import RecordingConsent from '@/components/shared/RecordingConsent'
import { BILLING_PERIODS, CERTIFICATES, DAYS, LEVELS, SUBJECTS, formatTime, listedSubject, toISODate } from '@/lib/format'
import type { BillingPeriod, CertificateType, Job, JobInput, LessonMode, Level, WeeklyTime } from '@/types'

const NONE = 'none'
const toMinutes = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))
const overlaps = (a: WeeklyTime, b: WeeklyTime) => a.day_of_week === b.day_of_week
  && toMinutes(a.start_time) < toMinutes(b.end_time) && toMinutes(a.end_time) > toMinutes(b.start_time)

/** Post a job, or edit an open one: what to teach, when, where, the price per lesson and about the child. */
export default function JobForm({ initial, submitLabel, onSubmit, onCancel }: {
  initial?: Job
  submitLabel: string
  onSubmit: (input: JobInput) => Promise<void>
  onCancel?: () => void
}) {
  const tomorrow = useMemo(() => { const d = new Date(); d.setDate(d.getDate() + 1); return toISODate(d) }, [])
  const [subjects, setSubjects] = useState<string[]>(initial?.subjects ?? [])
  const [subjectDraft, setSubjectDraft] = useState('')
  const [subjectProblem, setSubjectProblem] = useState<string | null>(null)
  const [level, setLevel] = useState<Level>(initial?.level ?? 'primary')
  const [mode, setMode] = useState<LessonMode>(initial?.mode ?? 'offline')
  const [area, setArea] = useState(initial?.area ?? '')
  const [consent, setConsent] = useState(initial?.mode === 'online')
  const [slots, setSlots] = useState<WeeklyTime[]>(initial?.slots.map((s) => ({
    ...s, start_time: formatTime(s.start_time), end_time: formatTime(s.end_time),
  })) ?? [{ day_of_week: 0, start_time: '16:00', end_time: '17:00' }])
  const [startDate, setStartDate] = useState(initial?.start_date ?? tomorrow)
  const [endDate, setEndDate] = useState(initial?.end_date ?? '')
  const [billing, setBilling] = useState<BillingPeriod>(initial?.billing_period ?? 'weekly')
  const [price, setPrice] = useState(initial ? String(initial.price) : '')
  const [qualifications, setQualifications] = useState(initial?.qualifications ?? '')
  const [minCertificate, setMinCertificate] = useState<CertificateType | null>(initial?.min_certificate ?? null)
  const [other, setOther] = useState(initial?.other_requirements ?? '')
  const [strengths, setStrengths] = useState(initial?.child_strengths ?? '')
  const [weaknesses, setWeaknesses] = useState(initial?.child_weaknesses ?? '')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function addSubject(name: string) {
    if (!name.trim()) return
    const listed = listedSubject(name)
    if (!listed) {
      setSubjectProblem('Choose a subject from the list.')
      return
    }
    if (!subjects.includes(listed)) setSubjects([...subjects, listed])
    setSubjectProblem(null)
    setSubjectDraft('')
  }

  function setSlot(i: number, patch: Partial<WeeklyTime>) {
    setProblem(null)
    setSlots(slots.map((s, n) => (n === i ? { ...s, ...patch } : s)))
  }

  function check(): string | null {
    if (subjects.length === 0) return 'Add at least one subject'
    if (mode === 'offline' && !area.trim()) return 'Enter the area for lessons at home'
    if (slots.length === 0) return 'Add at least one lesson time'
    for (const s of slots) {
      if (!s.start_time || !s.end_time || toMinutes(s.end_time) <= toMinutes(s.start_time)) return 'Each lesson must end after it starts'
    }
    if (slots.some((s, i) => slots.slice(i + 1).some((t) => overlaps(s, t)))) return 'Two of your lesson times overlap'
    if (!startDate) return 'Choose a start date'
    if (endDate && endDate < startDate) return 'The end date must be after the start date'
    if (!(Number(price) > 0)) return 'Enter the price you will pay per lesson'
    if (!qualifications.trim()) return 'Describe the qualifications you want'
    if (mode === 'online' && !consent) return 'Please agree that online lessons will be recorded'
    if (strengths.trim().length < 10) return "Tell tutors your child's strengths (at least 10 characters)"
    if (weaknesses.trim().length < 10) return 'Tell tutors what your child finds hard (at least 10 characters)'
    return null
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const issue = check()
    setProblem(issue)
    if (issue) return
    setBusy(true)
    try {
      await onSubmit({
        subjects, level, mode, area: area.trim() || null, slots, start_date: startDate, end_date: endDate || null,
        billing_period: billing, qualifications: qualifications.trim(), min_certificate: minCertificate,
        other_requirements: other.trim() || null, price: Number(price),
        child_strengths: strengths.trim(), child_weaknesses: weaknesses.trim(),
        recording_consent: mode === 'online' && consent,
      })
    } catch {
      // The page shows the error; keep the form as it is.
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6" noValidate>
      <div className="space-y-2">
        <Label htmlFor="job-subject">Subjects</Label>
        <div className="flex flex-wrap gap-2">
          {subjects.map((s) => (
            <span key={s} className="flex items-center gap-1 rounded-full border bg-muted px-3 py-1 text-sm">
              {s}
              <button type="button" aria-label={`Remove ${s}`} onClick={() => setSubjects(subjects.filter((x) => x !== s))}>
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <Input id="job-subject" list="job-subject-list" placeholder="Pick a subject" value={subjectDraft}
            onChange={(e) => setSubjectDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSubject(subjectDraft) } }} />
          <datalist id="job-subject-list">{SUBJECTS.map((s) => <option key={s} value={s} />)}</datalist>
          <Button type="button" variant="outline" onClick={() => addSubject(subjectDraft)}>Add</Button>
        </div>
        {subjectProblem && <p role="alert" className="text-xs text-destructive">{subjectProblem}</p>}
        <p className="text-xs text-muted-foreground">One price covers every subject in a lesson.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="job-level">Level</Label>
          <Select value={level} onValueChange={(v) => setLevel(v as Level)}>
            <SelectTrigger id="job-level"><SelectValue /></SelectTrigger>
            <SelectContent>{LEVELS.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="job-price">Your price per lesson (₦)</Label>
          <Input id="job-price" type="number" min="1" step="100" inputMode="numeric" value={price}
            onChange={(e) => setPrice(e.target.value)} placeholder="e.g. 5000" />
          <p className="text-xs text-muted-foreground">Your total per lesson, including TutorLink&apos;s fee, is shown once you post.</p>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>Lessons</Label>
        <Choice label="Lesson mode" value={mode} onChange={setMode} options={[
          { value: 'offline', label: 'At home (offline)' }, { value: 'online', label: 'Online' },
        ]} />
        {mode === 'online' && <RecordingConsent checked={consent} onChange={setConsent} />}
      </div>
      {mode === 'offline' && (
        <div className="space-y-1.5">
          <Label htmlFor="job-area">Area</Label>
          <Input id="job-area" value={area} onChange={(e) => setArea(e.target.value)} placeholder="e.g. Lekki" maxLength={120} />
          <p className="text-xs text-muted-foreground">Tutors see the area only, never your address.</p>
        </div>
      )}

      <div className="space-y-2">
        <Label>Weekly lesson times</Label>
        {slots.map((s, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2">
            <Select value={String(s.day_of_week)} onValueChange={(d) => setSlot(i, { day_of_week: Number(d) })}>
              <SelectTrigger className="w-36" aria-label="Day"><SelectValue /></SelectTrigger>
              <SelectContent>{DAYS.map((d, n) => <SelectItem key={d} value={String(n)}>{d}</SelectItem>)}</SelectContent>
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
        <Button type="button" variant="outline" size="sm" onClick={() => setSlots([...slots, { ...slots[slots.length - 1] ?? { day_of_week: 0, start_time: '16:00', end_time: '17:00' } }])}>
          <Plus className="mr-1 h-4 w-4" aria-hidden />Add another lesson each week
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="job-start">Start date</Label>
          <Input id="job-start" type="date" min={tomorrow} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="job-end">End date (optional)</Label>
          <Input id="job-end" type="date" min={startDate} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>How often you pay</Label>
        <Choice label="How often you pay" value={billing} onChange={setBilling} options={BILLING_PERIODS} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="job-qualifications">Qualifications you want</Label>
          <Textarea id="job-qualifications" rows={3} maxLength={2000} value={qualifications}
            onChange={(e) => setQualifications(e.target.value)} placeholder="e.g. A science degree and two years of teaching" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="job-certificate">Minimum certificate (optional)</Label>
          <Select value={minCertificate ?? NONE} onValueChange={(v) => setMinCertificate(v === NONE ? null : (v as CertificateType))}>
            <SelectTrigger id="job-certificate"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>No minimum</SelectItem>
              {CERTIFICATES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="job-other">Other requirements (optional)</Label>
        <Textarea id="job-other" rows={2} maxLength={2000} value={other} onChange={(e) => setOther(e.target.value)}
          placeholder="e.g. Patient with young learners" />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="job-strengths">Your child&apos;s strengths</Label>
          <Textarea id="job-strengths" rows={3} maxLength={1000} value={strengths} onChange={(e) => setStrengths(e.target.value)}
            placeholder="e.g. Quick with mental arithmetic, loves reading" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="job-weaknesses">What your child finds hard</Label>
          <Textarea id="job-weaknesses" rows={3} maxLength={1000} value={weaknesses} onChange={(e) => setWeaknesses(e.target.value)}
            placeholder="e.g. Word problems and fractions" />
        </div>
      </div>

      {problem && <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{problem}</p>}
      <p className="rounded-md bg-accent px-3 py-2 text-sm">
        Every job post is checked by TutorLink before tutors can see it. We&apos;ll let you know when it&apos;s live.
      </p>
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>{busy ? 'Saving…' : submitLabel}</Button>
        {onCancel && <Button type="button" variant="outline" onClick={onCancel} disabled={busy}>Cancel</Button>}
      </div>
    </form>
  )
}

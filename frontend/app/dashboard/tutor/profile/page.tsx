'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { RatingSummary } from '@/components/reviews/StarRating'
import FormField from '@/components/shared/FormField'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { VettingStatusBadge } from '@/components/shared/StatusBadge'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { LEVELS, SUBJECTS, levelLabel } from '@/lib/format'
import { addSubject, removeSubject, upsertProfile } from '@/lib/tutors'
import type { Level, TutorProfile, TutorSubject } from '@/types'

const profileSchema = z.object({
  full_name: z.string().trim().min(2, 'Enter your full name').max(200),
  phone: z.string().trim().regex(/^\+?[0-9 ]{7,20}$/, 'Enter a valid phone number').optional().or(z.literal('')),
  bio: z.string().trim().max(2000).optional().or(z.literal('')),
  area: z.string().trim().min(2, 'Enter the area you cover').max(120),
  rate_per_session: z.coerce.number({ message: 'Enter your rate in Naira' }).positive('Rate must be more than ₦0'),
})
type ProfileInput = z.input<typeof profileSchema>
type ProfileValues = z.output<typeof profileSchema>

function SubjectsSection({ subjects, onChange }: { subjects: TutorSubject[]; onChange: () => Promise<void> }) {
  const toast = useToast()
  const [subject, setSubject] = useState('')
  const [level, setLevel] = useState<Level | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function add(e: React.FormEvent) {
    e.preventDefault()
    if (!subject.trim() || !level) { setError('Enter a subject and choose a level'); return }
    setBusy(true)
    setError(null)
    try {
      await addSubject(subject.trim(), level)
      setSubject('')
      setLevel('')
      toast.success('Subject added')
      await onChange()
    } catch (err) {
      setError(errorStatus(err) === 409 ? 'You already teach this subject at this level.' : errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function remove(s: TutorSubject) {
    try {
      await removeSubject(s.id)
      toast.success('Subject removed')
      await onChange()
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Subjects</CardTitle>
        <CardDescription>Parents can only book you for subjects and levels listed here.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {subjects.length === 0 ? (
          <p className="text-sm text-muted-foreground">No subjects yet. Add at least one so parents can book you.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {subjects.map((s) => (
              <li key={s.id}>
                <Badge variant="secondary" className="gap-1 py-1 pl-3 pr-1 text-sm">
                  {s.subject} • {levelLabel(s.level)}
                  <button type="button" onClick={() => remove(s)} aria-label={`Remove ${s.subject} (${levelLabel(s.level)})`}
                    className="rounded-full p-0.5 hover:bg-destructive/10 hover:text-destructive">
                    <X className="h-3.5 w-3.5" />
                  </button>
                </Badge>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={add} className="grid gap-3 sm:grid-cols-[1fr_200px_auto] sm:items-end" noValidate>
          <FormField id="new-subject" label="Subject">
            <Input id="new-subject" list="subject-suggestions" placeholder="e.g. Mathematics" value={subject} onChange={(e) => setSubject(e.target.value)} />
            <datalist id="subject-suggestions">{SUBJECTS.map((s) => <option key={s} value={s} />)}</datalist>
          </FormField>
          <FormField id="new-level" label="Level">
            <Select value={level} onValueChange={(v) => setLevel(v as Level)}>
              <SelectTrigger id="new-level"><SelectValue placeholder="Choose level" /></SelectTrigger>
              <SelectContent>{LEVELS.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}</SelectContent>
            </Select>
          </FormField>
          <Button type="submit" disabled={busy}>{busy ? 'Adding…' : 'Add Subject'}</Button>
        </form>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  )
}

export default function TutorProfilePage() {
  const { user, refresh } = useAuth()
  const toast = useToast()
  const profile = user?.profile as TutorProfile | null | undefined
  const { register, handleSubmit, reset, formState: { errors, isSubmitting, isDirty } } =
    useForm<ProfileInput, unknown, ProfileValues>({ resolver: zodResolver(profileSchema) })

  useEffect(() => {
    if (profile) {
      reset({
        full_name: profile.full_name,
        phone: profile.phone ?? '',
        bio: profile.bio ?? '',
        area: profile.area,
        rate_per_session: profile.rate_per_session,
      })
    }
  }, [profile, reset])

  async function onSubmit(values: ProfileValues) {
    try {
      await upsertProfile({ ...values, phone: values.phone || undefined, bio: values.bio || undefined })
      toast.success('Profile saved')
      await refresh()
    } catch (e) {
      toast.error(errorMessage(e))
    }
  }

  if (!user) return <LoadingSpinner />

  return (
    <>
      <PageHeader
        title="Profile & subjects"
        description="This is what parents see when they find you."
        action={profile && <div className="flex items-center gap-2 text-sm">Vetting status: <VettingStatusBadge status={profile.vetting_status} /></div>}
      />
      <div className="space-y-6">
        {profile && (
          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-2 pt-5">
              <span className="text-sm font-medium">Your rating from parents</span>
              <RatingSummary average={profile.average_rating} count={profile.rating_count} />
            </CardContent>
          </Card>
        )}
        <Card>
          <CardHeader><CardTitle className="text-lg">Your details</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
              <FormField id="full_name" label="Full name" error={errors.full_name?.message}>
                <Input id="full_name" {...register('full_name')} aria-invalid={!!errors.full_name} />
              </FormField>
              <FormField id="phone" label="Phone (optional)" error={errors.phone?.message}>
                <Input id="phone" type="tel" {...register('phone')} aria-invalid={!!errors.phone} />
              </FormField>
              <FormField id="area" label="Area you cover" error={errors.area?.message}>
                <Input id="area" {...register('area')} aria-invalid={!!errors.area} />
              </FormField>
              <FormField id="rate_per_session" label="Rate per session (₦)" error={errors.rate_per_session?.message}>
                <Input id="rate_per_session" type="number" inputMode="decimal" min={1} step="50" {...register('rate_per_session')} aria-invalid={!!errors.rate_per_session} />
              </FormField>
              <div className="sm:col-span-2">
                <FormField id="bio" label="About you" error={errors.bio?.message}>
                  <Textarea id="bio" rows={4} {...register('bio')} />
                </FormField>
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={isSubmitting || (!!profile && !isDirty)}>{isSubmitting ? 'Saving…' : 'Save profile'}</Button>
              </div>
            </form>
          </CardContent>
        </Card>
        {profile && <SubjectsSection subjects={profile.subjects} onChange={refresh} />}
      </div>
    </>
  )
}

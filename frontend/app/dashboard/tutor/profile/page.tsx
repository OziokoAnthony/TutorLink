'use client'

import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { RatingSummary } from '@/components/reviews/StarRating'
import ChangePasswordCard from '@/components/shared/ChangePasswordCard'
import FormField from '@/components/shared/FormField'
import PhotoUploader from '@/components/shared/PhotoUploader'
import OfferFields, { EMPTY_OFFER, offerProblem } from '@/components/tutors/OfferFields'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { VettingStatusBadge } from '@/components/shared/StatusBadge'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { createOffer, getMyOffers, removeOffer, updateOffer, upsertProfile, type OfferInput } from '@/lib/tutors'
import type { Offer, TutorProfile } from '@/types'

const profileSchema = z.object({
  first_name: z.string().trim().min(1, 'Enter your first name').max(100),
  middle_name: z.string().trim().max(100).optional().or(z.literal('')),
  surname: z.string().trim().min(1, 'Enter your surname').max(100),
  phone: z.string().trim().regex(/^\+?[0-9 ]{7,20}$/, 'Enter a valid phone number').optional().or(z.literal('')),
  bio: z.string().trim().max(2000).optional().or(z.literal('')),
  area: z.string().trim().min(2, 'Enter the area you cover').max(120),
})
type ProfileInput = z.input<typeof profileSchema>
type ProfileValues = z.output<typeof profileSchema>

function OfferEditor({ offer, onSaved, canRemove }: { offer: Offer | null; onSaved: () => Promise<void>; canRemove: boolean }) {
  const toast = useToast()
  const [value, setValue] = useState<OfferInput>(offer ?? EMPTY_OFFER)
  const [busy, setBusy] = useState(false)

  async function save() {
    const problem = offerProblem(value)
    if (problem) { toast.error(problem); return }
    setBusy(true)
    try {
      if (offer) await updateOffer(offer.id, value)
      else await createOffer(value)
      toast.success('Saved. Bookings you already accepted keep what was agreed.')
      if (!offer) setValue(EMPTY_OFFER)
      await onSaved()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!offer) return
    setBusy(true)
    try {
      await removeOffer(offer.id)
      toast.success('Removed')
      await onSaved()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <OfferFields value={value} onChange={setValue} />
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={save} disabled={busy}>{busy ? 'Saving…' : offer ? 'Save changes' : 'Add this offer'}</Button>
        {offer && canRemove && <Button type="button" variant="ghost" className="text-destructive" onClick={remove} disabled={busy}>Remove</Button>}
      </div>
    </div>
  )
}

function OffersSection() {
  const [offers, setOffers] = useState<Offer[] | null>(null)
  const load = useCallback(async () => setOffers(await getMyOffers()), [])
  useEffect(() => { load().catch(() => setOffers([])) }, [load])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">What you teach</CardTitle>
        <CardDescription>
          Each offer is one or more subjects taught together, the times you can teach them every week, and one price per lesson.
          Parents can only book times inside these. Change them anytime.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {offers === null ? <LoadingSpinner /> : offers.map((o) => (
          <OfferEditor key={`${o.id}-${o.price}-${o.subjects.join()}`} offer={o} onSaved={load} canRemove={offers.length > 1} />
        ))}
        <details>
          <summary className="cursor-pointer text-sm font-medium text-primary">Add another offer</summary>
          <div className="mt-3"><OfferEditor offer={null} onSaved={load} canRemove={false} /></div>
        </details>
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
        first_name: profile.first_name ?? '',
        middle_name: profile.middle_name ?? '',
        surname: profile.surname ?? '',
        phone: profile.phone ?? '',
        bio: profile.bio ?? '',
        area: profile.area,
      })
    }
  }, [profile, reset])

  async function onSubmit(values: ProfileValues) {
    try {
      await upsertProfile({
        ...values, middle_name: values.middle_name || undefined, phone: values.phone || undefined, bio: values.bio || undefined,
      })
      toast.success('Profile saved')
      await refresh()
    } catch (e) {
      toast.error(errorMessage(e))
    }
  }

  if (!user) return <LoadingSpinner />
  // Verified against the NIN record, so only an admin can change it (spec 4 R3.5).
  const nameLocked = Boolean(profile?.nin_verified_at)

  return (
    <>
      <PageHeader
        title="Profile & what you teach"
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
          <CardHeader><CardTitle className="text-lg">Profile picture</CardTitle><CardDescription>Parents see it when they find and book you.</CardDescription></CardHeader>
          <CardContent><PhotoUploader name={profile?.full_name ?? ''} /></CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Your details</CardTitle>
            {user.work_email && (
              <CardDescription>
                You log in with <span className="font-medium text-foreground">{user.work_email}</span>.
                It stays the same if you change your name. Messages go to {user.email}.
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2" noValidate>
              <p className="text-sm text-muted-foreground sm:col-span-2">
                {nameLocked
                  ? "Your name is verified against your NIN record and can't be changed. Contact TutorLink support if it needs correcting."
                  : 'Your name must match your NIN record exactly, including any middle name.'}
              </p>
              <div className="grid gap-4 sm:col-span-2 sm:grid-cols-3">
                <FormField id="first_name" label="First name" error={errors.first_name?.message}>
                  <Input id="first_name" readOnly={nameLocked} {...register('first_name')} aria-invalid={!!errors.first_name} />
                </FormField>
                <FormField id="middle_name" label="Middle name" error={errors.middle_name?.message}>
                  <Input id="middle_name" readOnly={nameLocked} {...register('middle_name')} aria-invalid={!!errors.middle_name} />
                </FormField>
                <FormField id="surname" label="Surname" error={errors.surname?.message}>
                  <Input id="surname" readOnly={nameLocked} {...register('surname')} aria-invalid={!!errors.surname} />
                </FormField>
              </div>
              <FormField id="phone" label="Phone (optional)" error={errors.phone?.message}>
                <Input id="phone" type="tel" {...register('phone')} aria-invalid={!!errors.phone} />
              </FormField>
              <FormField id="area" label="Area you cover" error={errors.area?.message}>
                <Input id="area" {...register('area')} aria-invalid={!!errors.area} />
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
        {profile && <OffersSection />}
        <ChangePasswordCard description="Replace the password we emailed you when you registered." />
      </div>
    </>
  )
}

'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import FormField from '@/components/shared/FormField'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { register as registerUser } from '@/lib/auth'
import type { OfferInput } from '@/lib/tutors'
import { cn } from '@/lib/utils'
import OfferFields, { EMPTY_OFFER, offerProblem } from '@/components/tutors/OfferFields'

const optionalText = z.string().trim().max(200).optional().or(z.literal(''))

const common = {
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters').max(72, 'Password is too long'),
  phone: z.string().trim().regex(/^\+?[0-9 ]{7,20}$/, 'Enter a valid phone number').optional().or(z.literal('')),
}

const schema = z.discriminatedUnion('role', [
  z.object({
    role: z.literal('parent'),
    ...common,
    full_name: z.string().trim().min(2, 'Enter your full name').max(200),
    address: optionalText,
  }),
  z.object({
    role: z.literal('tutor'),
    ...common,
    first_name: z.string().trim().min(1, 'Enter your first name').max(100),
    surname: z.string().trim().min(1, 'Enter your surname').max(100),
    area: z.string().trim().min(2, 'Enter the area you cover').max(120),
    bio: z.string().trim().max(2000).optional().or(z.literal('')),
  }),
])
type RegisterValues = z.input<typeof schema>
type RegisterOutput = z.output<typeof schema>
type Role = RegisterValues['role']

export default function RegisterPage() {
  const router = useRouter()
  const toast = useToast()
  const [formError, setFormError] = useState<string | null>(null)
  const [offer, setOffer] = useState<OfferInput>(EMPTY_OFFER)
  const [workEmail, setWorkEmail] = useState<string | null>(null)
  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } =
    useForm<RegisterValues, unknown, RegisterOutput>({
      resolver: zodResolver(schema),
      defaultValues: { role: 'parent' },
      shouldUnregister: true, // drop the other role's fields when switching
    })
  const role = watch('role')
  // Field errors for tutor-only fields live on the tutor branch of the union.
  const tutorErrors = errors as Partial<Record<'first_name' | 'surname' | 'area' | 'bio', { message?: string }>>
  const parentErrors = errors as Partial<Record<'full_name' | 'address', { message?: string }>>

  async function onSubmit(values: RegisterOutput) {
    setFormError(null)
    const problem = values.role === 'tutor' ? offerProblem(offer) : null
    if (problem) {
      setFormError(`What you teach: ${problem.toLowerCase()}.`)
      return
    }
    try {
      const { work_email } = await registerUser({
        ...values,
        phone: values.phone || undefined,
        ...(values.role === 'parent'
          ? { address: values.address || undefined }
          : { bio: values.bio || undefined, offers: [offer] }),
      })
      toast.success('Account created!')
      if (work_email) setWorkEmail(work_email) // tutors must see the email they'll log in with
      else router.push('/login')
    } catch (error) {
      setFormError(errorStatus(error) === 409 ? 'Email already registered' : errorMessage(error))
    }
  }

  if (workEmail) return <WorkEmailCreated email={workEmail} />

  return (
    <div className="mx-auto flex max-w-xl px-4 py-12">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Create your account</CardTitle>
          <CardDescription>Parents find tutors; tutors get booked for weekly lessons. You&apos;ll add a profile picture after signing in.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div role="radiogroup" aria-label="Account type" className="grid grid-cols-2 gap-1 rounded-lg bg-muted p-1">
              {(['parent', 'tutor'] as Role[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  role="radio"
                  aria-checked={role === r}
                  onClick={() => setValue('role', r)}
                  className={cn(
                    'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    role === r ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {r === 'parent' ? "I'm a Parent" : "I'm a Tutor"}
                </button>
              ))}
            </div>
            <input type="hidden" {...register('role')} />

            {role === 'parent' ? (
              <FormField id="full_name" label="Full name" error={parentErrors.full_name?.message}>
                <Input id="full_name" autoComplete="name" {...register('full_name')} aria-invalid={!!parentErrors.full_name} />
              </FormField>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="first_name" label="First name" error={tutorErrors.first_name?.message}>
                  <Input id="first_name" autoComplete="given-name" {...register('first_name')} aria-invalid={!!tutorErrors.first_name} />
                </FormField>
                <FormField id="surname" label="Surname" error={tutorErrors.surname?.message}>
                  <Input id="surname" autoComplete="family-name" {...register('surname')} aria-invalid={!!tutorErrors.surname} />
                </FormField>
              </div>
            )}
            <FormField id="email" label={role === 'tutor' ? 'Your own email' : 'Email'} error={errors.email?.message}
              hint={role === 'tutor' ? "We'll send your messages here. You'll get a TutorLink email to log in with." : undefined}>
              <Input id="email" type="email" autoComplete="email" {...register('email')} aria-invalid={!!errors.email} />
            </FormField>
            <FormField id="password" label="Password" error={errors.password?.message} hint="At least 8 characters.">
              <Input id="password" type="password" autoComplete="new-password" {...register('password')} aria-invalid={!!errors.password} />
            </FormField>
            <FormField id="phone" label="Phone (optional)" error={errors.phone?.message}>
              <Input id="phone" type="tel" autoComplete="tel" placeholder="0801 234 5678" {...register('phone')} aria-invalid={!!errors.phone} />
            </FormField>

            {role === 'parent' ? (
              <FormField id="address" label="Home address (optional)" error={parentErrors.address?.message}>
                <Textarea id="address" rows={2} autoComplete="street-address" {...register('address')} />
              </FormField>
            ) : (
              <>
                <FormField id="area" label="Area you cover" error={tutorErrors.area?.message} hint="e.g. Lekki, Yaba, Ikeja">
                  <Input id="area" {...register('area')} aria-invalid={!!tutorErrors.area} />
                </FormField>
                <fieldset className="space-y-3 rounded-lg border p-4">
                  <legend className="px-1 text-sm font-medium">What you teach</legend>
                  <p className="text-xs text-muted-foreground">
                    Pick the subjects you teach together in one lesson, when you can teach, and one price per lesson.
                    You can add more offers and change them anytime from your dashboard.
                  </p>
                  <OfferFields value={offer} onChange={setOffer} />
                </fieldset>
                <FormField id="bio" label="About you (optional)" error={tutorErrors.bio?.message}>
                  <Textarea id="bio" rows={3} placeholder="Your experience, qualifications and teaching style" {...register('bio')} />
                </FormField>
              </>
            )}

            {formError && <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Creating account…' : 'Create account'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Already have an account? <Link href="/login" className="font-medium text-primary hover:underline">Log in</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

/** Shown once to a new tutor: the work email TutorLink assigned, which is their only login. */
function WorkEmailCreated({ email }: { email: string }) {
  const toast = useToast()
  async function copy() {
    try {
      await navigator.clipboard.writeText(email)
      toast.success('Copied')
    } catch {
      toast.error("Couldn't copy. Please write it down.")
    }
  }
  return (
    <div className="mx-auto flex max-w-xl px-4 py-12">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Your TutorLink email</CardTitle>
          <CardDescription>
            This is your login. Use it with your password every time you log in. We&apos;ve also sent it to your own email.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-muted px-4 py-3">
            <span className="break-all font-mono text-lg font-semibold">{email}</span>
            <Button type="button" variant="outline" size="sm" onClick={copy}>Copy</Button>
          </div>
          <Button asChild className="w-full"><Link href="/login">Log in</Link></Button>
        </CardContent>
      </Card>
    </div>
  )
}

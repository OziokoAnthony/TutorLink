'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import FormField from '@/components/shared/FormField'
import GoogleButton from '@/components/auth/GoogleButton'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { register as registerUser, registerWithGoogle } from '@/lib/auth'
import { readCredential, takeForSignUp, type GoogleCredential } from '@/lib/google'
import type { OfferInput } from '@/lib/tutors'
import { cn } from '@/lib/utils'
import OfferFields, { EMPTY_OFFER, offerProblem } from '@/components/tutors/OfferFields'

const optionalText = z.string().trim().max(200).optional().or(z.literal(''))
const phone = z.string().trim().regex(/^\+?[0-9 ]{7,20}$/, 'Enter a valid phone number').optional().or(z.literal(''))

/** Parents and tutors sign up the same way: any email and a password, or Google. With Google, the email
 * comes from the Google account and there's no password (spec 4 R1.1, R1.4). */
function makeSchema(withGoogle: boolean) {
  const emailAndPassword = {
    email: z.string().trim().email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters').max(72, 'Password is too long'),
  }
  // Both are optional in the type; without Google they're required by the parser.
  const account = (withGoogle
    ? { email: emailAndPassword.email.optional(), password: emailAndPassword.password.optional() }
    : emailAndPassword) as { email: z.ZodOptional<z.ZodString>; password: z.ZodOptional<z.ZodString> }
  return z.discriminatedUnion('role', [
    z.object({
      role: z.literal('parent'),
      ...account,
      phone,
      full_name: z.string().trim().min(2, 'Enter your full name').max(200),
      address: optionalText,
    }),
    z.object({
      role: z.literal('tutor'),
      ...account,
      phone,
      first_name: z.string().trim().min(1, 'Enter your first name').max(100),
      middle_name: z.string().trim().max(100).optional().or(z.literal('')),
      surname: z.string().trim().min(1, 'Enter your surname').max(100),
      area: z.string().trim().min(2, 'Enter the area you cover').max(120),
      bio: z.string().trim().max(2000).optional().or(z.literal('')),
    }),
  ])
}
type Schema = ReturnType<typeof makeSchema>
type RegisterValues = z.input<Schema>
type RegisterOutput = z.output<Schema>
type Role = RegisterValues['role']
type FieldName = 'email' | 'password' | 'full_name' | 'address' | 'first_name' | 'middle_name' | 'surname' | 'area' | 'bio' | 'phone'

export default function RegisterPage() {
  return (
    <Suspense>
      <Register />
    </Suspense>
  )
}

function Register() {
  const params = useSearchParams()
  const toast = useToast()
  const { enter, login } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const [offer, setOffer] = useState<OfferInput>(EMPTY_OFFER)
  const [google, setGoogle] = useState<GoogleCredential | null>(null)
  const [useGooglePhoto, setUseGooglePhoto] = useState(true)
  const schema = useMemo(() => makeSchema(google !== null), [google])
  const { register, handleSubmit, watch, setValue, getValues, formState: { errors, isSubmitting } } =
    useForm<RegisterValues, unknown, RegisterOutput>({
      resolver: zodResolver(schema),
      defaultValues: { role: params.get('role') === 'tutor' ? 'tutor' : 'parent' },
      shouldUnregister: true, // drop the other role's fields when switching
    })
  const role = watch('role')
  const fieldErrors = errors as Partial<Record<FieldName, { message?: string }>>

  // A parent sent here from the login page's Google button keeps the Google account they chose.
  useEffect(() => {
    if (params.get('with') !== 'google') return
    const pending = takeForSignUp()
    if (pending) applyCredential(pending, 'parent')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function applyCredential(credential: GoogleCredential, forRole: Role) {
    setFormError(null)
    setGoogle(credential)
    setValue('role', forRole)
    // Prefill the names from Google (R1.1); they can still correct them. setTimeout: the role's fields
    // mount on the next render.
    setTimeout(() => {
      if (forRole === 'tutor') {
        if (!getValues('first_name')) setValue('first_name', credential.given_name)
        if (!getValues('surname')) setValue('surname', credential.family_name)
      } else if (!getValues('full_name')) {
        setValue('full_name', credential.name)
      }
    })
  }

  function onGoogle(idToken: string) {
    const credential = readCredential(idToken)
    if (credential) applyCredential(credential, role)
    else setFormError('Google sign-in failed. Please try again.')
  }

  function switchRole(r: Role) {
    setValue('role', r)
    setFormError(null)
  }

  async function onSubmit(values: RegisterOutput) {
    setFormError(null)
    const problem = values.role === 'tutor' ? offerProblem(offer) : null
    if (problem) {
      setFormError(`What you teach: ${problem.toLowerCase()}.`)
      return
    }
    const profile = values.role === 'parent'
      ? { role: values.role, full_name: values.full_name, phone: values.phone || undefined, address: values.address || undefined }
      : {
          role: values.role, first_name: values.first_name, middle_name: values.middle_name || undefined,
          surname: values.surname, phone: values.phone || undefined,
          area: values.area, bio: values.bio || undefined, offers: [offer],
        }
    try {
      if (google) {
        await registerWithGoogle({
          ...profile, id_token: google.token, use_google_photo: Boolean(google.picture) && useGooglePhoto,
        })
        toast.success('Account created!')
        await enter()
      } else if (values.email && values.password) {
        await registerUser({ ...profile, email: values.email, password: values.password })
        toast.success('Account created!')
        await login(values.email, values.password)
      }
    } catch (error) {
      setFormError(errorMessage(error))
    }
  }

  return (
    <div className="mx-auto flex max-w-xl px-4 py-12">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Create your account</CardTitle>
          <CardDescription>Parents find tutors; tutors get booked for weekly lessons. You&apos;ll add a profile picture after signing in.</CardDescription>
          {params.get('reason') === 'tutors' && (
            <p className="rounded-md bg-accent px-3 py-2 text-sm">
              Create a free parent account to see our tutors. Already registered?{' '}
              <Link href="/login" className="font-medium text-primary hover:underline">Log in</Link>
            </p>
          )}
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
                  onClick={() => switchRole(r)}
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

            {google ? (
              <GoogleAccount credential={google} useGooglePhoto={useGooglePhoto} onUseGooglePhoto={setUseGooglePhoto}
                onChange={() => setGoogle(null)} />
            ) : (
              <>
                <GoogleButton onCredential={onGoogle} text="signup_with" />
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="h-px flex-1 bg-border" />or sign up with your email<span className="h-px flex-1 bg-border" />
                </div>
              </>
            )}

            <>
                {role === 'parent' ? (
                  <FormField id="full_name" label="Full name" error={fieldErrors.full_name?.message}>
                    <Input id="full_name" autoComplete="name" {...register('full_name')} aria-invalid={!!fieldErrors.full_name} />
                  </FormField>
                ) : (
                  <fieldset className="space-y-3">
                    <legend className="text-sm text-muted-foreground">
                      Enter your name <strong className="text-foreground">exactly as it appears on your NIN record</strong>.
                      We check it against your NIN, and it can&apos;t be changed once verified.
                    </legend>
                    <div className="grid gap-4 sm:grid-cols-3">
                      <FormField id="first_name" label="First name" error={fieldErrors.first_name?.message}>
                        <Input id="first_name" autoComplete="given-name" {...register('first_name')} aria-invalid={!!fieldErrors.first_name} />
                      </FormField>
                      <FormField id="middle_name" label="Middle name" hint="Only if your NIN record has one." error={fieldErrors.middle_name?.message}>
                        <Input id="middle_name" autoComplete="additional-name" {...register('middle_name')} aria-invalid={!!fieldErrors.middle_name} />
                      </FormField>
                      <FormField id="surname" label="Surname" error={fieldErrors.surname?.message}>
                        <Input id="surname" autoComplete="family-name" {...register('surname')} aria-invalid={!!fieldErrors.surname} />
                      </FormField>
                    </div>
                  </fieldset>
                )}
                {!google && (
                  <>
                    <FormField id="email" label="Email" error={fieldErrors.email?.message}
                      hint="Any email you use works: Gmail, Yahoo, Outlook, iCloud and others. You'll log in with it.">
                      <Input id="email" type="email" autoComplete="email" {...register('email')} aria-invalid={!!fieldErrors.email} />
                    </FormField>
                    <FormField id="password" label="Password" error={fieldErrors.password?.message} hint="At least 8 characters.">
                      <Input id="password" type="password" autoComplete="new-password" {...register('password')} aria-invalid={!!fieldErrors.password} />
                    </FormField>
                  </>
                )}
                <FormField id="phone" label="Phone (optional)" error={fieldErrors.phone?.message}>
                  <Input id="phone" type="tel" autoComplete="tel" placeholder="0801 234 5678" {...register('phone')} aria-invalid={!!fieldErrors.phone} />
                </FormField>

                {role === 'parent' ? (
                  <FormField id="address" label="Home address (optional)" error={fieldErrors.address?.message}>
                    <Textarea id="address" rows={2} autoComplete="street-address" {...register('address')} />
                  </FormField>
                ) : (
                  <>
                    <FormField id="area" label="Area you cover" error={fieldErrors.area?.message} hint="e.g. Lekki, Yaba, Ikeja">
                      <Input id="area" {...register('area')} aria-invalid={!!fieldErrors.area} />
                    </FormField>
                    <fieldset className="space-y-3 rounded-lg border p-4">
                      <legend className="px-1 text-sm font-medium">What you teach</legend>
                      <p className="text-xs text-muted-foreground">
                        Pick the subjects you teach together in one lesson, when you can teach, and one price per lesson.
                        You can add more offers and change them anytime from your dashboard.
                      </p>
                      <OfferFields value={offer} onChange={setOffer} />
                    </fieldset>
                    <FormField id="bio" label="About you (optional)" error={fieldErrors.bio?.message}>
                      <Textarea id="bio" rows={3} placeholder="Your experience, qualifications and teaching style" {...register('bio')} />
                    </FormField>
                  </>
                )}
            </>

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

/** The Google account being signed up with, and whether its photo starts as the profile picture (R1b.3). */
function GoogleAccount({ credential, useGooglePhoto, onUseGooglePhoto, onChange }: {
  credential: GoogleCredential
  useGooglePhoto: boolean
  onUseGooglePhoto: (use: boolean) => void
  onChange: () => void
}) {
  return (
    <div className="space-y-3 rounded-lg border bg-muted/40 p-4">
      <div className="flex items-center gap-3">
        {credential.picture && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={credential.picture} alt="" referrerPolicy="no-referrer" className="h-10 w-10 rounded-full object-cover" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">Signing up with Google as</p>
          <p className="truncate text-sm font-medium">{credential.email}</p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onChange}>Change</Button>
      </div>
      {credential.picture && (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={useGooglePhoto} onChange={(e) => onUseGooglePhoto(e.target.checked)}
            className="h-4 w-4 rounded border-input" />
          Use this photo as my profile picture (you can change it later)
        </label>
      )}
    </div>
  )
}

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
import { cn } from '@/lib/utils'

const optionalText = z.string().trim().max(200).optional().or(z.literal(''))

const common = {
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters').max(72, 'Password is too long'),
  full_name: z.string().trim().min(2, 'Enter your full name').max(200),
  phone: z.string().trim().regex(/^\+?[0-9 ]{7,20}$/, 'Enter a valid phone number').optional().or(z.literal('')),
}

const schema = z.discriminatedUnion('role', [
  z.object({ role: z.literal('parent'), ...common, address: optionalText }),
  z.object({
    role: z.literal('tutor'),
    ...common,
    area: z.string().trim().min(2, 'Enter the area you cover').max(120),
    rate_per_session: z.coerce.number({ message: 'Enter your rate in Naira' })
      .positive('Rate must be more than ₦0').max(10_000_000, 'Rate is too high'),
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
  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } =
    useForm<RegisterValues, unknown, RegisterOutput>({
      resolver: zodResolver(schema),
      defaultValues: { role: 'parent' },
      shouldUnregister: true, // drop the other role's fields when switching
    })
  const role = watch('role')
  // Field errors for tutor-only fields live on the tutor branch of the union.
  const tutorErrors = errors as Partial<Record<'area' | 'rate_per_session' | 'bio', { message?: string }>>
  const parentErrors = errors as Partial<Record<'address', { message?: string }>>

  async function onSubmit(values: RegisterOutput) {
    setFormError(null)
    try {
      await registerUser({
        ...values,
        phone: values.phone || undefined,
        ...(values.role === 'parent'
          ? { address: values.address || undefined }
          : { bio: values.bio || undefined }),
      })
      toast.success('Account created!')
      router.push('/login')
    } catch (error) {
      setFormError(errorStatus(error) === 409 ? 'Email already registered' : errorMessage(error))
    }
  }

  return (
    <div className="mx-auto flex max-w-lg px-4 py-12">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Create your account</CardTitle>
          <CardDescription>Parents find tutors; tutors get booked for weekly lessons.</CardDescription>
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

            <FormField id="full_name" label="Full name" error={errors.full_name?.message}>
              <Input id="full_name" autoComplete="name" {...register('full_name')} aria-invalid={!!errors.full_name} />
            </FormField>
            <FormField id="email" label="Email" error={errors.email?.message}>
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
                <FormField id="rate_per_session" label="Rate per session (₦)" error={tutorErrors.rate_per_session?.message}>
                  <Input id="rate_per_session" type="number" inputMode="decimal" min={1} step="50" {...register('rate_per_session')} aria-invalid={!!tutorErrors.rate_per_session} />
                </FormField>
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

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
import FormField from '@/components/shared/FormField'
import GoogleButton from '@/components/auth/GoogleButton'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage, errorStatus } from '@/lib/api'
import { keepForSignUp } from '@/lib/google'

const schema = z.object({
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})
type LoginValues = z.infer<typeof schema>

export default function LoginPage() {
  const router = useRouter()
  const { login, loginWithGoogle } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(values: LoginValues) {
    setFormError(null)
    try {
      await login(values.email, values.password) // stores cookie and redirects by role
    } catch (error) {
      setFormError(errorMessage(error))
    }
  }

  async function onGoogle(idToken: string) {
    setFormError(null)
    try {
      await loginWithGoogle(idToken)
    } catch (error) {
      if (errorStatus(error) === 404) {
        // No account for this Google email yet: they sign up with it (spec 4 R1.4).
        keepForSignUp(idToken)
        router.push('/register?with=google')
        return
      }
      // Admins are told to use their password.
      setFormError(errorMessage(error))
    }
  }

  return (
    <div className="mx-auto flex max-w-md px-4 py-16">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Log in</CardTitle>
          <CardDescription>Welcome back to TutorLink.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <FormField id="email" label="Email" error={errors.email?.message}>
              <Input id="email" type="email" autoComplete="email" {...register('email')} aria-invalid={!!errors.email} />
            </FormField>
            <FormField id="password" label="Password" error={errors.password?.message}>
              <Input id="password" type="password" autoComplete="current-password" {...register('password')} aria-invalid={!!errors.password} />
            </FormField>
            <p className="-mt-2 text-right text-sm">
              <Link href="/forgot-password" className="text-primary hover:underline">Forgot password?</Link>
            </p>
            {formError && <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Logging in…' : 'Log in'}
            </Button>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="h-px flex-1 bg-border" />or<span className="h-px flex-1 bg-border" />
            </div>
            <GoogleButton onCredential={onGoogle} />
            <p className="text-center text-sm text-muted-foreground">
              New to TutorLink? <Link href="/register" className="font-medium text-primary hover:underline">Create an account</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

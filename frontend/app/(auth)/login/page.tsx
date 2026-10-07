'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import FormField from '@/components/shared/FormField'
import { useAuth } from '@/hooks/useAuth'
import { errorMessage } from '@/lib/api'

const schema = z.object({
  email: z.string().trim().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})
type LoginValues = z.infer<typeof schema>

export default function LoginPage() {
  const { login } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(values: LoginValues) {
    setFormError(null)
    try {
      await login(values.email, values.password) // stores cookie and redirects by role
    } catch (error) {
      // The backend's 401 text is shown as is: it tells a tutor who used their own email which one to use.
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
            <FormField id="email" label="Email" error={errors.email?.message}
              hint="Tutors: use your TutorLink email, like o.anthony@tutorlink.com.">
              <Input id="email" type="email" autoComplete="email" {...register('email')} aria-invalid={!!errors.email} />
            </FormField>
            <FormField id="password" label="Password" error={errors.password?.message}>
              <Input id="password" type="password" autoComplete="current-password" {...register('password')} aria-invalid={!!errors.password} />
            </FormField>
            {formError && <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Logging in…' : 'Log in'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              New to TutorLink? <Link href="/register" className="font-medium text-primary hover:underline">Create an account</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

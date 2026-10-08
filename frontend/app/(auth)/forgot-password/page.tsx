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
import { errorMessage } from '@/lib/api'
import { forgotPassword } from '@/lib/auth'

const schema = z.object({ email: z.string().trim().email('Enter a valid email address') })
type Values = z.infer<typeof schema>

/** Spec 4 R0.7. The answer is the same whether or not the email has an account. */
export default function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) })

  async function onSubmit(values: Values) {
    setFormError(null)
    try {
      await forgotPassword(values.email)
      setSentTo(values.email)
    } catch (error) {
      setFormError(errorMessage(error))
    }
  }

  return (
    <div className="mx-auto flex max-w-md px-4 py-16">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Forgot password?</CardTitle>
          <CardDescription>
            Enter your own email. Tutors: use the Google email you signed up with, not your TutorLink email.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sentTo ? (
            <div className="space-y-4">
              <p className="text-sm">
                If a TutorLink account uses <strong className="break-all">{sentTo}</strong>, we&apos;ve sent it a link
                to set a new password. The link works once and expires in 1 hour. Tutors will also find their
                TutorLink email in it.
              </p>
              <Button asChild variant="outline" className="w-full"><Link href="/login">Back to log in</Link></Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField id="email" label="Your email" error={errors.email?.message}>
                <Input id="email" type="email" autoComplete="email" {...register('email')} aria-invalid={!!errors.email} />
              </FormField>
              {formError && <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Sending…' : 'Send me a link'}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                <Link href="/login" className="font-medium text-primary hover:underline">Back to log in</Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

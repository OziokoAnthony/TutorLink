'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import FormField from '@/components/shared/FormField'
import { errorMessage } from '@/lib/api'
import { resetPassword } from '@/lib/auth'

const schema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters').max(72, 'Password is too long'),
  confirm: z.string(),
}).refine((v) => v.password === v.confirm, { message: "The passwords don't match", path: ['confirm'] })
type Values = z.infer<typeof schema>

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPassword />
    </Suspense>
  )
}

/** Opened from the "Forgot password?" email (spec 4 R0.7). */
function ResetPassword() {
  const token = useSearchParams().get('token')
  const [done, setDone] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) })

  async function onSubmit(values: Values) {
    if (!token) return
    setFormError(null)
    try {
      await resetPassword(token, values.password)
      setDone(true)
    } catch (error) {
      setFormError(errorMessage(error))
    }
  }

  return (
    <div className="mx-auto flex max-w-md px-4 py-16">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl">Set a new password</CardTitle>
          <CardDescription>Your old password stops working once you save the new one.</CardDescription>
        </CardHeader>
        <CardContent>
          {done ? (
            <div className="space-y-4">
              <p className="text-sm">Your password is set. Log in with your email and new password.</p>
              <Button asChild className="w-full"><Link href="/login">Log in</Link></Button>
            </div>
          ) : !token ? (
            <div className="space-y-4">
              <p className="text-sm">This link is incomplete. Please open the link from the email again, or ask for a new one.</p>
              <Button asChild variant="outline" className="w-full"><Link href="/forgot-password">Ask for a new link</Link></Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField id="password" label="New password" error={errors.password?.message} hint="At least 8 characters.">
                <Input id="password" type="password" autoComplete="new-password" {...register('password')} aria-invalid={!!errors.password} />
              </FormField>
              <FormField id="confirm" label="New password again" error={errors.confirm?.message}>
                <Input id="confirm" type="password" autoComplete="new-password" {...register('confirm')} aria-invalid={!!errors.confirm} />
              </FormField>
              {formError && (
                <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {formError} <Link href="/forgot-password" className="font-medium underline">Ask for a new link</Link>
                </p>
              )}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Saving…' : 'Save new password'}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

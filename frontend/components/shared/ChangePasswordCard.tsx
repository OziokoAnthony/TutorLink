'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import FormField from '@/components/shared/FormField'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { changePassword } from '@/lib/auth'

const schema = z.object({
  current_password: z.string().min(1, 'Enter your current password'),
  new_password: z.string().min(8, 'Password must be at least 8 characters').max(72, 'Password is too long'),
  confirm: z.string(),
}).refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: "Passwords don't match" })
type Values = z.infer<typeof schema>

/** Lets a user replace their password; tutors use it to replace the one emailed to them. */
export default function ChangePasswordCard({ description }: { description?: string }) {
  const toast = useToast()
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm<Values>({ resolver: zodResolver(schema) })

  async function onSubmit(values: Values) {
    try {
      await changePassword(values.current_password, values.new_password)
      toast.success('Password changed')
      reset()
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Password</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-3" noValidate>
          <FormField id="current_password" label="Current password" error={errors.current_password?.message}>
            <Input id="current_password" type="password" autoComplete="current-password" {...register('current_password')} aria-invalid={!!errors.current_password} />
          </FormField>
          <FormField id="new_password" label="New password" error={errors.new_password?.message}>
            <Input id="new_password" type="password" autoComplete="new-password" {...register('new_password')} aria-invalid={!!errors.new_password} />
          </FormField>
          <FormField id="confirm" label="Repeat new password" error={errors.confirm?.message}>
            <Input id="confirm" type="password" autoComplete="new-password" {...register('confirm')} aria-invalid={!!errors.confirm} />
          </FormField>
          <div className="sm:col-span-3">
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : 'Change password'}</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

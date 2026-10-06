'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import FormField from '@/components/shared/FormField'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { DAYS, levelLabel } from '@/lib/format'
import { createSchedule } from '@/lib/schedules'
import type { TutorProfile } from '@/types'

const CLASH_MESSAGE = 'This tutor is already booked at that time. Please choose another slot.'

const schema = z.object({
  day_of_week: z.string().min(1, 'Choose a day'),
  start_time: z.string().min(1, 'Choose a start time'),
  end_time: z.string().min(1, 'Choose an end time'),
  subject_id: z.string().min(1, 'Choose a subject'),
}).refine((v) => !v.start_time || !v.end_time || v.end_time > v.start_time, {
  message: 'End time must be after start time',
  path: ['end_time'],
})
type BookingValues = z.infer<typeof schema>

/** "Book recurring slot" modal. */
export default function BookingForm({ tutor, open, onOpenChange }: {
  tutor: TutorProfile
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()
  const toast = useToast()
  const [clashError, setClashError] = useState<string | null>(null)
  const { register, control, handleSubmit, formState: { errors, isSubmitting } } = useForm<BookingValues>({
    resolver: zodResolver(schema),
    defaultValues: { day_of_week: '', start_time: '15:00', end_time: '16:00', subject_id: '' },
  })

  async function onSubmit(values: BookingValues) {
    setClashError(null)
    const subject = tutor.subjects.find((s) => s.id === values.subject_id)!
    try {
      await createSchedule({
        tutor_id: tutor.user_id,
        day_of_week: Number(values.day_of_week),
        start_time: values.start_time,
        end_time: values.end_time,
        subject: subject.subject,
        level: subject.level,
      })
      toast.success('Session booked!')
      router.push('/dashboard/parent/schedules')
    } catch (error) {
      if (errorStatus(error) === 409) setClashError(CLASH_MESSAGE)
      else toast.error(errorMessage(error))
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !isSubmitting && onOpenChange(next)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Book a weekly session with {tutor.full_name}</DialogTitle>
          <DialogDescription>The lesson repeats every week at this time. You can cancel anytime.</DialogDescription>
        </DialogHeader>
        <form id="booking-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField id="booking-subject" label="Subject" error={errors.subject_id?.message}>
            <Controller control={control} name="subject_id" render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="booking-subject" aria-invalid={!!errors.subject_id}><SelectValue placeholder="Choose a subject" /></SelectTrigger>
                <SelectContent>
                  {tutor.subjects.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.subject} • {levelLabel(s.level)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )} />
          </FormField>
          <FormField id="booking-day" label="Day of week" error={errors.day_of_week?.message}>
            <Controller control={control} name="day_of_week" render={({ field }) => (
              <Select value={field.value} onValueChange={(v) => { field.onChange(v); setClashError(null) }}>
                <SelectTrigger id="booking-day" aria-invalid={!!errors.day_of_week}><SelectValue placeholder="Choose a day" /></SelectTrigger>
                <SelectContent>
                  {DAYS.map((day, i) => <SelectItem key={day} value={String(i)}>{day}</SelectItem>)}
                </SelectContent>
              </Select>
            )} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField id="booking-start" label="Start time" error={errors.start_time?.message}>
              <Input id="booking-start" type="time" {...register('start_time', { onChange: () => setClashError(null) })} />
            </FormField>
            <FormField id="booking-end" label="End time" error={errors.end_time?.message}>
              <Input id="booking-end" type="time" {...register('end_time', { onChange: () => setClashError(null) })} />
            </FormField>
          </div>
          {clashError && <p role="alert" className="-mt-2 text-sm text-destructive">{clashError}</p>}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" form="booking-form" disabled={isSubmitting}>{isSubmitting ? 'Booking…' : 'Book weekly session'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

'use client'

import { useEffect, useMemo } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import FormField from '@/components/shared/FormField'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { DAYS, formatTime, latestDateOnWeekday, parseDate, toISODate, todayDayOfWeek } from '@/lib/format'
import { logSession } from '@/lib/sessions'
import type { Schedule, Session } from '@/types'

const schema = z.object({
  schedule_id: z.string().min(1, 'Choose a schedule'),
  session_date: z.string().min(1, 'Choose the lesson date'),
  topic_covered: z.string().trim().min(2, 'Describe what you covered').max(2000),
  homework: z.string().trim().max(2000).optional().or(z.literal('')),
})
type LogValues = z.infer<typeof schema>

function scheduleLabel(s: Schedule): string {
  return `${DAYS[s.day_of_week]} ${formatTime(s.start_time)}–${formatTime(s.end_time)} · ${s.subject} · ${s.parent_name ?? 'Parent'}`
}

/** Tutor logs topic + homework for a lesson they taught. */
export default function LogSessionForm({ schedules, onLogged }: { schedules: Schedule[]; onLogged: (session: Session) => void }) {
  const toast = useToast()
  const today = toISODate(new Date())

  // Today's lessons first, then the rest of the week in order.
  const ordered = useMemo(() => {
    const t = todayDayOfWeek()
    return [...schedules].sort((a, b) => (a.day_of_week - t + 7) % 7 - (b.day_of_week - t + 7) % 7
      || a.start_time.localeCompare(b.start_time))
  }, [schedules])

  const defaults = (): LogValues => {
    const first = ordered[0]
    return {
      schedule_id: first?.id ?? '',
      session_date: first ? latestDateOnWeekday(first.day_of_week) : today,
      topic_covered: '',
      homework: '',
    }
  }

  const { register, control, handleSubmit, reset, setValue, setError, watch, formState: { errors, isSubmitting } } =
    useForm<LogValues>({ resolver: zodResolver(schema), defaultValues: defaults() })

  useEffect(() => { reset(defaults()) }, [ordered]) // eslint-disable-line react-hooks/exhaustive-deps

  const selected = ordered.find((s) => s.id === watch('schedule_id'))
  const sessionDate = watch('session_date')
  const wrongDay = selected && sessionDate && (parseDate(sessionDate).getDay() + 6) % 7 !== selected.day_of_week

  async function onSubmit(values: LogValues) {
    try {
      const session = await logSession(values)
      toast.success('Session logged! The parent will be notified to confirm.')
      reset(defaults())
      onLogged(session)
    } catch (error) {
      if (errorStatus(error) === 409) {
        setError('session_date', { message: errorMessage(error).includes('cancelled')
          ? errorMessage(error) : 'You already logged a session for this date.' })
      } else if (errorStatus(error) === 422) {
        setError('session_date', { message: errorMessage(error) })
      } else {
        toast.error(errorMessage(error))
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <FormField id="log-schedule" label="Schedule" error={errors.schedule_id?.message}>
        <Controller control={control} name="schedule_id" render={({ field }) => (
          <Select
            value={field.value}
            onValueChange={(id) => {
              field.onChange(id)
              const s = ordered.find((x) => x.id === id)
              if (s) setValue('session_date', latestDateOnWeekday(s.day_of_week))
            }}
          >
            <SelectTrigger id="log-schedule"><SelectValue placeholder="Choose a schedule" /></SelectTrigger>
            <SelectContent>
              {ordered.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.day_of_week === todayDayOfWeek() ? 'Today · ' : ''}{scheduleLabel(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
      </FormField>
      <FormField
        id="log-date"
        label="Lesson date"
        error={errors.session_date?.message}
        hint={selected ? `Must be a ${DAYS[selected.day_of_week]}, today or earlier.` : undefined}
      >
        <Input id="log-date" type="date" max={today} {...register('session_date')} aria-invalid={!!errors.session_date} />
      </FormField>
      {wrongDay && !errors.session_date && (
        <p className="-mt-2 text-sm text-amber-700">That date isn&apos;t a {DAYS[selected.day_of_week]}. The lesson date must match the schedule.</p>
      )}
      <FormField id="log-topic" label="Topic covered" error={errors.topic_covered?.message}>
        <Textarea id="log-topic" rows={3} placeholder="e.g. Algebra: linear equations" {...register('topic_covered')} aria-invalid={!!errors.topic_covered} />
      </FormField>
      <FormField id="log-homework" label="Homework (optional)" error={errors.homework?.message}>
        <Textarea id="log-homework" rows={2} placeholder="e.g. Exercises 3.1 to 3.5" {...register('homework')} />
      </FormField>
      <Button type="submit" disabled={isSubmitting || ordered.length === 0}>{isSubmitting ? 'Logging…' : 'Log session'}</Button>
    </form>
  )
}

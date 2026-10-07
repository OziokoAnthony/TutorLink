import { DAYS, formatTime } from '@/lib/format'
import type { TutorAvailability } from '@/types'

/** A tutor's week: booked times, free times, and whether they're teaching right now. */
export default function AvailabilityView({ availability }: { availability: TutorAvailability }) {
  return (
    <div className="space-y-3">
      <p className="flex items-center gap-2 text-sm">
        <span className={availability.in_session_now ? 'h-2.5 w-2.5 rounded-full bg-amber-500' : 'h-2.5 w-2.5 rounded-full bg-emerald-500'} aria-hidden />
        {availability.in_session_now ? 'In a lesson right now' : 'Not in a lesson right now'}
      </p>
      <div className="divide-y rounded-md border text-sm">
        {DAYS.map((day, d) => {
          const free = availability.free.filter((s) => s.day_of_week === d)
          const busy = availability.busy.filter((s) => s.day_of_week === d)
          if (free.length === 0 && busy.length === 0) return null
          return (
            <div key={day} className="flex flex-col gap-1.5 px-3 py-2 sm:flex-row sm:items-center">
              <span className="w-24 shrink-0 font-medium">{day}</span>
              <div className="flex flex-wrap gap-1.5">
                {[...free.map((s) => ({ ...s, busy: false })), ...busy.map((s) => ({ ...s, busy: true }))]
                  .sort((a, b) => a.start_time.localeCompare(b.start_time))
                  .map((s) => (
                    <span key={`${s.start_time}-${s.busy}`}
                      className={s.busy
                        ? 'rounded border border-zinc-300 bg-zinc-100 px-2 py-0.5 text-zinc-500 line-through'
                        : 'rounded border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-emerald-900'}>
                      {formatTime(s.start_time)}–{formatTime(s.end_time)}
                      <span className="sr-only">{s.busy ? ' (booked)' : ' (free)'}</span>
                    </span>
                  ))}
              </div>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="text-emerald-800">Green</span> times are free; crossed-out times are already booked.
      </p>
    </div>
  )
}

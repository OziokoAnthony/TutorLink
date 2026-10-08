import { cn } from '@/lib/utils'

/** A row of buttons acting as radio options, e.g. billing period or lesson mode. */
export default function Choice<T extends string>({ value, options, onChange, label }: {
  value: T; options: { value: T; label: string; hint?: string }[]; onChange: (v: T) => void; label: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className="grid gap-2 sm:grid-cols-3">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={cn('rounded-md border px-3 py-2 text-left text-sm transition-colors',
            value === o.value ? 'border-primary bg-primary/5 font-medium' : 'hover:bg-muted')}>
          {o.label}
          {o.hint && <span className="block text-xs font-normal text-muted-foreground">{o.hint}</span>}
        </button>
      ))}
    </div>
  )
}

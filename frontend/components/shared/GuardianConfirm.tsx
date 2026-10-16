import { GUARDIAN_TEXT } from '@/lib/format'

/** Spec 15 R2: before booking or posting nursery or primary lessons. */
export default function GuardianConfirm({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="mt-2 flex items-start gap-2 rounded-md border bg-muted/40 p-3 text-sm">
      <input type="checkbox" className="mt-0.5 h-4 w-4 accent-primary" checked={checked}
        onChange={(e) => onChange(e.target.checked)} />
      <span>
        I confirm: {GUARDIAN_TEXT}
        <span className="block text-xs text-muted-foreground">Tutors teach; they don&apos;t look after young children.</span>
      </span>
    </label>
  )
}

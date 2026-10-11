import Link from 'next/link'
import { RECORDING_CONSENT } from '@/lib/format'

/** The consent a parent must give before booking or posting online lessons (spec 3 R1.4). */
export default function RecordingConsent({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="mt-2 flex items-start gap-2 rounded-md border bg-muted/40 p-3 text-sm">
      <input type="checkbox" className="mt-0.5 h-4 w-4 accent-primary" checked={checked}
        onChange={(e) => onChange(e.target.checked)} />
      <span>
        I agree: {RECORDING_CONSENT}
        <span className="block text-xs text-muted-foreground">
          The tutor uploads each lesson&apos;s recording. Only you, the tutor and TutorLink can watch it, and it&apos;s deleted after 90 days.{' '}
          <Link href="/privacy" target="_blank" className="underline hover:text-foreground">Privacy notice</Link>
        </span>
      </span>
    </label>
  )
}

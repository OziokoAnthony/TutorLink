import type { Metadata } from 'next'
import Link from 'next/link'
import { SignUpButtons, tutorsText } from '@/components/public/PublicBits'
import { LEVELS } from '@/lib/format'
import { publicSubjects } from '@/lib/public'
import type { SubjectGroup } from '@/types'

export const dynamic = 'force-dynamic' // rendered on request, its data cached for an hour (spec 14 R6.4)

export const metadata: Metadata = {
  title: 'Tutors by subject in Nigeria | TutorLink',
  description: 'Find verified home and online tutors for every subject, from primary school to WAEC, NECO and '
    + 'international curricula. See prices before you sign up.',
}

const GROUPS: { value: SubjectGroup; label: string }[] = [
  { value: 'nigerian', label: 'Nigerian curriculum' },
  { value: 'international', label: 'International curriculum' },
]

/** Spec 14 R4.1: every offered subject, with how many verified tutors teach it. */
export default async function SubjectsPage() {
  const subjects = await publicSubjects()
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Tutors by subject</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Every TutorLink tutor has had their identity, certificates and teaching knowledge checked. Choose a subject to
        see how many tutors teach it and what lessons cost.
      </p>
      <p className="mt-4 text-sm">
        By level:{' '}
        {LEVELS.map((l, i) => (
          <span key={l.value}>{i > 0 && ' · '}<Link href={`/levels/${l.value}`} className="text-primary hover:underline">{l.label}</Link></span>
        ))}
      </p>
      {GROUPS.map((g) => {
        const list = subjects.filter((s) => s.group === g.value)
        if (list.length === 0) return null
        return (
          <section key={g.value} className="mt-10">
            <h2 className="text-xl font-semibold">{g.label}</h2>
            <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {list.map((s) => (
                <li key={s.slug}>
                  <Link href={`/subjects/${s.slug}`} className="block rounded-lg border bg-card p-4 hover:border-primary">
                    <span className="font-medium">{s.name}</span>
                    <span className="block text-sm text-muted-foreground">
                      {s.tutors ? tutorsText(s.tutors) : 'No tutors yet: post a request'}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
      <div className="mt-12"><SignUpButtons /></div>
    </div>
  )
}

import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { SignUpButtons, Steps, priceText, tutorsText } from '@/components/public/PublicBits'
import { LEVELS, levelLabel } from '@/lib/format'
import { publicLevel } from '@/lib/public'
import type { Level } from '@/types'

export const dynamic = 'force-dynamic' // rendered on request, its data cached for an hour (spec 14 R6.4)

type Props = { params: Promise<{ level: string }> }

function known(level: string): level is Level {
  return LEVELS.some((l) => l.value === level)
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { level } = await params
  if (!known(level)) return { title: 'Level not found | TutorLink' }
  return {
    title: `${levelLabel(level)} tutors in Nigeria | TutorLink`,
    description: `Verified ${levelLabel(level).toLowerCase()} tutors for every subject, at home or online. See prices per `
      + 'lesson before you sign up.',
  }
}

/** Spec 14 R5.1: the subjects taught at a level, each with its tutor count and price range. */
export default async function LevelPage({ params }: Props) {
  const { level } = await params
  if (!known(level)) notFound()
  const data = await publicLevel(level)
  if (!data) notFound()
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <p className="text-sm"><Link href="/subjects" className="text-primary hover:underline">All subjects</Link></p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">{levelLabel(level)} tutors</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        {data.tutors
          ? `${tutorsText(data.tutors)} teach at ${levelLabel(level).toLowerCase()} level on TutorLink. Prices are per lesson, TutorLink's fee included.`
          : 'No tutors teach at this level yet. Post a request and tutors can apply.'}
      </p>
      {data.subjects.length > 0 && (
        <ul className="mt-8 divide-y rounded-lg border bg-card">
          {data.subjects.map((s) => (
            <li key={s.slug} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
              <Link href={`/subjects/${s.slug}`} className="font-medium hover:underline">{s.name}</Link>
              <span className="text-muted-foreground">{tutorsText(s.tutors)} · {priceText(s.min_price, s.max_price)}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-8"><SignUpButtons /></div>
      <section className="mt-12">
        <h2 className="mb-4 text-xl font-semibold">How it works</h2>
        <Steps />
      </section>
    </div>
  )
}

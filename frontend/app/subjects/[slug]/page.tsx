import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ReviewList, SignUpButtons, Steps, priceText, tutorsText } from '@/components/public/PublicBits'
import { levelLabel } from '@/lib/format'
import { publicSubject } from '@/lib/public'

export const dynamic = 'force-dynamic' // rendered on request, its data cached for an hour (spec 14 R6.4)

type Props = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const subject = await publicSubject((await params).slug)
  if (!subject) return { title: 'Subject not found | TutorLink' }
  return {
    title: `${subject.name} tutors in Nigeria | TutorLink`,
    description: `Verified ${subject.name} tutors for home and online lessons. See how many tutors teach it at each `
      + 'level and what lessons cost, then sign up to choose one.',
  }
}

/** Spec 14 R4.2-R4.4: tutor counts and price ranges per level, reviews, and sign-up. */
export default async function SubjectPage({ params }: Props) {
  const subject = await publicSubject((await params).slug)
  if (!subject) notFound()
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <p className="text-sm"><Link href="/subjects" className="text-primary hover:underline">All subjects</Link></p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">{subject.name} tutors</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        {subject.tutors
          ? `${tutorsText(subject.tutors)} teach ${subject.name} on TutorLink, at home or online. Each one passed our identity, certificate and teaching checks.`
          : `No ${subject.name} tutors are available yet. Post a request and tutors who teach it can apply.`}
      </p>

      {subject.levels.length > 0 && (
        <section className="mt-8">
          <h2 className="text-xl font-semibold">Levels and prices</h2>
          <p className="mt-1 text-sm text-muted-foreground">What parents pay per lesson, TutorLink&apos;s fee included.</p>
          <ul className="mt-4 divide-y rounded-lg border bg-card">
            {subject.levels.map((l) => (
              <li key={l.level} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <Link href={`/levels/${l.level}`} className="font-medium hover:underline">{levelLabel(l.level)}</Link>
                <span className="text-muted-foreground">{tutorsText(l.tutors)} · {priceText(l.min_price, l.max_price)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-8"><SignUpButtons /></div>

      {subject.reviews.length > 0 && (
        <section className="mt-12">
          <h2 className="mb-4 text-xl font-semibold">What parents say</h2>
          <ReviewList reviews={subject.reviews} />
        </section>
      )}

      <section className="mt-12">
        <h2 className="mb-4 text-xl font-semibold">How it works</h2>
        <Steps />
      </section>
    </div>
  )
}

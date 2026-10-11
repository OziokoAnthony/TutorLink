import Link from 'next/link'
import { Search, CalendarCheck, Wallet } from 'lucide-react'
import { Button } from '@/components/ui/button'
import HeroSlideshow from '@/components/home/HeroSlideshow'

const STEPS = [
  {
    icon: Search,
    title: 'Search',
    text: 'Browse tutors vetted by our team. Filter by subject, level and area.',
  },
  {
    icon: CalendarCheck,
    title: 'Book',
    text: 'Request weekly lesson times that suit your family. The tutor accepts, and lessons recur every week.',
  },
  {
    icon: Wallet,
    title: 'Pay before lessons',
    text: 'Pay by bank transfer into your own TutorLink account number. If a lesson goes wrong, report it and we can refund it.',
  },
]

/** An outline button that reads on top of the photos. */
const GLASS_BUTTON = 'border-white/70 bg-white/10 text-white backdrop-blur hover:bg-white/20 hover:text-white'

export default function LandingPage() {
  return (
    <>
      <section className="relative flex min-h-[calc(100svh-3.5rem)] items-center overflow-hidden">
        <HeroSlideshow />
        <div className="relative z-10 mx-auto max-w-4xl px-4 py-24 text-center text-white">
          <h1 className="text-balance text-4xl font-bold tracking-tight drop-shadow-lg md:text-6xl">
            Find a vetted home tutor. Pay by bank transfer, protected if a lesson goes wrong.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-white/90 drop-shadow md:text-xl">
            TutorLink connects Nigerian parents with checked, qualified tutors for lessons at home or online,
            paid daily, weekly or monthly before they happen.
          </p>
          <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
            <Button size="lg" asChild><Link href="/tutors">Find a Tutor</Link></Button>
            <Button size="lg" variant="outline" asChild className={GLASS_BUTTON}>
              <Link href="/dashboard/parent/jobs/new">Post a Job</Link>
            </Button>
            <Button size="lg" variant="outline" asChild className={GLASS_BUTTON}>
              <Link href="/register?role=tutor">Become a Tutor</Link>
            </Button>
          </div>
          <p className="mt-4 text-sm text-white/80">
            Parents only: create a free account to see tutors or post a job. Every job post is checked by TutorLink before tutors see it.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16">
        <h2 className="text-center text-2xl font-bold tracking-tight">How it works</h2>
        <ol className="mt-10 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="rounded-lg border bg-card p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {i + 1}
                </span>
                <step.icon className="h-5 w-5 text-primary" aria-hidden />
              </div>
              <h3 className="mt-4 font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}

import Link from 'next/link'
import { Search, CalendarCheck, Wallet } from 'lucide-react'
import { Button } from '@/components/ui/button'

const STEPS = [
  {
    icon: Search,
    title: 'Search',
    text: 'Browse tutors vetted by our team. Filter by subject, level and area.',
  },
  {
    icon: CalendarCheck,
    title: 'Book',
    text: 'Book a weekly slot that suits your family. Lessons recur every week.',
  },
  {
    icon: Wallet,
    title: 'Pay confirmed lessons',
    text: 'Confirm each lesson after it happens. Your monthly invoice only includes confirmed lessons.',
  },
]

export default function LandingPage() {
  return (
    <>
      <section className="border-b bg-gradient-to-b from-accent/60 to-background">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center md:py-28">
          <h1 className="text-balance text-4xl font-bold tracking-tight md:text-5xl">
            Find a vetted home tutor. Pay only for lessons that happened.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            TutorLink connects Nigerian parents with checked, qualified tutors for weekly home lessons,
            billed monthly for the lessons you confirm.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button size="lg" asChild><Link href="/tutors">Find a Tutor</Link></Button>
            <Button size="lg" variant="outline" asChild><Link href="/register">Become a Tutor</Link></Button>
          </div>
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

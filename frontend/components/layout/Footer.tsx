import Link from 'next/link'

const COLUMNS = [
  {
    title: 'For parents',
    links: [
      { href: '/tutors', label: 'Find a tutor' },
      { href: '/dashboard/parent/jobs/new', label: 'Post a job' },
      { href: '/register', label: 'Create an account' },
    ],
  },
  {
    title: 'For tutors',
    links: [
      { href: '/register', label: 'Become a tutor' },
      { href: '/dashboard/tutor/jobs', label: 'Find jobs' },
      { href: '/login', label: 'Tutor login' },
    ],
  },
  {
    title: 'Account',
    links: [
      { href: '/login', label: 'Log in' },
      { href: '/forgot-password', label: 'Forgot password?' },
      { href: '/privacy', label: 'Privacy notice' },
      { href: '/terms', label: 'Terms of service' },
    ],
  },
]

export default function Footer() {
  return (
    <footer className="border-t bg-muted/40 print:hidden">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:grid-cols-2 md:grid-cols-4">
        <div>
          <Link href="/" className="text-lg font-bold tracking-tight text-primary">TutorLink</Link>
          <p className="mt-3 text-sm text-muted-foreground">
            Vetted home and online tutors for Nigerian families, from primary school to international high school.
          </p>
        </div>
        {COLUMNS.map((column) => (
          <nav key={column.title} aria-label={column.title}>
            <h2 className="text-sm font-semibold">{column.title}</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {column.links.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="text-muted-foreground hover:text-foreground">{link.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:justify-between">
          <p>© {new Date().getFullYear()} TutorLink. All rights reserved.</p>
          <p>Photos from <a href="https://unsplash.com" className="underline hover:text-foreground">Unsplash</a></p>
        </div>
      </div>
    </footer>
  )
}

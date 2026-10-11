import Link from 'next/link'
import { detail, legalIsComplete } from '@/lib/legal'

/** The layout shared by the privacy notice and the terms. */
export default function LegalPage({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <article className="mx-auto max-w-3xl px-4 py-12 text-sm leading-relaxed [&_h2]:mb-2 [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_li]:mt-1 [&_p]:mt-3 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5">
      {!legalIsComplete && (
        <p role="note" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-900">
          Draft: this page isn&apos;t final yet. The business details in <code>lib/legal.ts</code> still need filling in.
        </p>
      )}
      <h1 className="mt-6 text-3xl font-bold tracking-tight">{title}</h1>
      <p className="text-muted-foreground">Effective {detail('effectiveDate')}</p>
      {children}
      <p className="mt-10 text-muted-foreground">
        See also our <Link href="/privacy" className="text-primary hover:underline">privacy notice</Link> and{' '}
        <Link href="/terms" className="text-primary hover:underline">terms of service</Link>.
      </p>
    </article>
  )
}

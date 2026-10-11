'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import LegalText, { LEGAL_PROSE, isDraft } from '@/components/legal/LegalText'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { errorMessage } from '@/lib/api'
import { getLegal } from '@/lib/content'
import { formatDayOf } from '@/lib/format'
import type { LegalDocument, LegalKind } from '@/types'

export const LEGAL_TITLES: Record<LegalKind, string> = {
  privacy: 'Privacy notice',
  terms: 'Terms of service',
  disclaimer: 'Disclaimer',
}

/** The privacy notice, terms or disclaimer, as an admin last published it (spec 7 R2). */
export default function LegalPage({ kind }: { kind: LegalKind }) {
  const [doc, setDoc] = useState<LegalDocument | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { getLegal(kind).then(setDoc).catch((e) => setError(errorMessage(e))) }, [kind])

  return (
    <article className="mx-auto max-w-3xl px-4 py-12">
      {doc && isDraft(doc.body) && (
        <p role="note" className="mb-6 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Draft: this page isn&apos;t final yet.
        </p>
      )}
      <h1 className="text-3xl font-bold tracking-tight">{LEGAL_TITLES[kind]}</h1>
      {error ? <EmptyState message={error} /> : doc === null ? <LoadingSpinner /> : (
        <>
          <p className="mt-1 text-sm text-muted-foreground">Last updated {formatDayOf(doc.published_at)}</p>
          <div className={LEGAL_PROSE}><LegalText text={doc.body} /></div>
        </>
      )}
      <p className="mt-10 text-sm text-muted-foreground">
        See also our{' '}
        {(Object.keys(LEGAL_TITLES) as LegalKind[]).filter((k) => k !== kind).map((k, i) => (
          <span key={k}>{i > 0 && ' and '}
            <Link href={`/${k}`} className="text-primary hover:underline">{LEGAL_TITLES[k].toLowerCase()}</Link>
          </span>
        ))}.
      </p>
    </article>
  )
}

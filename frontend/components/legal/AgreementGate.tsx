'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import AgreementPanel from '@/components/legal/AgreementPanel'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { getMyLegal } from '@/lib/content'
import type { MyLegal } from '@/types'

/**
 * Spec 9 R3, R5: a parent (or a tutor who agreed before) who hasn't agreed to the latest documents sees them
 * instead of the page, and continues once they agree. The API refuses their other requests meanwhile.
 */
export default function AgreementGate({ children }: { children: React.ReactNode }) {
  const [legal, setLegal] = useState<MyLegal | null>(null)
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    getMyLegal().then(setLegal).catch(() => {}).finally(() => setChecked(true))
  }, [])

  if (!checked) return <LoadingSpinner />
  if (!legal?.required) return <>{children}</>

  const again = legal.documents.some((d) => d.accepted_at)
  return (
    <Card className="mx-auto max-w-3xl">
      <CardHeader>
        <CardTitle className="text-xl">{again ? 'We have updated our terms' : 'Before you continue'}</CardTitle>
        <CardDescription>
          Please read TutorLink&apos;s terms of service, privacy notice and disclaimer, and agree to continue.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <AgreementPanel legal={legal} onChange={setLegal} />
      </CardContent>
    </Card>
  )
}

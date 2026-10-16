'use client'

import { useEffect, useState } from 'react'
import AgreementPanel from '@/components/legal/AgreementPanel'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getMyLegal } from '@/lib/content'
import type { MyLegal } from '@/types'

/** Spec 9 R2.4: a parent's or tutor's own documents and when they agreed, from their dashboard. */
export default function MyLegalPage() {
  const toast = useToast()
  const [legal, setLegal] = useState<MyLegal | null>(null)
  useEffect(() => { getMyLegal().then(setLegal).catch((e) => toast.error(errorMessage(e))) }, [toast])

  return (
    <>
      <PageHeader title="Terms & privacy"
        description="The terms of service, privacy notice and disclaimer that apply to you, and when you agreed to them." />
      {legal === null ? <LoadingSpinner /> : <AgreementPanel legal={legal} onChange={setLegal} />}
    </>
  )
}

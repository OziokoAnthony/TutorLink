import type { Metadata } from 'next'
import LegalPage from '@/components/legal/LegalPage'

export const metadata: Metadata = { title: 'Disclaimer · TutorLink' }

/** The disclaimer an admin keeps at /admin/legal (spec 7 R2, R3). */
export default function DisclaimerPage() {
  return <LegalPage kind="disclaimer" />
}

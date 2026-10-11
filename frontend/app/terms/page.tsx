import type { Metadata } from 'next'
import LegalPage from '@/components/legal/LegalPage'

export const metadata: Metadata = { title: 'Terms of service · TutorLink' }

/** The terms an admin keeps at /admin/legal (spec 7 R2). */
export default function TermsPage() {
  return <LegalPage kind="terms" />
}

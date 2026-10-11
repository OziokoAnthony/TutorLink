import type { Metadata } from 'next'
import LegalPage from '@/components/legal/LegalPage'

export const metadata: Metadata = { title: 'Privacy notice · TutorLink' }

/** The privacy notice an admin keeps at /admin/legal (spec 7 R2). */
export default function PrivacyPage() {
  return <LegalPage kind="privacy" />
}

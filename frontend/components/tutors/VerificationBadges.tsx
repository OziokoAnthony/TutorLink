import { BadgeCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { TutorProfile } from '@/types'

/** Spec 4 R2.4, R4.4: every listed tutor is a Verified tutor (an admin approved them); "NIN verified" and
 *  each certificate type an admin verified are shown too. Never files or numbers. */
export default function VerificationBadges({ tutor, compact }: { tutor: TutorProfile; compact?: boolean }) {
  const certificates = compact ? [] : tutor.verified_certificates ?? []
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge className="gap-1 border-emerald-300 bg-emerald-100 text-emerald-900 hover:bg-emerald-100" variant="outline">
        <BadgeCheck className="h-3.5 w-3.5" aria-hidden />Verified tutor
      </Badge>
      {tutor.nin_verified && <Badge variant="outline">NIN verified</Badge>}
      {certificates.map((c) => <Badge key={c} variant="outline">{c} verified</Badge>)}
    </div>
  )
}

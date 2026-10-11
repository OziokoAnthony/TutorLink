import Link from 'next/link'
import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { RatingSummary } from '@/components/reviews/StarRating'
import Avatar from '@/components/shared/Avatar'
import VerificationBadges from '@/components/tutors/VerificationBadges'
import { formatNaira, levelLabel } from '@/lib/format'
import type { Offer, TutorProfile } from '@/types'

/** Every subject + level the tutor offers, once each. */
export function subjectBadges(offers: Offer[]): string[] {
  const seen = new Set<string>()
  for (const offer of offers) {
    for (const subject of offer.subjects) seen.add(`${subject} • ${levelLabel(offer.level)}`)
  }
  return Array.from(seen)
}

export default function TutorCard({ tutor }: { tutor: TutorProfile }) {
  return (
    <Card className="flex flex-col">
      <CardContent className="flex-1 space-y-3 pt-6">
        <div className="flex items-center gap-3">
          <Avatar name={tutor.full_name} photoUrl={tutor.photo_url} />
          <div className="min-w-0">
            <h3 className="truncate font-semibold">{tutor.full_name}</h3>
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" aria-hidden />{tutor.area}
            </p>
          </div>
        </div>
        <VerificationBadges tutor={tutor} compact />
        <RatingSummary average={tutor.average_rating} count={tutor.rating_count} />
        <div className="flex flex-wrap gap-1.5">
          {subjectBadges(tutor.offers).map((s) => <Badge key={s} variant="secondary">{s}</Badge>)}
        </div>
        {tutor.price_from !== null && (
          <p className="text-sm">From <span className="text-lg font-semibold">{formatNaira(tutor.price_from)}</span> per lesson</p>
        )}
      </CardContent>
      <CardFooter>
        <Button className="w-full" variant="outline" asChild>
          <Link href={`/tutors/${tutor.user_id}`}>View Profile</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

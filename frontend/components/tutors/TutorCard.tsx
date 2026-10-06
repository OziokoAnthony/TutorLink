import Link from 'next/link'
import { MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { RatingSummary } from '@/components/reviews/StarRating'
import { formatNaira, levelLabel } from '@/lib/format'
import type { TutorProfile } from '@/types'

export function TutorAvatar({ name, size = 'md' }: { name: string; size?: 'md' | 'lg' }) {
  const initials = name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
  return (
    <div
      aria-hidden
      className={size === 'lg'
        ? 'flex h-20 w-20 items-center justify-center rounded-full bg-accent text-2xl font-semibold text-accent-foreground'
        : 'flex h-12 w-12 items-center justify-center rounded-full bg-accent text-base font-semibold text-accent-foreground'}
    >
      {initials}
    </div>
  )
}

export default function TutorCard({ tutor }: { tutor: TutorProfile }) {
  return (
    <Card className="flex flex-col">
      <CardContent className="flex-1 space-y-3 pt-6">
        <div className="flex items-center gap-3">
          <TutorAvatar name={tutor.full_name} />
          <div className="min-w-0">
            <h3 className="truncate font-semibold">{tutor.full_name}</h3>
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" aria-hidden />{tutor.area}
            </p>
          </div>
        </div>
        <RatingSummary average={tutor.average_rating} count={tutor.rating_count} />
        <div className="flex flex-wrap gap-1.5">
          {tutor.subjects.map((s) => (
            <Badge key={s.id} variant="secondary">{s.subject} • {levelLabel(s.level)}</Badge>
          ))}
        </div>
        <p className="text-sm"><span className="text-lg font-semibold">{formatNaira(tutor.rate_per_session)}</span> per session</p>
      </CardContent>
      <CardFooter>
        <Button className="w-full" variant="outline" asChild>
          <Link href={`/tutors/${tutor.user_id}`}>View Profile</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}

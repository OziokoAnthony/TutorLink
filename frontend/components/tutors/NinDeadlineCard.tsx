'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { NinForm } from '@/components/tutors/OnboardingChecklist'
import { useAuth } from '@/hooks/useAuth'
import { formatDayOf } from '@/lib/format'
import { getOnboarding } from '@/lib/onboarding'
import type { Onboarding } from '@/types'

/** Spec 11 R3: an approved tutor who started with an ID document verifies their NIN here, before the deadline. */
export default function NinDeadlineCard() {
  const { refresh } = useAuth()
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null)
  const load = useCallback(async () => { setOnboarding(await getOnboarding().catch(() => null)) }, [])
  useEffect(() => { load() }, [load])

  if (!onboarding || onboarding.nin_verified || !onboarding.nin_due_at) return null
  const overdue = onboarding.nin_overdue
  return (
    <Card className={`mb-6 ${overdue ? 'border-destructive' : 'border-amber-300'}`}>
      <CardHeader>
        <CardTitle className="text-lg">{overdue ? 'Parents can no longer see your profile' : 'Verify your NIN'}</CardTitle>
        <CardDescription>
          {overdue
            ? `You didn't verify your NIN by ${formatDayOf(onboarding.nin_due_at)}. Lessons you already have carry on; verify your NIN to be found and booked again.`
            : `Verify your NIN by ${formatDayOf(onboarding.nin_due_at)}. After that, parents won't be able to find or book you until you do.`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <NinForm attemptsLeft={onboarding.nin_attempts_left} retryAt={onboarding.nin_retry_at}
          onDone={async () => { await Promise.all([load(), refresh()]) }} />
      </CardContent>
    </Card>
  )
}

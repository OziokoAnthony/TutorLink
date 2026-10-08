'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Circle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import FormField from '@/components/shared/FormField'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import SelfieCamera from '@/components/tutors/SelfieCamera'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { getOnboarding, verifyNin } from '@/lib/onboarding'
import type { NinResult, Onboarding, OnboardingStepKey } from '@/types'

const STEP_TITLES: Record<OnboardingStepKey, string> = {
  profile: 'Profile',
  nin: 'Verify your NIN',
  review: 'Waiting for admin review',
}

function NinForm({ attemptsLeft, retryAt, onDone }: { attemptsLeft: number; retryAt: string | null; onDone: () => Promise<void> }) {
  const toast = useToast()
  const [nin, setNin] = useState('')
  const [selfie, setSelfie] = useState<Blob | null>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<NinResult | null>(null)
  const ninValid = /^\d{11}$/.test(nin)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!selfie || !ninValid) return
    setBusy(true)
    try {
      const r = await verifyNin(nin, selfie)
      setResult(r)
      if (r.verified) toast.success('Your NIN is verified')
      await onDone()
    } catch (err) {
      toast.error(errorMessage(err))
      await onDone()
    } finally {
      setBusy(false)
    }
  }

  if (attemptsLeft === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {result && !result.verified && <span className="mb-1 block text-destructive">{result.message}</span>}
        You&apos;ve used all 3 NIN checks for now.{retryAt ? ` You can try again after ${formatDateTime(retryAt)}.` : ''}
      </p>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <p className="text-sm text-muted-foreground">
        We check your NIN with the national database, that your name matches it exactly and that your selfie
        matches your NIN photo. We keep only the last 4 digits of your NIN, never your selfie.
      </p>
      {result && !result.verified && (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-950">
          {result.message}
          {result.name_matches === false && <> <Link href="/dashboard/tutor/profile" className="font-medium underline">Correct your name</Link>.</>}
        </p>
      )}
      <FormField id="nin" label="NIN (11 digits)" error={nin && !ninValid ? 'Your NIN is 11 digits' : undefined}>
        <Input id="nin" inputMode="numeric" autoComplete="off" maxLength={11} value={nin}
          onChange={(e) => setNin(e.target.value.replace(/\D/g, ''))} className="max-w-xs" />
      </FormField>
      <SelfieCamera onChange={setSelfie} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={busy || !ninValid || !selfie}>{busy ? 'Checking…' : 'Verify my NIN'}</Button>
        <span className="text-xs text-muted-foreground">{attemptsLeft} of 3 checks left in 24 hours</span>
      </div>
    </form>
  )
}

/** The tutor's onboarding checklist (spec 4 R2.1): Profile → NIN → waiting for admin review. */
export default function OnboardingChecklist() {
  const { refresh } = useAuth()
  const toast = useToast()
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null)

  const load = useCallback(async () => {
    try {
      setOnboarding(await getOnboarding())
    } catch (e) {
      toast.error(errorMessage(e))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function afterNinCheck() {
    await Promise.all([load(), refresh()])
  }

  if (!onboarding) return <LoadingSpinner />
  const current = onboarding.steps.find((s) => !s.done)?.key

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-lg">Become a Verified tutor</CardTitle>
        <CardDescription>Finish each step. Parents can find and book you once an admin approves you.</CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="space-y-5">
          {onboarding.steps.map((step) => (
            <li key={step.key} className="flex gap-3">
              {step.done
                ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" aria-label="Done" />
                : <Circle className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-label="To do" />}
              <div className="min-w-0 flex-1 space-y-2">
                <p className={step.key === current ? 'font-medium' : 'text-muted-foreground'}>{STEP_TITLES[step.key]}</p>
                {step.key === 'profile' && !step.done && (
                  <ul className="list-disc pl-5 text-sm">
                    {step.todo.map((t) => (
                      <li key={t}><Link href="/dashboard/tutor/profile" className="underline">{t}</Link></li>
                    ))}
                  </ul>
                )}
                {step.key === 'nin' && !step.done && current === 'nin' && (
                  <NinForm attemptsLeft={onboarding.nin_attempts_left} retryAt={onboarding.nin_retry_at} onDone={afterNinCheck} />
                )}
                {step.key === 'review' && current === 'review' && (
                  <p className="text-sm text-muted-foreground">
                    {step.todo.length ? `Still needed: ${step.todo.join(', ')}.` : 'An admin is reviewing your profile. We’ll email you once you’re approved.'}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  )
}

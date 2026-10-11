'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage, errorStatus } from '@/lib/api'
import { getExamStatus, saveExamAnswer, startExam, submitExam } from '@/lib/exam'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { ExamAttempt, ExamResult, ExamStatus } from '@/types'

const LETTERS = ['A', 'B', 'C', 'D']

function useSecondsLeft(deadline: string | null): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!deadline) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [deadline])
  return deadline ? Math.max(0, Math.floor((new Date(deadline).getTime() - now) / 1000)) : 0
}

function minutesAndSeconds(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** One attempt in progress: answers are saved as they're chosen; the server ignores anything after the deadline. */
function Attempt({ attempt, onFinished }: { attempt: ExamAttempt; onFinished: (result: ExamResult) => void }) {
  const toast = useToast()
  const [chosen, setChosen] = useState<Record<number, number | null>>(
    () => Object.fromEntries(attempt.questions.map((q) => [q.position, q.chosen_index])))
  const [confirming, setConfirming] = useState(false)
  const secondsLeft = useSecondsLeft(attempt.deadline)
  const answered = Object.values(chosen).filter((c) => c !== null).length

  const finish = useCallback(async () => {
    try {
      onFinished(await submitExam(attempt.id))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }, [attempt.id, onFinished, toast])

  // Time's up: the server scores what was saved before the deadline.
  useEffect(() => {
    if (secondsLeft === 0) finish().catch(() => undefined)
  }, [secondsLeft]) // eslint-disable-line react-hooks/exhaustive-deps

  async function choose(position: number, choice: number) {
    const previous = chosen[position]
    setChosen((c) => ({ ...c, [position]: choice }))
    try {
      await saveExamAnswer(attempt.id, position, choice)
    } catch (e) {
      setChosen((c) => ({ ...c, [position]: previous }))
      toast.error(errorMessage(e))
      if (errorStatus(e) === 409) finish().catch(() => undefined)
    }
  }

  return (
    <>
      <div className="sticky top-0 z-10 -mx-4 mb-4 flex items-center justify-between gap-3 border-b bg-background/95 px-4 py-3 backdrop-blur">
        <span className={cn('flex items-center gap-1.5 font-semibold tabular-nums', secondsLeft < 300 && 'text-red-700')} role="timer" aria-live="off">
          <Clock className="h-4 w-4" aria-hidden />{minutesAndSeconds(secondsLeft)} left
        </span>
        <span className="text-sm text-muted-foreground">{answered} of {attempt.questions.length} answered</span>
        <Button size="sm" onClick={() => setConfirming(true)}>Submit</Button>
      </div>
      <ol className="space-y-4">
        {attempt.questions.map((q) => (
          <li key={q.position}>
            <Card>
              <CardContent className="space-y-3 pt-5">
                <p className="whitespace-pre-line font-medium"><span className="text-muted-foreground">{q.position}. </span>{q.text}</p>
                <fieldset className="space-y-2">
                  <legend className="sr-only">Question {q.position}</legend>
                  {q.options.map((option, i) => (
                    <label key={i} className={cn('flex cursor-pointer items-start gap-3 rounded-md border p-3 text-sm hover:bg-accent',
                      chosen[q.position] === i && 'border-primary bg-accent')}>
                      <input type="radio" name={`q-${q.position}`} className="mt-0.5" checked={chosen[q.position] === i}
                        onChange={() => choose(q.position, i)} />
                      <span><span className="font-semibold">{LETTERS[i]}.</span> {option}</span>
                    </label>
                  ))}
                </fieldset>
              </CardContent>
            </Card>
          </li>
        ))}
      </ol>
      <div className="mt-6"><Button onClick={() => setConfirming(true)}>Submit my answers</Button></div>
      <ConfirmDialog open={confirming} onOpenChange={setConfirming} title="Submit your answers?"
        description={answered < attempt.questions.length
          ? `You've answered ${answered} of ${attempt.questions.length}. Unanswered questions score nothing.`
          : 'You can’t change them afterwards.'}
        confirmLabel="Submit" onConfirm={finish} />
    </>
  )
}

/** Spec 4 R5: the qualifying exam. Passing it completes registration; an admin then approves the tutor. */
export default function TutorExamPage() {
  const toast = useToast()
  const [status, setStatus] = useState<ExamStatus | null>(null)
  const [attempt, setAttempt] = useState<ExamAttempt | null>(null)
  const [result, setResult] = useState<ExamResult | null>(null)
  const [preparing, setPreparing] = useState(false)
  const [starting, setStarting] = useState(false)

  const load = useCallback(async () => {
    try {
      const s = await getExamStatus()
      setStatus(s)
      setAttempt(s.open_attempt)
    } catch (e) {
      toast.error(errorMessage(e))
    }
  }, [toast])
  useEffect(() => { load() }, [load])

  async function start() {
    setStarting(true)
    setPreparing(false)
    setResult(null)
    try {
      setAttempt(await startExam())
    } catch (e) {
      if (errorStatus(e) === 409 && errorMessage(e).includes('being prepared')) setPreparing(true)
      else toast.error(errorMessage(e))
      await load()
    } finally {
      setStarting(false)
    }
  }

  async function finished(r: ExamResult) {
    setResult(r)
    setAttempt(null)
    await load()
  }

  if (!status) return <LoadingSpinner />

  if (attempt) {
    return (
      <>
        <PageHeader title="Qualifying exam" description={`${status.total} questions • pass mark ${status.pass_mark} • the timer runs on our server`} />
        <Attempt attempt={attempt} onFinished={finished} />
      </>
    )
  }

  return (
    <>
      <PageHeader title="Qualifying exam"
        description="Every TutorLink tutor passes this exam. It tests careful reasoning and the subjects you teach." />
      <div className="space-y-6">
        {result && (
          <p role="status" className={cn('rounded-md border px-4 py-3 text-sm',
            result.passed ? 'border-emerald-300 bg-emerald-50 text-emerald-950' : 'border-red-300 bg-red-50 text-red-950')}>
            You scored <strong>{result.score} of {result.total}</strong>.{' '}
            {result.passed ? 'You passed! An admin will now review your application.' : `You need ${status.pass_mark} to pass.`}
          </p>
        )}

        {status.passed ? (
          <Card>
            <CardHeader><CardTitle className="text-lg">You passed the qualifying exam</CardTitle></CardHeader>
            <CardContent><Button variant="outline" asChild><Link href="/dashboard/tutor">Back to your checklist</Link></Button></CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Before you start</CardTitle>
              <CardDescription>
                {status.total} multiple-choice questions: half on general reasoning, half on the subjects and levels you teach.
                You have {status.minutes} minutes once you start, and you need {status.pass_mark} right to pass.
                Your answers are saved as you choose them. Afterwards you see your score, not the answers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {status.locked_until ? (
                <p className="text-sm">You&apos;ve used all 6 attempts. You can try again after {formatDateTime(status.locked_until)}.</p>
              ) : (
                <>
                  {preparing && (
                    <p role="status" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                      Your exam is being prepared, try again shortly.
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-3">
                    <Button onClick={start} disabled={starting}>{starting ? 'Starting…' : preparing ? 'Try again' : 'Start the exam'}</Button>
                    <span className="text-sm text-muted-foreground">{status.attempts_left} of 6 attempts left before a 24-hour break</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

        {status.attempts.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-lg">Your attempts</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {status.attempts.map((a) => (
                  <li key={a.id} className="flex justify-between gap-3">
                    <span>{formatDateTime(a.started_at)}</span>
                    <span className={a.passed ? 'font-medium text-emerald-700' : 'text-muted-foreground'}>
                      {a.score} / {a.total} {a.passed ? '• passed' : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  )
}

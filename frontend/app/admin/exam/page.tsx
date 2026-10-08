'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getAdminExamAttempts, getAdminExamQuestions, getExamBank, retireExamQuestion } from '@/lib/exam'
import { formatDateTime, levelLabel } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { AdminExamAttempt, AdminExamQuestion, ExamBankLevel } from '@/types'

const LETTERS = ['A', 'B', 'C', 'D']

function tagName(b: { subject: string | null; level: ExamBankLevel['level'] }): string {
  return b.subject ? `${b.subject} • ${b.level ? levelLabel(b.level) : ''}` : 'General reasoning'
}

function Attempts() {
  const toast = useToast()
  const [attempts, setAttempts] = useState<AdminExamAttempt[] | null>(null)
  useEffect(() => {
    getAdminExamAttempts().then(setAttempts).catch((e) => { toast.error(errorMessage(e)); setAttempts([]) })
  }, [toast])

  if (attempts === null) return <LoadingSpinner />
  if (attempts.length === 0) return <EmptyState message="No finished attempts yet." />
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tutor</TableHead>
            <TableHead>Started</TableHead>
            <TableHead>Time taken</TableHead>
            <TableHead className="text-right">Score</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {attempts.map((a) => (
            <TableRow key={a.id}>
              <TableCell className="font-medium">{a.tutor_name}</TableCell>
              <TableCell className="whitespace-nowrap text-sm">{formatDateTime(a.started_at)}</TableCell>
              <TableCell className="text-sm">{Math.round(a.seconds_taken / 60)} min</TableCell>
              <TableCell className={cn('text-right font-semibold tabular-nums', a.passed ? 'text-emerald-700' : 'text-red-700')}>
                {a.score} / {a.total} {a.passed ? 'passed' : 'failed'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function Bank() {
  const toast = useToast()
  const [levels, setLevels] = useState<ExamBankLevel[] | null>(null)
  const [selected, setSelected] = useState<ExamBankLevel | null>(null)
  const [questions, setQuestions] = useState<AdminExamQuestion[] | null>(null)
  const [retiring, setRetiring] = useState<AdminExamQuestion | null>(null)

  useEffect(() => {
    getExamBank().then((l) => { setLevels(l); setSelected(l[0] ?? null) })
      .catch((e) => { toast.error(errorMessage(e)); setLevels([]) })
  }, [toast])

  const loadQuestions = useCallback(() => {
    if (!selected) return
    setQuestions(null)
    getAdminExamQuestions(selected.subject
      ? { subject: selected.subject, level: selected.level ?? undefined }
      : { general: true })
      .then(setQuestions).catch((e) => { toast.error(errorMessage(e)); setQuestions([]) })
  }, [selected, toast])
  useEffect(loadQuestions, [loadQuestions])

  async function retire(question: AdminExamQuestion) {
    try {
      await retireExamQuestion(question.id)
      toast.success('Retired: it won’t be served again')
      setQuestions((list) => list?.filter((q) => q.id !== question.id) ?? null)
      setLevels((list) => list?.map((l) => l === selected ? { ...l, active: l.active - 1 } : l) ?? null)
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  if (levels === null) return <LoadingSpinner />
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Claude writes the questions and a second, independent Claude call must get each one right before it&apos;s kept.
        The bank is topped up in the background towards each target.
      </p>
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow><TableHead>Questions on</TableHead><TableHead className="text-right">In the bank</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            {levels.map((l) => (
              <TableRow key={tagName(l)} className={cn('cursor-pointer', l === selected && 'bg-accent')} onClick={() => setSelected(l)}>
                <TableCell className="font-medium">{tagName(l)}</TableCell>
                <TableCell className={cn('text-right tabular-nums', l.active < l.target && 'text-amber-700')}>{l.active} / {l.target}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {selected && (
        <section className="space-y-3">
          <h2 className="font-semibold">{tagName(selected)}: newest questions</h2>
          {questions === null ? <LoadingSpinner /> : questions.length === 0 ? <EmptyState message="No questions yet." /> : (
            questions.map((q) => (
              <Card key={q.id}>
                <CardContent className="space-y-2 pt-5 text-sm">
                  <p className="whitespace-pre-line font-medium">{q.text}</p>
                  <ol className="space-y-0.5">
                    {q.options.map((o, i) => (
                      <li key={i} className={i === q.correct_index ? 'font-semibold text-emerald-700' : ''}>
                        {LETTERS[i]}. {o}{i === q.correct_index ? ' ✓' : ''}
                      </li>
                    ))}
                  </ol>
                  <p className="text-muted-foreground">{q.explanation}</p>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground">{formatDateTime(q.created_at)} • {q.model}</span>
                    <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setRetiring(q)}>Retire</Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </section>
      )}

      <ConfirmDialog open={retiring !== null} onOpenChange={(open) => { if (!open) setRetiring(null) }}
        title="Retire this question?" description="It will never be served to a tutor again." confirmLabel="Retire" destructive
        onConfirm={() => retiring ? retire(retiring) : undefined} />
    </div>
  )
}

/** Spec 4 R5.2, R5.9: every attempt's score, date and time taken, and the question bank. */
export default function AdminExamPage() {
  const [tab, setTab] = useState<'attempts' | 'bank'>('attempts')
  return (
    <>
      <PageHeader title="Qualifying exam" description="Tutors must pass with 14 of 20 before you can approve them." />
      <Tabs value={tab} onValueChange={(v) => setTab(v as 'attempts' | 'bank')} className="mb-4">
        <TabsList>
          <TabsTrigger value="attempts">Attempts</TabsTrigger>
          <TabsTrigger value="bank">Question bank</TabsTrigger>
        </TabsList>
      </Tabs>
      {tab === 'attempts' ? <Attempts /> : <Bank />}
    </>
  )
}

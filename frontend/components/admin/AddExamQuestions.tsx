'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useSubjects } from '@/hooks/useSubjects'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { addExamQuestion, addExamQuestions, readExamPdf } from '@/lib/exam'
import { LEVELS } from '@/lib/format'
import type { ExamQuestionBody, ExamQuestionTag, Level, ParsedExamQuestions } from '@/types'

const LETTERS = ['A', 'B', 'C', 'D']

/** A question being written or checked: no option is ticked yet until the admin picks one. */
type Editing = Omit<ExamQuestionBody, 'correct_index'> & { correct_index: number | null }
const GENERAL = 'general'

const EXAMPLE = `1. What is 3 x 4?
A. 7
B. 12
C. 34
D. 1
Answer: B
Explanation: 3 groups of 4 make 12.   (optional)`

/** General reasoning, or a listed subject at a level (spec 12 R1.1). */
function TagPicker({ tag, onChange }: { tag: ExamQuestionTag; onChange: (tag: ExamQuestionTag) => void }) {
  const subjects = useSubjects()
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="space-y-1.5">
        <Label>Questions on</Label>
        <Select value={tag.subject ?? GENERAL}
          onValueChange={(v) => onChange(v === GENERAL ? { subject: null, level: null }
            : { subject: v, level: tag.level ?? 'senior_secondary' })}>
          <SelectTrigger aria-label="Subject"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={GENERAL}>General reasoning</SelectItem>
            {subjects.map((s) => <SelectItem key={s.name} value={s.name}>{s.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      {tag.subject && (
        <div className="space-y-1.5">
          <Label>Level</Label>
          <Select value={tag.level ?? undefined} onValueChange={(v) => onChange({ ...tag, level: v as Level })}>
            <SelectTrigger aria-label="Level"><SelectValue /></SelectTrigger>
            <SelectContent>{LEVELS.map((l) => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      )}
    </div>
  )
}

/** One question's text, four options, the right one and an explanation; used to write and to check PDF questions. */
function QuestionEditor({ value, onChange }: { value: Editing; onChange: (v: Editing) => void }) {
  return (
    <div className="space-y-3">
      <Textarea rows={3} value={value.text} maxLength={2000} placeholder="The question"
        onChange={(e) => onChange({ ...value, text: e.target.value })} aria-label="Question" />
      <div className="grid gap-2 sm:grid-cols-2">
        {LETTERS.map((letter, i) => (
          <label key={letter} className="flex items-center gap-2 text-sm">
            <input type="radio" checked={value.correct_index === i} onChange={() => onChange({ ...value, correct_index: i })}
              aria-label={`${letter} is correct`} />
            <span className="w-4 font-medium">{letter}</span>
            <Input value={value.options[i] ?? ''} maxLength={500} aria-label={`Option ${letter}`}
              onChange={(e) => onChange({ ...value, options: value.options.map((o, j) => (j === i ? e.target.value : o)) })} />
          </label>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">Tick the correct option.</p>
      <Input value={value.explanation ?? ''} maxLength={2000} placeholder="Explanation (optional, only admins see it)"
        onChange={(e) => onChange({ ...value, explanation: e.target.value })} aria-label="Explanation" />
    </div>
  )
}

const BLANK: Editing = { text: '', options: ['', '', '', ''], correct_index: null, explanation: '' }

function ready(q: Editing): boolean {
  return q.text.trim().length >= 10 && q.options.every((o) => o.trim()) && q.correct_index !== null
    && new Set(q.options.map((o) => o.trim().toLowerCase())).size === 4
}

function WriteOne() {
  const toast = useToast()
  const [tag, setTag] = useState<ExamQuestionTag>({ subject: null, level: null })
  const [question, setQuestion] = useState<Editing>(BLANK)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try {
      await addExamQuestion(tag, { ...question, correct_index: question.correct_index! })
      toast.success('Question added to the bank')
      setQuestion(BLANK)
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">Write a question</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <TagPicker tag={tag} onChange={setTag} />
        <QuestionEditor value={question} onChange={setQuestion} />
        <Button onClick={save} disabled={saving || !ready(question)}>{saving ? 'Adding…' : 'Add question'}</Button>
      </CardContent>
    </Card>
  )
}

function UploadPdf() {
  const toast = useToast()
  const [tag, setTag] = useState<ExamQuestionTag>({ subject: null, level: null })
  const [file, setFile] = useState<File | null>(null)
  const [reading, setReading] = useState(false)
  const [found, setFound] = useState<ParsedExamQuestions | null>(null)
  const [drafts, setDrafts] = useState<(Editing & { number: number })[]>([])
  const [saving, setSaving] = useState(false)

  async function read() {
    if (!file) return
    setReading(true)
    try {
      const result = await readExamPdf(file)
      setFound(result)
      setDrafts(result.questions.map((q) => ({ ...q, explanation: q.explanation ?? '' })))
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setReading(false)
    }
  }

  async function save() {
    setSaving(true)
    try {
      const { added, duplicates } = await addExamQuestions(tag, drafts.map((d) => ({
        text: d.text, options: d.options, correct_index: d.correct_index!, explanation: d.explanation,
      })))
      toast.success(`${added} added${duplicates ? `, ${duplicates} already in the bank were skipped` : ''}`)
      setFound(null)
      setDrafts([])
      setFile(null)
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const allReady = drafts.length > 0 && drafts.every(ready)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Upload a PDF of questions</CardTitle>
        <CardDescription>
          Use a PDF with real text (not a scan or photo), laid out like this. You check every question before it&apos;s saved.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <pre className="rounded-md bg-muted p-3 text-xs">{EXAMPLE}</pre>
        <TagPicker tag={tag} onChange={setTag} />
        <div className="flex flex-wrap items-end gap-3">
          <Input type="file" accept="application/pdf,.pdf" className="max-w-sm"
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setFound(null); setDrafts([]) }} aria-label="PDF file" />
          <Button variant="outline" onClick={read} disabled={!file || reading}>{reading ? 'Reading…' : 'Read questions'}</Button>
        </div>

        {found && (
          <div className="space-y-4">
            <p className="text-sm">
              Found {found.questions.length} question{found.questions.length === 1 ? '' : 's'}. Check each one, fix what&apos;s wrong
              or remove it, then save.
            </p>
            {found.problems.length > 0 && (
              <ul className="list-disc rounded-md border border-amber-300 bg-amber-50 py-2 pl-8 pr-3 text-sm text-amber-900">
                {found.problems.map((p, i) => <li key={i}>{p.number ? `Question ${p.number}: ` : ''}{p.message}</li>)}
              </ul>
            )}
            {drafts.map((d, i) => (
              <div key={`${d.number}-${i}`} className={`space-y-2 rounded-md border p-3 ${ready(d) ? '' : 'border-amber-400'}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Question {d.number}{ready(d) ? '' : ' (needs fixing)'}</span>
                  <Button size="sm" variant="ghost" className="text-destructive"
                    onClick={() => setDrafts((list) => list.filter((_, j) => j !== i))}>Remove</Button>
                </div>
                <QuestionEditor value={d} onChange={(v) => setDrafts((list) => list.map((x, j) => (j === i ? { ...x, ...v } : x)))} />
              </div>
            ))}
            <Button onClick={save} disabled={saving || !allReady}>
              {saving ? 'Saving…' : `Save ${drafts.length} question${drafts.length === 1 ? '' : 's'}`}
            </Button>
            {!allReady && drafts.length > 0 && (
              <p className="text-xs text-muted-foreground">Every question needs text, four different options and a ticked answer.</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/** Spec 12 R1, R2: admins write questions, or upload a PDF and check them before they're saved. */
export default function AddExamQuestions() {
  return (
    <div className="space-y-6">
      <WriteOne />
      <UploadPdf />
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { addSubject, getAdminSubjects, setSubjectOffered } from '@/lib/content'
import type { SubjectAdmin, SubjectGroup } from '@/types'

const GROUPS: { value: SubjectGroup; label: string }[] = [
  { value: 'nigerian', label: 'Nigerian curriculum' },
  { value: 'international', label: 'International' },
]

/** Spec 7 R1: the subjects tutors can offer and parents can post jobs for. */
export default function AdminSubjectsPage() {
  const toast = useToast()
  const [subjects, setSubjects] = useState<SubjectAdmin[] | null>(null)
  const [name, setName] = useState('')
  const [group, setGroup] = useState<SubjectGroup>('nigerian')
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState<SubjectAdmin | null>(null)

  useEffect(() => {
    getAdminSubjects().then(setSubjects).catch((e) => { toast.error(errorMessage(e)); setSubjects([]) })
  }, [toast])

  const replace = (s: SubjectAdmin) => setSubjects((list) => list && list.map((x) => (x.id === s.id ? s : x)))

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setAdding(true)
    try {
      const added = await addSubject(name, group)
      setSubjects((list) => [...(list ?? []), added])
      setName('')
      toast.success(`${added.name} added. Tutors and parents can choose it now.`)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setAdding(false)
    }
  }

  async function setOffered(subject: SubjectAdmin, offered: boolean) {
    try {
      replace(await setSubjectOffered(subject.id, offered))
      toast.success(offered ? `${subject.name} restored.` : `${subject.name} removed.`)
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Subjects"
        description="The subjects tutors can offer and parents can post jobs for. Removing one hides it from new offers and jobs; existing offers, jobs and bookings keep it." />

      <form onSubmit={add} className="mb-6 grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-[1fr_14rem_auto] sm:items-end">
        <div className="space-y-1.5">
          <Label htmlFor="subject-name">New subject</Label>
          <Input id="subject-name" value={name} maxLength={60} placeholder="e.g. Data Science"
            onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="subject-group">Group</Label>
          <Select value={group} onValueChange={(v) => setGroup(v as SubjectGroup)}>
            <SelectTrigger id="subject-group"><SelectValue /></SelectTrigger>
            <SelectContent>{GROUPS.map((g) => <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <Button type="submit" disabled={adding || name.trim().length < 2}>{adding ? 'Adding…' : 'Add subject'}</Button>
      </form>

      {subjects === null ? <LoadingSpinner /> : GROUPS.map((g) => (
        <section key={g.value} className="mb-8">
          <h2 className="mb-2 text-lg font-semibold">{g.label}</h2>
          <ul className="divide-y rounded-lg border bg-card">
            {subjects.filter((s) => s.group === g.value)
              .sort((a, b) => Number(b.is_offered) - Number(a.is_offered) || a.name.localeCompare(b.name))
              .map((s) => (
                <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm">
                  <span className={s.is_offered ? '' : 'text-muted-foreground line-through'}>{s.name}</span>
                  <span className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {s.offers === 1 ? '1 tutor offer' : `${s.offers} tutor offers`}
                    </span>
                    {s.is_offered ? (
                      <Button size="sm" variant="outline" onClick={() => setRemoving(s)}>Remove</Button>
                    ) : (
                      <>
                        <Badge variant="secondary">Removed</Badge>
                        <Button size="sm" variant="outline"
                          onClick={() => setOffered(s, true).catch(() => {})}>Restore</Button>
                      </>
                    )}
                  </span>
                </li>
              ))}
          </ul>
        </section>
      ))}

      {removing && (
        <ConfirmDialog open onOpenChange={(open) => !open && setRemoving(null)}
          title={`Remove ${removing.name}?`}
          description={`Tutors and parents won't be able to choose it for new offers or jobs.${removing.offers
            ? ` The ${removing.offers === 1 ? 'tutor offer' : `${removing.offers} tutor offers`} that already teach it keep it.`
            : ''} You can restore it later.`}
          confirmLabel="Remove"
          onConfirm={() => setOffered(removing, false)} />
      )}
    </>
  )
}

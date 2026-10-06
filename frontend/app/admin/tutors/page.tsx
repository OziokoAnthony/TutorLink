'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatNaira, levelLabel } from '@/lib/format'
import { getPendingTutors, vetTutor } from '@/lib/tutors'
import type { TutorProfile } from '@/types'

export default function AdminVetTutorsPage() {
  const toast = useToast()
  const [tutors, setTutors] = useState<TutorProfile[] | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [rejecting, setRejecting] = useState<TutorProfile | null>(null)
  const [note, setNote] = useState('')

  useEffect(() => {
    getPendingTutors().then(setTutors).catch((e) => { toast.error(errorMessage(e)); setTutors([]) })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function vet(tutor: TutorProfile, status: 'approved' | 'rejected', rejectionNote?: string) {
    setBusyId(tutor.user_id)
    try {
      await vetTutor(tutor.user_id, status, rejectionNote)
      setTutors((list) => list?.filter((t) => t.user_id !== tutor.user_id) ?? null)
      toast.success(status === 'approved' ? `${tutor.full_name} approved` : `${tutor.full_name} rejected`)
      setRejecting(null)
      setNote('')
    } catch (e) {
      toast.error(errorMessage(e))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <PageHeader title="Vet tutors" description="Approve tutors before parents can see and book them." />
      {tutors === null ? <LoadingSpinner /> : tutors.length === 0 ? (
        <EmptyState message="No tutors pending review." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Area</TableHead>
                <TableHead>Subjects</TableHead>
                <TableHead>Rate</TableHead>
                <TableHead className="min-w-[200px]">Bio</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tutors.map((t) => (
                <TableRow key={t.user_id}>
                  <TableCell className="font-medium">{t.full_name}</TableCell>
                  <TableCell>{t.area}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {t.subjects.length === 0
                        ? <span className="text-muted-foreground">None yet</span>
                        : t.subjects.map((s) => <Badge key={s.id} variant="secondary">{s.subject} • {levelLabel(s.level)}</Badge>)}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">{formatNaira(t.rate_per_session)}</TableCell>
                  <TableCell className="max-w-xs text-sm text-muted-foreground">{t.bio || '—'}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button size="sm" className="bg-emerald-600 text-white hover:bg-emerald-700" disabled={busyId === t.user_id}
                        onClick={() => vet(t, 'approved')}>Approve</Button>
                      <Button size="sm" variant="destructive" disabled={busyId === t.user_id}
                        onClick={() => setRejecting(t)}>Reject</Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={rejecting !== null} onOpenChange={(open) => { if (!open && !busyId) { setRejecting(null); setNote('') } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject {rejecting?.full_name}?</DialogTitle>
            <DialogDescription>The tutor sees this note on their dashboard and in their email.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="rejection-note">Reason</Label>
            <Textarea id="rejection-note" rows={3} value={note} onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. We couldn't verify your teaching certificate." />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setRejecting(null); setNote('') }} disabled={!!busyId}>Cancel</Button>
            <Button variant="destructive" disabled={!!busyId || !note.trim()} onClick={() => rejecting && vet(rejecting, 'rejected', note.trim())}>
              {busyId ? 'Rejecting…' : 'Reject tutor'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

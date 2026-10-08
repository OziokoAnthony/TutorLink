'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import Avatar from '@/components/shared/Avatar'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime, formatNaira, levelLabel, slotText } from '@/lib/format'
import { getPendingTutors, vetTutor } from '@/lib/tutors'
import type { NinCheck, TutorProfile } from '@/types'

function CheckLine({ label, passed }: { label: string; passed: boolean | null }) {
  const [text, colour] = passed === null ? ['not checked', 'text-muted-foreground'] : passed ? ['passed', 'text-emerald-700'] : ['failed', 'text-red-700']
  return <li>{label}: <span className={colour}>{text}</span></li>
}

/** The result of each NIN check (spec 4 R3.9). The NIN record's name is never sent, only whether it matched. */
function NinSummary({ check, verifiedAt }: { check?: NinCheck | null; verifiedAt?: string | null }) {
  if (!check) return <span className="text-muted-foreground">Not checked yet</span>
  return (
    <div className="space-y-1 text-sm">
      <p className={verifiedAt ? 'font-medium text-emerald-700' : 'font-medium text-red-700'}>
        {verifiedAt ? 'Verified' : 'Not verified'} • NIN ending {check.nin_last4}
      </p>
      <ul className="text-xs">
        <CheckLine label="NIN exists" passed={check.nin_found} />
        <CheckLine label="Name matches" passed={check.name_matches} />
        <CheckLine label="Selfie matches" passed={check.selfie_matches} />
      </ul>
      <p className="text-xs text-muted-foreground">{formatDateTime(check.checked_at)}</p>
    </div>
  )
}

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
      <PageHeader title="Vet tutors" description="Approve tutors before parents can see and book them. Approval needs a verified NIN." />
      {tutors === null ? <LoadingSpinner /> : tutors.length === 0 ? (
        <EmptyState message="No tutors pending review." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[200px]">Name</TableHead>
                <TableHead className="min-w-[180px]">NIN</TableHead>
                <TableHead>Area</TableHead>
                <TableHead className="min-w-[220px]">Offers</TableHead>
                <TableHead className="min-w-[200px]">Bio</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tutors.map((t) => (
                <TableRow key={t.user_id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar name={t.full_name} photoUrl={t.photo_url} />
                      <div>
                        <p className="font-medium">{[t.first_name, t.middle_name, t.surname].filter(Boolean).join(' ') || t.full_name}</p>
                        {!t.photo_url && <p className="text-xs text-muted-foreground">No profile picture</p>}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell><NinSummary check={t.nin_check} verifiedAt={t.nin_verified_at} /></TableCell>
                  <TableCell>{t.area}</TableCell>
                  <TableCell>
                    {t.offers.length === 0 ? <span className="text-muted-foreground">None yet</span> : (
                      <ul className="space-y-1 text-sm">
                        {t.offers.map((o) => (
                          <li key={o.id}>
                            <span className="font-medium">{o.subjects.join(', ')}</span> • {levelLabel(o.level)} • {formatNaira(o.price)}
                            <span className="block text-xs text-muted-foreground">{o.windows.map(slotText).join(', ')}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </TableCell>
                  <TableCell className="max-w-xs text-sm text-muted-foreground">{t.bio || '—'}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button size="sm" className="bg-emerald-600 text-white hover:bg-emerald-700" disabled={busyId === t.user_id || !t.nin_verified_at}
                        title={t.nin_verified_at ? undefined : 'Approval needs a verified NIN'}
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

'use client'

import { useCallback, useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime, formatDayOf } from '@/lib/format'
import {
  cancelRemovalNotice, getUsers, getUsersOverview, removeUser, restoreUser, sendRemovalNotice, type UserFilters,
} from '@/lib/users'
import type { ActivityBand, RoleCounts, UserRow, UsersOverview } from '@/types'

const ALL = 'all'

const BAND_LABELS: Record<ActivityBand, string> = {
  active: 'Active',
  inactive: 'Inactive (90-180 days)',
  long_inactive: 'Inactive for a while (180+ days)',
  notice: 'Removal notice sent',
  removed: 'Removed',
}

const BAND_VARIANT: Record<ActivityBand, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  active: 'default', inactive: 'secondary', long_inactive: 'outline', notice: 'destructive', removed: 'outline',
}

const STAGE_LABELS = { pending: 'Onboarding', approved: 'Approved', rejected: 'Rejected' } as const

function Counts({ title, counts, extra }: { title: string; counts: RoleCounts; extra?: React.ReactNode }) {
  const items: [string, number][] = [
    ['Active', counts.active], ['Inactive', counts.inactive], ['Inactive for a while', counts.long_inactive],
    ['Notice sent', counts.notice], ['Removed', counts.removed],
  ]
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{title}: {counts.registered} registered</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <dl className="grid grid-cols-3 gap-3 text-sm sm:grid-cols-5">
          {items.map(([label, n]) => (
            <div key={label}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="text-xl font-semibold">{n}</dd></div>
          ))}
        </dl>
        {extra}
      </CardContent>
    </Card>
  )
}

/** Spec 10: how many parents and tutors there are, how active they are, and removing accounts with notice. */
export default function AdminUsersPage() {
  const toast = useToast()
  const [overview, setOverview] = useState<UsersOverview | null>(null)
  const [rows, setRows] = useState<UserRow[] | null>(null)
  const [role, setRole] = useState<string>(ALL)
  const [band, setBand] = useState<string>(ALL)
  const [vetting, setVetting] = useState<string>(ALL)
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const [noticing, setNoticing] = useState<UserRow | null>(null)
  const [removing, setRemoving] = useState<UserRow | null>(null)

  const loadOverview = useCallback(() => {
    getUsersOverview().then(setOverview).catch((e) => toast.error(errorMessage(e)))
  }, [toast])
  useEffect(loadOverview, [loadOverview])

  useEffect(() => {
    const filters: UserFilters = {
      role: role === ALL ? undefined : (role as UserFilters['role']),
      band: band === ALL ? undefined : (band as ActivityBand),
      vetting: vetting === ALL ? undefined : (vetting as UserFilters['vetting']),
      q: search || undefined,
    }
    setRows(null)
    getUsers(filters).then(setRows).catch((e) => { toast.error(errorMessage(e)); setRows([]) })
  }, [role, band, vetting, search, toast])

  function replace(row: UserRow) {
    setRows((list) => list && list.map((r) => (r.id === row.id ? row : r)))
    loadOverview()
  }

  async function act(action: () => Promise<UserRow>, done: string) {
    try {
      replace(await action())
      toast.success(done)
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Parents & tutors"
        description="Active: used TutorLink in the last 90 days. Inactive: 90-180 days. Inactive for a while: over 180 days. An account can be removed 14 days after a notice, and only with no balance, unpaid earnings, or unfinished bookings or lessons." />

      {overview === null ? <LoadingSpinner /> : (
        <div className="mb-6 grid gap-4 lg:grid-cols-2">
          <Counts title="Parents" counts={overview.parents} />
          <Counts title="Tutors" counts={overview.tutors} extra={
            <p className="text-sm text-muted-foreground">
              Onboarding {overview.tutor_stages.onboarding} · Approved {overview.tutor_stages.approved} · Rejected {overview.tutor_stages.rejected}
            </p>
          } />
        </div>
      )}

      <form className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[10rem_16rem_12rem_1fr]"
        onSubmit={(e) => { e.preventDefault(); setSearch(q.trim()) }}>
        <Select value={role} onValueChange={(v) => { setRole(v); if (v !== 'tutor') setVetting(ALL) }}>
          <SelectTrigger aria-label="Role"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Parents and tutors</SelectItem>
            <SelectItem value="parent">Parents</SelectItem>
            <SelectItem value="tutor">Tutors</SelectItem>
          </SelectContent>
        </Select>
        <Select value={band} onValueChange={setBand}>
          <SelectTrigger aria-label="Activity"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any activity</SelectItem>
            {(Object.keys(BAND_LABELS) as ActivityBand[]).map((b) => <SelectItem key={b} value={b}>{BAND_LABELS[b]}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={vetting} onValueChange={(v) => { setVetting(v); if (v !== ALL) setRole('tutor') }}>
          <SelectTrigger aria-label="Onboarding"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any onboarding</SelectItem>
            {(Object.keys(STAGE_LABELS) as (keyof typeof STAGE_LABELS)[]).map((s) => (
              <SelectItem key={s} value={s}>{STAGE_LABELS[s]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex gap-2">
          <Input value={q} maxLength={100} placeholder="Search name or email" onChange={(e) => setQ(e.target.value)} />
          <Button type="submit" variant="outline">Search</Button>
        </div>
      </form>

      {rows === null ? <LoadingSpinner /> : rows.length === 0 ? <EmptyState message="No accounts match." /> : (
        <ul className="divide-y rounded-lg border bg-card">
          {rows.map((r) => (
            <li key={r.id} className="space-y-2 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-medium">{r.name ?? r.email}</span>
                  <span className="text-muted-foreground"> · {r.email} · {r.role === 'parent' ? 'Parent' : 'Tutor'}</span>
                  {r.vetting_status && <span className="text-muted-foreground"> · {STAGE_LABELS[r.vetting_status]}</span>}
                </div>
                <Badge variant={BAND_VARIANT[r.band]}>{BAND_LABELS[r.band]}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Joined {formatDayOf(r.joined_at)} · Last seen {formatDateTime(r.last_seen_at)}
                {r.removed_at && ` · Removed ${formatDayOf(r.removed_at)}`}
              </p>
              {r.outstanding.length > 0 && (
                <p className="text-xs text-amber-700">Outstanding: {r.outstanding.join(', ')}. It can&apos;t be removed until these are settled.</p>
              )}
              {r.removal_due_at && (
                <p className="text-xs">
                  {r.ready_to_remove ? 'Notice ran out: ready to remove.' : `Closes on ${formatDayOf(r.removal_due_at)} at the earliest.`}
                  {r.removal_reason && ` Reason: ${r.removal_reason}`}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                {r.band !== 'removed' && !r.removal_due_at && (
                  <Button size="sm" variant="outline" disabled={r.outstanding.length > 0} onClick={() => setNoticing(r)}>
                    Send removal notice
                  </Button>
                )}
                {r.removal_due_at && (
                  <>
                    <Button size="sm" variant="outline"
                      onClick={() => act(() => cancelRemovalNotice(r.id), 'Notice cancelled. They have been told.').catch(() => {})}>
                      Cancel notice
                    </Button>
                    <Button size="sm" variant="destructive" disabled={!r.ready_to_remove || r.outstanding.length > 0}
                      onClick={() => setRemoving(r)}>
                      Remove
                    </Button>
                  </>
                )}
                {r.band === 'removed' && (
                  <Button size="sm" variant="outline"
                    onClick={() => act(() => restoreUser(r.id), 'Account restored. They can log in again.').catch(() => {})}>
                    Restore
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {noticing && (
        <NoteDialog open onOpenChange={(open) => !open && setNoticing(null)}
          title={`Send a removal notice to ${noticing.name ?? noticing.email}?`}
          description="They'll be told in the app and by email that their account will be closed in 14 days, and why. They can reply through Help & feedback. After 14 days you can remove the account."
          confirmLabel="Send notice" destructive noteLabel="Reason they will see (10-1,000 characters)" noteRequired
          onConfirm={(reason) => act(() => sendRemovalNotice(noticing.id, reason), 'Notice sent.')} />
      )}
      {removing && (
        <ConfirmDialog open onOpenChange={(open) => !open && setRemoving(null)}
          title={`Remove ${removing.name ?? removing.email}?`}
          description="They won't be able to log in, a tutor disappears from search, and a parent's open job posts close. Their bookings and payments are kept, and you can restore the account later."
          confirmLabel="Remove" onConfirm={() => act(() => removeUser(removing.id), 'Account removed. They have been emailed.')} />
      )}
    </>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useToast } from '@/hooks/useToast'
import { getAdminDashboard, getTeamActivity } from '@/lib/activity'
import { errorMessage } from '@/lib/api'
import { getAdmins, setMyAdminName } from '@/lib/auth'
import { formatDateTime } from '@/lib/format'
import type { ActivityEntry, AdminAccount, AdminDashboard, TeamActivityEntry } from '@/types'

const EVERYONE = 'everyone'

function ActivityList({ entries, empty }: { entries: ActivityEntry[]; empty: string }) {
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">{empty}</p>
  return (
    <ul className="divide-y">
      {entries.map((e) => (
        <li key={e.id} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5 py-2 text-sm">
          <span>{e.text}</span>
          <span className="text-xs text-muted-foreground">{formatDateTime(e.created_at)}</span>
        </li>
      ))}
    </ul>
  )
}

/** Spec 8: the welcome, the last session and recent actions; the super admin also sees the team's activity. */
export default function AdminDashboardPage() {
  const toast = useToast()
  const [dash, setDash] = useState<AdminDashboard | null>(null)
  const [name, setName] = useState('')
  const [savingName, setSavingName] = useState(false)
  const [admins, setAdmins] = useState<AdminAccount[]>([])
  const [filter, setFilter] = useState(EVERYONE)
  const [team, setTeam] = useState<TeamActivityEntry[] | null>(null)

  useEffect(() => {
    getAdminDashboard().then(setDash).catch((e) => toast.error(errorMessage(e)))
  }, [toast])

  // Team activity is only asked for by the super admin; anyone else gets a 403 (R4.4).
  const isSuper = !!dash?.is_super_admin
  useEffect(() => {
    if (!isSuper) return
    getAdmins().then(setAdmins).catch(() => {})
  }, [isSuper])
  useEffect(() => {
    if (!isSuper) return
    setTeam(null)
    getTeamActivity(filter === EVERYONE ? undefined : filter)
      .then(setTeam).catch((e) => { toast.error(errorMessage(e)); setTeam([]) })
  }, [isSuper, filter, toast])

  async function saveName(e: React.FormEvent) {
    e.preventDefault()
    setSavingName(true)
    try {
      const saved = await setMyAdminName(name.trim())
      setDash((d) => d && { ...d, name: saved.name })
      toast.success('Name saved')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSavingName(false)
    }
  }

  if (!dash) return <LoadingSpinner />

  const last = dash.last_session
  const others = admins.filter((a) => !a.is_super_admin)

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Welcome, {dash.name ?? dash.email}</h1>
        <p className="text-sm text-muted-foreground">
          {dash.is_super_admin ? 'Super admin. ' : ''}
          {dash.session_started_at ? `Logged in ${formatDateTime(dash.session_started_at)}.` : ''}
        </p>
      </div>

      {!dash.name && (
        <form onSubmit={saveName}
          className="mb-6 grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="my-name">What should we call you?</Label>
            <Input id="my-name" value={name} maxLength={80} placeholder="Your name"
              onChange={(e) => setName(e.target.value)} />
          </div>
          <Button type="submit" disabled={savingName || name.trim().length < 2}>
            {savingName ? 'Saving…' : 'Save name'}
          </Button>
        </form>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Your last session</CardTitle>
            <CardDescription>
              {last ? `${formatDateTime(last.started_at)} to ${formatDateTime(last.ended_at)}`
                : 'This is your first session we have a record of.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {last && <ActivityList entries={last.actions} empty="You didn't change anything." />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Your recent actions</CardTitle>
            <CardDescription>Your latest 50.</CardDescription>
          </CardHeader>
          <CardContent>
            <ActivityList entries={dash.recent} empty="Nothing yet." />
          </CardContent>
        </Card>
      </div>

      {isSuper && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 space-y-0">
            <div className="space-y-1.5">
              <CardTitle className="text-lg">Team activity</CardTitle>
              <CardDescription>What the other admins did, latest 100. Only you can see this.</CardDescription>
            </div>
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-56" aria-label="Show activity of"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={EVERYONE}>All admins</SelectItem>
                {others.map((a) => <SelectItem key={a.id} value={a.id}>{a.name ?? a.email}</SelectItem>)}
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent>
            {team === null ? <LoadingSpinner /> : team.length === 0
              ? <EmptyState message="No activity from other admins yet." />
              : (
                <ul className="divide-y">
                  {team.map((e) => (
                    <li key={e.id} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5 py-2 text-sm">
                      <span><span className="font-medium">{e.admin_name ?? e.admin_email}</span>: {e.text}</span>
                      <span className="text-xs text-muted-foreground">{formatDateTime(e.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
          </CardContent>
        </Card>
      )}
    </>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import ChangePasswordCard from '@/components/shared/ChangePasswordCard'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { addAdmin, getAdmins, removeAdmin, setMyAdminName } from '@/lib/auth'
import { formatDateTime } from '@/lib/format'
import type { AdminAccount } from '@/types'

/** Who can use /admin. The super admin adds admins (with a temporary password they pass on) and removes them. */
export default function AdminAdminsPage() {
  const toast = useToast()
  const { user } = useAuth()
  const [admins, setAdmins] = useState<AdminAccount[] | null>(null)
  const [newName, setNewName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState<AdminAccount | null>(null)
  const [myName, setMyName] = useState<string | null>(null)
  const [savingName, setSavingName] = useState(false)

  useEffect(() => {
    getAdmins().then(setAdmins).catch((e) => { toast.error(errorMessage(e)); setAdmins([]) })
  }, [toast])

  const me = admins?.find((a) => a.id === user?.id)
  const iAmSuper = !!me?.is_super_admin

  async function saveMyName(e: React.FormEvent) {
    e.preventDefault()
    setSavingName(true)
    try {
      const saved = await setMyAdminName((myName ?? '').trim())
      setAdmins((list) => list && list.map((a) => (a.id === saved.id ? saved : a)))
      setMyName(null)
      toast.success('Name saved')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSavingName(false)
    }
  }

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setAdding(true)
    try {
      const added = await addAdmin(newName.trim(), email.trim(), password)
      setAdmins((list) => [...(list ?? []).filter((a) => a.id !== added.id), added])
      setNewName('')
      setEmail('')
      setPassword('')
      toast.success(`${added.email} can log in now. Give them the temporary password and ask them to change it.`)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setAdding(false)
    }
  }

  async function remove(admin: AdminAccount) {
    try {
      await removeAdmin(admin.id)
      setAdmins((list) => list && list.map((a) => (a.id === admin.id ? { ...a, is_active: false } : a)))
      toast.success(`${admin.email} is no longer an admin.`)
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Admins"
        description={iAmSuper
          ? 'You are the super admin: you add and remove admins, and nobody can remove you.'
          : 'Only the super admin can add or remove admins.'} />

      {iAmSuper && (
        <form onSubmit={add} className="mb-6 grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="admin-name">Their name</Label>
            <Input id="admin-name" value={newName} maxLength={80} autoComplete="off"
              onChange={(e) => setNewName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="admin-email">New admin&apos;s email</Label>
            <Input id="admin-email" type="email" autoComplete="off" value={email}
              onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="admin-password">Temporary password</Label>
            <Input id="admin-password" type="text" autoComplete="new-password" value={password} maxLength={72}
              placeholder="At least 8 characters" onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button type="submit" disabled={adding || newName.trim().length < 2 || !email.includes('@') || password.length < 8}>
            {adding ? 'Adding…' : 'Add admin'}
          </Button>
        </form>
      )}

      {admins === null ? <LoadingSpinner /> : (
        <ul className="mb-8 divide-y rounded-lg border bg-card">
          {admins.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm">
              <span className={a.is_active ? '' : 'text-muted-foreground line-through'}>
                {a.name ? <><span className="font-medium">{a.name}</span> · {a.email}</> : a.email}
                {a.id === user?.id && ' (you)'}
              </span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">Added {formatDateTime(a.created_at)}</span>
                {a.is_super_admin && <Badge>Super admin</Badge>}
                {!a.is_active && <Badge variant="secondary">Removed</Badge>}
                {iAmSuper && a.is_active && !a.is_super_admin && (
                  <Button size="sm" variant="outline" onClick={() => setRemoving(a)}>Remove</Button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      {me && (
        <form onSubmit={saveMyName}
          className="mb-6 grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="my-name">Your name</Label>
            <Input id="my-name" value={myName ?? me.name ?? ''} maxLength={80} placeholder="Shown in your welcome"
              onChange={(e) => setMyName(e.target.value)} />
          </div>
          <Button type="submit"
            disabled={savingName || myName === null || myName.trim().length < 2 || myName.trim() === me.name}>
            {savingName ? 'Saving…' : 'Save name'}
          </Button>
        </form>
      )}

      <ChangePasswordCard description="Change your own password. If an admin gave you a temporary one, replace it here." />

      {removing && (
        <ConfirmDialog open onOpenChange={(open) => !open && setRemoving(null)}
          title={`Remove ${removing.email}?`}
          description="They'll be logged out everywhere and can't open the admin pages any more. To bring them back, add their email again with a new temporary password."
          confirmLabel="Remove"
          onConfirm={() => remove(removing)} />
      )}
    </>
  )
}

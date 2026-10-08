'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Bell } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { formatDateTime } from '@/lib/format'
import { getNotifications, markAllRead, markRead } from '@/lib/notifications'
import { cn } from '@/lib/utils'
import type { AppNotification, NotificationList } from '@/types'

const REFRESH_MS = 60_000

/** Bell with the unread count; opening it lists recent notifications. Clicking one marks it read and follows its link. */
export default function NotificationBell() {
  const router = useRouter()
  const [list, setList] = useState<NotificationList | null>(null)

  const load = useCallback(() => {
    getNotifications().then(setList).catch(() => undefined)
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, REFRESH_MS)
    return () => clearInterval(timer)
  }, [load])

  async function open(n: AppNotification) {
    if (!n.read_at) {
      setList((l) => l && {
        unread_count: Math.max(0, l.unread_count - 1),
        items: l.items.map((x) => x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x),
      })
      markRead(n.id).catch(() => undefined)
    }
    if (n.link) router.push(n.link)
  }

  async function readAll() {
    const now = new Date().toISOString()
    setList((l) => l && { unread_count: 0, items: l.items.map((x) => ({ ...x, read_at: x.read_at ?? now })) })
    markAllRead().catch(load)
  }

  const unread = list?.unread_count ?? 0
  return (
    <DropdownMenu onOpenChange={(isOpen) => isOpen && load()}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="relative" aria-label={unread ? `Notifications (${unread} unread)` : 'Notifications'}>
          <Bell className="h-4 w-4" aria-hidden />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-w-[calc(100vw-2rem)]">
        <div className="flex items-center justify-between">
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          {unread > 0 && (
            <Button variant="link" size="sm" className="h-auto px-2 text-xs" onClick={readAll}>Mark all read</Button>
          )}
        </div>
        <DropdownMenuSeparator />
        <div className="max-h-96 overflow-y-auto">
          {!list || list.items.length === 0 ? (
            <p className="px-2 py-6 text-center text-sm text-muted-foreground">No notifications yet.</p>
          ) : list.items.map((n) => (
            <DropdownMenuItem key={n.id} onSelect={() => open(n)} className="flex-col items-start gap-0.5 py-2">
              <span className={cn('text-sm', !n.read_at && 'font-semibold')}>
                {!n.read_at && <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-primary" aria-label="Unread" />}
                {n.title}
              </span>
              <span className="text-xs text-muted-foreground">{n.body}</span>
              <span className="text-[11px] text-muted-foreground">{formatDateTime(n.created_at)}</span>
            </DropdownMenuItem>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

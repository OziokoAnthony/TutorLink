import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

export default function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center">
      <Inbox className="h-8 w-8 text-muted-foreground" aria-hidden />
      <p className="text-sm text-muted-foreground">{message}</p>
      {action}
    </div>
  )
}

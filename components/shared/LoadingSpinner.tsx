import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function LoadingSpinner({ label = 'Loading…', className }: { label?: string; className?: string }) {
  return (
    <div role="status" className={cn('flex items-center justify-center gap-2 py-12 text-muted-foreground', className)}>
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  )
}

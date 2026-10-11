import Link from 'next/link'
import { Button } from '@/components/ui/button'

/** Any address that isn't a page. */
export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-24 text-center">
      <p className="text-sm font-semibold text-primary">404</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">Page not found</h1>
      <p className="mt-3 text-muted-foreground">The page you&apos;re looking for doesn&apos;t exist or has moved.</p>
      <div className="mt-8 flex gap-3">
        <Button asChild><Link href="/">Go home</Link></Button>
        <Button variant="outline" asChild><Link href="/tutors">Find a tutor</Link></Button>
      </div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { Copy, Landmark } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { requestAccountNumber } from '@/lib/wallet'
import type { VirtualAccount } from '@/types'

/** The parent's own TutorLink account number: every bank transfer to it tops up their balance. */
export default function AccountNumberCard({ account, onCreated }: { account: VirtualAccount | null; onCreated: () => void }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)

  async function create() {
    setBusy(true)
    try {
      await requestAccountNumber()
      onCreated()
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg"><Landmark className="h-5 w-5" aria-hidden />How to pay</CardTitle>
        <CardDescription>Pay by bank transfer from any Nigerian bank app. No card needed.</CardDescription>
      </CardHeader>
      <CardContent>
        {account ? (
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Your own TutorLink account number</p>
            <div className="flex items-center gap-2">
              <span className="font-mono text-2xl font-bold tracking-wider">{account.account_number}</span>
              <Button variant="ghost" size="sm" aria-label="Copy account number"
                onClick={() => navigator.clipboard.writeText(account.account_number).then(() => toast.success('Account number copied'))}>
                <Copy className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            <p className="text-sm">{account.bank_name} • {account.account_name}</p>
            <p className="pt-2 text-xs text-muted-foreground">
              Money you send here is added to your TutorLink balance within minutes, and lessons waiting to be paid are paid from it automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">You&apos;ll get your account number when a tutor accepts your first booking.</p>
            <Button variant="outline" size="sm" onClick={create} disabled={busy}>{busy ? 'Creating…' : 'Get my account number now'}</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

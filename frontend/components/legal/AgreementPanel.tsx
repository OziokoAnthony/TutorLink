'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LEGAL_TITLES } from '@/components/legal/LegalPage'
import LegalText, { LEGAL_PROSE } from '@/components/legal/LegalText'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { acceptLegal, getMyLegal } from '@/lib/content'
import { formatDateTime, formatDayOf } from '@/lib/format'
import type { LegalKind, MyLegal } from '@/types'

/**
 * The reader's privacy notice, terms and disclaimer, with "I agree" (spec 9 R2.1). Shows when they agreed once
 * they have. If a document changed while it was open, the latest versions are loaded to read again (R2.3).
 */
export default function AgreementPanel({ legal, onChange }: { legal: MyLegal; onChange: (legal: MyLegal) => void }) {
  const toast = useToast()
  const [kind, setKind] = useState<LegalKind>(legal.documents[0]?.kind ?? 'terms')
  const [ticked, setTicked] = useState(false)
  const [saving, setSaving] = useState(false)

  const doc = legal.documents.find((d) => d.kind === kind) ?? legal.documents[0]
  const agreed = legal.documents.length > 0 && legal.documents.every((d) => d.accepted_at)

  async function agree() {
    setSaving(true)
    try {
      onChange(await acceptLegal(legal.documents.map((d) => d.id)))
      toast.success('Thank you. You can continue.')
    } catch (e) {
      toast.error(errorMessage(e))
      setTicked(false)
      getMyLegal().then(onChange).catch(() => {})
    } finally {
      setSaving(false)
    }
  }

  if (!doc) return <p className="text-sm text-muted-foreground">There is nothing to agree to yet.</p>

  return (
    <div className="space-y-4">
      <Tabs value={doc.kind} onValueChange={(v) => setKind(v as LegalKind)}>
        <TabsList>
          {legal.documents.map((d) => <TabsTrigger key={d.kind} value={d.kind}>{LEGAL_TITLES[d.kind]}</TabsTrigger>)}
        </TabsList>
      </Tabs>
      <div className="max-h-[50vh] overflow-y-auto rounded-md border bg-background p-4">
        <p className="text-xs text-muted-foreground">Last updated {formatDayOf(doc.published_at)}</p>
        <div className={LEGAL_PROSE}><LegalText text={doc.body} /></div>
      </div>
      {agreed ? (
        <p className="text-sm text-muted-foreground">
          You agreed to these versions on {formatDateTime(legal.documents[0].accepted_at!)}.
        </p>
      ) : (
        <div className="space-y-3">
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={ticked} disabled={!legal.can_accept}
              onChange={(e) => setTicked(e.target.checked)} />
            <span>I have read and agree to the Terms of Service, Privacy Notice and Disclaimer.</span>
          </label>
          <Button onClick={agree} disabled={!ticked || saving || !legal.can_accept}>
            {saving ? 'Saving…' : 'I agree'}
          </Button>
          {!legal.can_accept && (
            <p className="text-sm text-muted-foreground">Finish the other onboarding steps first, then agree here.</p>
          )}
        </div>
      )}
    </div>
  )
}

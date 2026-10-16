'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { AUDIENCE_LABELS, LEGAL_TITLES } from '@/components/legal/LegalPage'
import LegalText, { LEGAL_PROSE, isDraft } from '@/components/legal/LegalText'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getLegalVersions, publishLegal } from '@/lib/content'
import { formatDateTime } from '@/lib/format'
import type { LegalAudience, LegalKind, LegalVersion } from '@/types'

const KINDS = Object.keys(LEGAL_TITLES) as LegalKind[]
const MIN = 100
const MAX = 50_000

/** Spec 7 R2, spec 9 R1.2: the parents' and tutors' privacy notice, terms and disclaimer, edited and published here. */
export default function AdminLegalPage() {
  const toast = useToast()
  const [audience, setAudience] = useState<LegalAudience>('parent')
  const [kind, setKind] = useState<LegalKind>('privacy')
  const [versions, setVersions] = useState<LegalVersion[] | null>(null)
  const [text, setText] = useState('')
  const [notify, setNotify] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const load = useCallback(() => {
    setVersions(null)
    getLegalVersions(audience, kind).then((list) => {
      setVersions(list)
      setText(list[0]?.body ?? '')
    }).catch((e) => { toast.error(errorMessage(e)); setVersions([]) })
  }, [audience, kind, toast])
  useEffect(load, [load])

  const who = audience === 'parent' ? 'parent' : 'tutor'
  const current = versions?.[0]?.body ?? ''
  const changed = text.trim() !== current.trim()
  const length = text.trim().length

  async function publish() {
    try {
      await publishLegal(audience, kind, text, notify)
      toast.success(`Published. Every ${who} must agree to it before continuing.`)
      setNotify(false)
      load()
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Legal pages"
        description="Parents and tutors each have their own privacy notice, terms and disclaimer. Publishing shows the new text at once, and everyone it's for must agree to it before continuing; earlier versions are kept below." />
      <Tabs value={audience} onValueChange={(v) => setAudience(v as LegalAudience)} className="mb-3">
        <TabsList>
          {(Object.keys(AUDIENCE_LABELS) as LegalAudience[]).map((a) => (
            <TabsTrigger key={a} value={a}>{AUDIENCE_LABELS[a]}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <Tabs value={kind} onValueChange={(v) => setKind(v as LegalKind)} className="mb-4">
        <TabsList>{KINDS.map((k) => <TabsTrigger key={k} value={k}>{LEGAL_TITLES[k]}</TabsTrigger>)}</TabsList>
      </Tabs>

      {versions === null ? <LoadingSpinner /> : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="legal-text" className="text-sm font-medium">Text</label>
              <Textarea id="legal-text" rows={24} value={text} maxLength={MAX} className="font-mono text-xs"
                onChange={(e) => setText(e.target.value)} />
              <p className="text-xs text-muted-foreground">
                A blank line starts a new paragraph. Start a line with <code>## </code> for a heading or <code>- </code>
                {' '}for a bullet, and wrap words in <code>**</code> for bold. {length.toLocaleString()} / {MAX.toLocaleString()} characters.
              </p>
              {isDraft(text) && (
                <p className="text-xs text-amber-700">
                  Fill in every &quot;[… to be filled in]&quot; before launch: until then the page shows a draft banner.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">
                Preview <Link href={`/${kind}`} target="_blank" className="font-normal text-primary hover:underline">(open live page)</Link>
              </p>
              <div className={`max-h-[34rem] overflow-y-auto rounded-md border bg-card px-4 pb-4 ${LEGAL_PROSE}`}>
                <LegalText text={text} />
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4 accent-primary" checked={notify}
                onChange={(e) => setNotify(e.target.checked)} />
              Also tell every {who} in the app
            </label>
            <Button disabled={!changed || length < MIN} onClick={() => setConfirming(true)}>Publish</Button>
            {changed && <Button variant="ghost" onClick={() => setText(current)}>Discard changes</Button>}
            {length > 0 && length < MIN && <span className="text-xs text-destructive">At least {MIN} characters.</span>}
          </div>

          <h2 className="mb-2 mt-10 text-lg font-semibold">Versions</h2>
          <ul className="divide-y rounded-lg border bg-card text-sm">
            {versions.map((v, i) => (
              <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
                <span>
                  {formatDateTime(v.published_at)} · {v.published_by ?? 'Starting version'}
                  {i === 0 && <span className="ml-2 text-xs font-medium text-primary">Live</span>}
                </span>
                {i > 0 && <Button size="sm" variant="outline" onClick={() => setText(v.body)}>Load into editor</Button>}
              </li>
            ))}
          </ul>
        </>
      )}

      <ConfirmDialog open={confirming} onOpenChange={setConfirming}
        title={`Publish the ${who}s' ${LEGAL_TITLES[kind].toLowerCase()}?`}
        description={`The new text goes live at once, and every ${who} must agree to it before they can continue.${
          notify ? ` They're also told in the app.` : ''}`}
        confirmLabel="Publish" onConfirm={publish} />
    </>
  )
}

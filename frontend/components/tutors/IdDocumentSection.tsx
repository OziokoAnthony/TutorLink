'use client'

import { useState } from 'react'
import { FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { ID_LABELS, uploadIdDocument } from '@/lib/identity'
import type { IdDocument, IdDocumentType } from '@/types'

const STATUS_TEXT = { pending: 'Waiting for an admin to check it', verified: 'Verified', rejected: 'Not accepted' }

/** Spec 11 R1: upload a valid ID to continue onboarding now, and verify the NIN within 90 days. */
export default function IdDocumentSection({ documents, onChange }: { documents: IdDocument[]; onChange: () => void }) {
  const toast = useToast()
  const [type, setType] = useState<IdDocumentType>('voters_card')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const latest = documents[0]
  const canUpload = !latest || latest.status === 'rejected'

  async function upload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    try {
      await uploadIdDocument(type, file)
      toast.success('ID uploaded. An admin will check it soon.')
      setFile(null)
      onChange()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3 rounded-md border bg-muted/30 p-3">
      {latest && (
        <div className="text-sm">
          <a href={latest.file_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 font-medium underline">
            <FileText className="h-4 w-4" aria-hidden />{ID_LABELS[latest.type]}
          </a>
          <span className="text-muted-foreground"> · {STATUS_TEXT[latest.status]}</span>
          {latest.status === 'rejected' && latest.review_note && (
            <p className="mt-1 text-xs text-destructive">Reason: {latest.review_note}</p>
          )}
        </div>
      )}
      {canUpload && (
        <form onSubmit={upload} className="grid gap-3 sm:grid-cols-[14rem_1fr_auto] sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="id-type">ID document</Label>
            <Select value={type} onValueChange={(v) => setType(v as IdDocumentType)}>
              <SelectTrigger id="id-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                {(Object.keys(ID_LABELS) as IdDocumentType[]).map((t) => <SelectItem key={t} value={t}>{ID_LABELS[t]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="id-file">Picture or scan (PDF, JPG or PNG, up to 10 MB)</Label>
            <Input id="id-file" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
          <Button type="submit" disabled={!file || busy}>{busy ? 'Uploading…' : 'Upload ID'}</Button>
        </form>
      )}
    </div>
  )
}

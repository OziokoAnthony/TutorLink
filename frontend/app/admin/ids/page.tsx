'use client'

import { useCallback, useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { ID_LABELS, getAdminIdDocuments, reviewIdDocument } from '@/lib/identity'
import type { AdminIdDocument } from '@/types'

const STATUS = {
  pending: { label: 'Waiting', variant: 'secondary' },
  verified: { label: 'Verified', variant: 'default' },
  rejected: { label: 'Rejected', variant: 'destructive' },
} as const

function tutorName(d: AdminIdDocument): string {
  return [d.tutor_first_name, d.tutor_middle_name, d.tutor_surname].filter(Boolean).join(' ')
}

/** Spec 11 R1.2, R4.1: ID documents tutors start with before their NIN; verify, or reject with a note. */
export default function AdminIdDocumentsPage() {
  const toast = useToast()
  const [pendingOnly, setPendingOnly] = useState(true)
  const [docs, setDocs] = useState<AdminIdDocument[] | null>(null)
  const [reviewing, setReviewing] = useState<{ doc: AdminIdDocument; verify: boolean } | null>(null)

  const load = useCallback(() => {
    setDocs(null)
    getAdminIdDocuments(pendingOnly ? 'pending' : undefined)
      .then(setDocs).catch((e) => { toast.error(errorMessage(e)); setDocs([]) })
  }, [pendingOnly, toast])
  useEffect(load, [load])

  async function review(doc: AdminIdDocument, verify: boolean, note: string) {
    try {
      const updated = await reviewIdDocument(doc.id, verify ? 'verified' : 'rejected', note || undefined)
      toast.success(verify ? `${ID_LABELS[doc.type]} verified` : `${ID_LABELS[doc.type]} rejected`)
      setDocs((list) => list && (pendingOnly ? list.filter((d) => d.id !== doc.id)
        : list.map((d) => (d.id === doc.id ? updated : d))))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="ID documents"
        description="Tutors can start with a valid ID and must verify their NIN within 90 days of registering. Open each file, check the name matches the tutor and the document looks genuine." />
      <Tabs value={pendingOnly ? 'pending' : 'all'} onValueChange={(v) => setPendingOnly(v === 'pending')} className="mb-4">
        <TabsList>
          <TabsTrigger value="pending">Waiting</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {docs === null ? <LoadingSpinner /> : docs.length === 0 ? (
        <EmptyState message={pendingOnly ? 'No ID documents waiting for review.' : 'No ID documents yet.'} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[180px]">Tutor</TableHead>
                <TableHead className="min-w-[200px]">Document</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {docs.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">{tutorName(d)}</TableCell>
                  <TableCell className="text-sm">
                    <a href={d.file_url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 font-medium underline">
                      <FileText className="h-4 w-4" aria-hidden />{ID_LABELS[d.type]}
                    </a>
                    <span className="block text-xs text-muted-foreground">Uploaded {formatDateTime(d.created_at)}</span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS[d.status].variant}>{STATUS[d.status].label}</Badge>
                    {d.review_note && <span className="mt-1 block max-w-xs text-xs text-muted-foreground">{d.review_note}</span>}
                  </TableCell>
                  <TableCell>
                    {d.status === 'pending' && (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" className="bg-emerald-600 text-white hover:bg-emerald-700"
                          onClick={() => setReviewing({ doc: d, verify: true })}>Verify</Button>
                        <Button size="sm" variant="destructive" onClick={() => setReviewing({ doc: d, verify: false })}>Reject</Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <NoteDialog
        open={reviewing !== null}
        onOpenChange={(open) => { if (!open) setReviewing(null) }}
        title={reviewing ? `${reviewing.verify ? 'Verify' : 'Reject'} ${tutorName(reviewing.doc)}'s ${ID_LABELS[reviewing.doc.type].toLowerCase()}?` : ''}
        description={reviewing?.verify
          ? 'Only if the name matches the tutor and the document looks genuine. The tutor is told.'
          : 'The tutor sees your note and can upload another ID.'}
        confirmLabel={reviewing?.verify ? 'Verify' : 'Reject'}
        destructive={!reviewing?.verify}
        noteLabel={reviewing?.verify ? 'Note (optional)' : 'Why it is rejected'}
        noteRequired={!reviewing?.verify}
        onConfirm={(note) => reviewing ? review(reviewing.doc, reviewing.verify, note) : undefined}
      />
    </>
  )
}

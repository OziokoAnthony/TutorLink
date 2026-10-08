'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import EmptyState from '@/components/shared/EmptyState'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import NoteDialog from '@/components/shared/NoteDialog'
import PageHeader from '@/components/shared/PageHeader'
import { CertificateStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getAdminCertificates, reviewCertificate } from '@/lib/certificates'
import { formatDateTime } from '@/lib/format'
import type { AdminCertificate } from '@/types'

export default function AdminCertificatesPage() {
  return (
    <Suspense>
      <Certificates />
    </Suspense>
  )
}

function verifiedName(c: AdminCertificate): string {
  return [c.tutor_first_name, c.tutor_middle_name, c.tutor_surname].filter(Boolean).join(' ')
}

/** Spec 4 R4.3: each certificate next to the tutor's NIN-verified name; verify, or reject with a note. */
function Certificates() {
  const toast = useToast()
  const tutorId = useSearchParams().get('tutor_id') ?? undefined
  const [pendingOnly, setPendingOnly] = useState(!tutorId)
  const [certificates, setCertificates] = useState<AdminCertificate[] | null>(null)
  const [reviewing, setReviewing] = useState<{ certificate: AdminCertificate; verify: boolean } | null>(null)

  const load = useCallback(() => {
    setCertificates(null)
    getAdminCertificates({ status: pendingOnly ? 'pending' : undefined, tutor_id: tutorId })
      .then(setCertificates).catch((e) => { toast.error(errorMessage(e)); setCertificates([]) })
  }, [pendingOnly, tutorId, toast])
  useEffect(load, [load])

  async function review(certificate: AdminCertificate, verify: boolean, note: string) {
    try {
      const updated = await reviewCertificate(certificate.id, verify ? 'verified' : 'rejected', note || undefined)
      toast.success(verify ? `${certificate.type} certificate verified` : `${certificate.type} certificate rejected`)
      setCertificates((list) => list && (pendingOnly ? list.filter((c) => c.id !== certificate.id)
        : list.map((c) => c.id === certificate.id ? updated : c)))
    } catch (e) {
      toast.error(errorMessage(e))
      throw e
    }
  }

  return (
    <>
      <PageHeader title="Certificates"
        description="Open each file and compare it with the tutor's NIN-verified name. Confirm WAEC and NECO results on the exam body's website with the PIN; it's deleted once you decide." />
      <Tabs value={pendingOnly ? 'pending' : 'all'} onValueChange={(v) => setPendingOnly(v === 'pending')} className="mb-4">
        <TabsList>
          <TabsTrigger value="pending">Waiting</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>

      {certificates === null ? <LoadingSpinner /> : certificates.length === 0 ? (
        <EmptyState message={pendingOnly ? 'No certificates waiting for review.' : 'No certificates yet.'} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[180px]">Tutor (NIN-verified name)</TableHead>
                <TableHead className="min-w-[200px]">Certificate</TableHead>
                <TableHead className="min-w-[180px]">Exam details</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {certificates.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    <p className="font-medium">{verifiedName(c)}</p>
                    <p className={c.tutor_nin_verified ? 'text-xs text-emerald-700' : 'text-xs text-red-700'}>
                      {c.tutor_nin_verified ? 'NIN verified' : 'NIN not verified'}
                    </p>
                  </TableCell>
                  <TableCell className="text-sm">
                    <a href={c.file_url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 font-medium underline">
                      <FileText className="h-4 w-4" aria-hidden />{c.type}
                    </a>
                    {c.institution} • {c.year}
                    <span className="block text-xs text-muted-foreground">Uploaded {formatDateTime(c.created_at)}</span>
                  </TableCell>
                  <TableCell className="text-sm">
                    {c.exam_number ? (
                      <dl className="grid grid-cols-[auto_1fr] gap-x-2 text-xs">
                        <dt className="text-muted-foreground">Exam no.</dt><dd className="font-mono">{c.exam_number}</dd>
                        <dt className="text-muted-foreground">Year</dt><dd>{c.exam_year}</dd>
                        <dt className="text-muted-foreground">PIN</dt><dd className="font-mono">{c.checker_pin ?? 'deleted'}</dd>
                      </dl>
                    ) : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell>
                    <CertificateStatusBadge status={c.status} />
                    {c.review_note && <span className="mt-1 block max-w-xs text-xs text-muted-foreground">{c.review_note}</span>}
                  </TableCell>
                  <TableCell>
                    {c.status === 'pending' && (
                      <div className="flex justify-end gap-2">
                        <Button size="sm" className="bg-emerald-600 text-white hover:bg-emerald-700"
                          onClick={() => setReviewing({ certificate: c, verify: true })}>Verify</Button>
                        <Button size="sm" variant="destructive" onClick={() => setReviewing({ certificate: c, verify: false })}>Reject</Button>
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
        title={reviewing?.verify ? `Verify this ${reviewing.certificate.type} certificate?` : `Reject this ${reviewing?.certificate.type ?? ''} certificate?`}
        description={reviewing?.verify
          ? 'Only if it is genuine and the name matches the NIN-verified name. The tutor is told.'
          : 'The tutor sees your note and can upload a replacement.'}
        confirmLabel={reviewing?.verify ? 'Verify' : 'Reject'}
        destructive={!reviewing?.verify}
        noteLabel={reviewing?.verify ? 'Note (optional)' : 'Why it is rejected'}
        noteRequired={!reviewing?.verify}
        onConfirm={(note) => reviewing ? review(reviewing.certificate, reviewing.verify, note) : undefined}
      />
    </>
  )
}

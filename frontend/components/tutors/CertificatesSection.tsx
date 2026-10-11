'use client'

import { useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import FormField from '@/components/shared/FormField'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { CertificateStatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { getMyCertificates, uploadCertificate } from '@/lib/certificates'
import { CERTIFICATES, CHECKER_CERTIFICATES } from '@/lib/format'
import type { Certificate, CertificateType } from '@/types'

const MAX_BYTES = 10 * 1024 * 1024
const THIS_YEAR = new Date().getFullYear()

function UploadForm({ initialType, onUploaded }: { initialType?: CertificateType; onUploaded: () => Promise<void> }) {
  const toast = useToast()
  const [type, setType] = useState<CertificateType>(initialType ?? 'Degree')
  const [institution, setInstitution] = useState('')
  const [year, setYear] = useState('')
  const [examNumber, setExamNumber] = useState('')
  const [examYear, setExamYear] = useState('')
  const [pin, setPin] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const needsChecker = CHECKER_CERTIFICATES.includes(type)

  function problem(): string | null {
    if (institution.trim().length < 2) return 'Enter the school or institution'
    const y = Number(year)
    if (!Number.isInteger(y) || y < 1950 || y > THIS_YEAR) return 'Enter the year you got it'
    if (needsChecker) {
      if (!examNumber.trim()) return 'Enter your exam number'
      const ey = Number(examYear)
      if (!Number.isInteger(ey) || ey < 1950 || ey > THIS_YEAR) return 'Enter the exam year'
      if (!pin.trim()) return 'Enter a result-checker PIN'
    }
    if (!file) return 'Choose the certificate file'
    if (file.size > MAX_BYTES) return 'Certificates can be at most 10 MB'
    return null
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const p = problem()
    if (p) { toast.error(p); return }
    setBusy(true)
    try {
      await uploadCertificate({
        type, institution: institution.trim(), year: Number(year),
        ...(needsChecker ? { exam_number: examNumber.trim(), exam_year: Number(examYear), checker_pin: pin.trim() } : {}),
      }, file as File)
      toast.success('Uploaded. An admin will check it.')
      setInstitution(''); setYear(''); setExamNumber(''); setExamYear(''); setPin(''); setFile(null)
      await onUploaded()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4 rounded-lg border p-4 sm:grid-cols-2" noValidate>
      <FormField id="cert-type" label="Type">
        <Select value={type} onValueChange={(v) => setType(v as CertificateType)}>
          <SelectTrigger id="cert-type"><SelectValue /></SelectTrigger>
          <SelectContent>{CERTIFICATES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
        </Select>
      </FormField>
      <FormField id="cert-institution" label="School or institution">
        <Input id="cert-institution" value={institution} maxLength={200} onChange={(e) => setInstitution(e.target.value)} />
      </FormField>
      <FormField id="cert-year" label="Year">
        <Input id="cert-year" inputMode="numeric" maxLength={4} value={year} onChange={(e) => setYear(e.target.value.replace(/\D/g, ''))} />
      </FormField>
      <FormField id="cert-file" label="File" hint="PDF, JPG or PNG, up to 10 MB.">
        <input id="cert-file" type="file" accept="application/pdf,image/jpeg,image/png" className="block w-full text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </FormField>
      {needsChecker && (
        <div className="grid gap-4 sm:col-span-2 sm:grid-cols-3">
          <p className="text-sm text-muted-foreground sm:col-span-3">
            We confirm {type} results on the exam body&apos;s website. The PIN is kept encrypted and deleted once we&apos;ve checked.
          </p>
          <FormField id="cert-exam-number" label="Exam number">
            <Input id="cert-exam-number" value={examNumber} maxLength={30} onChange={(e) => setExamNumber(e.target.value)} />
          </FormField>
          <FormField id="cert-exam-year" label="Exam year">
            <Input id="cert-exam-year" inputMode="numeric" maxLength={4} value={examYear} onChange={(e) => setExamYear(e.target.value.replace(/\D/g, ''))} />
          </FormField>
          <FormField id="cert-pin" label="Result-checker PIN">
            <Input id="cert-pin" autoComplete="off" value={pin} maxLength={30} onChange={(e) => setPin(e.target.value)} />
          </FormField>
        </div>
      )}
      <div className="sm:col-span-2">
        <Button type="submit" disabled={busy}>{busy ? 'Uploading…' : 'Upload certificate'}</Button>
      </div>
    </form>
  )
}

/** The tutor's certificates and the upload form (spec 4 R4.1-R4.3). */
export default function CertificatesSection({ onChange }: { onChange?: () => Promise<void> }) {
  const [certificates, setCertificates] = useState<Certificate[] | null>(null)
  const [replacing, setReplacing] = useState<CertificateType | null>(null)

  async function load() {
    setCertificates(await getMyCertificates())
  }

  useEffect(() => { load().catch(() => setCertificates([])) }, [])

  async function uploaded() {
    setReplacing(null)
    await Promise.all([load(), onChange?.()])
  }

  if (certificates === null) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      {certificates.length > 0 && (
        <ul className="space-y-2">
          {certificates.map((c) => (
            <li key={c.id} className="rounded-lg border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <a href={c.file_url} target="_blank" rel="noreferrer" className="flex items-center gap-2 font-medium underline-offset-2 hover:underline">
                  <FileText className="h-4 w-4" aria-hidden />{c.type} • {c.institution} • {c.year}
                </a>
                <CertificateStatusBadge status={c.status} />
              </div>
              {c.review_note && <p className="mt-1 text-muted-foreground">Admin&apos;s note: {c.review_note}</p>}
              {c.status === 'rejected' && (
                <Button type="button" variant="link" size="sm" className="h-auto px-0" onClick={() => setReplacing(c.type)}>
                  Upload a replacement
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      <UploadForm key={replacing ?? 'new'} initialType={replacing ?? undefined} onUploaded={uploaded} />
    </div>
  )
}

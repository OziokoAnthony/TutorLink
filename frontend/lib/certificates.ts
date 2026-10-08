import api from '@/lib/api'
import type { AdminCertificate, Certificate, CertificateStatus, CertificateType } from '@/types'

export interface CertificateInput {
  type: CertificateType
  institution: string
  year: number
  // WAEC and NECO only (spec 4 R4.2)
  exam_number?: string
  exam_year?: number
  checker_pin?: string
}

export async function getMyCertificates(): Promise<Certificate[]> {
  const { data } = await api.get<Certificate[]>('/certificates')
  return data
}

/** A PDF, JPG or PNG up to 10 MB, once the tutor's NIN is verified. */
export async function uploadCertificate(input: CertificateInput, file: File): Promise<Certificate> {
  const form = new FormData()
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && value !== '') form.append(key, String(value))
  }
  form.append('file', file)
  const { data } = await api.post<Certificate>('/certificates', form)
  return data
}

export async function getAdminCertificates(params: { status?: CertificateStatus; tutor_id?: string } = {}): Promise<AdminCertificate[]> {
  const { data } = await api.get<AdminCertificate[]>('/admin/certificates', { params })
  return data
}

/** Verify, or reject with a note the tutor sees. The checker PIN is erased either way. */
export async function reviewCertificate(id: string, status: 'verified' | 'rejected', note?: string): Promise<AdminCertificate> {
  const { data } = await api.patch<AdminCertificate>(`/admin/certificates/${id}`, { status, note })
  return data
}

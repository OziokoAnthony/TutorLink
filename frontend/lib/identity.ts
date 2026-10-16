import api from '@/lib/api'
import type { AdminIdDocument, IdDocument, IdDocumentStatus, IdDocumentType } from '@/types'

export const ID_LABELS: Record<IdDocumentType, string> = {
  nin: 'NIN slip or card',
  voters_card: "Voter's card",
  drivers_licence: "Driver's licence",
  passport: 'International passport',
}

/** The tutor's own ID documents, newest first (spec 11 R1). */
export async function getMyIdDocuments(): Promise<IdDocument[]> {
  const { data } = await api.get<IdDocument[]>('/id-documents')
  return data
}

/** A PDF, JPG or PNG up to 10 MB; one can wait for review at a time. */
export async function uploadIdDocument(type: IdDocumentType, file: File): Promise<IdDocument> {
  const form = new FormData()
  form.append('type', type)
  form.append('file', file)
  const { data } = await api.post<IdDocument>('/id-documents', form)
  return data
}

export async function getAdminIdDocuments(status?: IdDocumentStatus): Promise<AdminIdDocument[]> {
  const { data } = await api.get<AdminIdDocument[]>('/admin/id-documents', { params: status ? { status } : {} })
  return data
}

export async function reviewIdDocument(id: string, status: 'verified' | 'rejected', note?: string): Promise<AdminIdDocument> {
  const { data } = await api.patch<AdminIdDocument>(`/admin/id-documents/${id}`, { status, note })
  return data
}

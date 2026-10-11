import api from '@/lib/api'
import type { LegalDocument, LegalKind, LegalVersion, Subject, SubjectAdmin, SubjectGroup } from '@/types'

/** The subjects offered for new offers, job posts and search (spec 7 R1). Public: sign-up needs them. */
export async function getSubjects(): Promise<Subject[]> {
  const { data } = await api.get<Subject[]>('/subjects')
  return data
}

export async function getAdminSubjects(): Promise<SubjectAdmin[]> {
  const { data } = await api.get<SubjectAdmin[]>('/admin/subjects')
  return data
}

export async function addSubject(name: string, group: SubjectGroup): Promise<SubjectAdmin> {
  const { data } = await api.post<SubjectAdmin>('/admin/subjects', { name, group })
  return data
}

/** Removing hides a subject from new offers and jobs; existing ones keep it. Restoring undoes that. */
export async function setSubjectOffered(id: string, isOffered: boolean): Promise<SubjectAdmin> {
  const { data } = await api.patch<SubjectAdmin>(`/admin/subjects/${id}`, { is_offered: isOffered })
  return data
}

export async function getLegal(kind: LegalKind): Promise<LegalDocument> {
  const { data } = await api.get<LegalDocument>(`/legal/${kind}`)
  return data
}

export async function getLegalVersions(kind: LegalKind): Promise<LegalVersion[]> {
  const { data } = await api.get<LegalVersion[]>(`/admin/legal/${kind}`)
  return data
}

export async function publishLegal(kind: LegalKind, body: string, notify: boolean): Promise<LegalDocument> {
  const { data } = await api.post<LegalDocument>(`/admin/legal/${kind}`, { body, notify })
  return data
}

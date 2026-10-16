import api from '@/lib/api'
import type {
  LegalAudience, LegalDocument, LegalKind, LegalVersion, MyLegal, Subject, SubjectAdmin, SubjectGroup,
} from '@/types'

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

/** Public: the parents' version unless the tutors' is asked for (spec 9 R1.3). */
export async function getLegal(kind: LegalKind, audience: LegalAudience = 'parent'): Promise<LegalDocument> {
  const { data } = await api.get<LegalDocument>(`/legal/${kind}`, { params: { audience } })
  return data
}

export async function getLegalVersions(audience: LegalAudience, kind: LegalKind): Promise<LegalVersion[]> {
  const { data } = await api.get<LegalVersion[]>(`/admin/legal/${audience}/${kind}`)
  return data
}

/** Everyone in the audience must agree to the new version (spec 9 R5.1). */
export async function publishLegal(audience: LegalAudience, kind: LegalKind, body: string,
  notify: boolean): Promise<LegalDocument> {
  const { data } = await api.post<LegalDocument>(`/admin/legal/${audience}/${kind}`, { body, notify })
  return data
}

/** The reader's own three documents and whether they must agree now (spec 9 R2.4). */
export async function getMyLegal(): Promise<MyLegal> {
  const { data } = await api.get<MyLegal>('/legal/me')
  return data
}

/** Agrees to the latest version of all three (spec 9 R2.1); a 409 if one changed meanwhile. */
export async function acceptLegal(documentIds: string[]): Promise<MyLegal> {
  const { data } = await api.post<MyLegal>('/legal/me/accept', { document_ids: documentIds })
  return data
}

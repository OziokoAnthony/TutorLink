import api from '@/lib/api'
import type {
  AdminExamAttempt, AdminExamQuestion, ExamAttempt, ExamBankLevel, ExamQuestionBody, ExamQuestionTag, ExamResult,
  ExamStatus, Level, ParsedExamQuestions,
} from '@/types'

/** The qualifying exam (spec 4 R5). */
export async function getExamStatus(): Promise<ExamStatus> {
  const { data } = await api.get<ExamStatus>('/exam')
  return data
}

/** Starts an attempt or returns the one in progress. A 409 "Your exam is being prepared" means the
 *  question bank is still being filled; a 429 means all 6 attempts are used for 24 hours. */
export async function startExam(): Promise<ExamAttempt> {
  const { data } = await api.post<ExamAttempt>('/exam/attempts')
  return data
}

export async function saveExamAnswer(attemptId: string, position: number, choice: number): Promise<void> {
  await api.put(`/exam/attempts/${attemptId}/answers`, { answers: [{ position, choice }] })
}

export async function submitExam(attemptId: string): Promise<ExamResult> {
  const { data } = await api.post<ExamResult>(`/exam/attempts/${attemptId}/submit`)
  return data
}

export async function getAdminExamAttempts(tutorId?: string): Promise<AdminExamAttempt[]> {
  const { data } = await api.get<AdminExamAttempt[]>('/admin/exam/attempts', { params: tutorId ? { tutor_id: tutorId } : {} })
  return data
}

export async function getAdminExamQuestions(params: { general?: boolean; subject?: string; level?: Level; include_retired?: boolean; skip?: number }): Promise<AdminExamQuestion[]> {
  const { data } = await api.get<AdminExamQuestion[]>('/admin/exam/questions', { params })
  return data
}

export async function retireExamQuestion(id: string): Promise<AdminExamQuestion> {
  const { data } = await api.post<AdminExamQuestion>(`/admin/exam/questions/${id}/retire`)
  return data
}

export async function getExamBank(): Promise<ExamBankLevel[]> {
  const { data } = await api.get<ExamBankLevel[]>('/admin/exam/bank')
  return data
}

/** Spec 12 R1: one question an admin writes. */
export async function addExamQuestion(tag: ExamQuestionTag, body: ExamQuestionBody): Promise<AdminExamQuestion> {
  const { data } = await api.post<AdminExamQuestion>('/admin/exam/questions', { ...tag, ...body })
  return data
}

/** Spec 12 R2.3: the questions found in a PDF in the fixed layout. Nothing is saved. */
export async function readExamPdf(file: File): Promise<ParsedExamQuestions> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<ParsedExamQuestions>('/admin/exam/questions/pdf', form)
  return data
}

/** Spec 12 R2.4: saves the checked questions; ones already in the bank are skipped. */
export async function addExamQuestions(tag: ExamQuestionTag, questions: ExamQuestionBody[]): Promise<{ added: number; duplicates: number }> {
  const { data } = await api.post<{ added: number; duplicates: number }>('/admin/exam/questions/batch', { ...tag, questions })
  return data
}

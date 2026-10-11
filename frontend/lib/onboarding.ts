import api from '@/lib/api'
import type { NinResult, Onboarding } from '@/types'

/** The tutor's checklist: Profile, NIN, waiting for review (spec 4 R2.1). */
export async function getOnboarding(): Promise<Onboarding> {
  const { data } = await api.get<Onboarding>('/onboarding')
  return data
}

/** Checks the NIN and a selfie with Dojah (spec 4 R3). A failed check resolves with `verified: false`
 *  and says which check failed; a 429 means all 3 attempts for 24 hours are used. */
export async function verifyNin(nin: string, selfie: Blob): Promise<NinResult> {
  const form = new FormData()
  form.append('nin', nin)
  form.append('selfie', selfie, 'selfie.jpg')
  const { data } = await api.post<NinResult>('/onboarding/nin', form)
  return data
}

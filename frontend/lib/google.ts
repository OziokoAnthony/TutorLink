/**
 * Google sign-in in the browser (spec 4 R1). Google Identity Services gives us an ID token
 * ("credential"); the backend verifies it. Here we only read its claims to prefill the sign-up form.
 */

export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''

export interface GoogleCredential {
  token: string
  email: string
  given_name: string
  family_name: string
  name: string
  picture: string | null
}

/** Reads the token's claims for display. Not a check: only the backend's verification counts. */
export function readCredential(token: string): GoogleCredential | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const bytes = Uint8Array.from(atob(payload), (c) => c.charCodeAt(0))
    const claims = JSON.parse(new TextDecoder().decode(bytes))
    if (typeof claims.email !== 'string') return null
    return {
      token,
      email: claims.email,
      given_name: claims.given_name ?? '',
      family_name: claims.family_name ?? '',
      name: claims.name ?? '',
      picture: claims.picture ?? null,
    }
  } catch {
    return null
  }
}

// A parent who tries Google on the login page without an account is sent to sign-up with their
// credential kept here, so they don't have to choose their Google account twice.
const PENDING_KEY = 'tutorlink_google_signup'

export function keepForSignUp(token: string): void {
  try {
    sessionStorage.setItem(PENDING_KEY, token)
  } catch {
    // Storage blocked: they choose their Google account again on the sign-up page.
  }
}

export function takeForSignUp(): GoogleCredential | null {
  try {
    const token = sessionStorage.getItem(PENDING_KEY)
    sessionStorage.removeItem(PENDING_KEY)
    return token ? readCredential(token) : null
  } catch {
    return null
  }
}

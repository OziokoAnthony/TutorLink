import axios from 'axios'

/**
 * The login token lives in an httpOnly cookie the backend sets (`tutorlink_token`): page scripts can't read
 * it, so an injected script can't steal it. Every request sends the cookie, and the header the backend
 * requires on cookie-authenticated changes, which other sites can't send (CSRF protection).
 */
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1',
  withCredentials: true,
  headers: { 'X-Requested-With': 'TutorLink' },
})

// Handle 401 globally: redirect to login. Except where a 401 is an expected answer: a wrong password on a
// sign-in request (the page shows it), and /auth/me for a visitor who isn't logged in.
const NO_REDIRECT_PATHS = ['/auth/login', '/auth/google/login', '/auth/google/register', '/auth/me']

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const expected = NO_REDIRECT_PATHS.some((path) => error.config?.url?.endsWith(path))
    if (error.response?.status === 401 && !expected) {
      // The session ended (expired, or a password change elsewhere): drop the stale cookie, then log in.
      api.post('/auth/logout').finally(() => { window.location.href = '/login' })
    }
    return Promise.reject(error)
  }
)

export default api

/** HTTP status of a failed request, if the server answered. */
export function errorStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

/** The backend's error message (`detail`), or `fallback` when there isn't a readable one. */
export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!axios.isAxiosError(error)) return fallback
  if (!error.response) return 'Cannot reach the server. Check your connection and try again.'
  const detail = error.response.data?.detail
  if (typeof detail === 'string') return detail
  // FastAPI validation errors: [{ msg: "..." }, ...]
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, '')
  return fallback
}

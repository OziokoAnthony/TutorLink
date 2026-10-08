import axios from 'axios'
import Cookies from 'js-cookie'

export const TOKEN_COOKIE = 'tutorlink_token'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1',
})

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = Cookies.get(TOKEN_COOKIE)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally — redirect to login.
// Exception: a 401 from a login or Google sign-up request means "wrong password" or "use your
// TutorLink email"; the page shows it.
const SIGN_IN_PATHS = ['/auth/login', '/auth/google/login', '/auth/google/register']

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = SIGN_IN_PATHS.some((path) => error.config?.url?.endsWith(path))
    if (error.response?.status === 401 && !isLoginRequest) {
      Cookies.remove(TOKEN_COOKIE)
      window.location.href = '/login'
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

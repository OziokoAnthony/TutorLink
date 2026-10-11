'use client'

import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import * as auth from '@/lib/auth'
import type { UserMe } from '@/types'

interface AuthContextValue {
  user: UserMe | null
  loading: boolean
  /** Logs in, loads the user, and redirects to their role's home page. */
  login: (email: string, password: string) => Promise<void>
  /** Logs a parent or tutor in with a Google ID token, then redirects like `login`. */
  loginWithGoogle: (idToken: string) => Promise<void>
  /** After a sign-up that signed the user in: loads them and goes to their home page. */
  enter: () => Promise<void>
  logout: () => Promise<void>
  /** Re-fetches /auth/me (e.g. after profile changes or a rating). */
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<UserMe | null>(null)
  const [loading, setLoading] = useState(true)

  // The login cookie is httpOnly, so the only way to know who's logged in is to ask: a visitor gets a 401.
  const refresh = useCallback(async () => {
    try {
      setUser(await auth.getMe())
    } catch {
      setUser(null)
    }
  }, [])

  // On every page load: fetch /auth/me.
  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  const enter = useCallback(async () => {
    const me = await auth.getMe()
    setUser(me)
    router.push(auth.ROLE_HOME[me.role])
    router.refresh()
  }, [router])

  const login = useCallback(async (email: string, password: string) => {
    await auth.login(email, password)
    await enter()
  }, [enter])

  const loginWithGoogle = useCallback(async (idToken: string) => {
    await auth.loginWithGoogle(idToken)
    await enter()
  }, [enter])

  const logout = useCallback(async () => {
    try {
      await auth.logout()
    } catch {
      // Logged out here either way; the cookie expires by itself.
    }
    setUser(null)
    router.push('/')
    router.refresh()
  }, [router])

  const value = useMemo(
    () => ({ user, loading, login, loginWithGoogle, enter, logout, refresh }),
    [user, loading, login, loginWithGoogle, enter, logout, refresh],
  )
  return createElement(AuthContext.Provider, { value }, children)
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

type Role = 'parent' | 'tutor' | 'admin'

const ROLE_HOME: Record<Role, string> = {
  parent: '/dashboard/parent',
  tutor: '/dashboard/tutor',
  admin: '/admin/tutors',
}

// Which role each protected area belongs to.
const AREA_ROLE: [string, Role][] = [
  ['/admin', 'admin'],
  ['/dashboard/parent', 'parent'],
  ['/dashboard/tutor', 'tutor'],
]

/**
 * Reads `role` from the JWT payload for routing only; null once it has expired. The signature isn't
 * checked here; the backend verifies the token and enforces permissions on every API call.
 */
function roleFromToken(token: string): Role | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { role, exp } = JSON.parse(atob(payload))
    if (typeof exp === 'number' && exp * 1000 <= Date.now()) return null
    return role === 'parent' || role === 'tutor' || role === 'admin' ? role : null
  } catch {
    return null
  }
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get('tutorlink_token')
  const { pathname } = request.nextUrl

  // Someone already logged in who opens the log-in or sign-up page goes to their own home instead: tutors
  // to the dashboard with their onboarding checklist, parents to theirs.
  if (pathname === '/login' || pathname === '/register') {
    const role = token ? roleFromToken(token.value) : null
    return role ? NextResponse.redirect(new URL(ROLE_HOME[role], request.url)) : NextResponse.next()
  }

  // Tutors' profiles are for registered parents (and admins): visitors are asked to sign up as a parent.
  if (pathname.startsWith('/tutors')) {
    const role = token ? roleFromToken(token.value) : null
    if (!role) return NextResponse.redirect(new URL('/register?role=parent&reason=tutors', request.url))
    if (role === 'tutor') return NextResponse.redirect(new URL(ROLE_HOME.tutor, request.url))
    return NextResponse.next()
  }

  const protectedPrefixes = ['/dashboard', '/admin', '/receipts']
  const isProtected = protectedPrefixes.some(p => pathname.startsWith(p))

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (isProtected && token) {
    const role = roleFromToken(token.value)
    if (!role) {
      const response = NextResponse.redirect(new URL('/login', request.url))
      response.cookies.delete('tutorlink_token')
      return response
    }
    // Admin pages only for admins; each dashboard only for its own role.
    const area = AREA_ROLE.find(([prefix]) => pathname.startsWith(prefix))
    const wrongArea = area ? area[1] !== role : pathname === '/dashboard' || pathname === '/dashboard/'
    if (wrongArea) {
      return NextResponse.redirect(new URL(ROLE_HOME[role], request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/admin/:path*', '/receipts/:path*', '/tutors', '/tutors/:path*', '/login', '/register'],
}

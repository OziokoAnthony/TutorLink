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
 * Reads `role` from the JWT payload for routing only. The signature isn't checked here;
 * the backend verifies the token and enforces permissions on every API call.
 */
function roleFromToken(token: string): Role | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const role = JSON.parse(atob(payload)).role
    return role === 'parent' || role === 'tutor' || role === 'admin' ? role : null
  } catch {
    return null
  }
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get('tutorlink_token')
  const { pathname } = request.nextUrl

  const protectedPrefixes = ['/dashboard', '/admin']
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
  matcher: ['/dashboard/:path*', '/admin/:path*'],
}

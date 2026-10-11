const isDev = process.env.NODE_ENV !== 'production'
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
// A relative NEXT_PUBLIC_API_URL ("/api/v1") means the API is reached through this site ('self').
const api = apiUrl.startsWith('/') ? '' : ` ${new URL(apiUrl).origin}`
// Where /api/v1 is forwarded, e.g. https://tutorlink-api.onrender.com. Set it when the site and the API have no
// domain in common (free *.vercel.app and *.onrender.com addresses): the browser then talks only to this site, so
// the login cookie is this site's own and the middleware can read it.
const apiProxyTarget = (process.env.API_PROXY_TARGET || '').replace(/\/+$/, '')
const google = 'https://accounts.google.com'

/**
 * What pages may load and from where. Scripts only from this site and Google sign-in, so a script injected
 * from elsewhere won't run; the API for data; https: for files, which are signed links to the storage
 * bucket; nobody may frame the site (clickjacking). Next.js needs inline scripts, and eval while developing.
 */
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${google}${isDev ? " 'unsafe-eval'" : ''}`,
  `style-src 'self' 'unsafe-inline' ${google}`,
  `img-src 'self' data: blob: https:${api}`,
  `media-src 'self' blob: https:${api}`,
  `connect-src 'self'${api} ${google} https:${isDev ? ' ws:' : ''}`,
  `frame-src ${google}`,
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ')

const securityHeaders = [
  { key: 'Content-Security-Policy', value: contentSecurityPolicy },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  // The camera is for the NIN selfie (spec 4 R3.2); nothing else needs these.
  { key: 'Permissions-Policy', value: 'camera=(self), microphone=(), geolocation=(), payment=()' },
  ...(isDev ? [] : [{ key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' }]),
]

/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }]
  },
  async rewrites() {
    return apiProxyTarget ? [{ source: '/api/v1/:path*', destination: `${apiProxyTarget}/v1/:path*` }] : []
  },
}

export default nextConfig

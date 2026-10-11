const isDev = process.env.NODE_ENV !== 'production'
const apiOrigin = new URL(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1').origin
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
  `img-src 'self' data: blob: https: ${apiOrigin}`,
  `media-src 'self' blob: https: ${apiOrigin}`,
  `connect-src 'self' ${apiOrigin} ${google} https:${isDev ? ' ws:' : ''}`,
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
}

export default nextConfig

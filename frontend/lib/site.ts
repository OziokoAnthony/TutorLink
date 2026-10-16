/** The site's public address for the sitemap and robots.txt (spec 14 R6.2): SITE_URL if set, else the production
 * address Vercel provides, else local development. */
export function siteUrl(): string {
  const explicit = process.env.SITE_URL?.replace(/\/+$/, '')
  if (explicit) return explicit
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL
  return vercel ? `https://${vercel}` : 'http://localhost:3000'
}

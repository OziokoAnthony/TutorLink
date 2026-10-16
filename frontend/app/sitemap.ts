import type { MetadataRoute } from 'next'
import { LEVELS } from '@/lib/format'
import { publicSubjects } from '@/lib/public'
import { siteUrl } from '@/lib/site'

export const dynamic = 'force-dynamic' // the subject list comes from the API, cached for an hour

/** Spec 14 R6.2: the public pages search engines should index. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteUrl()
  const subjects = await publicSubjects().catch(() => [])
  return [
    { url: `${base}/`, changeFrequency: 'daily', priority: 1 },
    { url: `${base}/subjects`, changeFrequency: 'daily', priority: 0.9 },
    ...subjects.map((s) => ({ url: `${base}/subjects/${s.slug}`, changeFrequency: 'daily' as const, priority: 0.8 })),
    ...LEVELS.map((l) => ({ url: `${base}/levels/${l.value}`, changeFrequency: 'daily' as const, priority: 0.7 })),
    ...['privacy', 'terms', 'disclaimer'].map((p) => ({ url: `${base}/${p}`, changeFrequency: 'monthly' as const, priority: 0.2 })),
    { url: `${base}/register`, changeFrequency: 'monthly', priority: 0.5 },
  ]
}

import type { MetadataRoute } from 'next'
import { siteUrl } from '@/lib/site'

/** Spec 14 R6.2: public pages are indexed; accounts, admin and receipts are not. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/', disallow: ['/dashboard', '/admin', '/receipts', '/api/'] },
    sitemap: `${siteUrl()}/sitemap.xml`,
  }
}

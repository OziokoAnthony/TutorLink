'use client'

import { useEffect, useState } from 'react'
import { getSubjects } from '@/lib/content'
import type { Subject } from '@/types'

// Fetched once per page load and shared: every form and filter on the page uses the same list.
let request: Promise<Subject[]> | null = null

/** The offered subjects (spec 7 R1), empty until they arrive. */
export function useSubjects(): Subject[] {
  const [subjects, setSubjects] = useState<Subject[]>([])
  useEffect(() => {
    request ??= getSubjects().catch((e) => { request = null; throw e })
    request.then(setSubjects).catch(() => setSubjects([]))
  }, [])
  return subjects
}

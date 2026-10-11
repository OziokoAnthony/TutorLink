'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { cn } from '@/lib/utils'

/** Unsplash photos in `public/auth/`. To change one, replace its file (any size; it's cropped to fit). */
const SLIDES = [
  { src: '/auth/1-tutor-at-home.webp', alt: 'A tutor helping a girl with her lesson at home',
    caption: 'Vetted tutors who come to your home' },
  { src: '/auth/2-online-lesson.webp', alt: 'A tutor teaching an online lesson on her laptop',
    caption: 'Or learn online, wherever you are' },
  { src: '/auth/3-parent-and-child.webp', alt: 'A mother and daughter laughing together',
    caption: 'Peace of mind for parents' },
  { src: '/auth/4-happy-homework.webp', alt: 'A smiling boy with his schoolwork',
    caption: 'Children who enjoy learning' },
  { src: '/auth/5-homework-review.webp', alt: 'A boy concentrating on his written work',
    caption: 'A report after every lesson' },
]

const SLIDE_MS = 5000

/** The login and sign-up pages: five photos that cross-fade on one side, the form on the other. On a phone
 * the photos become a short strip above the form. Visitors who ask for reduced motion get no automatic change. */
export default function AuthShell({ children }: { children: React.ReactNode }) {
  const [current, setCurrent] = useState(0)
  const [autoplay, setAutoplay] = useState(false)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setAutoplay(!reduce.matches)
    update()
    reduce.addEventListener('change', update)
    return () => reduce.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (!autoplay) return
    const timer = setTimeout(() => setCurrent((current + 1) % SLIDES.length), SLIDE_MS)
    return () => clearTimeout(timer)
  }, [autoplay, current])

  return (
    <div className="lg:grid lg:min-h-[calc(100svh-3.5rem)] lg:grid-cols-2">
      <div className="relative h-48 overflow-hidden bg-neutral-900 sm:h-64 lg:sticky lg:top-14 lg:h-[calc(100svh-3.5rem)]">
        {SLIDES.map((slide, i) => (
          <div key={slide.src} aria-hidden={i !== current}
               className={cn('absolute inset-0 transition-opacity duration-1000 ease-in-out',
                             i === current ? 'opacity-100' : 'opacity-0')}>
            <Image src={slide.src} alt={slide.alt} fill priority={i === 0} sizes="(min-width: 1024px) 50vw, 100vw"
                   className="object-cover" />
          </div>
        ))}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 z-10 p-5 text-white lg:p-10">
          <p aria-live="polite" className="text-lg font-semibold drop-shadow sm:text-2xl lg:text-3xl">
            {SLIDES[current].caption}
          </p>
          <div className="mt-3 flex gap-2">
            {SLIDES.map((slide, i) => (
              <button key={slide.src} type="button" onClick={() => setCurrent(i)}
                      aria-label={`Show photo ${i + 1}: ${slide.alt}`} aria-current={i === current}
                      className={cn('h-2 rounded-full transition-all',
                                    i === current ? 'w-6 bg-white' : 'w-2 bg-white/50 hover:bg-white/80')} />
            ))}
          </div>
        </div>
      </div>
      <div className="flex items-start justify-center lg:items-center">{children}</div>
    </div>
  )
}

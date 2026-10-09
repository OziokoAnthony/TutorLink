'use client'

import { useCallback, useEffect, useState } from 'react'
import Image from 'next/image'
import { cn } from '@/lib/utils'

/** Free Unsplash photos, stored in `public/hero/`. */
const SLIDES = [
  { src: '/hero/01-home-lesson.webp', alt: 'A tutor helping a girl with her homework at home' },
  { src: '/hero/02-happy-student.webp', alt: 'A smiling student at his desk' },
  { src: '/hero/03-online-lesson.webp', alt: 'A tutor teaching an online lesson on her laptop' },
  { src: '/hero/04-happy-parent.webp', alt: 'A mother and daughter laughing together' },
  { src: '/hero/05-young-graduate.webp', alt: 'A proud young girl in her graduation gown' },
  { src: '/hero/06-classwork.webp', alt: 'Students writing in their exercise books' },
  { src: '/hero/07-family-time.webp', alt: 'Parents and children playing a board game' },
  { src: '/hero/08-learning-online.webp', alt: 'A little girl learning on a laptop' },
  { src: '/hero/09-graduate.webp', alt: 'A smiling graduate holding her certificate' },
  { src: '/hero/10-proud-student.webp', alt: 'A happy schoolboy with his backpack' },
]

const SLIDE_MS = 6000

/** The home page's background: photos that cross-fade with a slow zoom. Visitors who ask for reduced
 * motion get no zoom and no automatic change; the dots still switch photos. */
export default function HeroSlideshow() {
  const [current, setCurrent] = useState(0)
  // How many times each photo has been shown. It keys the photo, so the zoom restarts each time the
  // photo appears, and a photo fading out keeps its zoom instead of snapping back.
  const [shown, setShown] = useState(() => SLIDES.map(() => 0))
  const [autoplay, setAutoplay] = useState(false)

  const show = useCallback((i: number) => {
    setCurrent(i)
    setShown((counts) => counts.map((n, j) => (j === i ? n + 1 : n)))
  }, [])

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setAutoplay(!reduce.matches)
    update()
    reduce.addEventListener('change', update)
    return () => reduce.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (!autoplay) return
    const timer = setTimeout(() => show((current + 1) % SLIDES.length), SLIDE_MS)
    return () => clearTimeout(timer)
  }, [autoplay, current, show])

  return (
    <div className="absolute inset-0 overflow-hidden bg-neutral-900">
      {SLIDES.map((slide, i) => (
        <div key={slide.src} aria-hidden={i !== current}
             className={cn('absolute inset-0 transition-opacity duration-1500 ease-in-out',
                           i === current ? 'opacity-100' : 'opacity-0')}>
          <Image
            key={shown[i]} src={slide.src} alt={slide.alt} fill priority={i === 0} sizes="100vw"
            className="animate-hero-zoom object-cover motion-reduce:animate-none"
          />
        </div>
      ))}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/45 to-black/70" />
      <div className="absolute inset-x-0 bottom-5 z-10 flex justify-center gap-2">
        {SLIDES.map((slide, i) => (
          <button key={slide.src} type="button" onClick={() => show(i)}
                  aria-label={`Show photo ${i + 1}: ${slide.alt}`} aria-current={i === current}
                  className={cn('h-2 rounded-full transition-all',
                                i === current ? 'w-6 bg-white' : 'w-2 bg-white/50 hover:bg-white/80')} />
        ))}
      </div>
    </div>
  )
}

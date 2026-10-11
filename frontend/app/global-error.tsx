'use client'

/** The last resort, when even the site's layout fails: plain HTML, no app styles or components. */
export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, sans-serif', textAlign: 'center', padding: '6rem 1rem' }}>
        <h1>Something went wrong</h1>
        <p>TutorLink couldn&apos;t load. Please try again in a moment.</p>
        <button type="button" onClick={reset} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>Try again</button>
      </body>
    </html>
  )
}

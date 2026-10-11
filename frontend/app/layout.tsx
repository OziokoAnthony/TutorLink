import type { Metadata } from 'next'
import localFont from 'next/font/local'
import './globals.css'
import Footer from '@/components/layout/Footer'
import Navbar from '@/components/layout/Navbar'
import { Toaster } from '@/components/ui/sonner'
import { AuthProvider } from '@/hooks/useAuth'
import { ThemeProvider } from 'next-themes'

// Bundled with the project, so builds don't need to download fonts.
const geist = localFont({ src: './fonts/GeistVF.woff', variable: '--font-sans', weight: '100 900' })

export const metadata: Metadata = {
  title: 'TutorLink: vetted home tutors in Nigeria',
  description: 'Find a vetted home tutor. Pay only for lessons that happened.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // next-themes sets the `dark` class before the page paints, so React sees an attribute it didn't render.
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} min-h-screen bg-background font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <AuthProvider>
            <Navbar />
            <main>{children}</main>
            <Footer />
            <Toaster richColors position="top-center" />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}

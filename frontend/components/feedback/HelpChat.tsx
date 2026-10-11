'use client'

import { useEffect, useRef, useState } from 'react'
import { MessageCircle, Send, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/useToast'
import { errorMessage } from '@/lib/api'
import { askHelp, sendFeedback } from '@/lib/feedback'
import { cn } from '@/lib/utils'
import type { ChatMessage, Role } from '@/types'

const GREETING: Record<'parent' | 'tutor', string> = {
  parent: 'Hi! Ask me how booking, paying, lessons or job posts work on TutorLink.',
  tutor: 'Hi! Ask me about getting verified, the quiz, bookings, lesson reports or getting paid.',
}

/**
 * Spec 6 R3: the help assistant, a chat bubble on every parent and tutor page. The conversation stays in the
 * browser (it survives moving between dashboard pages) until the user sends it to the TutorLink team.
 */
export default function HelpChat({ role }: { role: Role }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [sending, setSending] = useState(false)
  const [sentToTeam, setSentToTeam] = useState(false)
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [messages, thinking, open])

  if (role === 'admin') return null

  async function ask(e?: React.FormEvent) {
    e?.preventDefault()
    const question = draft.trim()
    if (!question || thinking) return
    const next: ChatMessage[] = [...messages, { role: 'user', content: question }]
    setMessages(next)
    setDraft('')
    setSentToTeam(false)
    setThinking(true)
    try {
      const reply = await askHelp(next.slice(-40))
      setMessages([...next, { role: 'assistant', content: reply }])
    } catch (err) {
      toast.error(errorMessage(err))
      setMessages(messages)  // take the question back so it can be asked again
      setDraft(question)
    } finally {
      setThinking(false)
    }
  }

  async function sendToTeam() {
    const first = messages.find((m) => m.role === 'user')?.content ?? ''
    setSending(true)
    try {
      await sendFeedback('question', `From the help chat: ${first}`.slice(0, 2000), messages.slice(-40))
      setSentToTeam(true)
      toast.success("Sent. The TutorLink team will reply in your notifications and by email.")
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      {open && (
        <section aria-label="Help chat"
          className="fixed inset-x-4 bottom-20 z-50 flex max-h-[70vh] flex-col rounded-lg border bg-background shadow-xl sm:inset-x-auto sm:right-6 sm:w-96">
          <header className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <p className="font-semibold">TutorLink help</p>
              <p className="text-xs text-muted-foreground">Answers come from an AI assistant.</p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close help chat">
              <X className="h-4 w-4" />
            </Button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm" aria-live="polite">
            <Bubble mine={false}>{GREETING[role]}</Bubble>
            {messages.map((m, i) => <Bubble key={i} mine={m.role === 'user'}>{m.content}</Bubble>)}
            {thinking && <Bubble mine={false}><span className="text-muted-foreground">Thinking…</span></Bubble>}
            <div ref={end} />
          </div>

          {messages.length > 0 && (
            <div className="border-t px-4 py-2 text-xs">
              {sentToTeam ? (
                <p className="text-muted-foreground">Sent to the TutorLink team. You&apos;ll see their reply under Help &amp; feedback.</p>
              ) : (
                <button type="button" onClick={sendToTeam} disabled={sending || thinking}
                  className="font-medium text-primary underline-offset-4 hover:underline disabled:opacity-50">
                  {sending ? 'Sending…' : 'Not answered? Send to the TutorLink team'}
                </button>
              )}
            </div>
          )}

          <form onSubmit={ask} className="flex items-end gap-2 border-t p-3">
            <Textarea rows={2} maxLength={4000} value={draft} placeholder="Type your question"
              aria-label="Your question" className="min-h-0 resize-none"
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask() } }} />
            <Button type="submit" size="icon" disabled={thinking || !draft.trim()} aria-label="Send">
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </section>
      )}

      <Button onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="fixed bottom-6 right-6 z-50 h-12 rounded-full px-4 shadow-lg">
        {open ? <X className="h-5 w-5" /> : <><MessageCircle className="mr-2 h-5 w-5" />Help</>}
      </Button>
    </>
  )
}

function Bubble({ mine, children }: { mine: boolean; children: React.ReactNode }) {
  return (
    <div className={cn('max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2',
      mine ? 'ml-auto bg-primary text-primary-foreground' : 'bg-muted')}>
      {children}
    </div>
  )
}

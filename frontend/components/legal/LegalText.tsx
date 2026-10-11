import { Fragment } from 'react'

/**
 * Spec 7 R2.2: a legal document's plain text as paragraphs, `## ` headings, `- ` bullets and `**bold**`. Every
 * piece is rendered as React text, never as HTML, so nothing an admin types can run in the page.
 */
export default function LegalText({ text }: { text: string }) {
  const blocks = text.replace(/\r\n/g, '\n').split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean)
  return (
    <>
      {blocks.map((block, i) => {
        if (block.startsWith('## ')) return <h2 key={i}>{bold(block.slice(3))}</h2>
        const lines = block.split('\n')
        if (lines.every((l) => l.trim().startsWith('- '))) {
          return <ul key={i}>{lines.map((l, j) => <li key={j}>{bold(l.trim().slice(2))}</li>)}</ul>
        }
        return (
          <p key={i}>
            {lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{bold(l)}</Fragment>)}
          </p>
        )
      })}
    </>
  )
}

/** `**text**` as bold; everything else as it is. */
function bold(line: string) {
  return line.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <Fragment key={i}>{part}</Fragment>)
}

/** A document still holding "[… to be filled in]" isn't final (spec 7 R2.6). */
export function isDraft(text: string): boolean {
  return /\[[^\]]*to be filled in\]/i.test(text)
}

/** The prose styles both the public pages and the admin preview use. */
export const LEGAL_PROSE =
  'text-sm leading-relaxed [&_h2]:mb-2 [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_li]:mt-1 [&_p]:mt-3 ' +
  '[&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5'

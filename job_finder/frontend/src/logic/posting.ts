// A posting's text, as headings, bullet lists and paragraphs, so the job panel
// can show it as a page instead of one wall of text. The text arrives as plain
// lines; these rules only read their shape, never change the words.

export type Block =
  | { kind: 'heading'; text: string }
  | { kind: 'list'; items: string[] }
  | { kind: 'paragraph'; text: string }

// "- ", "• ", "* ", "1. ", "2) " at the start of a line.
const BULLET = /^\s*(?:[-•*·●▪◦–]|\d{1,2}[.)])\s+/

// Section names postings use, as a whole line ("Requirements", "What you'll do").
const SECTION = new RegExp('^(?:about(?: us| the (?:role|team|company|position|job))?|description|' +
  'job description|the role|your role|role overview|overview|the position|responsibilities|' +
  'key responsibilities|requirements|qualifications|' +
  "(?:basic|minimum|preferred|required) qualifications|what (?:you'?ll|you will|will you) do|" +
  "what you'?ll bring|what we(?:'re| are) looking for|who you are|you have|you are|" +
  "nice to have|advantages?|bonus(?: points)?|benefits|what we offer|why join us|" +
  'must have|skills|experience)\\b', 'i')

// A short line with no full stop that ends in ":" or is a known section name.
function isHeading(line: string) {
  if (line.length > 60 || /[.!?]$/.test(line)) return false
  if (line.split(/\s+/).length > 8) return false
  return line.endsWith(':') || SECTION.test(line)
}

export function postingBlocks(text: string): Block[] {
  const blocks: Block[] = []
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()
    if (!line) continue
    const last = blocks.at(-1)
    if (BULLET.test(line)) {
      const item = line.replace(BULLET, '')
      if (last?.kind === 'list') last.items.push(item)
      else blocks.push({ kind: 'list', items: [item] })
    } else if (isHeading(line)) {
      blocks.push({ kind: 'heading', text: line.replace(/:\s*$/, '') })
    } else {
      blocks.push({ kind: 'paragraph', text: line })
    }
  }
  return blocks
}

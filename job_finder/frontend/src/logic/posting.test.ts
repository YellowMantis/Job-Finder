// Tests for reading a posting's shape. Run with: npm test

import { describe, expect, it } from 'vitest'
import { postingBlocks } from './posting'

describe('posting text as a page', () => {
  it('finds headings, bullet lists and paragraphs', () => {
    const text = [
      'About us:',
      'We build tools for finance teams.',
      '',
      "What you'll do",
      '- Lead design work',
      '• Work with developers',
      'Requirements:',
      '1. 2+ years of Python',
      '2) Docker',
    ].join('\n')
    expect(postingBlocks(text)).toEqual([
      { kind: 'heading', text: 'About us' },
      { kind: 'paragraph', text: 'We build tools for finance teams.' },
      { kind: 'heading', text: "What you'll do" },
      { kind: 'list', items: ['Lead design work', 'Work with developers'] },
      { kind: 'heading', text: 'Requirements' },
      { kind: 'list', items: ['2+ years of Python', 'Docker'] },
    ])
  })

  it('leaves sentences as paragraphs, even ones that start like a section name', () => {
    expect(postingBlocks('Experience with cloud platforms is a big plus.\nSkills matter here, and so do people.'))
      .toEqual([
        { kind: 'paragraph', text: 'Experience with cloud platforms is a big plus.' },
        { kind: 'paragraph', text: 'Skills matter here, and so do people.' },
      ])
  })

  it('does not take a long line ending in a colon for a heading', () => {
    const line = 'In this role you will work with many teams across the company on the following:'
    expect(postingBlocks(line)).toEqual([{ kind: 'paragraph', text: line }])
  })
})

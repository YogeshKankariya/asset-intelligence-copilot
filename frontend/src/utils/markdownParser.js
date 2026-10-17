import React from 'react'

/**
 * Safe inline Markdown renderer.
 * Converts inline Markdown tokens (bold, italic, code, safe links) into React elements
 * without using dangerouslySetInnerHTML or any unsafe DOM injection.
 */
export function renderInlineMarkdown(text) {
  if (!text) return null
  if (typeof text !== 'string') return String(text)

  // Regex splitting by:
  // 1. Inline code: `...`
  // 2. Bold italic: ***...***
  // 3. Bold: **...** or __...__
  // 4. Italic: *...* or _..._
  // 5. Links: [text](url)
  const tokenRegex = /(`[^`]+`|\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\))/g

  const parts = text.split(tokenRegex)

  return parts.map((part, idx) => {
    if (!part) return null

    // 1. Inline code: `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return React.createElement(
        'code',
        { key: idx, className: 'inline-code' },
        part.slice(1, -1)
      )
    }

    // 2. Bold Italic: ***text***
    if (part.startsWith('***') && part.endsWith('***') && part.length >= 6) {
      return React.createElement(
        'strong',
        { key: idx },
        React.createElement('em', null, renderInlineMarkdown(part.slice(3, -3)))
      )
    }

    // 3. Bold: **text** or __text__
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      return React.createElement(
        'strong',
        { key: idx },
        renderInlineMarkdown(part.slice(2, -2))
      )
    }

    // 4. Italic: *text* or _text_
    if (
      (part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length >= 2)
    ) {
      return React.createElement(
        'em',
        { key: idx },
        renderInlineMarkdown(part.slice(1, -1))
      )
    }

    // 5. Link: [label](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (linkMatch) {
      const [, label, url] = linkMatch
      const cleanUrl = url.trim()
      // Only permit safe web / relative protocols
      const isSafe =
        cleanUrl.startsWith('http://') ||
        cleanUrl.startsWith('https://') ||
        cleanUrl.startsWith('#') ||
        cleanUrl.startsWith('/')

      if (isSafe) {
        return React.createElement(
          'a',
          {
            key: idx,
            href: cleanUrl,
            target: '_blank',
            rel: 'noopener noreferrer',
            className: 'markdown-link',
          },
          label
        )
      }
      return React.createElement('span', { key: idx }, label)
    }

    // Plain text
    return part
  })
}

/**
 * Parses and renders a markdown table safely.
 */
function renderTableBlock(lines, key) {
  const headerLine = lines[0].trim()
  const headerCells = headerLine
    .split('|')
    .map((c) => c.trim())
    .filter((_, idx, arr) => idx > 0 && idx < arr.length - (headerLine.endsWith('|') ? 1 : 0))

  const bodyLines = lines.slice(2)
  const rows = bodyLines
    .filter((l) => l.trim().length > 0 && l.includes('|'))
    .map((line) => {
      const trimmed = line.trim()
      return trimmed
        .split('|')
        .map((c) => c.trim())
        .filter((_, idx, arr) => idx > 0 && idx < arr.length - (trimmed.endsWith('|') ? 1 : 0))
    })

  const thElements = headerCells.map((header, hIdx) =>
    React.createElement('th', { key: hIdx }, renderInlineMarkdown(header))
  )
  const thead = React.createElement(
    'thead',
    null,
    React.createElement('tr', null, thElements)
  )

  const trElements = rows.map((row, rIdx) => {
    const tdElements = row.map((cell, cIdx) =>
      React.createElement('td', { key: cIdx }, renderInlineMarkdown(cell))
    )
    return React.createElement('tr', { key: rIdx }, tdElements)
  })
  const tbody = React.createElement('tbody', null, trElements)

  const table = React.createElement(
    'table',
    { className: 'markdown-table' },
    thead,
    tbody
  )

  return React.createElement('div', { key, className: 'markdown-table-wrapper' }, table)
}

/**
 * Safe block-level Markdown parser.
 * Converts text into semantic React elements (h1-h4, blockquotes, lists, tables, paragraphs).
 */
export function parseMarkdown(markdownText) {
  if (!markdownText) return null

  // Normalize line endings and split into line array
  const rawLines = markdownText.replace(/\r\n/g, '\n').split('\n')
  const elements = []
  let lineIdx = 0
  let elemKey = 0

  while (lineIdx < rawLines.length) {
    const line = rawLines[lineIdx]
    const trimmed = line.trim()

    // Skip empty lines
    if (!trimmed) {
      lineIdx++
      continue
    }

    // 1. Table Detection
    if (trimmed.includes('|') && lineIdx + 1 < rawLines.length) {
      const nextLine = rawLines[lineIdx + 1].trim()
      if (/^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$/.test(nextLine)) {
        const tableLines = []
        while (lineIdx < rawLines.length && rawLines[lineIdx].trim().includes('|')) {
          tableLines.push(rawLines[lineIdx])
          lineIdx++
        }
        elements.push(renderTableBlock(tableLines, elemKey++))
        continue
      }
    }

    // 2. Headings (#, ##, ###, ####)
    if (trimmed.startsWith('#')) {
      const headingMatch = trimmed.match(/^(#{1,4})\s+(.*)$/)
      if (headingMatch) {
        const level = headingMatch[1].length
        const content = renderInlineMarkdown(headingMatch[2])
        const tag = level === 1 ? 'h1' : level === 2 ? 'h2' : level === 3 ? 'h3' : 'h4'
        elements.push(React.createElement(tag, { key: elemKey++ }, content))
        lineIdx++
        continue
      }
    }

    // 3. Blockquotes (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines = []
      while (lineIdx < rawLines.length && rawLines[lineIdx].trim().startsWith('>')) {
        quoteLines.push(rawLines[lineIdx].trim().replace(/^>\s?/, ''))
        lineIdx++
      }
      const quoteChildren = quoteLines.map((ql, qIdx) =>
        React.createElement(
          React.Fragment,
          { key: qIdx },
          qIdx > 0 ? React.createElement('br') : null,
          renderInlineMarkdown(ql)
        )
      )
      elements.push(
        React.createElement(
          'blockquote',
          { key: elemKey++, className: 'answer-quote' },
          quoteChildren
        )
      )
      continue
    }

    // 4. Unordered List (- or *)
    if (/^[-*]\s+/.test(trimmed)) {
      const listItems = []
      while (lineIdx < rawLines.length && /^[-*]\s+/.test(rawLines[lineIdx].trim())) {
        const itemText = rawLines[lineIdx].trim().replace(/^[-*]\s+/, '')
        listItems.push(itemText)
        lineIdx++
      }
      const liElements = listItems.map((item, iIdx) =>
        React.createElement('li', { key: iIdx }, renderInlineMarkdown(item))
      )
      elements.push(
        React.createElement(
          'ul',
          { key: elemKey++, className: 'answer-bullet-list' },
          liElements
        )
      )
      continue
    }

    // 5. Ordered List (1. , 2. )
    if (/^\d+\.\s+/.test(trimmed)) {
      const listItems = []
      while (lineIdx < rawLines.length && /^\d+\.\s+/.test(rawLines[lineIdx].trim())) {
        const itemText = rawLines[lineIdx].trim().replace(/^\d+\.\s+/, '')
        listItems.push(itemText)
        lineIdx++
      }
      const liElements = listItems.map((item, iIdx) =>
        React.createElement('li', { key: iIdx }, renderInlineMarkdown(item))
      )
      elements.push(
        React.createElement(
          'ol',
          { key: elemKey++, className: 'answer-ordered-list' },
          liElements
        )
      )
      continue
    }

    // 6. Regular Paragraph
    const paraLines = []
    while (
      lineIdx < rawLines.length &&
      rawLines[lineIdx].trim() &&
      !rawLines[lineIdx].trim().startsWith('#') &&
      !rawLines[lineIdx].trim().startsWith('>') &&
      !/^[-*]\s+/.test(rawLines[lineIdx].trim()) &&
      !/^\d+\.\s+/.test(rawLines[lineIdx].trim()) &&
      !(rawLines[lineIdx].trim().includes('|') && lineIdx + 1 < rawLines.length && /^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$/.test(rawLines[lineIdx + 1].trim()))
    ) {
      paraLines.push(rawLines[lineIdx].trim())
      lineIdx++
    }

    if (paraLines.length > 0) {
      const pChildren = paraLines.map((pl, pIdx) =>
        React.createElement(
          React.Fragment,
          { key: pIdx },
          pIdx > 0 ? ' ' : null,
          renderInlineMarkdown(pl)
        )
      )
      elements.push(React.createElement('p', { key: elemKey++ }, pChildren))
    }
  }

  return elements
}

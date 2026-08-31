import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('chat composer layout', () => {
  it('anchors the composer to the chat panel flow instead of page coordinates', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8')
    const composerRule = css.match(/\.composer-wrap \{[^}]+\}/)?.[0] ?? ''

    expect(composerRule).toContain('position: relative')
    expect(composerRule).toContain('flex: 0 0 auto')
    expect(composerRule).not.toContain('left: calc(')
    expect(css).toContain('.message-stream { flex: 1 1 auto; min-height: 0; overflow-y: auto;')
  })
})

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, describe, expect, it } from 'vitest'

import { COMPOSER_PASTES_DIRNAME, writeComposerPaste } from './composer-paste'

const scratch: string[] = []

afterEach(() => {
  for (const dir of scratch.splice(0)) {
    fs.rmSync(dir, { force: true, recursive: true })
  }
})

describe('writeComposerPaste', () => {
  it('lands the paste directly under <ANAKOT_HOME>/composer-pastes so the backend admits it', async () => {
    const anakotHome = fs.mkdtempSync(path.join(os.tmpdir(), 'anakot-home-'))
    scratch.push(anakotHome)

    const filePath = await writeComposerPaste(anakotHome, 'pasted body')

    expect(path.dirname(filePath)).toBe(path.join(anakotHome, COMPOSER_PASTES_DIRNAME))
    expect(fs.readFileSync(filePath, 'utf8')).toBe('pasted body')
  })
})

import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { once } from 'node:events'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { test } from 'vitest'

import { preflightStateDb } from './state-db-preflight'

const PYTHON: string = process.env.ANAKOT_PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
const SCRIPT: string = fileURLToPath(new URL('../../../../anakot_cli/backup_sqlite.py', import.meta.url))

// Regression: the preflight used to copy state.db with fs.copyFileSync, which
// silently dropped every committed transaction still sitting in the -wal
// sidecar — an "emergency" backup that restored an empty database.
test('the desktop preflight publishes committed WAL rows before its caller can stop the backend', async (): Promise<void> => {
  const home: string = fs.mkdtempSync(path.join(os.tmpdir(), 'desktop-db-'))

  const child = spawn(
    PYTHON,
    [
      '-I',
      '-S',
      '-u',
      '-c',
      `
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('PRAGMA journal_mode=WAL')
c.execute('PRAGMA wal_autocheckpoint=0')
c.execute('CREATE TABLE messages (body TEXT)')
c.commit()
c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
c.execute("INSERT INTO messages VALUES ('pending in WAL')")
c.commit()
print('ready', flush=True)
sys.stdin.readline()
c.close()
`,
      path.join(home, 'state.db')
    ],
    { stdio: ['pipe', 'pipe', 'pipe'] }
  )

  const logs: string[] = []

  try {
    await once(child.stdout!, 'data')
    preflightStateDb({
      python: PYTHON,
      script: SCRIPT,
      home,
      log: (message: string): void => {
        logs.push(message)
      }
    })
    assert.equal(child.exitCode, null)
    const backups: string[] = fs.readdirSync(home).filter((name: string): boolean => name.endsWith('.bak'))
    assert.equal(backups.length, 1, logs.join('\n'))

    const verify = spawnSync(
      PYTHON,
      [
        '-I',
        '-S',
        '-c',
        `
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as c:
    assert c.execute('SELECT body FROM messages').fetchall() == [('pending in WAL',)]
`,
        path.join(home, backups[0]!)
      ],
      { encoding: 'utf8' }
    )

    assert.equal(verify.status, 0, verify.stderr)
    const exited = once(child, 'exit')
    child.stdin!.end('\n')
    await exited
  } finally {
    if (child.exitCode === null && child.signalCode === null) {
      child.kill('SIGKILL')
      await once(child, 'exit')
    }

    fs.rmSync(home, { recursive: true, force: true })
  }
})

// The helper keeps the newest two snapshots so a botched update is always
// recoverable; a third publication must not accumulate without bound.
test('repeated preflights retain the two most recent snapshots', (): void => {
  const home: string = fs.mkdtempSync(path.join(os.tmpdir(), 'preflight-retention-'))

  try {
    const created = spawnSync(
      PYTHON,
      [
        '-I',
        '-S',
        '-c',
        "import sqlite3, sys; c = sqlite3.connect(sys.argv[1]); c.execute('CREATE TABLE t (x)'); c.commit(); c.close()",
        path.join(home, 'state.db')
      ],
      { encoding: 'utf8' }
    )

    assert.equal(created.status, 0, created.stderr)

    for (let i = 0; i < 4; i++) {
      preflightStateDb({ python: PYTHON, script: SCRIPT, home, log: (): void => {} })
    }

    const backups: string[] = fs.readdirSync(home).filter((name: string): boolean => name.endsWith('.bak'))
    assert.equal(backups.length, 2)
    assert.equal(
      fs.readdirSync(home).filter((name: string): boolean => name.endsWith('.partial')).length,
      0,
      'staging files must never survive a successful snapshot'
    )
  } finally {
    fs.rmSync(home, { recursive: true, force: true })
  }
})

test('an older selected checkout without the snapshot helper refuses before backend stop', (): void => {
  const oldRoot: string = fs.mkdtempSync(path.join(os.tmpdir(), 'old-preflight-'))
  let stopped = false

  try {
    assert.throws((): void => {
      preflightStateDb({
        python: PYTHON,
        script: path.join(oldRoot, 'anakot_cli', 'backup_sqlite.py'),
        home: oldRoot,
        log: (): void => {}
      })
      stopped = true
    }, /snapshot|pre-flight/)
    assert.equal(stopped, false)
  } finally {
    fs.rmSync(oldRoot, { recursive: true, force: true })
  }
})
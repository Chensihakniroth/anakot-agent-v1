import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { once } from 'node:events'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { test, vi } from 'vitest'

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
    let eventLoopResponsive = false
    setImmediate((): void => {
      eventLoopResponsive = true
    })

    await preflightStateDb({
      python: PYTHON,
      script: SCRIPT,
      home,
      log: (message: string): void => {
        logs.push(message)
      }
    })
    assert.equal(eventLoopResponsive, true, 'pre-flight must not block Electron while it snapshots')
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
test('repeated preflights retain the two most recent snapshots', async (): Promise<void> => {
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
      await preflightStateDb({ python: PYTHON, script: SCRIPT, home, log: (): void => {} })
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

test.each([
  { value: 'off', enabled: false },
  { value: false, enabled: false },
  { value: null, enabled: false },
  { value: 'false', enabled: false },
  { value: 'none', enabled: false },
  { value: ' DISABLED ', enabled: false },
  { value: 'quick', enabled: true },
  { value: 'full', enabled: true },
  { value: true, enabled: true },
  { value: 0, enabled: true },
  { value: 'unexpected', enabled: true },
  { value: undefined, enabled: true },
  { value: true, managed: false, enabled: false },
  { value: false, managed: true, enabled: true },
  { value: '${DESKTOP_TEST_BACKUP_MODE}', enabled: false }
])(
  'preflight obeys effective config $value (managed: $managed) in the target home',
  async ({ value, managed, enabled }): Promise<void> => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'backup config '))
    const homes = [path.join(root, 'a'), path.join(root, 'a', 'profiles', 'b')]
    const managedDir = path.join(root, 'managed')

    try {
      fs.mkdirSync(managedDir)

      if (managed !== undefined) {
        fs.writeFileSync(
          path.join(managedDir, 'config.yaml'),
          JSON.stringify({ updates: { pre_update_backup: managed } })
        )
      }

      vi.stubEnv('ANAKOT_MANAGED_DIR', managedDir)
      vi.stubEnv('DESKTOP_TEST_BACKUP_MODE', 'off')
      // The ambient launch home must not replace the explicit snapshot owner.
      vi.stubEnv('ANAKOT_HOME', homes[1]!)

      for (const [index, home] of homes.entries()) {
        fs.mkdirSync(home, { recursive: true })
        fs.writeFileSync(
          path.join(home, 'config.yaml'),
          JSON.stringify({ updates: { pre_update_backup: index === 0 ? value : !enabled } })
        )

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
      }

      // A root-home probe must not follow the CLI's sticky named profile.
      fs.writeFileSync(path.join(homes[0]!, 'active_profile'), 'b')
      const counts = [0, 0]

      for (const index of [0, 1, 0]) {
        const home = homes[index]!
        const logs: string[] = []
        await preflightStateDb({
          python: PYTHON,
          script: SCRIPT,
          home,
          log: message => {
            logs.push(message)
          }
        })
        const shouldBackUp = managed !== undefined ? managed : index === 0 ? enabled : !enabled

        if (shouldBackUp) {
          counts[index]!++
        }

        assert.equal(fs.readdirSync(home).filter(name => name.endsWith('.bak')).length, counts[index], logs.join('\n'))
        assert.equal(
          logs.some(message => message.includes('disabled by updates.pre_update_backup')),
          !shouldBackUp
        )
      }
    } finally {
      vi.unstubAllEnvs()
      fs.rmSync(root, { recursive: true, force: true })
    }
  },
  30_000
)

test.each([
  { label: 'missing config CLI', cli: null },
  { label: 'malformed response', cli: "print('not-json')" },
  { label: 'failed probe with misleading stdout', cli: "print('false'); raise SystemExit(1)" },
  { label: 'timeout with misleading stdout', cli: "import time; print('false', flush=True); time.sleep(60)" }
])(
  'preflight retains the SQLite safety net after $label',
  async ({ cli }): Promise<void> => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'broken checkout '))
    const home = path.join(root, 'home')
    const packageDir = path.join(root, 'anakot_cli')
    const script = path.join(packageDir, 'backup_sqlite.py')

    try {
      fs.mkdirSync(home)
      fs.mkdirSync(packageDir)
      fs.writeFileSync(path.join(packageDir, '__init__.py'), '')

      if (cli !== null) {
        fs.writeFileSync(path.join(packageDir, 'main.py'), cli)
      }

      fs.copyFileSync(SCRIPT, script)
      // Off must not be inferred from an unreadable runtime or raw config file.
      fs.writeFileSync(path.join(home, 'config.yaml'), 'updates:\n  pre_update_backup: off\n')

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

      const logs: string[] = []
      await preflightStateDb({
        python: PYTHON,
        script,
        home,
        log: message => {
          logs.push(message)
        }
      })
      assert.equal(fs.readdirSync(home).filter(name => name.endsWith('.bak')).length, 1, logs.join('\n'))
      assert.equal(
        logs.some(message => message.includes('disabled by')),
        false
      )
    } finally {
      fs.rmSync(root, { recursive: true, force: true })
    }
  },
  30_000
)

test('an older selected checkout without the snapshot helper refuses before backend stop', async (): Promise<void> => {
  const oldRoot: string = fs.mkdtempSync(path.join(os.tmpdir(), 'old-preflight-'))
  let stopped = false

  try {
    await assert.rejects(async (): Promise<void> => {
      await preflightStateDb({
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

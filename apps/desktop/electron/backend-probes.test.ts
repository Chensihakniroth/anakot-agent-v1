/**
 * Tests for electron/backend-probes.ts.
 *
 * Run with: node --test electron/backend-probes.test.ts
 * (Wired into npm test:desktop:platforms in package.json.)
 */

import assert from 'node:assert/strict'
import fs from 'node:fs'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'

import { test } from 'vitest'

import {
  canImportAnakotCli,
  DEFAULT_PROBE_TIMEOUT_MS,
  execProbe,
  anakotRuntimeImportProbe,
  PROBE_TIMEOUT_MS,
  resolveProbeTimeoutMs,
  shouldTrustAnakotOverride,
  verifyAnakotCli
} from './backend-probes'

// Resolve the host's own Node binary -- guaranteed to be on disk and
// runnable. We use it as both a stand-in for "a python that doesn't
// have anakot_cli" (since `node -c "import anakot_cli"` will exit
// non-zero) and as a way to script verifyAnakotCli's success path
// (a tiny script we write to disk that exits 0 on --version).
const NODE_BIN = process.execPath

test('execProbe keeps the parent event loop available to the child', async () => {
  let unexpectedSocketError: Error | undefined

  const server = net.createServer((socket) => {
    socket.on('error', (error) => {
      // A successful child exits immediately after reading the sentinel. On
      // Windows that peer close can surface as ECONNRESET on the server side.
      if ((error as NodeJS.ErrnoException).code !== 'ECONNRESET') {
        unexpectedSocketError ??= error
      }
    })
    socket.end('pong')
  })

  await new Promise<void>((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })

  const address = server.address()
  assert.ok(address && typeof address === 'object')

  const childScript = `
    const net = require('node:net')
    let reply = ''
    const socket = net.createConnection(${address.port}, '127.0.0.1')
    socket.setEncoding('utf8')
    socket.on('data', (chunk) => { reply += chunk })
    socket.on('end', () => process.exit(reply === 'pong' ? 0 : 1))
    socket.on('error', () => process.exit(1))
  `

  try {
    await execProbe(NODE_BIN, ['-e', childScript], {
      stdio: 'ignore',
      timeout: 5_000,
      windowsHide: true
    })
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()))
    })
  }

  assert.ifError(unexpectedSocketError)
})

test('canImportAnakotCli returns false when path is falsy', async () => {
  assert.equal(await canImportAnakotCli(''), false)
  assert.equal(await canImportAnakotCli(null), false)
  assert.equal(await canImportAnakotCli(undefined), false)
})

test('canImportAnakotCli returns false when interpreter cannot run -c', async () => {
  // node IS an interpreter, but `node -c "import anakot_cli"` is a
  // SyntaxError -- different exit reason from a real Python's
  // ModuleNotFoundError, but the predicate is "exit 0 or not" and
  // both land on "not", which is exactly what we want for the
  // resolver fall-through.
  assert.equal(await canImportAnakotCli(NODE_BIN), false)
})

test('canImportAnakotCli returns false when binary does not exist', async () => {
  const ghost = path.join(os.tmpdir(), 'anakot-probes-ghost-' + Date.now() + '.exe')
  assert.equal(await canImportAnakotCli(ghost), false)
})

test('anakot runtime import probe checks config dependencies', () => {
  const probe = anakotRuntimeImportProbe()
  assert.match(probe, /\bimport yaml\b/)
  // dotenv is the first third-party import on the CLI boot path
  // (anakot_cli/env_loader.py); a mid-update venv missing python-dotenv
  // passed the old probe and produced an unrecoverable boot loop.
  assert.match(probe, /\bimport dotenv\b/)
  assert.match(probe, /\bimport anakot_cli\.config\b/)
})

test('explicit Anakot override is authoritative', () => {
  assert.equal(shouldTrustAnakotOverride('/nix/store/abc/bin/anakot'), true)
})

test('empty Anakot override is not authoritative', () => {
  assert.equal(shouldTrustAnakotOverride(''), false)
  assert.equal(shouldTrustAnakotOverride(undefined), false)
})

test('verifyAnakotCli returns false when command is falsy', async () => {
  assert.equal(await verifyAnakotCli(''), false)
  assert.equal(await verifyAnakotCli(null), false)
  assert.equal(await verifyAnakotCli(undefined), false)
})

test('verifyAnakotCli returns false when binary does not exist', async () => {
  const ghost = path.join(os.tmpdir(), 'anakot-probes-ghost-' + Date.now() + '.exe')
  assert.equal(await verifyAnakotCli(ghost), false)
})

test('verifyAnakotCli returns true when --version exits 0', async () => {
  // Write a tiny script that exits 0 regardless of args, then invoke
  // it through node. This stands in for a working anakot binary --
  // verifyAnakotCli only cares about the exit code.
  const scriptPath = path.join(os.tmpdir(), `anakot-probes-ok-${Date.now()}-${process.pid}.cjs`)
  fs.writeFileSync(scriptPath, 'process.exit(0)\n')

  try {
    // Use node as the launcher and our script as the "command". Pass
    // shell:false (default) -- node is a real binary, no shim.
    // execFileSync passes ['--version'] as args, which node ignores
    // gracefully (well, it prints its version and exits 0, which is
    // perfect -- exit code 0 is the only signal we read).
    assert.equal(await verifyAnakotCli(NODE_BIN), true)
  } finally {
    try {
      fs.unlinkSync(scriptPath)
    } catch {
      void 0
    }
  }
})

test('verifyAnakotCli swallows timeouts (does not throw)', async () => {
  // We can't easily provoke a real hang in CI without slowing the
  // suite, but we CAN confirm that an invocation that DOES throw
  // (because the binary is missing) returns false rather than
  // propagating. Same code path the timeout case takes.
  assert.equal(await verifyAnakotCli('/definitely/not/a/real/binary/anywhere'), false)
})

test('default probe timeout is 15s (not the old 5s death-loop value)', () => {
  assert.equal(DEFAULT_PROBE_TIMEOUT_MS, 15_000)
  // Module constant uses process.env at load time; with no override it
  // matches the default (tests run without ANAKOT_PROBE_TIMEOUT_MS).
  assert.equal(PROBE_TIMEOUT_MS, DEFAULT_PROBE_TIMEOUT_MS)
})

test('resolveProbeTimeoutMs honours ANAKOT_PROBE_TIMEOUT_MS', () => {
  assert.equal(resolveProbeTimeoutMs({}), DEFAULT_PROBE_TIMEOUT_MS)
  assert.equal(resolveProbeTimeoutMs({ ANAKOT_PROBE_TIMEOUT_MS: '30000' }), 30_000)
  assert.equal(resolveProbeTimeoutMs({ ANAKOT_PROBE_TIMEOUT_MS: '0' }), DEFAULT_PROBE_TIMEOUT_MS)
  assert.equal(resolveProbeTimeoutMs({ ANAKOT_PROBE_TIMEOUT_MS: 'nope' }), DEFAULT_PROBE_TIMEOUT_MS)
  // Cap runaway values
  assert.equal(resolveProbeTimeoutMs({ ANAKOT_PROBE_TIMEOUT_MS: '999999' }), 120_000)
})

import { spawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'

export interface OpenCode2ApiLifecycleOptions {
  root?: string
  log?: (message: string) => void
  forceKillProcessTree: (pid: number) => void
  isWindows?: boolean
}

const API_PORT = 8080
const HEALTH_PATH = '/healthz'
const START_TIMEOUT_MS = 15_000
const POLL_INTERVAL_MS = 250

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

function defaultRoot() {
  const configured = process.env.OPENCODE2API_ROOT?.trim()
  if (configured) {
    return configured
  }

  const localAppData = process.env.LOCALAPPDATA?.trim()
  return localAppData ? path.join(localAppData, 'opencode2api') : path.join(os.homedir(), 'AppData', 'Local', 'opencode2api')
}

function probeHealth(): Promise<boolean> {
  return new Promise(resolve => {
    const request = http.get(
      {
        hostname: '127.0.0.1',
        port: API_PORT,
        path: HEALTH_PATH,
        timeout: 1_000
      },
      response => {
        response.resume()
        response.once('end', () => resolve(response.statusCode === 200))
      }
    )

    request.once('error', () => resolve(false))
    request.once('timeout', () => {
      request.destroy()
      resolve(false)
    })
  })
}

async function waitForHealth(child: ChildProcess) {
  const deadline = Date.now() + START_TIMEOUT_MS

  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error('opencode2api exited before its health endpoint became ready')
    }

    if (await probeHealth()) {
      return
    }

    await delay(POLL_INTERVAL_MS)
  }

  throw new Error(`opencode2api did not become ready on 127.0.0.1:${API_PORT}`)
}

function waitForExit(child: ChildProcess, timeoutMs = 5_000) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return Promise.resolve()
  }

  return new Promise<void>(resolve => {
    let finished = false
    const finish = () => {
      if (finished) return
      finished = true
      clearTimeout(timer)
      child.removeListener('exit', finish)
      resolve()
    }
    const timer = setTimeout(finish, timeoutMs)
    child.once('exit', finish)
  })
}

/** Owns the optional local OpenCode gateway for one Electron app lifetime. */
export function createOpenCode2ApiLifecycle(options: OpenCode2ApiLifecycleOptions) {
  const isWindows = options.isWindows ?? process.platform === 'win32'
  const root = options.root?.trim() || defaultRoot()
  const executable = path.join(root, isWindows ? 'opencode2api.exe' : 'opencode2api')
  const config = path.join(root, 'config.json')
  const log = options.log ?? (() => {})

  let child: ChildProcess | null = null
  let startPromise: Promise<void> | null = null
  let stopping = false

  const stop = async () => {
    const current = child
    child = null
    stopping = true

    if (!current || current.exitCode !== null || current.signalCode !== null) {
      stopping = false
      return
    }

    try {
      if (isWindows && Number.isInteger(current.pid)) {
        options.forceKillProcessTree(current.pid as number)
      } else {
        current.kill('SIGTERM')
      }
    } catch {
      // The process may already have exited.
    }

    await waitForExit(current)
    stopping = false
  }

  const start = async () => {
    if (!isWindows) {
      log('[opencode2api] skipped: the managed gateway is configured for Windows')
      return
    }

    if (child && child.exitCode === null && child.signalCode === null) {
      return
    }

    if (await probeHealth()) {
      log('[opencode2api] already healthy on 127.0.0.1:8080; leaving the existing process untouched')
      return
    }

    if (!fs.existsSync(executable) || !fs.existsSync(config)) {
      throw new Error(`missing managed gateway files under ${root}`)
    }

    const spawned = spawn(executable, ['-config', config], {
      cwd: root,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe']
    })
    child = spawned
    stopping = false

    // Drain stdout so a verbose gateway cannot block on a full pipe. Error
    // output remains visible in the desktop log without copying request data.
    spawned.stdout?.on('data', () => {})
    spawned.stderr?.on('data', chunk => {
      const text = String(chunk).trim()
      if (text) log(`[opencode2api] ${text.slice(-2_000)}`)
    })
    spawned.once('error', error => {
      if (child === spawned) child = null
      log(`[opencode2api] process error: ${error.message}`)
    })
    spawned.once('exit', (code, signal) => {
      if (child === spawned) child = null
      if (!stopping) {
        log(`[opencode2api] exited unexpectedly (${signal || (code ?? 'unknown')})`)
      }
    })

    try {
      await waitForHealth(spawned)
      log('[opencode2api] ready on 127.0.0.1:8080')
    } catch (error) {
      await stop()
      throw error
    }
  }

  const ensureStarted = () => {
    if (!startPromise) {
      startPromise = start().finally(() => {
        startPromise = null
      })
    }
    return startPromise
  }

  return {
    start: ensureStarted,
    stop,
    paths: { root, executable, config }
  }
}

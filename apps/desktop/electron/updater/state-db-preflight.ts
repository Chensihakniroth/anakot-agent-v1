import { execFile } from 'node:child_process'
import path from 'node:path'
import { promisify } from 'node:util'

import { hiddenWindowsChildOptions } from '../windows-child-options'

const execFileAsync = promisify(execFile)
const CONFIG_PROBE_TIMEOUT_MS = 15_000
const STATE_DB_PREFLIGHT_TIMEOUT_MS = 5 * 60_000

async function readPreUpdateBackupEnabled(
  python: string,
  script: string,
  home: string,
  log: (message: string) => void
): Promise<boolean> {
  try {
    // Query the selected checkout, not a potentially different CLI on PATH.
    // The backend owns defaults, managed policy and environment expansion.
    const root = path.resolve(path.dirname(script), '..')
    const targetHome = path.resolve(home)
    // ANAKOT_HOME alone still follows active_profile for a root-home CLI, so
    // name the profile explicitly. `-m anakot_cli.main` cannot be used: the
    // package import executes the module once (stripping --profile from argv)
    // and runpy executes it again, which re-homes a root probe to the sticky
    // active profile. Import-and-call runs it exactly once.
    const profile = path.basename(path.dirname(targetHome)) === 'profiles' ? path.basename(targetHome) : 'default'

    const { stdout } = await execFileAsync(
      python,
      [
        '-c',
        'import sys;from anakot_cli.main import main;sys.exit(main())',
        '--profile',
        profile,
        'config',
        'get',
        'updates.pre_update_backup',
        '--json'
      ],
      hiddenWindowsChildOptions({
        cwd: root,
        env: {
          ...process.env,
          ANAKOT_HOME: targetHome,
          PYTHONPATH: [root, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)
        },
        encoding: 'utf8',
        timeout: CONFIG_PROBE_TIMEOUT_MS,
        stdio: ['ignore', 'pipe', 'pipe']
      })
    )

    const value: unknown = JSON.parse(stdout.trim())

    return (
      value !== false &&
      value !== null &&
      !(typeof value === 'string' && ['off', 'false', 'none', 'disabled'].includes(value.trim().toLowerCase()))
    )
  } catch (error: unknown) {
    // Old/broken runtimes and malformed output must not disable recovery.
    log(
      `[updates] could not read updates.pre_update_backup; keeping the safety snapshot enabled: ${
        error instanceof Error ? error.message : String(error)
      }`
    )
    return true
  }
}

interface StateDbPreflight {
  python: string | null
  script: string
  home: string
  log: (message: string) => void
}

// The backend stays alive until this resolves; async execution keeps Electron responsive
// while large databases are copied and allows substantially longer than a fixed 30s window.
export async function preflightStateDb({ python, script, home, log }: StateDbPreflight): Promise<void> {
  try {
    if (!python) {
      throw new Error('Python not found')
    }

    if (!(await readPreUpdateBackupEnabled(python, script, home, log))) {
      log('[updates] emergency state.db backup disabled by updates.pre_update_backup')

      return
    }

    // -I -S runs the helper without site-packages, so it works before the
    // backend dies and while application imports still cannot load.
    const { stdout } = await execFileAsync(
      python,
      ['-I', '-S', script, home],
      hiddenWindowsChildOptions({
        encoding: 'utf8',
        timeout: STATE_DB_PREFLIGHT_TIMEOUT_MS,
        stdio: ['ignore', 'pipe', 'pipe']
      })
    )

    log(`[updates] state.db pre-flight: ${stdout.trim()}`)
  } catch (error: unknown) {
    const message =
      `state.db pre-flight failed: ${error instanceof Error ? error.message : String(error)}. ` +
      'Update cancelled before backend shutdown. Update the selected installation with its anakot update command, then retry.'

    log(`[updates] ${message}`)
    throw new Error(message, { cause: error })
  }
}

import { execFileSync } from 'node:child_process'
import path from 'node:path'

import { hiddenWindowsChildOptions } from '../windows-child-options'

function readPreUpdateBackupEnabled(python: string, script: string, home: string): boolean {
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

    const result = execFileSync(
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
        timeout: 15_000,
        stdio: ['ignore', 'pipe', 'pipe']
      })
    )

    const value: unknown = JSON.parse(result.trim())

    return (
      value !== false &&
      value !== null &&
      !(typeof value === 'string' && ['off', 'false', 'none', 'disabled'].includes(value.trim().toLowerCase()))
    )
  } catch {
    // Old/broken runtimes and malformed output must not disable recovery.
    return true
  }
}

interface StateDbPreflight {
  python: string | null
  script: string
  home: string
  log: (message: string) => void
}

// Synchronous by design: the caller must not stop the backend before the snapshot.
export function preflightStateDb({ python, script, home, log }: StateDbPreflight): void {
  try {
    if (!python) {
      throw new Error('Python not found')
    }

    if (!readPreUpdateBackupEnabled(python, script, home)) {
      log('[updates] emergency state.db backup disabled by updates.pre_update_backup')

      return
    }

    // -I -S runs the helper without site-packages, so it works before the
    // backend dies and while application imports still cannot load.
    const result: string = execFileSync(
      python,
      ['-I', '-S', script, home],
      hiddenWindowsChildOptions({
        encoding: 'utf8',
        timeout: 30_000,
        stdio: ['ignore', 'pipe', 'pipe']
      })
    )

    log(`[updates] state.db pre-flight: ${result.trim()}`)
  } catch (error: unknown) {
    const message =
      `state.db pre-flight failed: ${error instanceof Error ? error.message : String(error)}. ` +
      'Update cancelled before backend shutdown. Update the selected installation with its anakot update command, then retry.'

    log(`[updates] ${message}`)
    throw new Error(message, { cause: error })
  }
}

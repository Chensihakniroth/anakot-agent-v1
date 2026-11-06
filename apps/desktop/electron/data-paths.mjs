// data-paths.mjs — the pure path-resolution core, shared by the desktop app
// (via data-paths.ts, a typed re-export) and the CI smoke driver (which runs
// under Node's type-stripping and therefore cannot import the app's
// extensionless TypeScript directly). No Electron imports here; only node:path.
//
// data-paths.ts re-exports these names and adds the TypeScript-facing
// `AnakotHomeOptions` interface. Keep the two in lockstep: every behavior in
// this file is exercised by data-paths.test.ts through the re-export.

import path from 'node:path'

/** A ANAKOT_HOME rooted inside a `profiles/` directory names the profile's
 * parent (the home), not the profile directory itself. */
function normalizeAnakotHomeRoot(anakotHome, pathModule) {
  if (!anakotHome) {
    return anakotHome
  }
  const resolved = pathModule.resolve(String(anakotHome))
  const parent = pathModule.dirname(resolved)
  if (pathModule.basename(parent).toLowerCase() === 'profiles') {
    return pathModule.dirname(parent)
  }
  return resolved
}

export function platformDefaultAnakotHome(home, env = process.env, platform = process.platform) {
  const suffix = env.ANAKOT_DATA_DIR_SUFFIX || ''
  if (platform === 'win32') {
    const base = (env.LOCALAPPDATA || '').trim() || path.win32.join(home, 'AppData', 'Local')
    return path.win32.join(base, 'anakot') + suffix
  }
  return path.posix.join(home, '.anakot') + suffix
}

export function resolveDesktopUserData(defaultPath, env = process.env) {
  return env.ANAKOT_DESKTOP_USER_DATA_DIR
    ? path.resolve(env.ANAKOT_DESKTOP_USER_DATA_DIR)
    : defaultPath + (env.ANAKOT_DATA_DIR_SUFFIX || '')
}

export function resolveDesktopAnakotHome({ home, env = process.env, platform = process.platform, directoryExists = () => false, readWindowsHome = () => null }) {
  const paths = platform === 'win32' ? path.win32 : path.posix
  if (env.ANAKOT_HOME) {
    return normalizeAnakotHomeRoot(env.ANAKOT_HOME, paths)
  }
  // Fresh-install rehearsals must not touch the real Anakot home.
  if (env.ANAKOT_DESKTOP_USER_DATA_DIR) {
    return paths.join(paths.resolve(env.ANAKOT_DESKTOP_USER_DATA_DIR), 'anakot-home')
  }
  if (platform === 'win32' && env.ANAKOT_HOME === undefined) {
    // Explorer can miss setx changes. An explicit empty value opts out of that fallback.
    const registryHome = readWindowsHome()
    if (registryHome) {
      return normalizeAnakotHomeRoot(registryHome, paths)
    }
  }
  const defaultHome = platformDefaultAnakotHome(home, env, platform)
  // Keep the legacy migration for ordinary installs, not isolated suffix runs.
  if (platform === 'win32' && !env.ANAKOT_DATA_DIR_SUFFIX) {
    const legacy = paths.join(home, '.anakot')
    if (!directoryExists(defaultHome) && directoryExists(legacy)) {
      return legacy
    }
  }
  return defaultHome
}

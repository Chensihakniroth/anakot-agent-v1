#!/usr/bin/env node
// bundle-electron-main.mjs — bundles electron/main.ts and electron/preload.ts
// into self-contained js files in dist/ so the packaged app doesn't need
// node_modules/ or tsx at runtime.
//
// Output:
//   dist/electron-main.mjs          (MJS bundle — entry point for packaged app)
//   dist/electron-preload.js        (CJS bundle — loaded via BrowserWindow preload)
//   dist/preview-guest-preload.js   (CJS bundle — preview <webview> guest preload)
//
// `electron` and `node-pty` are external (provided by the runtime / staged
// separately via stage-native-deps).
import { build } from 'esbuild'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { mkdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { buildCommandScreenshotMonitor } from './build-command-screenshot-monitor.mjs'
import { isMain } from './utils.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const defaultSource = resolve(here, '../../..')
const requireFromHere = createRequire(import.meta.url)
const external = ['electron', 'node-pty', 'get-windows', 'fs']

export function createElectronBundleDefines({ dev, productIdentity, installStamp }) {
  return {
    __HERMES_PRODUCT_IDENTITY__: JSON.stringify(productIdentity),
    ...(dev
      ? {}
      : {
          'process.env.ANAKOT_DESKTOP_IS_PACKAGED': JSON.stringify(true),
          __HERMES_INSTALL_STAMP__: JSON.stringify(installStamp)
        })
  }
}

export async function bundleElectronMain({ source = defaultSource, out, dev = false } = {}) {
  const desktopRoot = resolve(source, 'apps/desktop')
  const distDir = resolve(out ?? resolve(desktopRoot, 'dist'))
  mkdirSync(distDir, { recursive: true })
  buildCommandScreenshotMonitor({ distDir })

  const productIdentity = requireFromHere(resolve(desktopRoot, 'product-identity.cjs'))
  const installStamp = dev
    ? undefined
    : JSON.parse(readFileSync(resolve(desktopRoot, 'build/install-stamp.json'), 'utf8'))
  const define = createElectronBundleDefines({ dev, productIdentity, installStamp })

  const mainOut = resolve(distDir, 'electron-main.mjs')
  await build({
    entryPoints: [resolve(desktopRoot, 'electron/entry.ts')],
    bundle: true,
    platform: 'node',
    format: 'esm',
    target: 'node20',
    outfile: mainOut,
    external,
    banner: {
      js: "import { createRequire } from 'module'; const require = createRequire(import.meta.url);"
    },
    define,
    logLevel: 'info'
  })
  console.log(`bundled ${mainOut}${dev ? ' (dev)' : ''}`)

  const preloadOut = resolve(distDir, 'electron-preload.js')
  await build({
    entryPoints: [resolve(desktopRoot, 'electron/preload.ts')],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    target: 'node20',
    outfile: preloadOut,
    external,
    define,
    logLevel: 'info'
  })
  console.log(`bundled ${preloadOut}${dev ? ' (dev)' : ''}`)

  const guestPreloadOut = resolve(distDir, 'preview-guest-preload.js')
  await build({
    entryPoints: [resolve(desktopRoot, 'electron/preview-guest-preload-entry.ts')],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    target: 'node20',
    outfile: guestPreloadOut,
    external,
    define,
    logLevel: 'info'
  })
  console.log(`bundled ${guestPreloadOut}${dev ? ' (dev)' : ''}`)

  return { mainOut, preloadOut, guestPreloadOut }
}

if (isMain(import.meta.url)) {
  await bundleElectronMain({ dev: process.argv.includes('--dev') })
}

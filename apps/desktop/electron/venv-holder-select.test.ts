import assert from 'node:assert/strict'

import { test } from 'vitest'

import { hasWindowsPathPrefix, isExternalVenvHolder, isAnakotOwnedVenvDaemon } from './venv-holder-select'

const SCRIPTS = 'C:\\Anakot\\venv\\Scripts'

test('matches the hindsight daemon shim (exe under venv Scripts + hindsight cmdline)', () => {
  assert.equal(
    isAnakotOwnedVenvDaemon(
      'C:\\Anakot\\venv\\Scripts\\pythonw.exe',
      'C:\\Anakot\\venv\\Scripts\\pythonw.exe -m hindsight_api.main --daemon --idle-timeout 300 --port 9177',
      SCRIPTS
    ),
    true
  )
})

test('Windows path prefix match is ordinal case-insensitive', () => {
  assert.equal(
    isAnakotOwnedVenvDaemon(
      'c:\\anakot\\venv\\scripts\\python.exe',
      'python.exe -m hindsight_api.main --daemon',
      'C:\\Anakot\\venv\\Scripts'
    ),
    true
  )
})

test('excludes external venv holders that are not the hindsight daemon', () => {
  // a user terminal running the anakot CLI from the venv — must NOT be killed
  assert.equal(isAnakotOwnedVenvDaemon('C:\\Anakot\\venv\\Scripts\\anakot.exe', 'anakot chat -q "hi"', SCRIPTS), false)
  // an unrelated python script using the venv interpreter
  assert.equal(
    isAnakotOwnedVenvDaemon('C:\\Anakot\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
})

test('excludes exes outside the venv even when the cmdline mentions hindsight', () => {
  assert.equal(
    isAnakotOwnedVenvDaemon('C:\\Other\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('prefix boundary: sibling dirs (ScriptsX) do not match', () => {
  assert.equal(hasWindowsPathPrefix('C:\\Anakot\\venv\\ScriptsX\\python.exe', SCRIPTS), false)
  assert.equal(hasWindowsPathPrefix('C:\\Anakot\\venv\\Scripts\\python.exe', SCRIPTS), true)
})

test('null/undefined fields never match', () => {
  assert.equal(isAnakotOwnedVenvDaemon(null, 'x', SCRIPTS), false)
  assert.equal(isAnakotOwnedVenvDaemon('C:\\Anakot\\venv\\Scripts\\pythonw.exe', null, SCRIPTS), false)
  assert.equal(isAnakotOwnedVenvDaemon(undefined, undefined, SCRIPTS), false)
})

// --- isExternalVenvHolder (#62311) ------------------------------------------

test('matches the autostart gateway shim (anakot.exe under venv Scripts)', () => {
  assert.equal(
    isExternalVenvHolder(
      'C:\\Anakot\\venv\\Scripts\\anakot.exe',
      '"C:\\Anakot\\venv\\Scripts\\anakot.exe" gateway run --external-supervisor',
      SCRIPTS
    ),
    true
  )
})

test('matches the dashboard scheduled task (python -m anakot_cli / -m anakot)', () => {
  assert.equal(
    isExternalVenvHolder(
      'C:\\Anakot\\venv\\Scripts\\python.exe',
      '"C:\\Anakot\\venv\\Scripts\\python.exe" -m anakot_cli.main dashboard',
      SCRIPTS
    ),
    true
  )
  assert.equal(
    isExternalVenvHolder('C:\\Anakot\\venv\\Scripts\\pythonw.exe', 'pythonw.exe -m anakot serve', SCRIPTS),
    true
  )
})

test('never matches an unrelated process that merely borrows the venv interpreter', () => {
  // a user's own script running on the venv python — NOT Anakot, must NOT be killed
  assert.equal(
    isExternalVenvHolder('C:\\Anakot\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
  // hindsight daemon is selected by isAnakotOwnedVenvDaemon, not here
  assert.equal(
    isExternalVenvHolder('C:\\Anakot\\venv\\Scripts\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('never matches a process outside the venv, even with anakot in the cmdline', () => {
  // an editor / shell whose command line mentions the install root (#62445 regression guard)
  assert.equal(
    isExternalVenvHolder('C:\\Windows\\System32\\cmd.exe', 'cmd /c cd C:\\Anakot\\venv\\Scripts && dir', SCRIPTS),
    false
  )
  assert.equal(isExternalVenvHolder('C:\\Other\\anakot.exe', 'anakot gateway run', SCRIPTS), false)
})

test('sibling-dir and boundary safety for the external selector', () => {
  assert.equal(isExternalVenvHolder('C:\\Anakot\\venv\\ScriptsX\\anakot.exe', 'anakot gateway run', SCRIPTS), false)
  assert.equal(isExternalVenvHolder(null, 'anakot gateway run', SCRIPTS), false)
  assert.equal(isExternalVenvHolder('C:\\Anakot\\venv\\Scripts\\anakot.exe', null, SCRIPTS), false)
})

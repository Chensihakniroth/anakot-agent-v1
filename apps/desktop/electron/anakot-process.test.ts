import { describe, expect, it } from 'vitest'

import { commandLineIsAnakotRuntime } from './anakot-process'

// HX003: process identity comes from a whole argv TOKEN, never an argv substring.
describe('commandLineIsAnakotRuntime (HX003 token matching)', () => {
  it('matches a real Anakot gateway command line', () => {
    expect(commandLineIsAnakotRuntime('anakot\0gateway\0run')).toBe(true)
    expect(commandLineIsAnakotRuntime('anakot gateway run')).toBe(true)
    expect(commandLineIsAnakotRuntime('anakot --profile work gateway run')).toBe(true)
  })

  it('matches a Anakot launched by an interpreter (basename of a path token)', () => {
    expect(commandLineIsAnakotRuntime('/venv/bin/python\0/venv/bin/anakot\0gateway\0run')).toBe(true)
    expect(commandLineIsAnakotRuntime('C:\\Anakot\\anakot.exe gateway run')).toBe(true)
  })

  // The bug this replaces: a bare `.includes('anakot')` matched any of these.
  it('does NOT match an unrelated process whose path merely contains "anakot"', () => {
    expect(commandLineIsAnakotRuntime('vim /home/user/anakot-notes.txt')).toBe(false)
    expect(commandLineIsAnakotRuntime('/opt/anakotbrew/bin/tool --run')).toBe(false)
    expect(commandLineIsAnakotRuntime('node /srv/anakot-dashboard/server.js')).toBe(false)
    expect(commandLineIsAnakotRuntime('cat ~/.anakot/config.yaml')).toBe(false)
  })

  // G2 (#150283): the real unmanaged-gateway launch is `python -m anakot_cli.main … gateway
  // run`, which the executable-basename-only matcher REJECTED — so findRunningGatewayProfiles
  // missed a live gateway at first launch / profile repair. Mirror the canonical Python matcher
  // (gateway.status.looks_like_gateway_command_line): recognize the module entry point, by argv
  // TOKENS not a substring, carrying the gateway subcommand.
  it('matches a module-launched gateway (python -m anakot_cli.main … gateway run)', () => {
    expect(commandLineIsAnakotRuntime('python\0-m\0anakot_cli.main\0-p\0x\0gateway\0run')).toBe(true)
    expect(commandLineIsAnakotRuntime('python -m anakot_cli.main -p x gateway run')).toBe(true)
    expect(commandLineIsAnakotRuntime('/venv/bin/python /venv/lib/anakot_cli/main.py gateway run')).toBe(true)
    expect(commandLineIsAnakotRuntime('python -m anakot_cli.main --profile work gateway run')).toBe(true)
  })

  it('does NOT match a module entry without the gateway subcommand, nor an unrelated anakot-tool path', () => {
    // A anakot_cli.main invocation that is not a gateway (e.g. `chat`) is not a running gateway.
    expect(commandLineIsAnakotRuntime('python -m anakot_cli.main chat')).toBe(false)
    // HX003: no substring; an unrelated tool whose path contains "anakot" is never a runtime.
    expect(commandLineIsAnakotRuntime('/opt/anakot-tool/foo gateway run')).toBe(false)
    // `-p gateway` is a profile value, not a subcommand.
    expect(commandLineIsAnakotRuntime('python -m anakot_cli.main -p gateway chat')).toBe(false)
  })
})

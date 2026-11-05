import { contextBridge, ipcRenderer, webFrame, webUtils } from 'electron'

import type { DesktopProfileRoute } from './desktop-profile'
import { customWindowControlsEnabled } from './window-controls'

// Which translucency the OS can back. Asked synchronously because the renderer
// needs it before its first paint, and answered by main because deciding it
// needs `os.release()` — a sandboxed preload may only require electron, events,
// timers and url, so importing node:os here throws before contextBridge runs
// and takes the ENTIRE bridge down with it (window.anakotDesktop undefined =>
// "Desktop IPC bridge is unavailable"). No reply means no glass, which degrades
// to an ordinary opaque window rather than a page thinned over nothing.
const translucencySupport = ipcRenderer.sendSync('anakot:translucency:support')
const hudWindowing = ipcRenderer.sendSync('anakot:hud:windowing')
const hudNativeDrag = hudWindowing?.nativeDrag === true
const launchFlags = ipcRenderer.sendSync('anakot:launch-flags')

contextBridge.exposeInMainWorld('anakotDesktop', {
  glassSupported: translucencySupport?.glass === true,
  translucencySupported: translucencySupport?.translucency === true,
  // Launch-flag fact: the app was started with --local, so the renderer may
  // show the local-models surfaces. Static for the window's lifetime.
  localModelsEnabled: launchFlags?.localModels === true,
  // Launch-flag fact: the Nous free tier is on for this launch
  // (ANAKOT_GUEST_ONBOARDING=1 or --guest-onboarding). Read-only; the same
  // decision is stamped onto every backend the app spawns.
  guestOnboardingEnabled: launchFlags?.guestOnboarding === true,
  // Launch-flag fact: skip the first-run film (ANAKOT_SKIP_INTRO=1 or
  // --skip-intro). Rehearsal aid for the guided chat behind it.
  skipIntro: launchFlags?.skipIntro === true,
  getConnection: (profile, opts) => ipcRenderer.invoke('anakot:connection', profile, opts),
  // Registry-scoped backend resolution: { connectionId, profile } → descriptor.
  getConnectionFor: payload => ipcRenderer.invoke('anakot:connection:for', payload),
  getProfileRoutes: profiles => ipcRenderer.invoke('anakot:plugin-profile-routes', profiles),
  revalidateConnection: () => ipcRenderer.invoke('anakot:connection:revalidate'),
  touchBackend: (profile, options) => ipcRenderer.invoke('anakot:backend:touch', profile, options),
  getPoolLimits: () => ipcRenderer.invoke('anakot:pool-limits:get'),
  setPoolLimits: limits => ipcRenderer.invoke('anakot:pool-limits:set', limits),
  getGatewayWsUrl: profile => ipcRenderer.invoke('anakot:gateway:ws-url', profile),
  // Registry-scoped fresh WS URL: { connectionId, profile } → result shape of
  // getGatewayWsUrl, minted against that connection's backend.
  getGatewayWsUrlFor: payload => ipcRenderer.invoke('anakot:gateway:ws-url-for', payload),
  // Union agent roster across every registered connection.
  getAgentRoster: () => ipcRenderer.invoke('anakot:agents:roster'),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('anakot:window:openSession', sessionId, opts),
  openSessionInTerminal: (sessionId, opts) => ipcRenderer.invoke('anakot:window:openInTerminal', sessionId, opts),
  openWindow: (options?: DesktopProfileRoute) => ipcRenderer.invoke('anakot:window:openInstance', options),
  openBrowserWindow: tabId => ipcRenderer.invoke('anakot:window:openBrowser', tabId),
  onBrowserPopoutClosed: callback => {
    const listener = (_event, tabId) => callback(tabId)
    ipcRenderer.on('anakot:browser-popout:closed', listener)

    return () => ipcRenderer.removeListener('anakot:browser-popout:closed', listener)
  },
  claimAmbientCue: key => ipcRenderer.invoke('anakot:ambient:claim', key),
  windowControls: {
    custom: customWindowControlsEnabled(),
    minimize: () => ipcRenderer.send('anakot:window-control', 'minimize'),
    toggleMaximize: () => ipcRenderer.send('anakot:window-control', 'toggle-maximize'),
    close: () => ipcRenderer.send('anakot:window-control', 'close')
  },
  wakeIndicator: {
    getState: () => ipcRenderer.invoke('anakot:wake-indicator:get'),
    setState: state => ipcRenderer.send('anakot:wake-indicator:set', state),
    onState: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('anakot:wake-indicator:state', listener)

      return () => ipcRenderer.removeListener('anakot:wake-indicator:state', listener)
    }
  },
  chatOnboarding: {
    grow: request => ipcRenderer.send('anakot:chat-onboarding:grow', request),
    soloBoot: () => ipcRenderer.send('anakot:chat-onboarding:solo-boot')
  },
  introReveal: {
    open: (payload?: { hideMain?: boolean }) => ipcRenderer.invoke('anakot:intro-reveal:open', payload),
    close: (payload?: { showMain?: boolean }) => ipcRenderer.invoke('anakot:intro-reveal:close', payload),
    skip: () => ipcRenderer.send('anakot:intro-reveal:skip'),
    ready: () => ipcRenderer.send('anakot:intro-reveal:ready'),
    onSkip: callback => {
      const listener = () => callback()

      ipcRenderer.on('anakot:intro-reveal:skip', listener)

      return () => ipcRenderer.removeListener('anakot:intro-reveal:skip', listener)
    },
    onClosed: callback => {
      const listener = () => callback()

      ipcRenderer.on('anakot:intro-reveal:closed', listener)

      return () => ipcRenderer.removeListener('anakot:intro-reveal:closed', listener)
    }
  },
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('anakot:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('anakot:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('anakot:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('anakot:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('anakot:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('anakot:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('anakot:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:pet-overlay:state', listener)

      return () => ipcRenderer.removeListener('anakot:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:pet-overlay:control', listener)

      return () => ipcRenderer.removeListener('anakot:pet-overlay:control', listener)
    }
  },
  // HUD mode: the chrome-free floating chat. A full app renderer (own gateway)
  // sized as a floating bar, so it mounts the real composer. Main owns the
  // window; `onChanged` keeps every window's toggle truthful.
  hud: {
    nativeDrag: hudNativeDrag,
    windowing: {
      clientPlacement: hudWindowing?.clientPlacement !== false,
      controlDrag: hudWindowing?.controlDrag === true,
      nativeDrag: hudNativeDrag,
      solid: hudWindowing?.solid === true,
      workspaceTransfer: hudWindowing?.workspaceTransfer === true
    },
    open: request => ipcRenderer.invoke('anakot:hud:open', request),
    close: () => ipcRenderer.invoke('anakot:hud:close'),
    setIgnoreMouse: ignore => ipcRenderer.send('anakot:hud:ignore-mouse', ignore),
    beginMove: () => ipcRenderer.send('anakot:hud:begin-move'),
    endMove: () => ipcRenderer.send('anakot:hud:end-move'),
    moveBy: delta => ipcRenderer.send('anakot:hud:move-by', delta),
    setWorkspaceTransfer: transferring => ipcRenderer.send('anakot:hud:workspace-transfer', transferring),
    setBounds: bounds => ipcRenderer.send('anakot:hud:set-bounds', bounds),
    resetLayout: () => ipcRenderer.invoke('anakot:hud:reset-layout'),
    // Whether the band covers the window below the bar. Main pairs it with the
    // user's translucency setting to decide the native frost (macOS vibrancy /
    // Windows 11 DWM backdrop) — see hudFrostFor.
    setFrost: showing => ipcRenderer.invoke('anakot:hud:frost', showing),
    // The HUD tells main which session it is on; main hands that back to the
    // app window when the HUD closes, so the app can re-home onto it.
    setSession: sessionId => ipcRenderer.send('anakot:hud:session', sessionId),
    onGoto: callback => {
      const listener = (_event, sessionId) => callback(sessionId)
      ipcRenderer.on('anakot:hud:goto', listener)

      return () => ipcRenderer.removeListener('anakot:hud:goto', listener)
    },
    onChanged: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('anakot:hud:changed', listener)

      return () => ipcRenderer.removeListener('anakot:hud:changed', listener)
    },
    // Linux only, and silent elsewhere: where the cursor is, in page
    // coordinates, or null when it has left the window. Stands in for the
    // mousemove that `setIgnoreMouseEvents(true, { forward: true })` delivers on
    // macOS and Windows but not here.
    onCursor: callback => {
      const listener = (_event, point) => callback(point)
      ipcRenderer.on('anakot:hud:cursor', listener)

      return () => ipcRenderer.removeListener('anakot:hud:cursor', listener)
    },
    // Main's game-overlay watch: whether a fullscreen app (a game) is under
    // the HUD, so the renderer can step back to the low-opacity overlay
    // treatment while one owns the screen.
    onGameOverlay: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('anakot:hud:game-overlay', listener)

      return () => ipcRenderer.removeListener('anakot:hud:game-overlay', listener)
    }
  },
  // macOS native screenshot gesture; captures require a main-issued request.
  screenshot: process.platform === 'darwin' ? {
    getSettings: () => ipcRenderer.invoke('anakot:screenshot:settings:get'),
    setEnabled: enabled => ipcRenderer.invoke('anakot:screenshot:settings:set', enabled),
    openPermissionSettings: kind => ipcRenderer.invoke('anakot:screenshot:permission', kind),
    capture: requestId => ipcRenderer.invoke('anakot:screenshot:capture', requestId),
    onStatus: callback => {
      const listener = (_event, status) => callback(status)
      ipcRenderer.on('anakot:screenshot:status', listener)

      return () => ipcRenderer.removeListener('anakot:screenshot:status', listener)
    },
    onRequest: callback => {
      const channel = 'anakot:screenshot:request'
      const listener = (_event, requestId) => callback(requestId)

      if (ipcRenderer.listenerCount(channel) === 0) {
        ipcRenderer.send('anakot:screenshot:subscribe', true)
      }

      ipcRenderer.on(channel, listener)

      return () => {
        ipcRenderer.removeListener(channel, listener)

        if (ipcRenderer.listenerCount(channel) === 0) {
          ipcRenderer.send('anakot:screenshot:subscribe', false)
        }
      }
    }
  } : undefined,
  // Quick Entry: the global-hotkey mini composer window. Main owns the OS
  // shortcut + the persisted preference; the quick window only captures text
  // and hands it back, and the primary renderer submits it through the normal
  // prompt path.
  quickEntry: {
    getSettings: () => ipcRenderer.invoke('anakot:quick-entry:settings:get'),
    setSettings: patch => ipcRenderer.invoke('anakot:quick-entry:settings:set', patch),
    submit: payload => ipcRenderer.send('anakot:quick-entry:submit', payload),
    dismiss: () => ipcRenderer.send('anakot:quick-entry:dismiss'),
    // Primary renderer → main → quick window: gateway connection state + the
    // recent-session options the target picker offers. Main caches the latest
    // payload so a freshly spawned quick window starts from truth.
    pushState: payload => ipcRenderer.send('anakot:quick-entry:state', payload),
    // Quick window subscribes to those pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:quick-entry:state', listener)

      return () => ipcRenderer.removeListener('anakot:quick-entry:state', listener)
    },
    // Main → primary renderer: a submit captured by the quick window.
    onSubmit: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:quick-entry:submit', listener)

      return () => ipcRenderer.removeListener('anakot:quick-entry:submit', listener)
    },
    // Main → quick window: you were just summoned (reset draft + refocus).
    onShown: callback => {
      const listener = () => callback()
      ipcRenderer.on('anakot:quick-entry:shown', listener)

      return () => ipcRenderer.removeListener('anakot:quick-entry:shown', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('anakot:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('anakot:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('anakot:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('anakot:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('anakot:connection-config:test', payload),
  // Opt-in OS-keychain encryption for stored gateway secrets (default off —
  // see secret-storage-policy.ts). get never touches the OS keychain.
  getSecretStorageEncryption: () => ipcRenderer.invoke('anakot:secret-storage:get'),
  setSecretStorageEncryption: (on: boolean) => ipcRenderer.invoke('anakot:secret-storage:set', on),
  // v2 multi-connection registry: named agent sources (local / remote / cloud / ssh).
  connections: {
    list: () => ipcRenderer.invoke('anakot:connections:list'),
    save: payload => ipcRenderer.invoke('anakot:connections:save', payload),
    remove: id => ipcRenderer.invoke('anakot:connections:remove', id),
    setPrimary: id => ipcRenderer.invoke('anakot:connections:set-primary', id),
    setLaunchMode: mode => ipcRenderer.invoke('anakot:connections:set-launch-mode', mode),
    setLastUsed: id => ipcRenderer.invoke('anakot:connections:set-last-used', id),
    test: id => ipcRenderer.invoke('anakot:connections:test', id),
    updateManaged: id => ipcRenderer.invoke('anakot:connections:update-managed', id),
    // Fan out `anakot update` to every eligible registered connection.
    // Optional excludeIds skips rows the caller updates through another path.
    updateAll: options => ipcRenderer.invoke('anakot:connections:update-all', options),
    // Registry lifecycle push (main → renderer): a connection was removed or
    // materially edited, so secondaries scoped to it must be disposed (and,
    // for edits, re-dialed at the new target).
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:connections:changed', listener)

      return () => ipcRenderer.removeListener('anakot:connections:changed', listener)
    }
  },
  sshConfigHosts: () => ipcRenderer.invoke('anakot:ssh-config:hosts'),
  sshResolveHost: host => ipcRenderer.invoke('anakot:ssh-config:resolve', host),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('anakot:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('anakot:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('anakot:connection-config:oauth-logout', remoteUrl),
  // Anakot Cloud: one portal login powers discovery + silent per-agent sign-in
  // (cloud-auto-discovery Phase 3).
  cloud: {
    status: () => ipcRenderer.invoke('anakot:cloud:status'),
    login: () => ipcRenderer.invoke('anakot:cloud:login'),
    logout: () => ipcRenderer.invoke('anakot:cloud:logout'),
    discover: org => ipcRenderer.invoke('anakot:cloud:discover', org),
    agentSignIn: dashboardUrl => ipcRenderer.invoke('anakot:cloud:agent-sign-in', dashboardUrl)
  },
  profile: {
    getDefault: () => ipcRenderer.invoke('anakot:profile:default:get'),
    setDefault: (route: DesktopProfileRoute) => ipcRenderer.invoke('anakot:profile:default:set', route),
    onDefaultChanged: (callback: (route: DesktopProfileRoute | null) => void) => {
      const listener = (_event: Electron.IpcRendererEvent, route: DesktopProfileRoute | null) => callback(route)
      ipcRenderer.on('anakot:profile:default:changed', listener)

      return () => ipcRenderer.removeListener('anakot:profile:default:changed', listener)
    },
    get: () => ipcRenderer.invoke('anakot:profile:get'),
    remember: name => ipcRenderer.invoke('anakot:profile:remember', name),
    set: name => ipcRenderer.invoke('anakot:profile:set', name)
  },
  api: request => ipcRenderer.invoke('anakot:api', request),
  notify: payload => ipcRenderer.invoke('anakot:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('anakot:requestMicrophoneAccess'),
  readWindowBelow: () => ipcRenderer.invoke('anakot:window:readBelow'),
  readFileDataUrl: filePath => ipcRenderer.invoke('anakot:readFileDataUrl', filePath),
  readFileDataUrlForAttach: filePath => ipcRenderer.invoke('anakot:readFileDataUrlForAttach', filePath),
  dataUrlReadMax: {
    get: () => ipcRenderer.invoke('anakot:data-url-read-max:get'),
    set: maxMb => ipcRenderer.invoke('anakot:data-url-read-max:set', maxMb)
  },
  readFileText: filePath => ipcRenderer.invoke('anakot:readFileText', filePath),
  readPluginSource: (filePath: string) => ipcRenderer.invoke('anakot:readPluginSource', filePath),
  selectPaths: options => ipcRenderer.invoke('anakot:selectPaths', options),
  selectSavePath: options => ipcRenderer.invoke('anakot:selectSavePath', options),
  writeClipboard: text => ipcRenderer.invoke('anakot:writeClipboard', text),
  readClipboard: () => ipcRenderer.invoke('anakot:readClipboard'),
  saveGatewayFile: payload => ipcRenderer.invoke('anakot:saveGatewayFile', payload),
  saveImageFromUrl: url => ipcRenderer.invoke('anakot:saveImageFromUrl', url),
  contextMenuEdit: command => ipcRenderer.invoke('anakot:context-menu:edit', command),
  contextMenuCopyImage: () => ipcRenderer.invoke('anakot:context-menu:copy-image'),
  contextMenuSpellcheck: action => ipcRenderer.invoke('anakot:context-menu:spellcheck', action),
  contextMenuGuestAddWord: payload => ipcRenderer.invoke('anakot:context-menu:guest-add-word', payload),
  onContextMenuSpellcheck: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:context-menu-spellcheck', listener)

    return () => ipcRenderer.removeListener('anakot:context-menu-spellcheck', listener)
  },
  saveImageBuffer: (data, ext, name) => ipcRenderer.invoke('anakot:saveImageBuffer', { data, ext, name }),
  capturePreview: payload => ipcRenderer.invoke('anakot:capturePreview', payload),
  savePastedText: text => ipcRenderer.invoke('anakot:savePastedText', { text }),
  saveClipboardImage: () => ipcRenderer.invoke('anakot:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('anakot:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('anakot:watchPreviewFile', url),
  watchDirectory: dir => ipcRenderer.invoke('anakot:watchDirectory', dir),
  stopPreviewFileWatch: id => ipcRenderer.invoke('anakot:stopPreviewFileWatch', id),
  setActiveWork: payload => ipcRenderer.send('anakot:active-work', payload),
  setTitleBarTheme: payload => ipcRenderer.send('anakot:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('anakot:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('anakot:translucency', payload),
  setKeepAwake: on => ipcRenderer.send('anakot:keep-awake', on),
  setDisableF12: blocked => ipcRenderer.send('anakot:devtools:disable-f12', blocked),
  setPreviewShortcutActive: active => ipcRenderer.send('anakot:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('anakot:openExternal', url),
  mcpOauth: {
    // One-shot loopback listener for MCP OAuth against remote backends: bind
    // on this machine, hand redirectUri to mcp.servers.oauth.start, then wait
    // for the provider redirect and relay code/state via oauth.callback.
    listen: () => ipcRenderer.invoke('anakot:mcp-oauth:listen'),
    wait: (id, timeoutMs) => ipcRenderer.invoke('anakot:mcp-oauth:wait', id, timeoutMs),
    cancel: id => ipcRenderer.invoke('anakot:mcp-oauth:cancel', id)
  },
  openPreviewInBrowser: url => ipcRenderer.invoke('anakot:openPreviewInBrowser', url),
  reachPreviewUrl: url => ipcRenderer.invoke('anakot:preview:reach', url),
  setActiveConnectionRoute: route => ipcRenderer.send('anakot:connection:active-route', route),
  fetchLinkTitle: url => ipcRenderer.invoke('anakot:fetchLinkTitle', url),
  resolveFavicon: url => ipcRenderer.invoke('anakot:resolveFavicon', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('anakot:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('anakot:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('anakot:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('anakot:setting:defaultProjectDir:pick')
  },
  zoom: {
    // Current zoom of this window, as { level, percent }.
    get: () => ipcRenderer.invoke('anakot:zoom:get'),
    // Synchronous zoom factor (1 = 100%). Coordinate math needs it in the
    // same tick as the event it converts, so no IPC round-trip here.
    factor: () => webFrame.getZoomFactor(),
    setPercent: percent => ipcRenderer.send('anakot:zoom:set-percent', percent),
    // Fires on every zoom change, including the Ctrl/Cmd +/-/0 shortcuts,
    // so the settings UI can stay in sync with the keyboard.
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:zoom:changed', listener)

      return () => ipcRenderer.removeListener('anakot:zoom:changed', listener)
    }
  },
  revealLogs: () => ipcRenderer.invoke('anakot:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('anakot:logs:recent'),
  // Fire-and-forget: persists a renderer error-boundary catch (with component
  // stack) to desktop.log so crashes survive the window (#79428).
  reportRendererError: report => ipcRenderer.send('anakot:logs:renderer-error', report),
  readDir: dirPath => ipcRenderer.invoke('anakot:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('anakot:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('anakot:fs:reveal', targetPath),
  openDir: dirPath => ipcRenderer.invoke('anakot:fs:openDir', dirPath),
  desktopPluginsRoot: () => ipcRenderer.invoke('anakot:fs:desktopPluginsRoot'),
  reconcileDesktopPlugins: () => ipcRenderer.invoke('anakot:fs:reconcileDesktopPlugins'),
  logsRoot: () => ipcRenderer.invoke('anakot:fs:logsRoot'),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('anakot:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('anakot:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('anakot:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('anakot:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('anakot:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('anakot:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('anakot:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('anakot:git:branchList', repoPath),
    baseBranchList: repoPath => ipcRenderer.invoke('anakot:git:baseBranchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('anakot:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('anakot:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('anakot:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('anakot:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('anakot:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('anakot:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('anakot:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('anakot:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('anakot:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('anakot:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('anakot:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('anakot:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('anakot:git:review:shipInfo', repoPath),
      prList: (repoPath, branches, numbers) =>
        ipcRenderer.invoke('anakot:git:review:prList', repoPath, branches, numbers),
      createPr: repoPath => ipcRenderer.invoke('anakot:git:review:createPr', repoPath)
    }
  },
  terminal: {
    attach: id => ipcRenderer.invoke('anakot:terminal:attach', id),
    cwd: id => ipcRenderer.invoke('anakot:terminal:cwd', id),
    dispose: id => ipcRenderer.invoke('anakot:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('anakot:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('anakot:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('anakot:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `anakot:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `anakot:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('anakot:close-preview-requested', listener)

    return () => ipcRenderer.removeListener('anakot:close-preview-requested', listener)
  },
  onPreviewNav: callback => {
    const listener = (_event, command) => callback(command)
    ipcRenderer.on('anakot:preview-nav', listener)

    return () => ipcRenderer.removeListener('anakot:preview-nav', listener)
  },
  onOpenFolderRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('anakot:open-folder-requested', listener)

    return () => ipcRenderer.removeListener('anakot:open-folder-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('anakot:open-updates', listener)

    return () => ipcRenderer.removeListener('anakot:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:deep-link', listener)

    return () => ipcRenderer.removeListener('anakot:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('anakot:deep-link-ready'),
  probePluginRepo: payload => ipcRenderer.invoke('anakot:plugin:probe', payload),
  installDesktopPlugin: payload => ipcRenderer.invoke('anakot:plugin:installDesktop', payload),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:window-state-changed', listener)

    return () => ipcRenderer.removeListener('anakot:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('anakot:focus-session', listener)

    return () => ipcRenderer.removeListener('anakot:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:notification-action', listener)

    return () => ipcRenderer.removeListener('anakot:notification-action', listener)
  },
  onNotificationActivate: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:notification-activate', listener)

    return () => ipcRenderer.removeListener('anakot:notification-activate', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:preview-file-changed', listener)

    return () => ipcRenderer.removeListener('anakot:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:backend-exit', listener)

    return () => ipcRenderer.removeListener('anakot:backend-exit', listener)
  },
  // Cooperative pool retirement (main → renderer): the pooled backend under
  // `poolKey` is being stopped for a foreground open. Park that scope; do not
  // redial into the slot it vacated.
  onPoolBackendRetiring: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:pool:retiring', listener)

    return () => ipcRenderer.removeListener('anakot:pool:retiring', listener)
  },
  // Soft gateway-mode apply finished tearing down the primary backend. Renderer
  // should wipe session lists + re-dial without a window reload.
  onConnectionApplied: callback => {
    const listener = () => callback()
    ipcRenderer.on('anakot:connection:applied', listener)

    return () => ipcRenderer.removeListener('anakot:connection:applied', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('anakot:power-resume', listener)

    return () => ipcRenderer.removeListener('anakot:power-resume', listener)
  },
  // AC ↔ battery transitions; renderers slow their backstop polls on battery.
  getOnBattery: () => ipcRenderer.invoke('anakot:power-battery:get'),
  onBatteryChanged: callback => {
    const listener = (_event, onBattery) => callback(Boolean(onBattery))
    ipcRenderer.on('anakot:power-battery', listener)

    return () => ipcRenderer.removeListener('anakot:power-battery', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:boot-progress', listener)

    return () => ipcRenderer.removeListener('anakot:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.ts (apps/desktop/electron/bootstrap-runner.ts).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('anakot:bootstrap:get'),
  continueBootstrapLocal: () => ipcRenderer.invoke('anakot:bootstrap:continue-local'),
  recycleBackend: profile => ipcRenderer.invoke('anakot:backend:recycle', profile),
  resetBootstrap: () => ipcRenderer.invoke('anakot:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('anakot:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('anakot:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('anakot:bootstrap:event', listener)

    return () => ipcRenderer.removeListener('anakot:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('anakot:version'),
  relaunchApp: () => ipcRenderer.invoke('anakot:app:relaunch'),
  getMachineProfile: () => ipcRenderer.invoke('anakot:machine:profile'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('anakot:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('anakot:uninstall:summary'),
    run: mode => ipcRenderer.invoke('anakot:uninstall:run', { mode })
  },
  updates: {
    check: opts => ipcRenderer.invoke('anakot:updates:check', opts),
    apply: opts => ipcRenderer.invoke('anakot:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('anakot:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('anakot:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('anakot:updates:progress', listener)

      return () => ipcRenderer.removeListener('anakot:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('anakot:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('anakot:vscode-theme:search', query)
  },
  // Find-in-page (Ctrl/Cmd+F): delegates to Electron's
  // webContents.findInPage on the IPC sender's window so a Cmd+F pressed
  // in a secondary session window searches THAT window, not the primary.
  // `onFoundInPage` returns the unsubscribe fn; the renderer wires it via
  // `initFindInPageListener` in store/find-in-page.ts and tears it down
  // when the FindBar unmounts.
  findInPage: (query, options) => ipcRenderer.invoke('anakot:find-in-page', query, options),
  stopFindInPage: () => ipcRenderer.invoke('anakot:stop-find-in-page'),
  onFoundInPage: callback => {
    const listener = (_event, result) => callback(result)
    ipcRenderer.on('anakot:found-in-page', listener)

    return () => ipcRenderer.removeListener('anakot:found-in-page', listener)
  },
  // Main-process `before-input-event` forwards Ctrl/Cmd+F here so renderer
  // can open the FindBar even when the GTK compositor has already grabbed
  // the chord at the windowing layer (#81727).
  onOpenFindBarRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('anakot:open-find-bar', listener)

    return () => ipcRenderer.removeListener('anakot:open-find-bar', listener)
  }
})

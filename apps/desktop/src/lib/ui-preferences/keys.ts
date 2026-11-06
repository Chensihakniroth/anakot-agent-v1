/**
 * Which persisted keys are machine-level UI preferences (#145213).
 *
 * Only these leave localStorage for the machine's shared store, so native
 * Desktop and every browser that opens this machine's Webapp show the same
 * choices. Scoped families keep their scope inside the key name (a
 * `….profile.<name>` or per-connection suffix): only the location changes.
 *
 * Deliberately NOT here (they stay in this browser/window):
 * - credentials, grants and connection config: gateway registry, custom model
 *   endpoints, plugin decisions and preview-script grants, embed permissions;
 * - per-window or per-device runtime state: layout tree, open tiles and tabs,
 *   last route/session, scroll, zoom, pet and popout geometry, keep-awake;
 * - drafts, queues, journals and caches: composer queue, in-flight turns,
 *   pending/prepared submissions, previews, pricing, backend skin cache, the
 *   "provider configured" onboarding cache (each backend answers that itself);
 * - one-off notices: butterbar, update and real-profile prompts.
 */

const SHARED_KEYS: ReadonlySet<string> = new Set([
  // Appearance.
  'anakot-desktop-theme-v2',
  'anakot-desktop-mode-v1',
  'anakot-desktop-profile-themes-v1',
  'anakot-desktop-profile-modes-v1',
  'anakot-desktop-user-themes-v1',
  'anakot.desktop.backdrop.v1',
  'anakot.desktop.chat-text-scale.v1',
  'anakot.desktop.interfaceMode.v1',
  'anakot.desktop.textDirection',
  'anakot.desktop.translucency.v2',
  'anakot.desktop.user-bubble-transparency.v1',
  // Sessions sidebar and profile rail.
  'anakot.desktop.agentsGroupedByWorkspace',
  'anakot.desktop.profileColors',
  'anakot.desktop.profileOrder',
  'anakot.desktop.profileRailVisible',
  'anakot.desktop.sessionListDensity',
  'anakot.desktop.sessionOrder',
  'anakot.desktop.sessionOrder.manual',
  'anakot.desktop.showAllProfiles',
  'anakot.desktop.sidebarAgentsGrouped.allProfiles',
  'anakot.desktop.sidebarCardRows',
  'anakot.desktop.sidebarGrouping',
  'anakot.desktop.sidebarGrouping.allProfiles',
  'anakot.desktop.sidebarRowMeta',
  'anakot.desktop.sidebarShowAllSessions',
  'anakot.desktop.sidebarShowArchived',
  'anakot.desktop.sidebarSortKey',
  // Status bar.
  'anakot.desktop.statusbarHidden.v2',
  'anakot.desktop.statusbarVisible.v2',
  // Transcript and tools.
  'anakot.desktop.hideThreadTimeline',
  'anakot.desktop.reasoning.collapsedByDefault',
  'anakot.desktop.toolView.hideCodeDiffs',
  'anakot.desktop.toolView.technical',
  // Shell, panes and behaviour.
  'anakot.desktop.alwaysExternalLinks.v1',
  'anakot.desktop.capabilities.catalogCardView',
  'anakot.desktop.composerPopout.enabled',
  'anakot.desktop.composerPopout.gesturesEnabled',
  'anakot.desktop.files.showIgnored',
  'anakot.desktop.keybinds',
  'anakot.desktop.layoutPresets.v2',
  'anakot.desktop.panesFlipped',
  'anakot.desktop.tabStripDefault',
  'anakot.desktop.titlebarAppActions',
  // Guidance: what the user already skipped, saw or dismissed does not come
  // back in every new browser or origin (#145600).
  'anakot-onboarding-skipped-v1',
  'anakot.desktop.tips.last.v1',
  'anakot.desktop.tips.next.v1',
  'anakot.desktop.tips.retired.v1',
  'anakot.desktop.tips.rotation.v1',
  'anakot.desktop.tips.shownAt.v1',
  'anakot.desktop.tours.v1',
  // Sound and media.
  'anakot.desktop.autoSpeakReplies',
  'anakot.desktop.completionSoundVariantId',
  'anakot.desktop.hapticsMuted',
  'anakot.desktop.videoPlaybackSpeed',
  // Model picker.
  'anakot.desktop.collapsed-providers',
  'anakot.desktop.favorite-models',
  // visible-models is a diff against known-models: they only make sense together.
  'anakot.desktop.known-models',
  'anakot.desktop.model-presets',
  'anakot.desktop.visible-models'
])

/** Families whose scope rides in the key suffix (gateway aliases/order/collapsed). */
const SHARED_PREFIXES: readonly string[] = ['anakot.desktop.sidebar.gatewayGroups.v1.']

export function isSharedPreferenceKey(key: string): boolean {
  return SHARED_KEYS.has(key) || SHARED_PREFIXES.some(prefix => key.startsWith(prefix))
}

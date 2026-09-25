import { type PluginLocaleBundles, type PluginTranslate, usePluginI18n } from '@anakot/plugin-sdk'
import { useMemo } from 'react'

const en = {
  apply: 'Apply',
  close: 'Close probe',
  current: 'Current',
  description: (count: number) => `Browse ${count} free models from providers already connected to this profile.`,
  empty: 'No free models found',
  emptyHelp: 'Connect a provider in Settings, then refresh this page.',
  failed: 'Free model probe failed',
  footer: 'A probe is stateless: it creates no session, runs no tools, and never changes your default model.',
  loading: 'Loading free models…',
  noResults: 'No free models match your search',
  open: 'Free Models: Open',
  probe: 'Test model',
  prompt: 'In one sentence, what is 2+2?',
  reasoning: 'Reasoning',
  refresh: 'Refresh catalog',
  run: 'Run test',
  running: 'Testing…',
  search: 'Search models or providers…',
  switchFailed: 'Could not apply the model',
  switched: 'Default model updated',
  title: 'Free Model Suite',
  toolCalls: (count: number) => `${count} unrequested tool call${count === 1 ? '' : 's'}`,
  truncated: 'The reply reached the token limit and may be incomplete.',
  filtered: 'The provider filtered the reply.',
  emptyReply: 'The model returned no visible answer.',
  reasoningOnly: 'The model used the whole budget for reasoning and returned no visible answer.'
}

type Messages = typeof en

function bind(t: PluginTranslate): Messages {
  return {
    ...en,
    description: (count: number) => t('description', count),
    toolCalls: (count: number) => t('toolCalls', count)
  }
}

export function useFreeModels(): Messages {
  const t = usePluginI18n('free-model-suite')

  return useMemo(() => bind(t), [t])
}

const ja = {
  ...en,
  apply: '適用',
  applying: '適用中…',
  close: '閉じる',
  current: '現在',
  description: (count: number) => `このプロファイルに接続済みのプロバイダーから無料モデル ${count} 件を表示します。`,
  empty: '無料モデルが見つかりません',
  emptyHelp: '設定でプロバイダーを接続してから、このページを更新してください。',
  failed: '無料モデルのテストに失敗しました',
  noResults: '検索条件に一致する無料モデルはありません',
  open: '無料モデル: 開く',
  probe: 'モデルをテスト',
  probeApply: 'テスト後に適用',
  reply: '返信',
  run: 'テスト',
  running: 'テスト中…',
  search: 'モデルまたはプロバイダーを検索…',
  switchFailed: 'モデルを適用できませんでした',
  switched: '既定モデルを更新しました',
  test: 'テスト',
  title: '無料モデルスイート',
  truncated: 'トークン上限に達したため、返信が不完全な可能性があります。'
}

const zh = {
  ...en,
  apply: '应用',
  applying: '应用中…',
  close: '关闭',
  current: '当前',
  description: (count: number) => `浏览此配置文件中已连接提供商提供的 ${count} 个免费模型。`,
  empty: '未找到免费模型',
  emptyHelp: '请先在设置中连接提供商，然后刷新此页面。',
  failed: '免费模型测试失败',
  noResults: '没有免费模型符合搜索条件',
  open: '免费模型：打开',
  probe: '测试模型',
  probeApply: '测试后应用',
  reply: '回复',
  run: '测试',
  running: '测试中…',
  search: '搜索模型或提供商…',
  switchFailed: '无法应用模型',
  switched: '默认模型已更新',
  test: '测试',
  title: '免费模型套件',
  truncated: '回复达到令牌上限，可能不完整。'
}

const zhHant = {
  ...zh,
  apply: '套用',
  applying: '套用中…',
  close: '關閉',
  current: '目前',
  description: (count: number) => `瀏覽此設定檔中已連線供應商提供的 ${count} 個免費模型。`,
  empty: '找不到免費模型',
  emptyHelp: '請先在設定中連線供應商，再重新整理此頁面。',
  failed: '免費模型測試失敗',
  noResults: '沒有免費模型符合搜尋條件',
  open: '免費模型：開啟',
  search: '搜尋模型或供應商…',
  switchFailed: '無法套用模型',
  switched: '預設模型已更新',
  test: '測試',
  title: '免費模型套件',
  truncated: '回覆已達權杖上限，可能不完整。'
}

export const FREE_MODEL_SUITE_LOCALES: PluginLocaleBundles = {
  en,
  ja,
  zh,
  'zh-hant': zhHant
}

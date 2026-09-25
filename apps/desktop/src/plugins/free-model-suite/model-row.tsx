import { icons } from '@anakot/plugin-sdk'
import { useMemo, useRef, useState } from 'react'

const { AlertTriangle, Brain, Play, Wrench, X, Zap } = icons

import { probeModel } from './api'
import { useFreeModels } from './i18n'
import type { ModelOptionProvider, ModelProbeResult } from './types'

function issuesFor(result: ModelProbeResult, copy: ReturnType<typeof useFreeModels>): string[] {
  const hasContent = Boolean(result.content.trim())
  const hasReasoning = Boolean(result.reasoning.trim())
  const issues: string[] = []

  if (!hasContent && !hasReasoning) {
    issues.push(
      result.tool_calls.length ? '' : result.finish_reason === 'content_filter' ? copy.filtered : copy.emptyReply
    )
  } else if (!hasContent && hasReasoning) {
    issues.push(copy.reasoningOnly)
  } else if (result.finish_reason === 'length') {
    issues.push(copy.truncated)
  } else if (result.finish_reason === 'content_filter') {
    issues.push(copy.filtered)
  }

  return issues.filter(Boolean)
}

function Probe({ model, provider }: { model: string; provider: ModelOptionProvider }) {
  const copy = useFreeModels()
  const [open, setOpen] = useState(false)
  const [prompt, setPrompt] = useState(copy.prompt)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ModelProbeResult | null>(null)
  const promptRef = useRef<HTMLTextAreaElement>(null)

  const run = async () => {
    const value = prompt.trim()

    if (!value || busy) {
      return
    }

    setBusy(true)
    setError('')
    setResult(null)

    try {
      setResult(await probeModel({ max_tokens: 1024, model, prompt: value, provider: provider.slug, timeout_s: 30 }))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button
        className="inline-flex items-center gap-1 text-[0.65rem] text-(--ui-text-tertiary) hover:text-foreground"
        onClick={() => {
          setOpen(true)
          requestAnimationFrame(() => promptRef.current?.focus())
        }}
        type="button"
      >
        <Zap className="size-3" />
        {copy.probe}
      </button>
    )
  }

  return (
    <div className="mt-2 grid gap-2 border-t border-(--ui-stroke-secondary)/30 pt-2">
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1 text-[0.65rem] font-semibold text-(--ui-text-secondary)">
          <Zap className="size-3" />
          {copy.probe}
        </span>
        <button
          aria-label={copy.close}
          className="text-(--ui-text-tertiary) hover:text-foreground"
          onClick={() => {
            setOpen(false)
            setResult(null)
            setError('')
          }}
          type="button"
        >
          <X className="size-3" />
        </button>
      </div>
      <textarea
        className="min-h-14 resize-y rounded-[3px] bg-(--ui-bg-quaternary) px-2 py-1.5 font-mono text-[0.7rem] text-foreground outline-none focus:ring-1 focus:ring-ring"
        maxLength={1000}
        onChange={event => setPrompt(event.target.value)}
        ref={promptRef}
        rows={2}
        value={prompt}
      />
      <button
        className="inline-flex w-fit items-center gap-1 text-xs font-semibold text-foreground underline-offset-4 hover:underline disabled:opacity-50"
        disabled={busy || !prompt.trim()}
        onClick={() => void run()}
        type="button"
      >
        <Play className="size-3" />
        {busy ? copy.running : copy.run}
      </button>
      {error && <p className="text-[0.65rem] text-destructive">{error}</p>}
      {result && <ProbeResult result={result} />}
    </div>
  )
}

function ProbeResult({ result }: { result: ModelProbeResult }) {
  const copy = useFreeModels()
  const issues = useMemo(() => issuesFor(result, copy), [copy, result])

  return (
    <div className="grid gap-2">
      {issues.length > 0 && (
        <ul className="grid gap-1 rounded-[3px] border border-amber-500/30 bg-amber-500/10 px-2 py-1.5 text-[0.65rem] text-amber-700 dark:text-amber-300">
          {issues.map(issue => (
            <li className="flex items-start gap-1" key={issue}>
              <AlertTriangle className="mt-0.5 size-3 shrink-0" />
              {issue}
            </li>
          ))}
        </ul>
      )}
      {result.reasoning && (
        <details className="rounded-[3px] bg-(--ui-bg-quaternary) px-2 py-1 text-[0.65rem] text-(--ui-text-tertiary)">
          <summary className="flex cursor-pointer items-center gap-1 font-semibold">
            <Brain className="size-3" />
            {copy.reasoning}
          </summary>
          <p className="mt-1 whitespace-pre-wrap break-words font-mono">{result.reasoning}</p>
        </details>
      )}
      {result.content && (
        <div className="rounded-[3px] bg-(--ui-bg-quaternary) px-2 py-1.5 text-[0.7rem] leading-relaxed whitespace-pre-wrap break-words">
          {result.content}
        </div>
      )}
      {result.tool_calls.length > 0 && (
        <details className="rounded-[3px] bg-(--ui-bg-quaternary) px-2 py-1 text-[0.65rem] text-(--ui-text-tertiary)">
          <summary className="flex cursor-pointer items-center gap-1 font-semibold text-amber-600">
            <Wrench className="size-3" />
            {copy.toolCalls(result.tool_calls.length)}
          </summary>
          <pre className="mt-1 overflow-auto whitespace-pre-wrap break-words font-mono">
            {result.tool_calls.map(call => `${call.name} ${call.arguments}`).join('\n')}
          </pre>
        </details>
      )}
    </div>
  )
}

export function ModelRow({
  current,
  model,
  onApply,
  provider
}: {
  current: boolean
  model: string
  onApply: (provider: ModelOptionProvider, model: string) => void
  provider: ModelOptionProvider
}) {
  const copy = useFreeModels()
  const capabilities = provider.capabilities?.[model]

  return (
    <article
      className={`rounded-[5px] border px-3 py-2.5 transition-colors ${
        current
          ? 'border-(--ui-accent)/50 bg-(--ui-accent)/8'
          : 'border-(--ui-stroke-secondary)/35 bg-(--ui-bg-secondary)/45 hover:bg-(--chrome-action-hover)'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="grid min-w-0 flex-1 gap-0.5">
          <span className="truncate font-mono text-xs text-(--ui-text-primary)">{model}</span>
          <span className="text-[0.62rem] text-(--ui-text-tertiary)">
            {capabilities?.reasoning ? 'Reasoning model' : 'Text model'}
            {capabilities?.fast ? ' · Fast routing' : ''}
          </span>
        </div>
        {current && (
          <span className="rounded-[3px] bg-(--ui-accent) px-1.5 py-0.5 text-[0.6rem] font-semibold text-(--ui-accent-contrast)">
            {copy.current}
          </span>
        )}
        {!current && (
          <button
            className="text-xs font-semibold text-(--ui-text-secondary) underline-offset-4 hover:text-foreground hover:underline"
            onClick={() => onApply(provider, model)}
            type="button"
          >
            {copy.apply}
          </button>
        )}
      </div>
      {!current && <Probe model={model} provider={provider} />}
    </article>
  )
}

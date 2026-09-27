/** Plugin settings form (#46600, #87934).
 *
 * Every key a plugin declares in its manifest `config_schema` arrives already
 * shaped by the backend (`settings_schema`), so this component is table-driven by
 * `type` and needs no per-plugin code.
 *
 * Secrets are the one field that must NOT round-trip: the backend never sends the
 * value, only the `.env` name and whether one is set. The field therefore starts
 * blank and blank means "leave alone" — saving a form where the user only touched
 * a plain field cannot blank a token. Non-blank secret values are routed to the
 * credential writer, never to `plugins.manage settings` (which refuses them).
 */
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { useI18n } from '@/i18n'
import {
  type GatewayRequest,
  type PluginSettingField,
  saveAgentPluginSettings,
  type SecretWriter
} from '@/store/agent-plugins'

export interface PluginSettingsFormProps {
  request: GatewayRequest
  pluginKey: string
  fields: PluginSettingField[]
  profile?: null | string
  onSaved?: () => void
  writeSecret?: SecretWriter
}

const asString = (value: unknown): string => (value === null || value === undefined ? '' : String(value))

export function PluginSettingsForm({
  request,
  pluginKey,
  fields,
  profile,
  onSaved,
  writeSecret
}: PluginSettingsFormProps) {
  const p = useI18n().t.skills.plugins

  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      fields.filter(field => field.type !== 'secret').map(field => [field.key, asString(field.value ?? field.default)])
    )
  )

  const [secrets, setSecrets] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  if (fields.length === 0) {
    return <p className="text-muted-foreground text-sm">{p.settingsNone}</p>
  }

  const setValue = (key: string, value: string) => setValues(prev => ({ ...prev, [key]: value }))

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)

    try {
      const ok = await saveAgentPluginSettings(request, {
        key: pluginKey,
        profile,
        failMessage: p.settingsSaveFailed,
        values: Object.fromEntries(
          fields
            .filter(field => field.type !== 'secret')
            .map(field => [field.key, field.type === 'boolean' ? values[field.key] === 'true' : values[field.key]])
        ),
        secrets,
        writeSecret
      })

      if (ok) {
        // Secrets are write-only: drop the typed values once they are stored.
        setSecrets({})
        onSaved?.()
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-4" onSubmit={event => void onSubmit(event)}>
      {fields.map(field => (
        <div className="space-y-1" key={field.key}>
          <label className="text-sm font-medium" htmlFor={`plugin-setting-${field.key}`}>
            {field.label}
            {field.required ? <span className="text-destructive"> *</span> : null}
          </label>

          {field.type === 'boolean' ? (
            <Switch
              checked={values[field.key] === 'true'}
              id={`plugin-setting-${field.key}`}
              onCheckedChange={checked => setValue(field.key, String(checked))}
            />
          ) : field.type === 'enum' ? (
            <Select onValueChange={value => setValue(field.key, value)} value={values[field.key]}>
              <SelectTrigger id={`plugin-setting-${field.key}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(field.choices ?? []).map(choice => (
                  <SelectItem key={choice} value={choice}>
                    {choice}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : field.type === 'json' ? (
            <Textarea
              id={`plugin-setting-${field.key}`}
              onChange={event => setValue(field.key, event.target.value)}
              rows={4}
              value={values[field.key]}
            />
          ) : field.type === 'number' ? (
            <Input
              id={`plugin-setting-${field.key}`}
              onChange={event => setValue(field.key, event.target.value)}
              type="number"
              value={values[field.key]}
            />
          ) : field.type === 'secret' ? (
            <Input
              autoComplete="off"
              id={`plugin-setting-${field.key}`}
              onChange={event => setSecrets(prev => ({ ...prev, [field.env ?? field.key]: event.target.value }))}
              placeholder={field.has_value ? p.settingsSecretUnchanged : p.settingsSecretUnset}
              type="password"
              value={secrets[field.env ?? field.key] ?? ''}
            />
          ) : (
            <Input
              id={`plugin-setting-${field.key}`}
              onChange={event => setValue(field.key, event.target.value)}
              value={values[field.key]}
            />
          )}

          {field.description ? <p className="text-muted-foreground text-xs">{field.description}</p> : null}
          {field.type === 'secret' ? (
            <p className="text-muted-foreground text-xs">{p.settingsSecretHint(field.env ?? '')}</p>
          ) : null}
        </div>
      ))}

      <Button disabled={busy} type="submit">
        {busy ? p.settingsSaving : p.settingsSave}
      </Button>
    </form>
  )
}

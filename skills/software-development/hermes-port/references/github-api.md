# GitHub API Quick Reference

## Commits

```bash
# Latest N commits
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=N" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    msg = c['commit']['message'].splitlines()[0]
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {msg}\")
"

# Since date
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?since=YYYY-MM-DD&per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {c['commit']['message'].splitlines()[0]}\")
"

# Single commit (full diff)
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits/SHA" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('=== MESSAGE ===')
print(d['commit']['message'])
print()
for f in d.get('files', []):
    print(f'  {f[\"status\"]:6} {f[\"filename\"]}  (+{f.get(\"additions\",0)} -{f.get(\"deletions\",0)})')
    if f.get('patch'):
        print(f['patch'])
    print()
"
```

## Search

```bash
# By keyword in commit message
curl -s "https://api.github.com/search/commits?q=repo:NousResearch/hermes-agent+KEYWORD&per_page=20" | python3 -c "
import json, sys
for item in json.load(sys.stdin).get('items', []):
    print(f\"{item['sha'][:8]}  {item['commit']['message'].splitlines()[0]}\")
"

# By file path
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?path=FILE&per_page=10" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"{c['sha'][:8]}  {c['commit']['message'].splitlines()[0]}\")
"

# By author
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?author=USERNAME&per_page=20" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"{c['sha'][:8]}  {c['commit']['message'].splitlines()[0]}\")
"
```

## Compare

```bash
# Compare two refs (e.g., release tag vs main)
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/compare/v2026.8.31...main?per_page=1" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Ahead by: {d.get(\"ahead_by\")} commits')
print(f'Behind by: {d.get(\"behind_by\")} commits')
"
```

## Releases

```bash
# Latest release
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'{d[\"tag_name\"]}  {d[\"published_at\"]}')
print(d['body'][:500])
"

# All releases
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=10" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f'{r[\"tag_name\"]}  {r[\"published_at\"][:10]}  {r[\"name\"]}')
"
```

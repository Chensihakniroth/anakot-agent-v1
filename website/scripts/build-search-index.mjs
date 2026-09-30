#!/usr/bin/env node
// Builds static/search-index.json from the docs sources.
//
// Why a hand-rolled index instead of Algolia: the committed Algolia credentials
// are rejected by the API (403 "Invalid Application-ID or API key"), and the
// previous local plugin shipped a ~16 MB lunr bundle that every visitor
// downloaded before their first result. This emits a compact JSON instead and
// the client only fetches it the first time search is opened, so page weight is
// untouched until someone actually searches.
//
// Run: node scripts/build-search-index.mjs   (wired into prebuild.mjs)

import {readdirSync, readFileSync, writeFileSync, mkdirSync, existsSync, statSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const websiteDir = resolve(scriptDir, '..');

const DOCS_DIR = join(websiteDir, 'docs');

const OUT_FILE = join(websiteDir, 'static', 'search-index.json');

// Keeps the payload small: enough text to match on, not the whole page.
// Tuned down after a first pass shipped 1.15 MB, which is not a payload any
// visitor should pull down to type a query.
const BODY_CHARS = 480;
const MAX_HEADINGS = 8;
const HEADING_CHARS = 60;

function walk(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else if (/\.mdx?$/.test(entry)) out.push(full);
  }
  return out;
}

function frontmatter(raw) {
  const m = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return {data: {}, body: raw};
  const data = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^(\w+):\s*(.*)$/);
    if (!kv) continue;
    let v = kv[2].trim().replace(/^["']|["']$/g, '');
    if (v.startsWith('[')) v = v.replace(/^\[|\].*$/g, '');
    data[kv[1]] = v;
  }
  return {data, body: raw.slice(m[0].length)};
}

/** Flatten markdown to plain text so matches land on real words. */
function toText(md) {
  return md
    .replace(/```[\s\S]*?```/g, ' ') // fenced code
    .replace(/`[^`]*`/g, ' ') // inline code
    .replace(/<[^>]+>/g, ' ') // jsx/html
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ') // images
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // links keep their label
    .replace(/^\s{0,3}#{1,6}\s+/gm, '') // heading marks
    .replace(/^\s{0,3}>\s?/gm, '') // quotes
    .replace(/[*_~]{1,3}/g, '') // emphasis
    .replace(/^\s{0,3}[-*+]\s+/gm, '') // bullets
    .replace(/^\s{0,3}\|.*\|\s*$/gm, ' ') // table rows
    .replace(/\[.*?\]\(.*?\)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function urlFor(file) {
  let rel = relative(websiteDir, file).replace(/\\/g, '/');
  rel = rel.replace(/^docs\//, '');
  rel = rel.replace(/\.mdx?$/, '');
  rel = rel.replace(/\/index$/, '');
  if (rel.endsWith('/README')) rel = rel.replace(/\/README$/, '');
  rel = rel.replace(/^README$/, '');
  return '/' + rel;
}

const docs = [];

for (const file of walk(DOCS_DIR)) {
  const raw = readFileSync(file, 'utf8');
  const {data, body} = frontmatter(raw);
  if (data.sidebar_class_name || data.hide) continue;
  const title = (data.title || '').trim();
  const h1 = body.match(/^#\s+(.+)$/m);
  const name = title || (h1 ? h1[1].trim() : '');
  if (!name) continue;

  const headings = [...body.matchAll(/^#{2,4}\s+(.+)$/gm)]
    .map((m) => toText(m[1]).slice(0, HEADING_CHARS))
    .filter(Boolean)
    .slice(0, MAX_HEADINGS);

  const text = toText(body.replace(/^#\s+.+$/m, ''));
  docs.push({
    u: urlFor(file),
    t: name,
    h: headings,
    b: text.slice(0, BODY_CHARS).toLowerCase(),
  });
}

const payload = {v: 1, built: new Date().toISOString().slice(0, 10), docs};
mkdirSync(dirname(OUT_FILE), {recursive: true});
writeFileSync(OUT_FILE, JSON.stringify(payload));

const kb = (Buffer.byteLength(JSON.stringify(payload)) / 1024).toFixed(0);
const counts = docs.reduce((acc, d) => ((acc[d.l] = (acc[d.l] || 0) + 1), acc), {});
console.log(
  `[search-index] ${docs.length} pages ${JSON.stringify(counts)} -> static/search-index.json (${kb} KB)`
);

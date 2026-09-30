import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import styles from './styles.module.css';

interface Doc {
  u: string;
  t: string;
  h: string[];
  b: string;
}

interface Hit {
  doc: Doc;
  score: number;
  where: 'title' | 'heading' | 'body';
  snippet: string;
}

/**
 * Local documentation search.
 *
 * Replaces Algolia DocSearch, whose committed credentials the API rejects
 * (403 "Invalid Application-ID or API key"). The index is a build-time JSON of
 * every page's title, headings, and a short body excerpt. It is fetched on the
 * first open and then cached in the module, so an ordinary page view never pays
 * for it and repeat searches cost nothing.
 */

let cache: Doc[] | null = null;
let inflight: Promise<Doc[]> | null = null;

function loadIndex(path: string): Promise<Doc[]> {
  if (cache) return Promise.resolve(cache);
  if (!inflight) {
    inflight = fetch(path)
      .then((r) => {
        if (!r.ok) throw new Error(`search index ${r.status}`);
        return r.json();
      })
      .then((data: {docs: Doc[]}) => {
        cache = data.docs;
        return cache;
      })
      .catch((err) => {
        // Allow a later attempt to retry rather than caching the failure.
        inflight = null;
        throw err;
      });
  }
  return inflight;
}

const escapeHtml = (s: string) => s.replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]!));

/** Split on the query so matched runs can be marked without dangerouslySetInnerHTML. */
function Highlight({text, query}: {text: string; query: string}) {
  if (!query) return <>{text}</>;
  const i = text.toLowerCase().indexOf(query.toLowerCase());
  if (i === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark>{text.slice(i, i + query.length)}</mark>
      {text.slice(i + query.length)}
    </>
  );
}

function search(docs: Doc[], rawQuery: string): Hit[] {
  const q = rawQuery.trim().toLowerCase();
  if (!q) return [];
  const hits: Hit[] = [];
  for (const doc of docs) {
    const title = doc.t.toLowerCase();
    let score = 0;
    let where: Hit['where'] = 'body';

    if (title.startsWith(q)) score = 120;
    else if (title.includes(q)) score = 80;

    const heading = doc.h.find((h) => h.toLowerCase().includes(q));
    if (heading) {
      score = Math.max(score, 55);
      where = 'heading';
    }

    const at = doc.b.indexOf(q);
    if (at !== -1) {
      // Tighter matches rank higher; body text alone is weak evidence.
      score = Math.max(score, 12 + Math.max(0, 20 - at / 240));
    }

    if (score <= 0) continue;
    const start = at === -1 ? 0 : Math.max(0, at - 40);
    hits.push({
      doc,
      score,
      where: score >= 55 ? where : 'body',
      snippet: (at === -1 ? doc.b : doc.b.slice(start, start + 150)).trim(),
    });
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 8);
}

export default function SiteSearch(): React.JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  // The index is a single asset built from docs/ and every entry's `u` is
  // already site-root absolute, so both the fetch path and the result hrefs
  // must be built from the site root, never from a locale-relative base.
  // useBaseUrl() is locale-relative, which 404s the index and double-prefixes
  // every result link.
  const baseUrl = siteConfig.baseUrl;
  const indexPath = siteConfig.baseUrl + 'search-index.json';

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [docs, setDocs] = useState<Doc[] | null>(cache);
  const [active, setActive] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const openerRef = useRef<HTMLButtonElement>(null);

  const hits = useMemo(() => search(docs ?? [], query), [docs, query]);

  const openSearch = useCallback(() => {
    setOpen(true);
    if (cache) {
      setDocs(cache);
    } else {
      loadIndex(indexPath)
        .then((d) => setDocs(d))
        .catch(() => setError('Search index could not be loaded.'));
    }
  }, [indexPath]);

  const closeSearch = useCallback(() => {
    setOpen(false);
    setQuery('');
    setActive(0);
    openerRef.current?.focus();
  }, []);

  // "/" opens search, matching the Docusaurus convention the old bar used.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);
      if (e.key === '/' && !typing && !open) {
        e.preventDefault();
        openSearch();
      } else if (e.key === 'Escape' && open) {
        e.preventDefault();
        closeSearch();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, openSearch, closeSearch]);

  useEffect(() => {
    if (open) {
      setActive(0);
      // Focus after paint so the modal is in the DOM and the caret lands correctly.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  const onInputKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => (hits.length ? (a + 1) % hits.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => (hits.length ? (a - 1 + hits.length) % hits.length : 0));
    } else if (e.key === 'Enter' && hits[active]) {
      e.preventDefault();
      window.location.href = baseUrl + hits[active].doc.u.replace(/^\//, '');
    }
  };

  return (
    <>
      <button
        ref={openerRef}
        type="button"
        className={styles.opener}
        onClick={openSearch}
        aria-label="Search documentation"
      >
        <svg className={styles.openerIcon} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M13.5 13.5 L17 17" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
        <span className={styles.openerLabel}>Search</span>
        <kbd className={styles.openerKey}>/</kbd>
      </button>

      {open && (
        <div className={styles.backdrop} role="presentation" onClick={closeSearch}>
          <div
            className={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-label="Search documentation"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.field}>
              <svg className={styles.fieldIcon} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
                <circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
                <path d="M13.5 13.5 L17 17" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              <input
                ref={inputRef}
                className={styles.input}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(0);
                }}
                onKeyDown={onInputKey}
                placeholder="Search the docs..."
                aria-label="Search query"
                role="combobox"
                aria-expanded={hits.length > 0}
                aria-controls="site-search-results"
                autoComplete="off"
                spellCheck={false}
              />
              <button type="button" className={styles.close} onClick={closeSearch} aria-label="Close search">
                Esc
              </button>
            </div>

            <div className={styles.results} id="site-search-results" role="listbox">
              {error && <p className={styles.note}>{escapeHtml(error)}</p>}

              {!error && docs === null && <p className={styles.note}>Loading search index...</p>}

              {!error && docs !== null && query.trim() === '' && (
                <p className={styles.note}>Type to search {docs.length} pages.</p>
              )}

              {!error && query.trim() !== '' && hits.length === 0 && (
                <p className={styles.note}>No results for &ldquo;{escapeHtml(query)}&rdquo;.</p>
              )}

              {hits.map((hit, i) => (
                <Link
                  key={hit.doc.u}
                  to={baseUrl + hit.doc.u.replace(/^\//, '')}
                  className={`${styles.hit} ${i === active ? styles.hitActive : ''}`}
                  role="option"
                  aria-selected={i === active}
                  onClick={closeSearch}
                  onMouseEnter={() => setActive(i)}
                >
                  <span className={styles.hitTitle}>
                    <Highlight text={hit.doc.t} query={query} />
                  </span>
                  <span className={styles.hitUrl}>{hit.doc.u}</span>
                  <span className={styles.hitSnippet}>
                    <Highlight text={hit.snippet} query={query} />
                  </span>
                </Link>
              ))}
            </div>

            <div className={styles.footer}>
              <span>
                <kbd>&uarr;</kbd>
                <kbd>&darr;</kbd> to navigate
              </span>
              <span>
                <kbd>&crarr;</kbd> to open
              </span>
              <span>
                <kbd>Esc</kbd> to close
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

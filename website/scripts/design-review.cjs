// Full-page design review capture: scrolls the landing page in viewport-sized
// slices so each section can be inspected on its own, plus one full-page shot.
// Run against `npm run serve -- --port 3012 --no-open --dir build`.
const assert = require('node:assert/strict');
const {mkdirSync} = require('node:fs');
const {join, resolve} = require('node:path');
const {chromium} = require('playwright');

(async () => {
  const base = process.env.DOCS_PREVIEW_URL || 'http://127.0.0.1:3012/docs/';
  const out = resolve(process.env.DOCS_REVIEW_DIR || '.docusaurus/design-review');
  mkdirSync(out, {recursive: true});
  const theme = process.env.DOCS_REVIEW_THEME || 'dark';
  const width = Number(process.env.DOCS_REVIEW_WIDTH || 1440);
  const height = Number(process.env.DOCS_REVIEW_HEIGHT || 900);

  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const context = await browser.newContext({viewport: {width, height}, colorScheme: theme});
    await context.addInitScript((mode) => localStorage.setItem('theme', mode), theme);
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(base);
    await page.locator('h1').first().waitFor();
    await page.waitForFunction(() => document.documentElement.dataset.hasHydrated === 'true');
    await page.waitForTimeout(600);

    const docHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    const slices = Math.ceil(docHeight / height);
    console.log(`doc height ${docHeight}px -> ${slices} slices`);

    for (let i = 0; i < slices; i += 1) {
      const y = i * height;
      await page.evaluate((top) => window.scrollTo(0, top), y);
      // Let the scroll-driven flyer/showcase settle before the shutter.
      await page.waitForTimeout(700);
      const atBottom = await page.evaluate(
        (top) => Math.round((document.documentElement.scrollHeight - innerHeight) * 100) / 100,
        y,
      );
      if (atBottom < 1) break;
      await page.screenshot({path: join(out, `${theme}-${width}-slice-${String(i).padStart(2, '0')}.png`)});
    }

    // What is actually on the page, in order, with rendered geometry. This is the
    // receipt for "is anything empty, off-balance, or overlapping".
    const sections = await page.evaluate(() => {
      const out = [];
      for (const el of document.querySelectorAll('main > *')) {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        out.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className && el.className.toString().slice(0, 60)) || '',
          h: Math.round(r.height),
          gapBefore: Math.round(parseFloat(cs.marginTop) || 0),
          text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 70),
        });
      }
      return out;
    });

    // Widest gap between consecutive content blocks: dead vertical air.
    let worst = {gap: 0, after: null, before: null};
    for (let i = 1; i < sections.length; i += 1) {
      const gap = sections[i].gapBefore;
      if (gap > worst.gap) worst = {gap, after: sections[i - 1], before: sections[i]};
    }

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(400);
    await page.screenshot({path: join(out, `${theme}-${width}-full.png`), fullPage: true});

    console.log(JSON.stringify({
      theme,
      width,
      docHeight,
      slices,
      worstGap: worst,
      sections,
      errors,
      out,
    }, null, 2));
    await context.close();
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

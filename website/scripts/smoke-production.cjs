// Verify the deployed site end to end. Uses waitUntil:'domcontentloaded'
// because waiting for 'load' can exceed the timeout on a heavy page whose
// large catalog JSON is still streaming — that is a weight observation, not
// a broken-page signal.
const assert = require('node:assert/strict');
const {chromium} = require('playwright');

const BASE = process.env.DOCS_PREVIEW_URL || 'https://anakot-agent-doc.up.railway.app/';

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 900}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto(BASE, {waitUntil: 'domcontentloaded', timeout: 60000});
  await page.waitForFunction(() => document.documentElement.dataset.hasHydrated === 'true', {timeout: 60000});
  await page.waitForTimeout(1200);

  // Hero
  const h1 = await page.locator('h1').first().innerText();
  console.log('h1:', JSON.stringify(h1));
  assert.ok(/grows with you/i.test(h1), 'landing hero headline present');

  // Search: open, query, assert real options appear
  await page.getByRole('button', {name: 'Search documentation', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: 'Search documentation'});
  await dialog.waitFor({timeout: 15000});
  await page.getByRole('combobox', {name: 'Search query'}).fill('installation');
  await page.locator('[role="option"]').first().waitFor({timeout: 20000});
  const options = await page.locator('[role="option"]').count();
  const first = await page.locator('[role="option"]').first().innerText();
  console.log('search options:', options);
  console.log('first result  :', JSON.stringify(first.split('\n')[0]));
  assert.ok(options > 0, 'search returns results in production');

  // Follow the first result and confirm it resolves
  await page.locator('[role="option"]').first().click();
  await page.waitForLoadState('domcontentloaded');
  console.log('navigated to  :', page.url());
  // The index is built from docs/ only and every entry's `u` is site-root
  // absolute, so a result must land inside the site's base path. This used to
  // assert "no double locale prefix" back when the index also carried zh-Hans
  // entries; with one locale the meaningful invariant is that the href stayed
  // under the base instead of escaping to a 404 or a raw filesystem path.
  const basePath = new URL(BASE).pathname.replace(/\/?$/, '/');
  assert.ok(page.url().startsWith(new URL(BASE).origin + basePath), 'result stayed under the site base path');
  assert.ok((await page.locator('h1').count()) === 1, 'exactly one h1 on the target page');
  console.log('target h1     :', JSON.stringify(await page.locator('h1').first().innerText()));

  // Getting-started content assertions
  await page.goto(new URL('getting-started/quickstart/', BASE).href, {waitUntil: 'domcontentloaded'});
  await page.waitForFunction(() => document.documentElement.dataset.hasHydrated === 'true');
  const body = await page.evaluate(() => document.body.innerText);
  assert.ok(body.includes('claude-opus-4.8'), 'corrected model id live');
  assert.ok(!body.includes('claude-opus-4.6'), 'stale model id gone');
  assert.ok(!body.includes('Onchain'), 'third-party video removed');

  console.log('page errors   :', errors.length ? JSON.stringify(errors) : 'none');
  console.log('\nPRODUCTION SMOKE: PASS');
  await browser.close();
})().catch(e => {console.error('PRODUCTION SMOKE: FAIL\n', e.message); process.exitCode = 1;});

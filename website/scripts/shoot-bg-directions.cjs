// Screenshots each background direction in bg-directions.html so the four
// options can be compared as images, not just described.
const {mkdirSync} = require('node:fs');
const {join, resolve} = require('node:path');
const {chromium} = require('playwright');

(async () => {
  const file = 'file:///' + resolve('.docusaurus/bg-directions.html').replace(/\\/g, '/');
  const out = resolve('.docusaurus/bg-dirs');
  mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1200, height: 1000}, colorScheme: 'dark'});
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(file);
    await page.waitForTimeout(1400);
    for (const opt of ['a', 'b', 'c', 'd']) {
      await page.click(`.tabs button[data-opt="${opt}"]`);
      await page.waitForTimeout(1500);
      const stage = page.locator(`.opt[data-opt="${opt}"] .stage`);
      await stage.screenshot({path: join(out, `bg-${opt}.png`)});
    }
    await page.click('.tabs button[data-opt="a"]');
    await page.waitForTimeout(400);
    await page.screenshot({path: join(out, 'bg-page.png'), fullPage: true});
    console.log(JSON.stringify({ok: true, errors, out}));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exitCode = 1; });

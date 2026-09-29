// Navbar contract: a flat, text-only bar (Arch-style). Text and hairlines only
// — no filled controls, no radius, no blur, no transform on the bar itself.
// Uses the repo's Playwright install and installed Google Chrome.
// DOCS_PREVIEW_URL can point at a dev server or a served production build.
const assert = require('node:assert/strict');
const {mkdirSync} = require('node:fs');
const {resolve, join} = require('node:path');
const {chromium} = require('playwright');

(async () => {
  const base = process.env.DOCS_PREVIEW_URL || 'http://127.0.0.1:3000/docs/';
  const output = resolve('.docusaurus/navbar-check');
  mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const receipts = [];
  try {
    for (const theme of ['dark', 'light']) {
      for (const width of [1440, 1199, 1024, 997, 996, 390, 320]) {
        const context = await browser.newContext({viewport: {width, height: 900}, colorScheme: theme});
        await context.addInitScript(mode => localStorage.setItem('theme', mode), theme);
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        for (const route of ['', 'getting-started/installation']) {
          assert.equal((await page.goto(new URL(route, base).href)).status(), 200);
          await page.waitForFunction(() => document.documentElement.dataset.hasHydrated === 'true');
          await page.evaluate(() => document.fonts.ready);

          const bar = await page.locator('nav.navbar').evaluate(el => {
            const s = getComputedStyle(el);
            const inner = el.querySelector('.navbar__inner');
            const is = getComputedStyle(inner);
            return {
              rect: el.getBoundingClientRect().toJSON(),
              y: el.getBoundingClientRect().y,
              x: el.getBoundingClientRect().x,
              width: el.getBoundingClientRect().width,
              bg: s.backgroundColor,
              backdrop: s.backdropFilter || s.webkitBackdropFilter || 'none',
              transform: s.transform,
              radius: s.borderTopLeftRadius,
              innerTransform: is.transform,
              innerFilter: is.filter,
              innerBackdrop: is.backdropFilter || is.webkitBackdropFilter || 'none',
            };
          });
          // Flat and full-bleed: no gap above the bar, edge to edge, no lift.
          assert.equal(bar.y, 0, 'bar sits flush against the top of the viewport');
          assert.equal(bar.x, 0, 'bar is full-bleed');
          assert.equal(Math.round(bar.width), width, 'bar spans the viewport width');
          assert.equal(bar.transform, 'none', 'no transform on the bar');
          assert.equal(bar.backdrop, 'none', 'no backdrop blur on the bar');
          assert.equal(parseFloat(bar.radius), 0, 'square corners, no floating island radius');
          // A transform/filter on either the bar or its inner wrapper would trap
          // the fixed-position search dialog inside the strip instead of the viewport.
          assert.equal(bar.innerTransform, 'none', 'no transform on the inner wrapper');
          assert.equal(bar.innerFilter, 'none', 'no filter on the inner wrapper');
          assert.equal(bar.innerBackdrop, 'none', 'no backdrop blur on the inner wrapper');

          // Text-only: every navigation control is transparent with square corners.
          const controls = await page.locator('.navbar__inner').evaluate(el => {
            const items = [...el.querySelectorAll('a.navbar__link, a.navbar__item, button')]
              .filter(e => !e.closest('.dropdown__menu') && e.checkVisibility() && e.getBoundingClientRect().width > 0);
            return items.map(e => {
              const s = getComputedStyle(e);
              const r = e.getBoundingClientRect();
              const text = (e.textContent || '').trim();
              return {
                label: text || e.getAttribute('aria-label') || '',
                // An icon-only control (theme toggle) may be round: it has no
                // fill, so its radius is not a "filled control" in disguise.
                hasText: text.length > 0,
                bg: s.backgroundColor,
                radius: parseFloat(s.borderTopLeftRadius),
                fontSize: parseFloat(s.fontSize),
                weight: s.fontWeight,
                box: {l: r.left, r: r.right, t: r.top, b: r.bottom},
              };
            });
          });
          // Desktop shows the full cluster; below 997px the links move into the
          // drawer and only the toggle and search remain in the bar.
          const minControls = width > 996 ? 6 : 2;
          assert.ok(controls.length >= minControls, `expected at least ${minControls} navigation controls, found ${controls.length}`);
          for (const c of controls) {
            // An OPAQUE colour serialises as rgb(r,g,b) with only three numbers,
            // so a missing 4th component means alpha 1, not "no alpha". Testing
            // `length < 4` reads every solid fill as transparent.
            const parts = c.bg.match(/[\d.]+/g)?.map(Number) ?? [];
            const alpha = parts.length === 4 ? parts[3] : 1;
            assert.equal(alpha, 0, `"${c.label}" has a filled background (${c.bg}) — the bar is text-only`);
            if (c.hasText) {
              assert.equal(c.radius, 0, `"${c.label}" is rounded — the bar is text-only`);
              assert.ok(c.fontSize <= 14, `"${c.label}" type is too large for a text bar: ${c.fontSize}px`);
            }
          }
          // No control overlaps another, and none escapes the bar.
          const barBox = await page.locator('nav.navbar').evaluate(el => {
            const r = el.getBoundingClientRect();
            return {l: r.left, r: r.right, t: r.top, b: r.bottom};
          });
          for (const c of controls) {
            assert.ok(c.box.l >= barBox.l - 1 && c.box.r <= barBox.r + 1 && c.box.t >= barBox.t - 1 && c.box.b <= barBox.b + 1,
              `"${c.label}" escapes the bar vertically or horizontally`);
          }
          for (let i = 0; i < controls.length; i++) {
            for (let j = i + 1; j < controls.length; j++) {
              const a = controls[i].box, b = controls[j].box;
              const overlap = Math.min(a.r, b.r) - Math.max(a.l, b.l) > 1 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 1;
              assert.ok(!overlap, `"${controls[i].label}" overlaps "${controls[j].label}"`);
            }
          }
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'no horizontal overflow');

          await page.evaluate(() => window.scrollTo(0, 650));
          await page.waitForTimeout(250);
          assert.equal(await page.locator('nav.navbar').evaluate(el => el.getBoundingClientRect().y), 0, 'bar stays pinned while reading');
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.waitForTimeout(150);

          // The search dialog is a fixed child of the bar: it must cover the
          // viewport, which only holds if no ancestor filters or transforms.
          const opener = page.getByRole('button', {name: 'Search documentation', exact: true});
          await opener.click();
          const dialog = page.getByRole('dialog', {name: 'Search documentation'});
          await dialog.waitFor();
          const overlay = await dialog.evaluate(el => {
            const r = el.parentElement.getBoundingClientRect();
            return {x: r.x, y: r.y, w: r.width, h: r.height, vw: innerWidth, vh: innerHeight};
          });
          assert.equal(overlay.x, 0, 'search overlay is viewport anchored, not bar anchored');
          assert.equal(overlay.y, 0);
          assert.equal(overlay.w, overlay.vw);
          assert.equal(overlay.h, overlay.vh);
          await page.getByRole('combobox', {name: 'Search query'}).fill('installation');
          await page.getByRole('option').first().waitFor();
          if (route === '' && [1440, 390].includes(width)) {
            await page.screenshot({path: join(output, `search-${theme}-${width}.png`)});
          }
          await page.keyboard.press('Escape');
          assert.equal(await dialog.count(), 0, 'Escape closes search');
          assert.equal(await opener.evaluate(el => el === document.activeElement), true, 'focus returns to the opener');

          if (width > 996) {
            const current = await page.locator('html').getAttribute('data-theme');
            await page.locator('.navbar__inner .dropdown > [role="button"]').click();
            await page.locator('.navbar .dropdown__menu').waitFor({state: 'visible'});
            assert.ok(await page.locator('.navbar .dropdown__link').count() >= 2, 'locale dropdown lists locales');
            await page.locator('h1').click();
            const toggle = page.getByRole('button', {name: /Switch between dark and light mode/});
            for (let i = 0; i < 3 && await page.locator('html').getAttribute('data-theme') === current; i++) await toggle.click();
            assert.notEqual(await page.locator('html').getAttribute('data-theme'), current, 'theme control works');
          } else {
            await page.getByRole('button', {name: 'Toggle navigation bar'}).click();
            const drawer = page.locator('.navbar-sidebar');
            await drawer.waitFor({state: 'visible'});
            await page.waitForTimeout(300);
            const panel = await drawer.evaluate(el => {
              const r = el.getBoundingClientRect();
              return {x: r.x, y: r.y, h: r.height, vh: innerHeight, bg: getComputedStyle(el).backgroundColor};
            });
            assert.equal(panel.x, 0, 'drawer is viewport anchored');
            assert.equal(panel.y, 0);
            assert.equal(panel.h, panel.vh);
            assert.ok(!panel.bg.startsWith('rgba'), `drawer must be opaque, got ${panel.bg}`);
            if (route === '') {
              if (width === 390) await page.screenshot({path: join(output, `menu-${theme}.png`)});
              await drawer.getByRole('link', {name: 'Get started', exact: true}).click();
              await page.waitForURL('**/getting-started/installation');
              assert.equal(await page.locator('.navbar-sidebar--show').count(), 0, 'choosing a destination closes the drawer');
            } else {
              await drawer.getByRole('button', {name: 'Close navigation bar'}).click();
              assert.equal(await page.locator('.navbar-sidebar--show').count(), 0, 'close button shuts the drawer');
            }
          }
          if (route === '' && [1440, 390].includes(width)) {
            await page.goto(base);
            await page.waitForFunction(() => document.documentElement.dataset.hasHydrated === 'true');
            await page.evaluate(() => document.fonts.ready);
            await page.screenshot({path: join(output, `home-${theme}-${width}.png`)});
          }
          receipts.push({theme, width, route: route || '/', status: 'passed'});
        }
        assert.deepEqual(errors, [], 'no browser runtime errors');
        await context.close();
      }
    }
    const calm = await browser.newPage({reducedMotion: 'reduce'});
    await calm.goto(base);
    await calm.waitForFunction(() => document.documentElement.dataset.hasHydrated === 'true');
    await calm.evaluate(() => document.fonts.ready);
    assert.equal(await calm.locator('nav.navbar').evaluate(el => getComputedStyle(el).transform), 'none', 'reduced motion keeps the bar static');
    console.log(JSON.stringify({checks: receipts.length, reducedMotion: 'passed', receipts, screenshots: output}, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});

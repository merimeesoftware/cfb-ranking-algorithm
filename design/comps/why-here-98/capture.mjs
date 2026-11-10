/**
 * Renders states/*.html to renders/*.png with Playwright + local Chrome.
 * 1440 → 1440x900 viewport, 390 → 390x844, both full page (the sheet is a
 * viewport still). share-card* → exactly 1200x675 (2-part and 1-part).
 * Usage: node design/comps/why-here-98/capture.mjs  (needs scripts/visual deps)
 */
import { readdirSync, mkdirSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(HERE, '../../../scripts/visual/package.json'));
const { chromium } = require('playwright-core');
const CHROME = process.env.CHROME_PATH || '/usr/bin/google-chrome';

const browser = await chromium.launch({ executablePath: CHROME });
mkdirSync(path.join(HERE, 'renders'), { recursive: true });
// Optional args: state file names to re-render (e.g. board-closed-1440.html); default = all, after clearing renders/.
const only = process.argv.slice(2);
if (!only.length) for (const f of readdirSync(path.join(HERE, 'renders'))) if (f.endsWith('.png')) rmSync(path.join(HERE, 'renders', f));
const files = only.length ? only : readdirSync(path.join(HERE, 'states')).filter((f) => f.endsWith('.html')).sort();
for (const f of files) {
  const name = f.replace(/\.html$/, '');
  const share = name.startsWith('share-card');
  const vp = share ? { width: 1200, height: 675 } : name.endsWith('-390') ? { width: 390, height: 844 } : { width: 1440, height: 900 };
  const page = await browser.newPage({ viewport: vp, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(path.join(HERE, 'states', f)).href);
  await page.evaluate(() => document.fonts.ready);
  const out = path.join(HERE, 'renders', share ? `${name}-1200x675.png` : `${name}.png`);
  await page.screenshot({ path: out, fullPage: !(share || name.startsWith('sheet-')), animations: 'disabled' });
  await page.close();
  console.log(path.relative(HERE, out));
}
console.log(`chrome ${browser.version()}`);
await browser.close();

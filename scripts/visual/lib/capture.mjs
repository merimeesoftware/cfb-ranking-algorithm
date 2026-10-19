import { chromium } from 'playwright-core';
import { assertChromeMajor } from './visual-rules.mjs';
import { attachNavGuard } from './nav-guard.mjs';

const FREEZE_CSS =
  '*,*::before,*::after{animation:none !important;transition:none !important;caret-color:transparent !important}';

/**
 * Google Chrome via Playwright's channel, sandbox left on.
 * Do not add --no-sandbox or --disable-setuid-sandbox.
 */
export async function launchChrome() {
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
    chromiumSandbox: true,
    args: ['--disable-dev-shm-usage', '--disable-background-networking', '--no-first-run'],
  });
  const version = browser.version();
  assertChromeMajor(version);
  return { browser, version };
}

export async function captureViewport(browser, { url, width, height, allowedOrigin, violations }) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    reducedMotion: 'reduce',
    colorScheme: 'light',
  });
  await context.addInitScript(() => {
    try {
      localStorage.setItem('theme', 'light');
    } catch {
      /* private mode */
    }
  });
  const page = await context.newPage();
  await attachNavGuard(page, { allowedOrigin, violations });
  const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 });
  await page.addStyleTag({ content: FREEZE_CSS });
  try {
    await page.waitForFunction(
      () => {
        const flag = window.__agentReached;
        return !flag || flag !== 'pending';
      },
      { timeout: 1500 }
    );
  } catch {
    /* pages that do not plant a flag */
  }
  const flags = await page
    .evaluate(() => ({
      agent: window.__agentReached || null,
      offsite: window.__offsiteReached || null,
    }))
    .catch(() => ({ agent: null, offsite: null }));
  const png = await page.screenshot({ type: 'png', fullPage: false });
  const status = response ? response.status() : 0;
  await context.close();
  return { png, status, flags };
}

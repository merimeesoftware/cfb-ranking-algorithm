/**
 * The built pages reference Google Fonts and CFBD logo CDN URLs. Those are
 * off-site, so the capture server rewrites them to same-origin resources
 * before the browser parses the document. The nav guard still fails the run
 * if any other off-site URL is requested — this rewrite is not an allowlist.
 */

const FONT_LINK =
  /<link\b[^>]*(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>\s*/gi;

const OFFSITE_ASSET =
  /https:\/\/(?:cdn\.collegefootballdata\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)\/[^"'\\\s)]+/gi;

export const SAME_ORIGIN_LOGO = '/__visual/logo.svg';

export function rewriteCaptureText(text) {
  return text.replace(FONT_LINK, '').replace(OFFSITE_ASSET, SAME_ORIGIN_LOGO);
}

export function shouldRewrite(filePath, contentType = '') {
  const lower = filePath.toLowerCase();
  const type = contentType.toLowerCase();
  return (
    lower.endsWith('.html') ||
    lower.endsWith('.json') ||
    lower.endsWith('.css') ||
    type.includes('text/html') ||
    type.includes('application/json') ||
    type.includes('text/css')
  );
}

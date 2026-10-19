import http from 'node:http';
import { readFileSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { rewriteCaptureText, shouldRewrite, SAME_ORIGIN_LOGO } from './rewrite.mjs';

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json',
};

function contentType(filePath) {
  return TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
}

function resolveUnder(root, pathname) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname.split('?')[0]);
  } catch {
    return null;
  }
  if (decoded.includes('\0') || decoded.split('/').includes('..')) return null;
  const rel = decoded.replace(/^\/+/, '');
  const candidates = rel === '' ? ['index.html'] : [rel, `${rel}.html`, path.join(rel, 'index.html')];
  const rootAbs = path.resolve(root);
  for (const candidate of candidates) {
    const abs = path.resolve(root, candidate);
    if (abs !== rootAbs && !abs.startsWith(rootAbs + path.sep)) continue;
    if (existsSync(abs) && statSync(abs).isFile()) return abs;
  }
  return null;
}

function send(res, status, body, type) {
  res.writeHead(status, {
    'content-type': type,
    'cache-control': 'no-store',
  });
  res.end(body);
}

function rankingsBody(apiFixture) {
  // Ignore the requested week. The offline board stays on the fixture's
  // year and week so a still does not change as the calendar moves.
  return { ...apiFixture, year: apiFixture.year, week: apiFixture.week };
}

/**
 * Local server for stills. `buildDir` is the SvelteKit build (HTML is
 * rewritten). `fixtureDir` is a raw static root for planted pages — those
 * pages are not rewritten, so an off-site fetch in a fixture still hits
 * the nav guard.
 */
export function startFixtureServer({
  buildDir = null,
  fixtureDir = null,
  apiFixture = null,
  logoPath = null,
  host = '127.0.0.1',
} = {}) {
  const agentHits = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url || '/', `http://${host}`);
    const pathname = url.pathname.replace(/\/+$/, '') || '/';

    if (pathname === '/api/agent' || pathname.toLowerCase().startsWith('/api/agent/')) {
      agentHits.push({ method: req.method, url: pathname });
      send(res, 403, JSON.stringify({ error: 'visual-check blocked /api/agent' }), TYPES['.json']);
      return;
    }

    if (pathname === SAME_ORIGIN_LOGO || pathname === '/__visual/logo.svg') {
      if (!logoPath || !existsSync(logoPath)) {
        send(res, 404, 'logo missing', TYPES['.txt']);
        return;
      }
      send(res, 200, readFileSync(logoPath), TYPES['.svg']);
      return;
    }

    if (pathname === '/api' || pathname === '/api/') {
      send(res, 200, JSON.stringify({ status: 'ok', offline: true }), TYPES['.json']);
      return;
    }

    if (pathname === '/api/weeks') {
      send(
        res,
        200,
        JSON.stringify({ weeks: Array.from({ length: 15 }, (_, i) => i + 1) }),
        TYPES['.json']
      );
      return;
    }

    if (pathname === '/api/rankings' && apiFixture) {
      send(res, 200, JSON.stringify(rankingsBody(apiFixture)), TYPES['.json']);
      return;
    }

    if (pathname.startsWith('/api/rankings/team/') && apiFixture) {
      const name = decodeURIComponent(pathname.slice('/api/rankings/team/'.length));
      send(
        res,
        200,
        JSON.stringify({
          team: { name },
          wins_details: [],
          losses_details: [],
          quality_wins: 0,
          quality_losses: 0,
          bad_losses: 0,
        }),
        TYPES['.json']
      );
      return;
    }

    if (pathname === '/api/drop/subscribe') {
      send(res, 200, JSON.stringify({ message: 'offline fixture' }), TYPES['.json']);
      return;
    }

    if (pathname.startsWith('/api/')) {
      send(res, 404, JSON.stringify({ error: 'no offline fixture' }), TYPES['.json']);
      return;
    }

    const root = buildDir || fixtureDir;
    if (!root) {
      send(res, 500, 'fixture server has no root', TYPES['.txt']);
      return;
    }
    const file = resolveUnder(root, url.pathname);
    if (!file) {
      send(res, 404, 'not found', TYPES['.txt']);
      return;
    }
    const type = contentType(file);
    let body = readFileSync(file);
    if (buildDir && shouldRewrite(file, type)) {
      body = Buffer.from(rewriteCaptureText(body.toString('utf8')), 'utf8');
    }
    send(res, 200, body, type);
  });

  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, host, () => {
      const { port } = server.address();
      resolve({
        server,
        origin: `http://${host}:${port}`,
        port,
        agentHits,
        close() {
          return new Promise((done, fail) => {
            server.close((error) => (error ? fail(error) : done()));
          });
        },
      });
    });
  });
}

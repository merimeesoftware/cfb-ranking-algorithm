import { classifyRequest } from './visual-rules.mjs';

function recordBlocked(violations, kind, url, method, resourceType) {
  violations.push({ kind, url, method, resourceType });
}

/**
 * Context-wide lock. page.route misses service-worker fetches, popups, and
 * websockets. Service workers are blocked on the context. Every websocket
 * is closed here and never connected upstream.
 */
export async function attachNavGuard(context, { allowedOrigin, violations }) {
  await context.route('**/*', (route) => {
    const request = route.request();
    const kind = classifyRequest(request.url(), allowedOrigin);
    if (kind !== 'ok') {
      recordBlocked(violations, kind, request.url(), request.method(), request.resourceType());
      return route.abort('blockedbyclient');
    }
    return route.continue();
  });

  await context.routeWebSocket(/.*/, (ws) => {
    // A ws: URL has a different origin from the page, so classifyRequest
    // would call a same-host socket offsite. Every socket is denied here.
    // An /api/agent socket stays labeled agent.
    const classified = classifyRequest(ws.url(), allowedOrigin);
    recordBlocked(
      violations,
      classified === 'agent' ? 'agent' : 'websocket',
      ws.url(),
      'WEBSOCKET',
      'websocket'
    );
    return ws.close({ code: 1008, reason: 'visual-check blocked websocket' });
  });
}

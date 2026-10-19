import { classifyRequest } from './visual-rules.mjs';

/**
 * Abort any /api/agent request and any request whose origin is not the
 * capture server. Records the attempt so the run can fail closed.
 * Chrome's sandbox is a launch option; this guard is the network lock.
 */
export function attachNavGuard(page, { allowedOrigin, violations }) {
  return page.route('**/*', (route) => {
    const request = route.request();
    const kind = classifyRequest(request.url(), allowedOrigin);
    if (kind !== 'ok') {
      violations.push({
        kind,
        url: request.url(),
        method: request.method(),
        resourceType: request.resourceType(),
      });
      return route.abort('blockedbyclient');
    }
    return route.continue();
  });
}

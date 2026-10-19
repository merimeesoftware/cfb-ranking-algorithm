/**
 * Edge caps for the public API: visitor identity, rate limits, query allowlist,
 * preview spend defaults, and the env block forwarded into the Flask container.
 */
import { dailyLimitFor, type SpendBucket } from './budget.ts';

export const BUSY_MESSAGE = 'Busy right now. Try again later.';
export const FORMULA_MESSAGE = "Same numbers, same time, for everyone. Custom settings aren't accepted.";
export const UNPUBLISHED_MESSAGE = "That week isn't on the board yet.";
export const SPEND_GATE_HOST = 'spend.budget';
/** Fixed origin for container fetches. The visitor path never chooses this host. */
export const UPSTREAM_ORIGIN = 'https://api.internal';
export const VISITOR_HOST_HEADER = 'x-visitor-host';

/**
 * Control-plane hosts. spend.budget is the spend store. ai.xai and ai.workers
 * are outbound-only. None of them are reachable from a visitor /api path.
 */
export function internalHosts(): readonly string[] {
	return [SPEND_GATE_HOST, 'ai.xai', 'ai.workers'];
}

export function isInternalHost(hostname: string): boolean {
	const host = hostname.trim().toLowerCase().replace(/:\d+$/, '').replace(/\.$/, '');
	return internalHosts().includes(host);
}

const PRODUCTION_WORKER_NAME = 'true-rankings-cfb';

export const FORMULA_PARAMS = new Set([
	'power_conf_initial',
	'group5_initial',
	'fcs_initial',
	'base_factor',
	'hfa_elo',
	'upset_bonus_mult',
	'team_quality_weight',
	'conference_weight',
	'record_weight',
	'prior_strength',
	'use_ats',
	'ats_bonus',
	'use_reference_ranks',
]);

const ROUTE_ALLOWED: Record<string, Set<string>> = {
	rankings: new Set(['year', 'week', 'all_divisions']),
	matchup: new Set(['year', 'week', 'team_a', 'team_b', 'a', 'b', 'market_spread']),
	weeks: new Set(['year']),
	team: new Set(['year', 'week']),
};

export interface Manifest {
	years: Record<string, number[]>;
}

export interface RateLimiter {
	limit(options: { key: string }): Promise<{ success: boolean }>;
}

export interface CapEnv {
	AI_MODE?: string;
	CFBD_OFFLINE?: string;
	XAI_MAX_CALLS?: string;
	XAI_ENABLED?: string;
	AI_MAX_CALLS?: string;
	CFBD_MAX_CALLS?: string;
	AI_KILL?: string;
	XAI_KILL?: string;
	WORKERS_AI_KILL?: string;
	CFBD_KILL?: string;
	PREVIEW_AI_MODE?: string;
	PREVIEW_CFBD_OFFLINE?: string;
	AGENT_RATE_LIMIT?: string;
	XAI_WEEKLY_USD_CAP?: string;
}

export type BoardRoute = 'rankings' | 'matchup' | 'weeks' | 'team';

export type QueryDecision =
	| { ok: true; route: BoardRoute; year: number; week?: number; weeks?: number[] }
	| { ok: false; status: number; body: Record<string, unknown> };

export function isKillSwitch(raw: string | undefined): boolean {
	return ['1', 'true', 'yes', 'on'].includes((raw ?? '').trim().toLowerCase());
}

export function isXaiEnabled(env: CapEnv): boolean {
	return isKillSwitch(env.XAI_ENABLED);
}

function pathOnly(value: string): string {
	const query = value.indexOf('?');
	return query === -1 ? value : value.slice(0, query);
}

/** True when a path uses //, an encoded slash pair, or a backslash. */
export function pathHasSpoof(path: string): boolean {
	const value = pathOnly(path);
	return value.includes('//')
		|| value.includes('\\')
		|| /%2f%2f/i.test(value)
		|| /%5c/i.test(value)
		|| /%2f\//i.test(value)
		|| /\/%2f/i.test(value);
}

/** Visitor API paths after URL normalization. `/api/../...` is not one of them. */
export function isVisitorApiPath(pathname: string): boolean {
	return /^\/api(\/|$)/.test(pathname);
}

/** Check the raw request string. The scheme's :// is not part of the path. */
export function requestPathSpoofed(rawUrl: string): boolean {
	const scheme = rawUrl.indexOf('://');
	const rest = scheme === -1 ? rawUrl : rawUrl.slice(scheme + 3);
	const slash = rest.indexOf('/');
	if (slash === -1) return false;
	return pathHasSpoof(rest.slice(slash));
}

/** Drop every query key that decodes to `secret`, in any case. */
function searchWithoutSecret(search: string): string {
	if (!search) return search;
	const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search);
	const kept = new URLSearchParams();
	for (const [key, value] of params) {
		if (key.toLowerCase() === 'secret') continue;
		kept.append(key, value);
	}
	const text = kept.toString();
	return text ? `?${text}` : '';
}

/**
 * Container URL from the one canonical path.
 * The URL parser must reproduce that path. A rewrite (a stripped tab, for
 * example) is a 400, not a different route.
 */
export function upstreamApiUrl(pathname: string, search: string): URL | null {
	if (!pathname.startsWith('/') || pathHasSpoof(pathname) || hasControlCharacter(pathname)) return null;
	const target = new URL(UPSTREAM_ORIGIN);
	target.pathname = pathname;
	target.search = searchWithoutSecret(search);
	if (target.origin !== UPSTREAM_ORIGIN || isInternalHost(target.hostname)) return null;
	let forwarded: string;
	try {
		forwarded = decodeURIComponent(target.pathname);
	} catch {
		return null;
	}
	if (forwarded !== pathname || pathHasSpoof(target.pathname)) return null;
	return target;
}

export type ApiRoute =
	| { ok: false; status: 400 }
	| { ok: true; upstream: URL; modeHost: string; apiPath: string };

/** Bytes encodeURIComponent leaves alone. Encoding them hides a route. */
const UNRESERVED_ASCII = /[A-Za-z0-9\-._~!*'()]/;

function requestTarget(rawUrl: string): { path: string; search: string; hostname: string } | null {
	let incoming: URL;
	try {
		incoming = new URL(rawUrl);
	} catch {
		return null;
	}
	const scheme = rawUrl.indexOf('://');
	const rest = scheme === -1 ? rawUrl : rawUrl.slice(scheme + 3);
	const slash = rest.indexOf('/');
	if (slash === -1) return null;
	let tail = rest.slice(slash);
	const hash = tail.indexOf('#');
	if (hash !== -1) tail = tail.slice(0, hash);
	const query = tail.indexOf('?');
	const path = query === -1 ? tail : tail.slice(0, query);
	const search = query === -1 ? '' : tail.slice(query);
	if (!path.startsWith('/')) return null;
	return { path, search, hostname: incoming.hostname };
}

/** C0 controls and DEL. Raw or percent-encoded, these are not team names. */
function hasControlCharacter(value: string): boolean {
	for (let i = 0; i < value.length; i += 1) {
		const code = value.charCodeAt(i);
		if (code <= 0x1f || code === 0x7f) return true;
	}
	return false;
}

/** U+2215 and U+FF0F. They are not `/`, and they are not a visitor route. */
function hasUnicodeSlash(value: string): boolean {
	return value.includes('\u2215') || value.includes('\uFF0F');
}

function hasEncodedControl(path: string): boolean {
	for (const token of path.match(/%[0-9A-Fa-f]{2}/g) ?? []) {
		const byte = Number.parseInt(token.slice(1), 16);
		if (byte <= 0x1f || byte === 0x7f) return true;
	}
	return false;
}

/**
 * Decode a visitor path once into the canonical path.
 * Team names use encodeURIComponent (spaces, accents). A control character,
 * an encoded slash or backslash, a slash lookalike (U+2215, U+FF0F), a
 * backslash, a failed decode, a second decode that changes the path, or an
 * encoded unreserved byte (`%61`) is rejected.
 */
export function decodeVisitorPath(path: string): string | null {
	if (path.includes('\\') || /%5c/i.test(path) || /%2f/i.test(path)) return null;
	if (hasControlCharacter(path) || hasEncodedControl(path)) return null;
	if (/%(?![0-9A-Fa-f]{2})/.test(path)) return null;
	for (const token of path.match(/%[0-9A-Fa-f]{2}/g) ?? []) {
		const byte = Number.parseInt(token.slice(1), 16);
		if (byte < 0x80 && UNRESERVED_ASCII.test(String.fromCharCode(byte))) return null;
	}
	let decoded: string;
	try {
		decoded = decodeURIComponent(path);
	} catch {
		return null;
	}
	if (hasControlCharacter(decoded) || decoded.includes('\\') || /%2f/i.test(decoded) || /%5c/i.test(decoded)) {
		return null;
	}
	if (hasUnicodeSlash(path) || hasUnicodeSlash(decoded)) return null;
	let again: string;
	try {
		again = decodeURIComponent(decoded);
	} catch {
		return null;
	}
	if (again !== decoded) return null;
	return decoded;
}

/** Collapse dot segments. `//` and `..` are not visitor routes. */
export function normalizeVisitorPath(path: string): string | null {
	if (!path.startsWith('/')) return null;
	const trailing = path.length > 1 && path.endsWith('/');
	const body = trailing ? path.slice(0, -1) : path;
	const parts: string[] = [];
	for (const segment of body.split('/')) {
		if (segment === '.' || segment === '') {
			if (segment === '' && parts.length > 0) return null;
			continue;
		}
		if (segment === '..') return null;
		parts.push(segment);
	}
	if (!parts.length) return null;
	return `/${parts.join('/')}${trailing ? '/' : ''}`;
}

/**
 * One canonical path for the classifier, the limiters, counter stripping,
 * and the container URL. Callers use `apiPath`; they do not parse the URL again.
 */
export function routeApiRequest(rawUrl: string): ApiRoute {
	if (requestPathSpoofed(rawUrl)) return { ok: false, status: 400 };
	const target = requestTarget(rawUrl);
	if (!target || isInternalHost(target.hostname)) return { ok: false, status: 400 };
	const decoded = decodeVisitorPath(target.path);
	if (!decoded) return { ok: false, status: 400 };
	const normalized = normalizeVisitorPath(decoded);
	if (!normalized || !isVisitorApiPath(normalized)) return { ok: false, status: 400 };
	const apiPath = normalized.replace(/^\/api/, '') || '/';
	if (!apiPath.startsWith('/')) return { ok: false, status: 400 };
	const upstream = upstreamApiUrl(apiPath, target.search);
	if (!upstream) return { ok: false, status: 400 };
	return { ok: true, upstream, modeHost: target.hostname, apiPath };
}

/** POST /api/spend/kill after the /api prefix is stripped. */
export function isSpendKillRoute(method: string, pathname: string): boolean {
	return method.toUpperCase() === 'POST' && pathname === '/spend/kill';
}

export function paidCallAllowed(env: CapEnv, bucket: SpendBucket): boolean {
	if (bucket === 'cfbd') return !isKillSwitch(env.CFBD_KILL);
	if (isKillSwitch(env.AI_KILL)) return false;
	if (bucket === 'xai') return isXaiEnabled(env) && !isKillSwitch(env.XAI_KILL);
	return !isKillSwitch(env.WORKERS_AI_KILL);
}

/** CF-Connecting-IP only. X-Forwarded-For is never a visitor key. */
export function clientIp(request: Request): string {
	const cf = request.headers.get('CF-Connecting-IP');
	const ip = (cf ?? '').trim();
	return ip || 'unknown';
}

export function boardRoute(pathname: string): BoardRoute | null {
	if (pathname === '/rankings') return 'rankings';
	if (pathname === '/matchup') return 'matchup';
	if (pathname === '/weeks') return 'weeks';
	if (pathname.startsWith('/rankings/team/')) return 'team';
	return null;
}

export function isNonProductionHostname(hostname: string): boolean {
	const host = hostname.toLowerCase().replace(/:\d+$/, '');
	if (host === 'localhost' || host === '127.0.0.1' || host.endsWith('.localhost')) {
		return true;
	}
	// Preview hosts use the platform suffix. The production worker name does not.
	if (!host.endsWith('.workers.dev')) return false;
	const label = host.split('.')[0] ?? '';
	return label !== PRODUCTION_WORKER_NAME;
}

/**
 * Unset production mode is stub + offline. Preview hostnames are the same
 * unless PREVIEW_AI_MODE / PREVIEW_CFBD_OFFLINE are set.
 */
export function resolveContainerModes(
	env: CapEnv,
	hostname: string,
): { AI_MODE: string; CFBD_OFFLINE: string } {
	if (!isNonProductionHostname(hostname)) {
		return {
			AI_MODE: env.AI_MODE?.trim() || 'stub',
			CFBD_OFFLINE: env.CFBD_OFFLINE?.trim() || '1',
		};
	}
	const previewAi = env.PREVIEW_AI_MODE?.trim();
	const previewOffline = env.PREVIEW_CFBD_OFFLINE?.trim();
	return {
		AI_MODE: previewAi || 'stub',
		CFBD_OFFLINE: previewOffline || '1',
	};
}

/** Secrets forwarded into the container. The xAI credential stays on the Worker. */
export function containerSecrets(env: {
	CFBD_API_KEY?: string;
	XAI_API_KEY?: string;
	CACHE_CLEAR_SECRET?: string;
	CORS_ORIGINS?: string;
}): Record<string, string> {
	return {
		...(env.CFBD_API_KEY ? { CFBD_API_KEY: env.CFBD_API_KEY } : {}),
		...(env.CACHE_CLEAR_SECRET ? { CACHE_CLEAR_SECRET: env.CACHE_CLEAR_SECRET } : {}),
		...(env.CORS_ORIGINS ? { CORS_ORIGINS: env.CORS_ORIGINS } : {}),
	};
}

export function buildRuntimeEnv(
	base: Record<string, string>,
	env: CapEnv,
	hostname: string,
): Record<string, string> {
	const modes = resolveContainerModes(env, hostname);
	const out: Record<string, string> = {
		...base,
		AI_MODE: modes.AI_MODE,
		CFBD_OFFLINE: modes.CFBD_OFFLINE,
		SPEND_GATE_HOST,
		AI_XAI_HOST: 'ai.xai',
		AI_WORKERS_HOST: 'ai.workers',
		XAI_MAX_CALLS: String(dailyLimitFor('xai', env)),
		XAI_ENABLED: isXaiEnabled(env) ? '1' : '0',
		AI_MAX_CALLS: String(dailyLimitFor('workers_ai', env)),
		CFBD_MAX_CALLS: String(dailyLimitFor('cfbd', env)),
		AI_KILL: isKillSwitch(env.AI_KILL) ? '1' : '0',
		XAI_KILL: isKillSwitch(env.XAI_KILL) ? '1' : '0',
		WORKERS_AI_KILL: isKillSwitch(env.WORKERS_AI_KILL) ? '1' : '0',
		CFBD_KILL: isKillSwitch(env.CFBD_KILL) ? '1' : '0',
		XAI_WEEKLY_USD_CAP: env.XAI_WEEKLY_USD_CAP?.trim() || '0',
	};
	if (env.AGENT_RATE_LIMIT?.trim()) {
		out.AGENT_RATE_LIMIT = env.AGENT_RATE_LIMIT.trim();
	}
	return out;
}

export function busyBody(code: string): Record<string, unknown> {
	return {
		busy: true,
		capped: true,
		message: BUSY_MESSAGE,
		code,
	};
}

export function busyResponse(code: string, status = 429): Response {
	return Response.json(busyBody(code), {
		status,
		headers: { 'cache-control': 'no-store' },
	});
}

function readInt(params: URLSearchParams, name: string): { present: boolean; value: number | null } {
	if (!params.has(name)) return { present: false, value: null };
	const raw = (params.get(name) ?? '').trim();
	if (!raw || !/^-?\d+$/.test(raw)) return { present: true, value: null };
	return { present: true, value: Number(raw) };
}

export function publishedWeeks(manifest: Manifest, year: number): number[] {
	const raw = manifest.years?.[String(year)];
	if (!Array.isArray(raw)) return [];
	return raw.map((item) => Number(item)).filter((item) => Number.isInteger(item));
}

export function checkPublicQuery(
	pathname: string,
	params: URLSearchParams,
	manifest: Manifest,
): QueryDecision | null {
	const route = boardRoute(pathname);
	if (!route) return null;
	const allowed = ROUTE_ALLOWED[route];
	const rejected: string[] = [];
	for (const key of params.keys()) {
		if (FORMULA_PARAMS.has(key) || !allowed.has(key)) rejected.push(key);
	}
	if (rejected.length) {
		return {
			ok: false,
			status: 400,
			body: {
				error: FORMULA_MESSAGE,
				code: 'formula_params',
				rejected,
			},
		};
	}

	const year = readInt(params, 'year');
	const week = readInt(params, 'week');
	if (year.present && year.value === null) {
		return { ok: false, status: 400, body: { error: 'year must be an integer.', code: 'bad_year' } };
	}
	if (week.present && week.value === null) {
		return { ok: false, status: 400, body: { error: 'week must be an integer.', code: 'bad_week' } };
	}

	if (route === 'weeks') {
		if (year.value === null) {
			return { ok: false, status: 400, body: { error: 'year is required.', code: 'missing_year' } };
		}
		const weeks = publishedWeeks(manifest, year.value);
		if (!weeks.length) {
			return {
				ok: false,
				status: 200,
				body: {
					year: year.value,
					weeks: [],
					max_week: 0,
					published: false,
					message: UNPUBLISHED_MESSAGE,
				},
			};
		}
		return { ok: true, route, year: year.value, weeks };
	}

	if (year.value === null || week.value === null) {
		return {
			ok: false,
			status: 400,
			body: { error: 'year and week are required.', code: 'missing_week' },
		};
	}
	if (!publishedWeeks(manifest, year.value).includes(week.value)) {
		return {
			ok: false,
			status: 200,
			body: {
				published: false,
				busy: false,
				message: UNPUBLISHED_MESSAGE,
				code: 'not_published',
				year: year.value,
				week: week.value,
				team_rankings: [],
				conference_rankings: [],
			},
		};
	}
	return { ok: true, route, year: year.value, week: week.value };
}

export async function enforceVisitorLimit(
	request: Request,
	limiters: { api: RateLimiter; agent: RateLimiter },
	apiPath: string,
): Promise<{ limited: boolean; ip: string; code: string }> {
	const ip = clientIp(request);
	const agentRoute = apiPath === '/agent' || apiPath.startsWith('/agent/');
	const apiResult = await limiters.api.limit({ key: ip });
	if (!apiResult.success) {
		return { limited: true, ip, code: 'api_rate_limit' };
	}
	if (agentRoute) {
		const agentResult = await limiters.agent.limit({ key: ip });
		if (!agentResult.success) {
			return { limited: true, ip, code: 'agent_rate_limit' };
		}
	}
	return { limited: false, ip, code: '' };
}

const PUBLIC_COUNTER_KEYS = [
	'cfbd_calls',
	'cfbd_max_calls',
	'cfbd_offline',
	'cfbd_key',
	'ai_live_calls',
	'ai_max_calls',
	'xai_live_calls',
	'xai_max_calls',
	'workers_ai_live_calls',
	'workers_ai_max_calls',
	'agent_rate_limit_per_hour',
	'development',
	'spend',
	'memory_entries',
	'indexed_prefixes',
	'file_entries',
	'cache_backend',
	'cache_dir',
];

export function stripPublicCounters(body: unknown): Record<string, unknown> {
	if (!body || typeof body !== 'object' || Array.isArray(body)) return { status: 'ok' };
	const out: Record<string, unknown> = { ...(body as Record<string, unknown>) };
	for (const key of PUBLIC_COUNTER_KEYS) delete out[key];
	return out;
}

export function isCounterEndpoint(pathname: string): boolean {
	return pathname === '/agent/health' || pathname === '/cache/stats'
		|| pathname === '/api/agent/health' || pathname === '/api/cache/stats';
}

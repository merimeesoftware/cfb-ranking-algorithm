/**
 * Edge caps for the public API: visitor identity, rate limits, query allowlist,
 * preview spend defaults, and the env block forwarded into the Flask container.
 */
import {
	DEFAULT_AI_MAX_CALLS_PER_DAY,
	DEFAULT_CFBD_MAX_CALLS_PER_DAY,
	dailyLimitFor,
	type SpendBucket,
} from './budget.ts';

export const BUSY_MESSAGE = 'Busy right now, try again later.';
export const FORMULA_MESSAGE = 'Custom formula parameters are not accepted.';
export const UNPUBLISHED_MESSAGE = "That week isn't on the board yet.";
export const SPEND_GATE_HOST = 'spend.budget';

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
	AI_MAX_CALLS?: string;
	CFBD_MAX_CALLS?: string;
	AI_KILL?: string;
	CFBD_KILL?: string;
	PREVIEW_AI_MODE?: string;
	PREVIEW_CFBD_OFFLINE?: string;
	AGENT_RATE_LIMIT?: string;
}

export type BoardRoute = 'rankings' | 'matchup' | 'weeks' | 'team';

export type QueryDecision =
	| { ok: true; route: BoardRoute; year: number; week?: number; weeks?: number[] }
	| { ok: false; status: number; body: Record<string, unknown> };

export function isKillSwitch(raw: string | undefined): boolean {
	return ['1', 'true', 'yes', 'on'].includes((raw ?? '').trim().toLowerCase());
}

export function paidCallAllowed(env: CapEnv, bucket: SpendBucket): boolean {
	return !isKillSwitch(bucket === 'ai' ? env.AI_KILL : env.CFBD_KILL);
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
	if (!host.endsWith('.workers.dev')) return false;
	const label = host.split('.')[0] ?? '';
	return label !== PRODUCTION_WORKER_NAME;
}

/**
 * Production keeps wrangler AI_MODE / CFBD_OFFLINE.
 * Every other hostname defaults to stub + offline unless PREVIEW_* is set.
 */
export function resolveContainerModes(
	env: CapEnv,
	hostname: string,
): { AI_MODE: string; CFBD_OFFLINE: string } {
	if (!isNonProductionHostname(hostname)) {
		return {
			AI_MODE: env.AI_MODE?.trim() || 'live',
			CFBD_OFFLINE: env.CFBD_OFFLINE?.trim() || '0',
		};
	}
	const previewAi = env.PREVIEW_AI_MODE?.trim();
	const previewOffline = env.PREVIEW_CFBD_OFFLINE?.trim();
	return {
		AI_MODE: previewAi || 'stub',
		CFBD_OFFLINE: previewOffline || '1',
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
		AI_MAX_CALLS: String(dailyLimitFor('ai', env)),
		CFBD_MAX_CALLS: String(dailyLimitFor('cfbd', env)),
		AI_KILL: isKillSwitch(env.AI_KILL) ? '1' : '0',
		CFBD_KILL: isKillSwitch(env.CFBD_KILL) ? '1' : '0',
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
): Promise<{ limited: boolean; ip: string; code: string }> {
	const ip = clientIp(request);
	const path = new URL(request.url).pathname;
	const agentRoute = path.startsWith('/api/agent');
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

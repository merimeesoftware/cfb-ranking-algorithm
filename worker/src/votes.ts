/**
 * Fan tallies for #177. One SQLite-backed Durable Object per published
 * year-week. Not a Workers KV namespace, and not the Flask container class:
 * this object has no internet, no CFBD client, and no outbound fetch.
 *
 * The raw vote id, name, email, and IP are not stored. The id is a random
 * 128-bit cookie value. The dedupe key is SHA-256(id|year|week|team).
 * There is no extra secret.
 *
 * POST /api/votes stays dark until TURNSTILE_SECRET_KEY is confirmed by name
 * on the production Worker. Nothing here reads that secret unless a caller
 * invokes the vote check, and the Worker entry does not invoke it.
 */
import { DurableObject } from 'cloudflare:workers';
import {
	FORMULA_MESSAGE,
	SITEVERIFY_URL,
	TURNSTILE_HEADER,
	UNPUBLISHED_MESSAGE,
	busyResponse,
	clientIp,
	jsonSecurityHeaders,
	publishedWeeks,
	type Manifest,
	type RateLimiter,
} from './caps.ts';

export const VOTE_COOKIE = '__Host-tr_vote';
/** 180 days. Not longer. */
export const VOTE_COOKIE_MAX_AGE = 180 * 24 * 60 * 60;
export const VOTE_ACTION = 'vote';
export const VOTE_LIMIT_PER_MINUTE = 10;
/** The id, name, email, and IP are not stored. */
export const VOTE_PRIVACY = 'The vote id, name, email, and IP are not stored.';

const COUNT_PREFIX = 'count:';
const MARK_PREFIX = 'mark:';
const VOTE_ID = /^[0-9a-f]{32}$/;
const VOTE_HASH = /^[0-9a-f]{64}$/;

export type VoteMark = 'too_high' | 'too_low';

export interface TeamVotes {
	too_high: number;
	too_low: number;
}

export type VoteMap = Record<string, TeamVotes>;

export interface VoteStorage {
	get<T = unknown>(key: string): Promise<T | undefined>;
	put(key: string, value: string | number): Promise<unknown>;
	list(prefix: string): Promise<Map<string, unknown>>;
}

export interface VoteState {
	storage: VoteStorage;
	blockConcurrencyWhile<T>(callback: () => Promise<T>): Promise<T>;
}

export interface VoteNamespace {
	idFromName(name: string): DurableObjectId;
	get(id: DurableObjectId): DurableObjectStub;
}

function voteState(ctx: DurableObjectState): VoteState {
	return {
		blockConcurrencyWhile: (callback) => ctx.blockConcurrencyWhile(callback),
		storage: {
			get: (key) => ctx.storage.get(key),
			put: (key, value) => ctx.storage.put(key, value),
			list: async (prefix) => ctx.storage.list({ prefix }),
		},
	};
}

export function voteObjectName(year: number, week: number): string {
	return `${year}-w${week}`;
}

function countKey(team: string, mark: VoteMark): string {
	return `${COUNT_PREFIX}${encodeURIComponent(team)}:${mark}`;
}

function markKey(hash: string): string {
	return `${MARK_PREFIX}${hash}`;
}

function emptyRow(): TeamVotes {
	return { too_high: 0, too_low: 0 };
}

export async function readVotes(state: VoteState): Promise<VoteMap> {
	const listed = await state.storage.list(COUNT_PREFIX);
	const votes: VoteMap = {};
	for (const [key, raw] of listed) {
		const rest = key.slice(COUNT_PREFIX.length);
		const split = rest.lastIndexOf(':');
		if (split <= 0) continue;
		const mark = rest.slice(split + 1);
		if (mark !== 'too_high' && mark !== 'too_low') continue;
		let team = rest.slice(0, split);
		try {
			team = decodeURIComponent(team);
		} catch {
			continue;
		}
		const count = typeof raw === 'number' && Number.isFinite(raw) ? raw : 0;
		const row = votes[team] ?? emptyRow();
		row[mark] = count;
		votes[team] = row;
	}
	return votes;
}

async function bump(storage: VoteStorage, key: string, delta: number): Promise<void> {
	const raw = await storage.get<number>(key);
	const current = typeof raw === 'number' && Number.isFinite(raw) ? raw : 0;
	await storage.put(key, Math.max(0, current + delta));
}

/**
 * Dedupe, mark, and count in one serialized request. A second mark from the
 * same hash replaces the first. It does not add a second tally.
 */
export async function applyMark(
	state: VoteState,
	input: { hash: string; team: string; mark: VoteMark },
): Promise<VoteMap> {
	return state.blockConcurrencyWhile(async () => {
		const existing = await state.storage.get<VoteMark>(markKey(input.hash));
		if (existing === input.mark) return readVotes(state);
		if (existing === 'too_high' || existing === 'too_low') {
			await bump(state.storage, countKey(input.team, existing), -1);
		}
		await state.storage.put(markKey(input.hash), input.mark);
		await bump(state.storage, countKey(input.team, input.mark), 1);
		return readVotes(state);
	});
}

export function newVoteId(): string {
	const bytes = crypto.getRandomValues(new Uint8Array(16));
	return [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function voteIdFromCookie(header: string | null): string | null {
	if (!header) return null;
	for (const part of header.split(';')) {
		const text = part.trim();
		const eq = text.indexOf('=');
		if (eq === -1) continue;
		if (text.slice(0, eq).trim() !== VOTE_COOKIE) continue;
		const value = text.slice(eq + 1).trim();
		return VOTE_ID.test(value) ? value : null;
	}
	return null;
}

export function voteSetCookie(id: string): string {
	return `${VOTE_COOKIE}=${id}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${VOTE_COOKIE_MAX_AGE}`;
}

/** SHA-256(id|year|week|team). The id is the only secret material, and it is not stored. */
export async function voteDedupeHash(
	id: string,
	year: number,
	week: number,
	team: string,
): Promise<string> {
	const bytes = new TextEncoder().encode(`${id}|${year}|${week}|${team}`);
	const digest = await crypto.subtle.digest('SHA-256', bytes);
	return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export type VoteTurnstileReason = 'secret' | 'token' | 'siteverify' | 'success' | 'hostname' | 'action';

export async function voteTurnstile(input: {
	secret: string | undefined;
	token: string | undefined;
	ip: string;
	hostname: string;
	siteverify?: typeof fetch;
}): Promise<{ ok: true } | { ok: false; reason: VoteTurnstileReason }> {
	const secret = (input.secret ?? '').trim();
	if (!secret) return { ok: false, reason: 'secret' };
	const token = (input.token ?? '').trim();
	if (!token) return { ok: false, reason: 'token' };
	const siteverify = input.siteverify ?? fetch;
	let response: Response;
	try {
		response = await siteverify(SITEVERIFY_URL, {
			method: 'POST',
			headers: { 'content-type': 'application/x-www-form-urlencoded' },
			body: new URLSearchParams({
				secret,
				response: token,
				remoteip: input.ip,
			}),
		});
	} catch {
		return { ok: false, reason: 'siteverify' };
	}
	if (!response.ok) return { ok: false, reason: 'siteverify' };
	try {
		const payload = await response.json() as {
			success?: unknown;
			hostname?: unknown;
			action?: unknown;
		};
		if (payload.success !== true) return { ok: false, reason: 'success' };
		if (payload.hostname !== input.hostname) return { ok: false, reason: 'hostname' };
		if (payload.action !== VOTE_ACTION) return { ok: false, reason: 'action' };
		return { ok: true };
	} catch {
		return { ok: false, reason: 'siteverify' };
	}
}

export function originAllowed(request: Request): boolean {
	const origin = request.headers.get('origin');
	if (!origin) return false;
	return origin === new URL(request.url).origin;
}

export async function enforceVoteLimit(limiter: RateLimiter, ip: string): Promise<Response | null> {
	const result = await limiter.limit({ key: ip });
	if (!result.success) return busyResponse('vote_rate_limit');
	return null;
}

function voteJson(body: Record<string, unknown>, status: number, cookie?: string): Response {
	const headers = jsonSecurityHeaders();
	if (cookie) headers.append('set-cookie', cookie);
	return Response.json(body, { status, headers });
}

function readQueryInt(params: URLSearchParams, name: string): { present: boolean; value: number | null } {
	if (!params.has(name)) return { present: false, value: null };
	const raw = (params.get(name) ?? '').trim();
	if (!/^-?\d+$/.test(raw)) return { present: true, value: null };
	return { present: true, value: Number(raw) };
}

export function publishedVoteWeek(manifest: Manifest, year: number, week: number): boolean {
	return publishedWeeks(manifest, year).includes(week);
}

function unpublished(year: number, week: number): Response {
	return voteJson({
		published: false,
		busy: false,
		message: UNPUBLISHED_MESSAGE,
		code: 'not_published',
		year,
		week,
	}, 200);
}

/** Public counts for one published week. Missing storage returns an empty zero map. */
export async function handleVoteGet(
	params: URLSearchParams,
	manifest: Manifest,
	namespace: VoteNamespace,
): Promise<Response> {
	const rejected: string[] = [];
	for (const key of params.keys()) {
		if (key !== 'year' && key !== 'week') rejected.push(key);
	}
	if (rejected.length) {
		return voteJson({
			error: FORMULA_MESSAGE,
			code: 'formula_params',
			rejected,
		}, 400);
	}
	const year = readQueryInt(params, 'year');
	const week = readQueryInt(params, 'week');
	if (!year.present || !week.present) {
		return voteJson({ error: 'year and week are required.', code: 'missing_week' }, 400);
	}
	if (year.value === null) return voteJson({ error: 'year must be an integer.', code: 'bad_year' }, 400);
	if (week.value === null) return voteJson({ error: 'week must be an integer.', code: 'bad_week' }, 400);
	if (!publishedVoteWeek(manifest, year.value, week.value)) return unpublished(year.value, week.value);
	const stub = namespace.get(namespace.idFromName(voteObjectName(year.value, week.value)));
	const stored = await stub.fetch(new Request('https://fan-votes.internal/counts'));
	const payload = await stored.json() as { votes?: VoteMap };
	return voteJson({
		year: year.value,
		week: week.value,
		votes: payload.votes ?? {},
	}, 200);
}

interface MarkRequest {
	hash: string;
	team: string;
	mark: VoteMark;
}

function parseStoredMark(raw: unknown): MarkRequest | null {
	if (!raw || typeof raw !== 'object') return null;
	const body = raw as Record<string, unknown>;
	if (typeof body.hash !== 'string' || !VOTE_HASH.test(body.hash)) return null;
	if (typeof body.team !== 'string' || body.team.trim() === '') return null;
	if (body.mark !== 'too_high' && body.mark !== 'too_low') return null;
	return { hash: body.hash, team: body.team, mark: body.mark };
}

/**
 * SQLite-backed tally. The public Worker does not call the mark path while
 * POST /api/votes is dark. GET /counts is the read.
 */
export class FanVoteTally extends DurableObject {
	async fetch(request: Request): Promise<Response> {
		const state = voteState(this.ctx);
		if (request.method === 'GET') {
			return voteJson({ votes: await readVotes(state) }, 200);
		}
		if (request.method !== 'POST') return voteJson({ ok: false }, 405);
		let raw: unknown = null;
		try {
			raw = await request.json();
		} catch {
			return voteJson({ ok: false, error: 'json' }, 400);
		}
		const parsed = parseStoredMark(raw);
		if (!parsed) return voteJson({ ok: false, error: 'json' }, 400);
		const votes = await applyMark(state, parsed);
		const row = votes[parsed.team] ?? emptyRow();
		return voteJson({
			votes,
			team: parsed.team,
			your_mark: parsed.mark,
			too_high: row.too_high,
			too_low: row.too_low,
		}, 200);
	}
}

interface PublicMark {
	year: number;
	week: number;
	team: string;
	mark: VoteMark;
}

function parsePublicMark(raw: unknown): PublicMark | null {
	if (!raw || typeof raw !== 'object') return null;
	const body = raw as Record<string, unknown>;
	if (typeof body.team !== 'string' || body.team.trim() === '') return null;
	if (body.mark !== 'too_high' && body.mark !== 'too_low') return null;
	if (typeof body.year !== 'number' || !Number.isInteger(body.year)) return null;
	if (typeof body.week !== 'number' || !Number.isInteger(body.week)) return null;
	return { year: body.year, week: body.week, team: body.team, mark: body.mark };
}

export interface VotePostEnv {
	TURNSTILE_SECRET_KEY?: string;
	VOTE_RATE_LIMITER: RateLimiter;
	FAN_VOTES: VoteNamespace;
}

/**
 * Mark handler. Not mounted. POST /api/votes stays dark until the Turnstile
 * secret is confirmed by name. The id and the IP are not stored.
 */
export async function handleVotePost(
	request: Request,
	env: VotePostEnv,
	manifest: Manifest,
	teams: ReadonlySet<string>,
	siteverify?: typeof fetch,
): Promise<Response> {
	if (!originAllowed(request)) return voteJson({ ok: false, code: 'origin' }, 403);
	const limited = await enforceVoteLimit(env.VOTE_RATE_LIMITER, clientIp(request));
	if (limited) return limited;
	const decision = await voteTurnstile({
		secret: env.TURNSTILE_SECRET_KEY,
		token: request.headers.get(TURNSTILE_HEADER) ?? '',
		ip: clientIp(request),
		hostname: new URL(request.url).hostname,
		siteverify,
	});
	if (!decision.ok) return voteJson({ ok: false, code: 'vote_turnstile', reason: decision.reason }, 403);
	let raw: unknown = null;
	try {
		raw = await request.json();
	} catch {
		return voteJson({ ok: false, error: 'json' }, 400);
	}
	const parsed = parsePublicMark(raw);
	if (!parsed) return voteJson({ ok: false, error: 'json' }, 400);
	if (!publishedVoteWeek(manifest, parsed.year, parsed.week)) return unpublished(parsed.year, parsed.week);
	if (!teams.has(parsed.team)) return voteJson({ ok: false, code: 'unknown_team' }, 400);
	const existingId = voteIdFromCookie(request.headers.get('cookie'));
	const id = existingId ?? newVoteId();
	const hash = await voteDedupeHash(id, parsed.year, parsed.week, parsed.team);
	const stub = env.FAN_VOTES.get(env.FAN_VOTES.idFromName(voteObjectName(parsed.year, parsed.week)));
	const stored = await stub.fetch(new Request('https://fan-votes.internal/mark', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ hash, team: parsed.team, mark: parsed.mark }),
	}));
	const payload = await stored.json() as {
		your_mark?: VoteMark;
		too_high?: number;
		too_low?: number;
	};
	return voteJson({
		year: parsed.year,
		week: parsed.week,
		team: parsed.team,
		your_mark: payload.your_mark ?? parsed.mark,
		too_high: payload.too_high ?? 0,
		too_low: payload.too_low ?? 0,
		privacy: VOTE_PRIVACY,
	}, 200, existingId ? undefined : voteSetCookie(id));
}
